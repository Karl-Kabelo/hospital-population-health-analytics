#!/usr/bin/env python3
"""
Module 1: Data Acquisition & Synthea Synthetic Dataset Generation (extract_data.py)
Generates realistic Synthea-formatted CSV exports (patients, encounters, conditions,
observations, medications, procedures, organizations, providers) with controlled
edge cases for Module 2 Data Quality Validation.

Reference: https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary
"""

import os
import uuid
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def deterministic_uuid(prefix: str, idx: int) -> str:
    """Generates a deterministic UUID v5-style string for reproducible Synthea IDs."""
    ns = uuid.UUID("12345678-1234-5678-1234-567812345678")
    return str(uuid.uuid5(ns, f"{prefix}_{idx}"))


def generate_synthea_raw_data(raw_dir: str, n_patients: int = 500, seed: int = 42) -> dict:
    """Generates 8 core Synthea CSV files in raw_dir with realistic distributions and seeded anomalies."""
    random.seed(seed)
    np.random.seed(seed)
    os.makedirs(raw_dir, exist_ok=True)

    # 1. ORGANIZATIONS (6 healthcare facilities)
    orgs_spec = [
        ("Massachusetts General Regional Hospital", "55 Fruit St", "Boston", "MA", "02114", 42.3626, -71.0686, "617-726-2000", 0.30),
        ("Cambridge Health Alliance Medical Center", "1493 Cambridge St", "Cambridge", "MA", "02139", 42.3744, -71.1042, "617-665-1000", 0.22),
        ("Worcester Memorial Medical Center", "119 Belmont St", "Worcester", "MA", "01605", 42.2775, -71.7621, "508-334-1000", 0.18),
        ("Springfield Community Valley Hospital", "759 Chestnut St", "Springfield", "MA", "01199", 42.1192, -72.6033, "413-794-0000", 0.13),
        ("Lowell General Urgent & Outpatient Clinic", "295 Varnum Ave", "Lowell", "MA", "01854", 42.6584, -71.3340, "978-937-6000", 0.10),
        ("Quincy South Shore Specialty Center", "100Hc South Shore Rd", "Quincy", "MA", "02169", "42.2487", -71.0023, "617-376-4000", 0.07),
    ]
    organizations = []
    org_weights = []
    for idx, (name, addr, city, state, zip_c, lat, lon, phone, w) in enumerate(orgs_spec, 1):
        org_id = deterministic_uuid("ORG", idx)
        organizations.append({
            "Id": org_id,
            "NAME": name,
            "ADDRESS": addr,
            "CITY": city,
            "STATE": state,
            "ZIP": zip_c,
            "LAT": float(lat),
            "LON": float(lon),
            "PHONE": phone,
            "REVENUE": round(random.uniform(12500000, 98000000), 2),
            "UTILIZATION": 0,
        })
        org_weights.append(w)

    # 2. PROVIDERS (24 clinicians across the 6 organizations)
    specialties = [
        "INTERNAL MEDICINE", "EMERGENCY MEDICINE", "FAMILY PRACTICE",
        "CARDIOLOGY", "ENDOCRINOLOGY", "PULMONOLOGY", "NEPHROLOGY", "GENERAL PRACTICE"
    ]
    first_names_m = ["James", "Robert", "John", "Michael", "David", "William", "Richard", "Thomas", "Charles", "daniel"]
    first_names_f = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

    providers = []
    for idx in range(1, 25):
        p_id = deterministic_uuid("PROV", idx)
        org = organizations[(idx - 1) % len(organizations)]
        gender = "M" if idx % 2 == 0 else "F"
        fname = random.choice(first_names_m if gender == "M" else first_names_f).title()
        lname = random.choice(last_names)
        providers.append({
            "Id": p_id,
            "ORGANIZATION": org["Id"],
            "NAME": f"Dr. {fname} {lname}",
            "GENDER": gender,
            "SPECIALITY": specialties[(idx - 1) % len(specialties)],
            "ADDRESS": org["ADDRESS"],
            "CITY": org["CITY"],
            "STATE": org["STATE"],
            "ZIP": org["ZIP"],
            "LAT": org["LAT"],
            "LON": org["LON"],
            "UTILIZATION": 0,
        })

    # 3. PATIENTS (500 unique synthetic patients + 4 seeded duplicate rows = 504 raw rows)
    ma_cities = [
        ("Boston", "Suffolk County", "02115", 42.34, -71.09),
        ("Cambridge", "Middlesex County", "02139", 42.37, -71.11),
        ("Worcester", "Worcester County", "01604", 42.26, -71.80),
        ("Springfield", "Hampden County", "01103", 42.10, -72.59),
        ("Lowell", "Middlesex County", "01852", 42.63, -71.31),
        ("Quincy", "Norfolk County", "02169", 42.25, -71.00),
        ("Somerville", "Middlesex County", "02143", 42.38, -71.10),
        ("Brookline", "Norfolk County", "02445", 42.33, -71.12),
    ]
    races = ["white", "black", "asian", "native", "other"]
    race_w = [0.62, 0.16, 0.11, 0.03, 0.08]
    ethnicities = ["nonhispanic", "hispanic"]
    eth_w = [0.82, 0.18]

    ref_date = datetime(2025, 12, 31)
    patients = []
    patient_meta = {}

    for idx in range(1, n_patients + 1):
        pat_id = deterministic_uuid("PAT", idx)
        # Age distribution: 0-17 (14%), 18-34 (21%), 35-49 (21%), 50-64 (22%), 65+ (22%)
        age_band = np.random.choice(["0-17", "18-34", "35-49", "50-64", "65+"], p=[0.14, 0.21, 0.21, 0.22, 0.22])
        if age_band == "0-17":
            age_yrs = random.randint(1, 17)
        elif age_band == "18-34":
            age_yrs = random.randint(18, 34)
        elif age_band == "35-49":
            age_yrs = random.randint(35, 49)
        elif age_band == "50-64":
            age_yrs = random.randint(50, 64)
        else:
            age_yrs = random.randint(65, 92)

        bdate = ref_date - timedelta(days=int(age_yrs * 365.25 + random.randint(0, 350)))
        # Mortality in ~3.6% of older patients
        ddate_str = ""
        if age_yrs >= 70 and random.random() < 0.15:
            ddate = ref_date - timedelta(days=random.randint(5, 180))
            ddate_str = ddate.strftime("%Y-%m-%d")

        gender = "F" if random.random() < 0.528 else "M"
        fname = random.choice(first_names_f if gender == "F" else first_names_m).title()
        lname = random.choice(last_names)
        city, county, zip_c, lat, lon = random.choice(ma_cities)
        race = np.random.choice(races, p=race_w)
        eth = np.random.choice(ethnicities, p=eth_w)
        marital = "" if age_yrs < 22 else random.choice(["M", "S", "D", "W"])

        # Seeded demographic anomalies on 6 records for Module 2 cleaning
        raw_gender = gender
        raw_zip = zip_c
        if idx in (15, 88):
            raw_gender = "male" if gender == "M" else "female"
        elif idx in (142, 219):
            raw_gender = "f" if gender == "F" else "m"
        elif idx in (305, 412):
            raw_gender = "Unknown"
        if idx in (22, 55, 109, 177, 250, 333, 401, 480):
            raw_zip = ""  # Missing ZIP code as documented in Synthea GitHub Issue #421

        row = {
            "Id": pat_id,
            "BIRTHDATE": bdate.strftime("%Y-%m-%d"),
            "DEATHDATE": ddate_str,
            "SSN": f"999-{random.randint(10,99)}-{random.randint(1000,9999)}",
            "DRIVERS": "" if age_yrs < 17 else f"S999{random.randint(10000,99999)}",
            "PASSPORT": "" if age_yrs < 20 or random.random() < 0.4 else f"X{random.randint(10000000,99999999)}X",
            "PREFIX": "" if age_yrs < 18 else ("Mr." if gender == "M" else "Ms."),
            "FIRST": fname,
            "LAST": lname,
            "SUFFIX": "",
            "MAIDEN": "",
            "MARITAL": marital,
            "RACE": race,
            "ETHNICITY": eth,
            "GENDER": raw_gender,
            "BIRTHPLACE": f"{city}  Massachusetts  US",
            "ADDRESS": f"{random.randint(10, 999)} {random.choice(['Main', 'Oak', 'Washington', 'Beacon', 'Harvard', 'Boylston'])} St",
            "CITY": city,
            "STATE": "Massachusetts",
            "COUNTY": county,
            "ZIP": raw_zip,
            "LAT": round(lat + random.uniform(-0.03, 0.03), 5),
            "LON": round(lon + random.uniform(-0.03, 0.03), 5),
            "HEALTHCARE_EXPENSES": round(random.uniform(2400, 185000), 2),
            "HEALTHCARE_COVERAGE": round(random.uniform(1200, 140000), 2),
        }
        patients.append(row)
        patient_meta[pat_id] = {
            "age": age_yrs,
            "age_band": age_band,
            "gender": gender,
            "city": city,
            "deathdate": ddate_str,
        }

    # Add 4 duplicate patient records for Data Quality detection
    for dup_idx in [10, 45, 120, 299]:
        patients.append(patients[dup_idx].copy())

    # 4. ENCOUNTERS, CONDITIONS, OBSERVATIONS, MEDICATIONS, PROCEDURES
    # Clinical Condition Catalog (SNOMED-CT)
    chronic_catalog = [
        ("59621000", "Essential hypertension (disorder)", True, 0.34),
        ("44054006", "Diabetes mellitus type 2 (disorder)", True, 0.23),
        ("15777000", "Prediabetes (disorder)", True, 0.21),
        ("162864005", "Body mass index 30+ - obesity (finding)", True, 0.25),
        ("233678006", "Childhood asthma (disorder)", True, 0.09),
        ("195967001", "Asthma (disorder)", True, 0.12),
        ("53741008", "Coronary arteriosclerosis (disorder)", True, 0.14),
        ("431855005", "Chronic kidney disease stage 1 (disorder)", True, 0.10),
        ("84114007", "Heart failure (disorder)", True, 0.09),
        ("396275006", "Osteoarthritis of knee (disorder)", True, 0.11),
    ]
    acute_catalog = [
        ("444814009", "Viral sinusitis (disorder)", False),
        ("195662009", "Acute viral pharyngitis (disorder)", False),
        ("10509002", "Acute bronchitis (disorder)", False),
        ("65363002", "Otitis media (disorder)", False),
        ("386661006", "Fever (finding)", False),
        ("43878008", "Streptococcal sore throat (disorder)", False),
        ("233604007", "Pneumonia (disorder)", False),
        ("75498004", "Acute bacterial sinusitis (disorder)", False),
        ("68496003", "Polyp of colon (disorder)", False),
        ("267036007", "Dyspnea (finding)", False),
    ]

    encounter_classes = ["ambulatory", "wellness", "emergency", "urgentcare", "inpatient", "outpatient"]
    class_codes = {
        "ambulatory": ("185345009", "Encounter for symptom (procedure)", 125.00),
        "wellness": ("162673000", "General examination of patient (procedure)", 140.00),
        "emergency": ("50849002", "Emergency room admission (procedure)", 1450.00),
        "urgentcare": ("371883000", "Outpatient procedure (procedure)", 260.00),
        "inpatient": ("32485007", "Hospital admission (procedure)", 4850.00),
        "outpatient": ("185349003", "Encounter for check up (procedure)", 180.00),
    }

    med_catalog = {
        "59621000": ("316049", "Lisinopril 10 MG Oral Tablet", 18.50),
        "44054006": ("860975", "24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet", 24.80),
        "15777000": ("860975", "24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet", 24.80),
        "195967001": ("745679", "200 ACTUAT Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", 64.00),
        "233678006": ("745679", "200 ACTUAT Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", 64.00),
        "53741008": ("259255", "Atorvastatin 80 MG Oral Tablet", 38.20),
        "84114007": ("200801", "Furosemide 40 MG Oral Tablet", 15.40),
        "444814009": ("308182", "Amoxicillin 250 MG / Clavulanate 125 MG Oral Tablet", 32.00),
        "10509002": ("1049630", "Acetaminophen 325 MG Oral Tablet", 9.50),
        "233604007": ("308192", "Azithromycin 250 MG Oral Tablet", 42.00),
    }

    proc_catalog = [
        ("430193006", "Medication Reconciliation (procedure)", 85.00),
        ("710824005", "Assessment of health and social care needs (procedure)", 110.00),
        ("268400002", "Diagnostic超声/Echocardiography (procedure)", 640.00),
        ("168731009", "Standard chest X-ray (procedure)", 320.00),
        ("252160004", "Standard electrocardiogram (procedure)", 215.00),
        ("386053000", "Evaluation procedure (procedure)", 145.00),
        ("410620009", "Well child visit (procedure)", 130.00),
        ("18286008", "General or neuraxial anesthesia (procedure)", 980.00),
    ]

    encounters = []
    conditions = []
    observations = []
    medications = []
    procedures = []

    enc_counter = 0
    start_window = datetime(2024, 1, 1, 8, 0, 0)
    end_window = datetime(2025, 12, 28, 18, 0, 0)
    total_window_days = (end_window - start_window).days

    for pat_idx, (pat_id, meta) in enumerate(patient_meta.items(), 1):
        age = meta["age"]
        # Assign chronic conditions based on age
        pat_chronics = []
        for c_code, c_desc, _, base_prob in chronic_catalog:
            if c_code == "233678006" and age > 17:
                continue
            if c_code in ("59621000", "44054006", "53741008", "431855005", "84114007", "396275006") and age < 22:
                continue
            age_mult = 1.75 if age >= 65 else (1.3 if age >= 50 else (0.85 if age >= 35 else 0.35))
            if random.random() < min(0.78, base_prob * age_mult):
                pat_chronics.append((c_code, c_desc))

        # Determine number of encounters (older & chronic patients have higher utilization)
        if age >= 65 or len(pat_chronics) >= 3:
            n_enc = np.random.choice([1, 2, 3, 4, 5, 6, 8, 10, 12], p=[0.06, 0.12, 0.18, 0.20, 0.16, 0.12, 0.08, 0.05, 0.03])
        elif age >= 50 or len(pat_chronics) >= 1:
            n_enc = np.random.choice([1, 2, 3, 4, 5, 6, 8], p=[0.14, 0.22, 0.24, 0.18, 0.11, 0.07, 0.04])
        else:
            n_enc = np.random.choice([1, 2, 3, 4, 5], p=[0.28, 0.32, 0.22, 0.12, 0.06])

        # Generate encounter dates sorted chronologically
        day_offsets = sorted([random.randint(0, total_window_days) for _ in range(n_enc)])
        # Inject 30-day inpatient readmission pattern for ~16% of inpatient-eligible high-risk patients
        force_inpatient_readm = (age >= 55 and len(pat_chronics) >= 2 and random.random() < 0.28 and n_enc >= 2)
        if force_inpatient_readm:
            day_offsets[1] = min(total_window_days, day_offsets[0] + random.randint(6, 24))
            day_offsets = sorted(day_offsets)

        for e_i, d_off in enumerate(day_offsets):
            enc_counter += 1
            enc_id = deterministic_uuid("ENC", enc_counter)

            # Choose organization and provider
            org_idx = np.random.choice(range(len(organizations)), p=org_weights)
            org = organizations[org_idx]
            org_provs = [p for p in providers if p["ORGANIZATION"] == org["Id"]]
            prov = random.choice(org_provs)

            # Encounter class distribution
            if force_inpatient_readm and e_i in (0, 1):
                e_class = "inpatient"
            else:
                if age >= 65:
                    e_class = np.random.choice(encounter_classes, p=[0.33, 0.17, 0.18, 0.10, 0.13, 0.09])
                elif age >= 50:
                    e_class = np.random.choice(encounter_classes, p=[0.38, 0.21, 0.14, 0.10, 0.08, 0.09])
                else:
                    e_class = np.random.choice(encounter_classes, p=[0.41, 0.27, 0.12, 0.09, 0.03, 0.08])

            enc_start = start_window + timedelta(days=int(d_off), hours=random.randint(0, 14), minutes=random.choice([0, 15, 30, 45]))

            # Duration by encounter class
            if e_class == "inpatient":
                los_hours = random.uniform(48.0, 216.0) * (1.22 if age >= 65 else 1.0)
            elif e_class == "emergency":
                los_hours = random.uniform(2.5, 14.5)
            elif e_class == "urgentcare":
                los_hours = random.uniform(0.75, 3.2)
            elif e_class == "outpatient":
                los_hours = random.uniform(0.6, 2.5)
            elif e_class == "ambulatory":
                los_hours = random.uniform(0.4, 1.5)
            else:  # wellness
                los_hours = random.uniform(0.5, 1.2)

            enc_stop = enc_start + timedelta(hours=los_hours)

            # Seeded anomaly: 5 encounters where STOP precedes START (swapped timestamps)
            if enc_counter in (25, 150, 310, 620, 990):
                raw_start, raw_stop = enc_stop, enc_start
            else:
                raw_start, raw_stop = enc_start, enc_stop

            c_code, c_desc, base_cost = class_codes[e_class]
            total_cost = round(base_cost * (1.0 + (los_hours / 24.0) * 0.45) + random.uniform(20, 380), 2)
            payer_cov = round(total_cost * random.uniform(0.60, 0.88), 2)

            # Primary diagnosis/reason
            if pat_chronics and (e_i == 0 or random.random() < 0.65):
                r_code, r_desc = random.choice(pat_chronics)
            else:
                r_code, r_desc, _ = random.choice(acute_catalog)

            encounters.append({
                "Id": enc_id,
                "START": raw_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "STOP": raw_stop.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "PATIENT": pat_id,
                "ORGANIZATION": org["Id"],
                "PROVIDER": prov["Id"],
                "PAYER": deterministic_uuid("PAYER", (pat_idx % 5) + 1),
                "ENCOUNTERCLASS": e_class,
                "CODE": c_code,
                "DESCRIPTION": c_desc,
                "BASE_ENCOUNTER_COST": base_cost,
                "TOTAL_CLAIM_COST": total_cost,
                "PAYER_COVERAGE": payer_cov,
                "REASONCODE": r_code,
                "REASONDESCRIPTION": r_desc,
            })

            # Record condition on first appearance or acute visit
            is_chronic = any(r_code == cc[0] for cc in chronic_catalog)
            cond_stop = "" if is_chronic else (enc_stop + timedelta(days=random.randint(7, 21))).strftime("%Y-%m-%d")
            conditions.append({
                "START": enc_start.strftime("%Y-%m-%d"),
                "STOP": cond_stop,
                "PATIENT": pat_id,
                "ENCOUNTER": enc_id,
                "CODE": r_code,
                "DESCRIPTION": r_desc,
            })

            # Additional chronic condition logged on initial encounter
            if e_i == 0 and len(pat_chronics) > 1:
                for extra_code, extra_desc in pat_chronics:
                    if extra_code != r_code:
                        conditions.append({
                            "START": enc_start.strftime("%Y-%m-%d"),
                            "STOP": "",
                            "PATIENT": pat_id,
                            "ENCOUNTER": enc_id,
                            "CODE": extra_code,
                            "DESCRIPTION": extra_desc,
                        })

            # Observations (Vitals + Labs + Text Smoking Status)
            has_htn = any(c[0] == "59621000" for c in pat_chronics)
            has_dm = any(c[0] in ("44054006", "15777000") for c in pat_chronics)
            sbp = round(random.gauss(144 if has_htn else 121, 14), 1)
            dbp = round(random.gauss(89 if has_htn else 77, 9), 1)
            bmi = round(random.gauss(31.2 if any(c[0] == "162864005" for c in pat_chronics) else 25.4, 3.8), 1)
            hr = round(random.gauss(78, 11), 0)

            obs_date = enc_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            observations.extend([
                {
                    "DATE": obs_date, "PATIENT": pat_id, "ENCOUNTER": enc_id, "CATEGORY": "vital-signs",
                    "CODE": "8480-6", "DESCRIPTION": "Systolic Blood Pressure",
                    "VALUE": str(sbp), "UNITS": "mm[Hg]", "TYPE": "numeric"
                },
                {
                    "DATE": obs_date, "PATIENT": pat_id, "ENCOUNTER": enc_id, "CATEGORY": "vital-signs",
                    "CODE": "8462-4", "DESCRIPTION": "Diastolic Blood Pressure",
                    "VALUE": str(dbp), "UNITS": "mm[Hg]", "TYPE": "numeric"
                },
                {
                    "DATE": obs_date, "PATIENT": pat_id, "ENCOUNTER": enc_id, "CATEGORY": "vital-signs",
                    "CODE": "39156-5", "DESCRIPTION": "Body mass index (BMI) [Ratio]",
                    "VALUE": str(bmi), "UNITS": "kg/m2", "TYPE": "numeric"
                },
                {
                    "DATE": obs_date, "PATIENT": pat_id, "ENCOUNTER": enc_id, "CATEGORY": "vital-signs",
                    "CODE": "8867-4", "DESCRIPTION": "Heart rate",
                    "VALUE": str(int(hr)), "UNITS": "/min", "TYPE": "numeric"
                },
            ])
            if has_dm or e_class in ("wellness", "inpatient"):
                a1c = round(random.gauss(7.6 if has_dm else 5.4, 0.9), 1)
                observations.append({
                    "DATE": obs_date, "PATIENT": pat_id, "ENCOUNTER": enc_id, "CATEGORY": "laboratory",
                    "CODE": "4548-4", "DESCRIPTION": "Hemoglobin A1c/Hemoglobin.total in Blood",
                    "VALUE": str(a1c), "UNITS": "%", "TYPE": "numeric"
                })
            if e_i == 0:
                smoker_val = np.random.choice(
                    ["Never smoker", "Former smoker", "Current every day smoker"],
                    p=[0.64, 0.24, 0.12]
                )
                observations.append({
                    "DATE": obs_date, "PATIENT": pat_id, "ENCOUNTER": enc_id, "CATEGORY": "social-history",
                    "CODE": "72166-2", "DESCRIPTION": "Tobacco smoking status NHIS",
                    "VALUE": smoker_val, "UNITS": "", "TYPE": "text"
                })

            # Medications if condition has mapped rx
            if r_code in med_catalog and random.random() < 0.78:
                rx_code, rx_desc, rx_cost = med_catalog[r_code]
                dispenses = random.randint(1, 12) if is_chronic else 1
                medications.append({
                    "START": enc_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "STOP": "" if is_chronic else (enc_stop + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "PATIENT": pat_id,
                    "PAYER": deterministic_uuid("PAYER", (pat_idx % 5) + 1),
                    "ENCOUNTER": enc_id,
                    "CODE": rx_code,
                    "DESCRIPTION": rx_desc,
                    "BASE_COST": rx_cost,
                    "PAYER_COVERAGE": round(rx_cost * 0.75, 2),
                    "DISPENSES": dispenses,
                    "TOTALCOST": round(rx_cost * dispenses, 2),
                    "REASONCODE": r_code,
                    "REASONDESCRIPTION": r_desc,
                })

            # Procedures (65% of encounters have a documented clinical procedure)
            if random.random() < 0.65:
                pr_code, pr_desc, pr_cost = random.choice(proc_catalog)
                procedures.append({
                    "DATE": enc_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "PATIENT": pat_id,
                    "ENCOUNTER": enc_id,
                    "CODE": pr_code,
                    "DESCRIPTION": pr_desc,
                    "BASE_COST": pr_cost,
                    "REASONCODE": r_code,
                    "REASONDESCRIPTION": r_desc,
                })

        # Synthea technical detail: Quality-of-Life observations (QALY, DALY, QOLS) have no ENCOUNTER link!
        for qol_yr in (2024, 2025):
            qol_date = f"{qol_yr}-06-15T00:00:00Z"
            qaly_val = round(max(0.35, 0.96 - (age / 180.0) - (0.06 * len(pat_chronics))), 2)
            daly_val = round(max(0.0, (0.05 * len(pat_chronics)) + (0.02 if age >= 65 else 0.0)), 2)
            qols_val = round(max(0.40, qaly_val - random.uniform(-0.03, 0.04)), 2)
            if pat_idx <= 45:  # Add unlinked QoL observations for 45 patients (270 records)
                observations.extend([
                    {
                        "DATE": qol_date, "PATIENT": pat_id, "ENCOUNTER": "", "CATEGORY": "survey",
                        "CODE": "QALY", "DESCRIPTION": "Quality-Adjusted Life Years",
                        "VALUE": str(qaly_val), "UNITS": "a", "TYPE": "numeric"
                    },
                    {
                        "DATE": qol_date, "PATIENT": pat_id, "ENCOUNTER": "", "CATEGORY": "survey",
                        "CODE": "DALY", "DESCRIPTION": "Disability-Adjusted Life Years",
                        "VALUE": str(daly_val), "UNITS": "a", "TYPE": "numeric"
                    },
                    {
                        "DATE": qol_date, "PATIENT": pat_id, "ENCOUNTER": "", "CATEGORY": "survey",
                        "CODE": "QOLS", "DESCRIPTION": "Quality of Life Score",
                        "VALUE": str(qols_val), "UNITS": "{score}", "TYPE": "numeric"
                    },
                ])

    # Inject controlled data quality anomalies into Encounters, Conditions, and Observations
    # - 3 duplicate encounter records
    for dup_e in [5, 80, 210]:
        encounters.append(encounters[dup_e].copy())
    # - 3 orphan encounters referencing non-existent patient UUIDs
    for orp_i in range(1, 4):
        orphan_enc = encounters[orp_i * 15].copy()
        orphan_enc["Id"] = deterministic_uuid("ENC_ORPHAN", orp_i)
        orphan_enc["PATIENT"] = deterministic_uuid("NONEXISTENT_PAT", orp_i)
        encounters.append(orphan_enc)
    # - 2 encounters with missing PATIENT ID
    for miss_i in range(1, 3):
        miss_enc = encounters[miss_i * 25].copy()
        miss_enc["Id"] = deterministic_uuid("ENC_MISSPAT", miss_i)
        miss_enc["PATIENT"] = ""
        encounters.append(miss_enc)
    # - 14 duplicate diagnosis records in conditions.csv
    for dup_c in range(10, 150, 10):
        conditions.append(conditions[dup_c].copy())

    # Save all 8 raw CSV tables
    tables = {
        "patients": pd.DataFrame(patients),
        "encounters": pd.DataFrame(encounters),
        "conditions": pd.DataFrame(conditions),
        "observations": pd.DataFrame(observations),
        "medications": pd.DataFrame(medications),
        "procedures": pd.DataFrame(procedures),
        "organizations": pd.DataFrame(organizations),
        "providers": pd.DataFrame(providers),
    }
    for name, df in tables.items():
        df.to_csv(os.path.join(raw_dir, f"{name}.csv"), index=False)

    return {k: len(v) for k, v in tables.items()}


if __name__ == "__main__":
    base_raw = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
    counts = generate_synthea_raw_data(base_raw)
    print("Generated Synthea raw CSV files:", counts)
