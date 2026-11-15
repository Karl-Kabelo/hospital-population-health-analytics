#!/usr/bin/env python3
"""
Module 3: Dimensional Star Schema Transformation (transform_data.py)
Transforms cleaned Synthea tables into star-schema dimensions and facts:
dim_patient, dim_organization, dim_provider, dim_date, fact_encounter,
fact_condition, fact_observation, fact_medication.
"""

import os
import pandas as pd
import numpy as np


def assign_age_group(age: float) -> str:
    if age < 18:
        return "0-17 (Pediatric)"
    elif age < 35:
        return "18-34 (Young Adult)"
    elif age < 50:
        return "35-49 (Adult)"
    elif age < 65:
        return "50-64 (Middle-Aged)"
    else:
        return "65+ (Senior)"


def transform_to_star_schema(processed_dir: str) -> dict:
    """Builds star schema DataFrames from cleaned CSVs and saves them in processed_dir."""
    patients = pd.read_csv(os.path.join(processed_dir, "patients_clean.csv"), dtype=str).fillna("")
    encounters = pd.read_csv(os.path.join(processed_dir, "encounters_clean.csv"), dtype=str).fillna("")
    conditions = pd.read_csv(os.path.join(processed_dir, "conditions_clean.csv"), dtype=str).fillna("")
    observations = pd.read_csv(os.path.join(processed_dir, "observations_clean.csv"), dtype=str).fillna("")
    medications = pd.read_csv(os.path.join(processed_dir, "medications_clean.csv"), dtype=str).fillna("")
    organizations = pd.read_csv(os.path.join(processed_dir, "organizations_clean.csv"), dtype=str).fillna("")
    providers = pd.read_csv(os.path.join(processed_dir, "providers_clean.csv"), dtype=str).fillna("")

    ref_date = pd.Timestamp("2025-12-31")
    bdate = pd.to_datetime(patients["BIRTHDATE"])
    ddate = pd.to_datetime(patients["DEATHDATE"], errors="coerce")
    eff_end = ddate.fillna(ref_date)
    age_years = ((eff_end - bdate).dt.days / 365.25).round(1)

    # 1. dim_patient
    dim_patient = pd.DataFrame({
        "patient_id": patients["Id"],
        "first_name": patients["FIRST"],
        "last_name": patients["LAST"],
        "full_name": patients["FIRST"] + " " + patients["LAST"],
        "birthdate": patients["BIRTHDATE"],
        "deathdate": patients["DEATHDATE"].replace("", None),
        "is_deceased": np.where(patients["DEATHDATE"] != "", 1, 0),
        "age_years": age_years,
        "age_group": [assign_age_group(a) for a in age_years],
        "gender": patients["GENDER"],
        "race": patients["RACE"],
        "ethnicity": patients["ETHNICITY"],
        "marital_status": patients["MARITAL"].replace("", "U"),
        "city": patients["CITY"],
        "state": patients["STATE"],
        "county": patients["COUNTY"],
        "zip": patients["ZIP"],
        "healthcare_expenses": pd.to_numeric(patients["HEALTHCARE_EXPENSES"], errors="coerce").fillna(0.0),
        "healthcare_coverage": pd.to_numeric(patients["HEALTHCARE_COVERAGE"], errors="coerce").fillna(0.0),
    })

    # 2. dim_organization
    dim_organization = pd.DataFrame({
        "organization_id": organizations["Id"],
        "organization_name": organizations["NAME"],
        "address": organizations["ADDRESS"],
        "city": organizations["CITY"],
        "state": organizations["STATE"],
        "zip": organizations["ZIP"],
        "lat": pd.to_numeric(organizations["LAT"], errors="coerce"),
        "lon": pd.to_numeric(organizations["LON"], errors="coerce"),
        "phone": organizations["PHONE"],
        "revenue": pd.to_numeric(organizations["REVENUE"], errors="coerce").fillna(0.0),
    })

    # 3. dim_provider
    dim_provider = pd.DataFrame({
        "provider_id": providers["Id"],
        "organization_id": providers["ORGANIZATION"],
        "provider_name": providers["NAME"],
        "gender": providers["GENDER"],
        "speciality": providers["SPECIALITY"],
        "city": providers["CITY"],
        "state": providers["STATE"],
    })

    # 4. dim_date (Calendar dimension covering 2024-01-01 to 2025-12-31)
    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    dim_date = pd.DataFrame({
        "date_key": dates.strftime("%Y%m%d").astype(int),
        "full_date": dates.strftime("%Y-%m-%d"),
        "year": dates.year,
        "quarter": dates.quarter,
        "year_quarter": dates.strftime("%Y-Q") + dates.quarter.astype(str),
        "month": dates.month,
        "month_name": dates.strftime("%B"),
        "year_month": dates.strftime("%Y-%m"),
        "day_of_week": dates.dayofweek + 1,
        "day_name": dates.strftime("%A"),
        "is_weekend": np.where(dates.dayofweek >= 5, 1, 0),
    })

    # 5. fact_encounter (including length of stay and 30-day inpatient readmission flag)
    start_ts = pd.to_datetime(encounters["START"], utc=True)
    stop_ts = pd.to_datetime(encounters["STOP"], utc=True)
    los_hours = ((stop_ts - start_ts).dt.total_seconds() / 3600.0).round(2)
    los_days = (los_hours / 24.0).round(2)

    fact_encounter = pd.DataFrame({
        "encounter_id": encounters["Id"],
        "patient_id": encounters["PATIENT"],
        "organization_id": encounters["ORGANIZATION"],
        "provider_id": encounters["PROVIDER"],
        "date_key": start_ts.dt.strftime("%Y%m%d").astype(int),
        "start_timestamp": encounters["START"],
        "stop_timestamp": encounters["STOP"],
        "encounter_date": start_ts.dt.strftime("%Y-%m-%d"),
        "encounter_class": encounters["ENCOUNTERCLASS"],
        "code": encounters["CODE"],
        "description": encounters["DESCRIPTION"],
        "los_hours": los_hours,
        "los_days": los_days,
        "is_emergency": np.where(encounters["ENCOUNTERCLASS"] == "emergency", 1, 0),
        "is_inpatient": np.where(encounters["ENCOUNTERCLASS"] == "inpatient", 1, 0),
        "base_encounter_cost": pd.to_numeric(encounters["BASE_ENCOUNTER_COST"], errors="coerce").fillna(0.0),
        "total_claim_cost": pd.to_numeric(encounters["TOTAL_CLAIM_COST"], errors="coerce").fillna(0.0),
        "payer_coverage": pd.to_numeric(encounters["PAYER_COVERAGE"], errors="coerce").fillna(0.0),
        "reason_code": encounters["REASONCODE"].replace("", None),
        "reason_description": encounters["REASONDESCRIPTION"].replace("", None),
    })

    # Compute 30-day inpatient readmission flag: whether an inpatient admission is followed by
    # another inpatient admission for the same patient within 30 days of discharge
    fact_encounter = fact_encounter.sort_values(["patient_id", "start_timestamp"]).reset_index(drop=True)
    inpat = fact_encounter[fact_encounter["is_inpatient"] == 1].copy()
    inpat["start_dt"] = pd.to_datetime(inpat["start_timestamp"], utc=True)
    inpat["stop_dt"] = pd.to_datetime(inpat["stop_timestamp"], utc=True)
    inpat["next_inpat_start"] = inpat.groupby("patient_id")["start_dt"].shift(-1)
    inpat["days_to_next_inpat"] = (inpat["next_inpat_start"] - inpat["stop_dt"]).dt.total_seconds() / 86400.0
    readm_ids = set(inpat.loc[(inpat["days_to_next_inpat"] >= 0) & (inpat["days_to_next_inpat"] <= 30.0), "encounter_id"])
    fact_encounter["is_30d_readmission_index"] = np.where(fact_encounter["encounter_id"].isin(readm_ids), 1, 0)

    # 6. fact_condition
    chronic_codes = {
        "59621000", "44054006", "15777000", "162864005", "233678006",
        "195967001", "53741008", "431855005", "84114007", "396275006"
    }
    cond_start = pd.to_datetime(conditions["START"])
    fact_condition = pd.DataFrame({
        "condition_id": range(1, len(conditions) + 1),
        "patient_id": conditions["PATIENT"],
        "encounter_id": conditions["ENCOUNTER"],
        "date_key": cond_start.dt.strftime("%Y%m%d").astype(int),
        "start_date": conditions["START"],
        "stop_date": conditions["STOP"].replace("", None),
        "code": conditions["CODE"],
        "description": conditions["DESCRIPTION"],
        "is_chronic": np.where(conditions["CODE"].isin(chronic_codes) | (conditions["STOP"] == ""), 1, 0),
    })

    # 7. fact_observation
    obs_dt = pd.to_datetime(observations["DATE"], utc=True)
    fact_observation = pd.DataFrame({
        "observation_id": range(1, len(observations) + 1),
        "patient_id": observations["PATIENT"],
        "encounter_id": observations["ENCOUNTER"].replace("", None),
        "date_key": obs_dt.dt.strftime("%Y%m%d").astype(int),
        "observation_date": obs_dt.dt.strftime("%Y-%m-%d"),
        "category": observations["CATEGORY"],
        "code": observations["CODE"],
        "description": observations["DESCRIPTION"],
        "value_raw": observations["VALUE"],
        "value_numeric": pd.to_numeric(observations["VALUE_NUMERIC"], errors="coerce"),
        "value_text": observations["VALUE_TEXT"].replace("", None),
        "units": observations["UNITS"].replace("", None),
        "value_type": observations["TYPE"],
        "is_qol_unlinked": pd.to_numeric(observations["IS_QOL_UNLINKED"], errors="coerce").fillna(0).astype(int),
    })

    # 8. fact_medication
    med_dt = pd.to_datetime(medications["START"], utc=True)
    fact_medication = pd.DataFrame({
        "medication_id": range(1, len(medications) + 1),
        "patient_id": medications["PATIENT"],
        "encounter_id": medications["ENCOUNTER"],
        "date_key": med_dt.dt.strftime("%Y%m%d").astype(int),
        "start_date": med_dt.dt.strftime("%Y-%m-%d"),
        "stop_date": medications["STOP"].replace("", None),
        "code": medications["CODE"],
        "description": medications["DESCRIPTION"],
        "base_cost": pd.to_numeric(medications["BASE_COST"], errors="coerce").fillna(0.0),
        "payer_coverage": pd.to_numeric(medications["PAYER_COVERAGE"], errors="coerce").fillna(0.0),
        "dispenses": pd.to_numeric(medications["DISPENSES"], errors="coerce").fillna(1).astype(int),
        "total_cost": pd.to_numeric(medications["TOTALCOST"], errors="coerce").fillna(0.0),
        "reason_code": medications["REASONCODE"].replace("", None),
        "reason_description": medications["REASONDESCRIPTION"].replace("", None),
    })

    star_tables = {
        "dim_patient": dim_patient,
        "dim_organization": dim_organization,
        "dim_provider": dim_provider,
        "dim_date": dim_date,
        "fact_encounter": fact_encounter,
        "fact_condition": fact_condition,
        "fact_observation": fact_observation,
        "fact_medication": fact_medication,
    }
    for t_name, df in star_tables.items():
        df.to_csv(os.path.join(processed_dir, f"{t_name}.csv"), index=False)

    return star_tables


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    star = transform_to_star_schema(os.path.join(repo_root, "data", "processed"))
    print("Transformed Star Schema tables:", {k: len(v) for k, v in star.items()})
