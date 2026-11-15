# Synthea Healthcare Data Dictionary & Relational Star Schema

## 1. Synthetic Data Provenance & Disclaimer
All patient records in `data/raw/` and `data/processed/` are **100% synthetic electronic health records** modeled on [Synthea — Synthetic Patient Population Simulator](https://github.com/synthetichealth/synthea) ([MITRE Corporation Downloads](https://synthea.mitre.org/downloads)). Column structures, clinical coding systems (`SNOMED-CT`, `LOINC`, `RxNorm`), and foreign key linkages strictly follow the official [Synthea CSV File Data Dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary).

> **Important Notice:** No real patient data or Protected Health Information (PHI/PII) is present in this repository. Analytical findings demonstrate clinical data engineering, SQL analytics, and Power BI reporting workflows and must never be interpreted as real-world hospital statistics.

## 2. Raw Synthea CSV Files (`data/raw/`)

| Raw CSV File | Raw Rows | Cleaned Rows | Primary Key | Foreign Keys | Clinical Content & Coding System |
| :--- | ---: | ---: | :--- | :--- | :--- |
| `patients.csv` | 504 | 500 | `Id` | — | Demographics, birth/death dates, race/ethnicity, address, ZIP, expenses |
| `encounters.csv` | 1,684 | 1,676 | `Id` | `PATIENT`, `ORGANIZATION`, `PROVIDER`, `PAYER` | Hospital and clinic visits across 6 classes (`SNOMED-CT`) |
| `conditions.csv` | 2,104 | 2,090 | Composite | `PATIENT`, `ENCOUNTER` | Active and resolved clinical diagnoses (`SNOMED-CT`) |
| `observations.csv` | 8,527 | 8,527 | Composite | `PATIENT`, `ENCOUNTER` (nullable) | Vital signs, lab results (`LOINC`), smoking status, and QoL scores (`QALY`/`DALY`/`QOLS`) |
| `medications.csv` | 729 | 729 | Composite | `PATIENT`, `ENCOUNTER`, `PAYER` | Outpatient and inpatient medication orders and dispenses (`RxNorm`) |
| `procedures.csv` | 1,100 | 1,100 | Composite | `PATIENT`, `ENCOUNTER` | Diagnostic and therapeutic clinical procedures (`SNOMED-CT`) |
| `organizations.csv` | 6 | 6 | `Id` | — | Healthcare facilities, locations, utilization, and revenue |
| `providers.csv` | 24 | 24 | `Id` | `ORGANIZATION` | Attending clinicians, gender, and medical specialties |

## 3. Relational Star Schema (`sql/schema.sql` & `hospital_analytics.db`)

```
                       +------------------------+
                       |      dim_organization  |
                       |------------------------|
                       | PK organization_id     |
                       |    organization_name   |
                       |    city, state, zip    |
                       +-----------+------------+
                                   | 1
                                   |
      +------------------------+   | * +------------------------+
      |      dim_patient       |   +---|      dim_provider      |
      |------------------------|   |   |------------------------|
      | PK patient_id          |   |   | PK provider_id         |
      |    full_name, gender   |   |   | FK organization_id     |
      |    age_years, age_group|   |   |    speciality          |
      +-----------+------------+   |   +-----------+------------+
                  | 1              | 1             | 1
                  |                |               |
                  +------------+   |   +-----------+
                               |   |   |
                             * v   v   v *
                       +------------------------+       +------------------------+
                       |     fact_encounter     |       |        dim_date        |
                       |------------------------|       |------------------------|
                       | PK encounter_id        | *   1 | PK date_key (YYYYMMDD) |
                       | FK patient_id          +------>|    full_date, year     |
                       | FK organization_id     |       |    quarter, year_month |
                       | FK provider_id         |       +------------------------+
                       | FK date_key            |
                       |    encounter_class     |
                       |    los_hours, los_days |
                       |    is_emergency        |
                       |    is_inpatient        |
                       |    is_30d_readmission  |
                       |    total_claim_cost    |
                       +---+--------+-------+---+
                         1 |      1 |     1 |
            +--------------+        |       +--------------+
          * |                     * |                    * | (nullable for QoL)
+-----------+------------+ +--------+---------------+ +----+-------------------+
|     fact_condition     | |    fact_medication     | |    fact_observation    |
|------------------------| |------------------------| |------------------------|
| PK condition_id        | | PK medication_id       | | PK observation_id      |
| FK patient_id          | | FK patient_id          | | FK patient_id          |
| FK encounter_id        | | FK encounter_id        | | FK encounter_id (NULL) |
| FK date_key            | | FK date_key            | | FK date_key            |
|    code, description   | |    code, description   | |    code, description   |
|    is_chronic          | |    dispenses, cost     | |    value_numeric       |
+------------------------+ +------------------------+ |    value_text          |
                                                      |    is_qol_unlinked     |
                                                      +------------------------+
```

## 4. Technical Handling of Synthea Observation Edge Cases
Per the [Synthea CSV File Data Dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary):
1. **Mixed Numeric and Text Values:** `observations.csv` stores quantitative measurements (`8480-6` Systolic BP, `4548-4` HbA1c, `39156-5` BMI) alongside categorical text strings (`72166-2` Tobacco smoking status). `fact_observation` splits these cleanly into `value_numeric` (`REAL`) and `value_text` (`TEXT`) alongside `value_type`.
2. **Unlinked Quality-of-Life Observations:** Synthea generates annual patient-level survey scores (`QALY`, `DALY`, `QOLS`) with an empty `ENCOUNTER` column (270 records in our dataset). `fact_observation` defines `encounter_id` as nullable and sets `is_qol_unlinked = 1` so encounter-level joins are never distorted while preserving longitudinal patient quality-of-life tracking.
