#!/usr/bin/env python3
"""
Module 2: Data Cleaning & Quality Assessment (clean_data.py)
Audits raw Synthea CSV exports against 8 clinical data quality rules, logs pre- and post-remediation
counts in reports/data_quality_report.csv, and writes cleaned CSV files to data/processed/.
"""

import os
import pandas as pd
import numpy as np


def clean_and_validate_data(raw_dir: str, processed_dir: str, report_path: str) -> pd.DataFrame:
    """Runs reproducible data cleaning and produces data_quality_report.csv."""
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    patients = pd.read_csv(os.path.join(raw_dir, "patients.csv"), dtype=str).fillna("")
    encounters = pd.read_csv(os.path.join(raw_dir, "encounters.csv"), dtype=str).fillna("")
    conditions = pd.read_csv(os.path.join(raw_dir, "conditions.csv"), dtype=str).fillna("")
    observations = pd.read_csv(os.path.join(raw_dir, "observations.csv"), dtype=str).fillna("")
    medications = pd.read_csv(os.path.join(raw_dir, "medications.csv"), dtype=str).fillna("")
    procedures = pd.read_csv(os.path.join(raw_dir, "procedures.csv"), dtype=str).fillna("")
    organizations = pd.read_csv(os.path.join(raw_dir, "organizations.csv"), dtype=str).fillna("")
    providers = pd.read_csv(os.path.join(raw_dir, "providers.csv"), dtype=str).fillna("")

    quality_rows = []

    # 1. Check duplicate patient IDs
    dup_pat_before = int(patients.duplicated(subset=["Id"]).sum())
    patients = patients.drop_duplicates(subset=["Id"], keep="first").copy()
    dup_pat_after = int(patients.duplicated(subset=["Id"]).sum())
    quality_rows.append({
        "check_id": "DQ-01",
        "table_name": "patients",
        "quality_check": "Duplicate patient IDs",
        "issues_detected_raw": dup_pat_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": dup_pat_after,
        "status": "PASS" if dup_pat_after == 0 else "FAIL",
        "remediation_policy": "Deduplicate on primary key Id (keep first occurrence) to maintain unique entity grain."
    })

    # 2. Check invalid or inconsistent demographic values (GENDER & ZIP)
    gender_map = {"M": "M", "MALE": "M", "F": "F", "FEMALE": "F"}
    invalid_gender_before = int((~patients["GENDER"].isin(["M", "F"])).sum())
    patients["GENDER"] = patients["GENDER"].str.strip().str.upper().map(lambda x: gender_map.get(x, "U"))
    # Impute any 'U' deterministically based on prefix Ms./Mr. or default F
    patients.loc[patients["GENDER"] == "U", "GENDER"] = np.where(
        patients.loc[patients["GENDER"] == "U", "PREFIX"] == "Mr.", "M", "F"
    )
    invalid_gender_after = int((~patients["GENDER"].isin(["M", "F"])).sum())
    quality_rows.append({
        "check_id": "DQ-02",
        "table_name": "patients",
        "quality_check": "Invalid or unstandardized demographic gender values",
        "issues_detected_raw": invalid_gender_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": invalid_gender_after,
        "status": "PASS" if invalid_gender_after == 0 else "FAIL",
        "remediation_policy": "Standardize case/labels ('male'->'M', 'female'->'F') and infer missing gender from prefix."
    })

    # 3. Missing ZIP codes & legitimate nulls (DEATHDATE, STOP)
    missing_zip_before = int((patients["ZIP"] == "").sum())
    patients["ZIP"] = patients["ZIP"].replace("", "00000")
    missing_zip_after = int((patients["ZIP"] == "").sum())
    quality_rows.append({
        "check_id": "DQ-03",
        "table_name": "patients",
        "quality_check": "Missing patient ZIP codes (Synthea Issue #421)",
        "issues_detected_raw": missing_zip_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": missing_zip_after,
        "status": "PASS" if missing_zip_after == 0 else "FAIL",
        "remediation_policy": "Impute missing ZIP with '00000' rather than deleting valid patients; preserve blank DEATHDATE for living patients."
    })

    # 4. Check duplicate encounter IDs
    dup_enc_before = int(encounters.duplicated(subset=["Id"]).sum())
    encounters = encounters.drop_duplicates(subset=["Id"], keep="first").copy()
    dup_enc_after = int(encounters.duplicated(subset=["Id"]).sum())
    quality_rows.append({
        "check_id": "DQ-04",
        "table_name": "encounters",
        "quality_check": "Duplicate encounter IDs",
        "issues_detected_raw": dup_enc_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": dup_enc_after,
        "status": "PASS" if dup_enc_after == 0 else "FAIL",
        "remediation_policy": "Deduplicate on Encounter Id (keep first occurrence)."
    })

    # 5. Missing patient IDs on encounters
    miss_pat_before = int((encounters["PATIENT"].str.strip() == "").sum())
    encounters = encounters[encounters["PATIENT"].str.strip() != ""].copy()
    miss_pat_after = int((encounters["PATIENT"].str.strip() == "").sum())
    quality_rows.append({
        "check_id": "DQ-05",
        "table_name": "encounters",
        "quality_check": "Missing patient IDs in encounters",
        "issues_detected_raw": miss_pat_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": miss_pat_after,
        "status": "PASS" if miss_pat_after == 0 else "FAIL",
        "remediation_policy": "Quarantine and remove encounter rows missing foreign key PATIENT identifier."
    })

    # 6. Orphan encounter records referencing nonexistent patients
    valid_pat_ids = set(patients["Id"])
    orphan_enc_before = int((~encounters["PATIENT"].isin(valid_pat_ids)).sum())
    encounters = encounters[encounters["PATIENT"].isin(valid_pat_ids)].copy()
    orphan_enc_after = int((~encounters["PATIENT"].isin(valid_pat_ids)).sum())
    quality_rows.append({
        "check_id": "DQ-06",
        "table_name": "encounters",
        "quality_check": "Orphan encounter records (nonexistent patient reference)",
        "issues_detected_raw": orphan_enc_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": orphan_enc_after,
        "status": "PASS" if orphan_enc_after == 0 else "FAIL",
        "remediation_policy": "Enforce referential integrity against dim_patient; remove orphan encounters."
    })

    # 7. Invalid date sequences (encounter STOP < START)
    start_dt = pd.to_datetime(encounters["START"], utc=True)
    stop_dt = pd.to_datetime(encounters["STOP"], utc=True)
    inv_date_mask = stop_dt < start_dt
    inv_date_before = int(inv_date_mask.sum())
    # Swap inverted timestamps rather than discarding clinical visits
    encounters.loc[inv_date_mask, ["START", "STOP"]] = encounters.loc[inv_date_mask, ["STOP", "START"]].values
    start_dt_new = pd.to_datetime(encounters["START"], utc=True)
    stop_dt_new = pd.to_datetime(encounters["STOP"], utc=True)
    inv_date_after = int((stop_dt_new < start_dt_new).sum())
    quality_rows.append({
        "check_id": "DQ-07",
        "table_name": "encounters",
        "quality_check": "Invalid date sequences (encounter end precedes start)",
        "issues_detected_raw": inv_date_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": inv_date_after,
        "status": "PASS" if inv_date_after == 0 else "FAIL",
        "remediation_policy": "Swap inverted START and STOP timestamps to preserve valid encounter volume and duration."
    })

    # 8. Duplicate diagnosis records in conditions.csv
    valid_enc_ids = set(encounters["Id"])
    conditions = conditions[conditions["PATIENT"].isin(valid_pat_ids) & conditions["ENCOUNTER"].isin(valid_enc_ids)].copy()
    dup_cond_before = int(conditions.duplicated(subset=["PATIENT", "ENCOUNTER", "CODE", "START"]).sum())
    conditions = conditions.drop_duplicates(subset=["PATIENT", "ENCOUNTER", "CODE", "START"], keep="first").copy()
    dup_cond_after = int(conditions.duplicated(subset=["PATIENT", "ENCOUNTER", "CODE", "START"]).sum())
    quality_rows.append({
        "check_id": "DQ-08",
        "table_name": "conditions",
        "quality_check": "Duplicate diagnosis records (same patient, encounter, code, start)",
        "issues_detected_raw": dup_cond_before,
        "expected_after_cleaning": 0,
        "issues_remaining_cleaned": dup_cond_after,
        "status": "PASS" if dup_cond_after == 0 else "FAIL",
        "remediation_policy": "Deduplicate composite key (PATIENT, ENCOUNTER, CODE, START)."
    })

    # 9. Observations without encounter reference (Quality-of-Life survey metrics QALY/DALY/QOLS)
    observations = observations[observations["PATIENT"].isin(valid_pat_ids)].copy()
    unlinked_obs_before = int((observations["ENCOUNTER"] == "").sum())
    observations["IS_QOL_UNLINKED"] = np.where(observations["ENCOUNTER"] == "", 1, 0)
    # Dual-value separation: numeric vs text
    observations["VALUE_NUMERIC"] = pd.to_numeric(observations["VALUE"], errors="coerce")
    observations["VALUE_TEXT"] = np.where(observations["TYPE"] == "text", observations["VALUE"], "")
    quality_rows.append({
        "check_id": "DQ-09",
        "table_name": "observations",
        "quality_check": "Observations lacking Encounter ID (Synthea QALY/DALY/QOLS survey records)",
        "issues_detected_raw": unlinked_obs_before,
        "expected_after_cleaning": unlinked_obs_before,
        "issues_remaining_cleaned": unlinked_obs_before,
        "status": "PASS (DOCUMENTED)",
        "remediation_policy": "Retain with nullable encounter_id and flag IS_QOL_UNLINKED=1; split VALUE into VALUE_NUMERIC and VALUE_TEXT."
    })

    # Filter medications and procedures for referential integrity
    medications = medications[medications["PATIENT"].isin(valid_pat_ids) & medications["ENCOUNTER"].isin(valid_enc_ids)].copy()
    procedures = procedures[procedures["PATIENT"].isin(valid_pat_ids) & procedures["ENCOUNTER"].isin(valid_enc_ids)].copy()

    # Save cleaned datasets
    patients.to_csv(os.path.join(processed_dir, "patients_clean.csv"), index=False)
    encounters.to_csv(os.path.join(processed_dir, "encounters_clean.csv"), index=False)
    conditions.to_csv(os.path.join(processed_dir, "conditions_clean.csv"), index=False)
    observations.to_csv(os.path.join(processed_dir, "observations_clean.csv"), index=False)
    medications.to_csv(os.path.join(processed_dir, "medications_clean.csv"), index=False)
    procedures.to_csv(os.path.join(processed_dir, "procedures_clean.csv"), index=False)
    organizations.to_csv(os.path.join(processed_dir, "organizations_clean.csv"), index=False)
    providers.to_csv(os.path.join(processed_dir, "providers_clean.csv"), index=False)

    dq_df = pd.DataFrame(quality_rows)
    dq_df.to_csv(report_path, index=False)
    return dq_df


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dq = clean_and_validate_data(
        os.path.join(repo_root, "data", "raw"),
        os.path.join(repo_root, "data", "processed"),
        os.path.join(repo_root, "reports", "data_quality_report.csv")
    )
    print(dq.to_string(index=False))
