-- ============================================================================
-- Hospital Population Health & Clinical Operations Analytics Platform
-- Relational Star Schema DDL (SQLite & PostgreSQL Compatible)
-- Dataset Provenance: Synthea Synthetic Patient Population Simulator
-- Reference: https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary
-- ============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_medication;
DROP TABLE IF EXISTS fact_observation;
DROP TABLE IF EXISTS fact_condition;
DROP TABLE IF EXISTS fact_encounter;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_provider;
DROP TABLE IF EXISTS dim_organization;
DROP TABLE IF EXISTS dim_patient;

-- 1. Patient Demographics Dimension
CREATE TABLE dim_patient (
    patient_id          TEXT PRIMARY KEY,
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    full_name           TEXT NOT NULL,
    birthdate           TEXT NOT NULL,
    deathdate           TEXT,
    is_deceased         INTEGER NOT NULL DEFAULT 0,
    age_years           REAL NOT NULL,
    age_group           TEXT NOT NULL,
    gender              TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    race                TEXT NOT NULL,
    ethnicity           TEXT NOT NULL,
    marital_status      TEXT,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    county              TEXT NOT NULL,
    zip                 TEXT NOT NULL,
    healthcare_expenses REAL NOT NULL DEFAULT 0.0,
    healthcare_coverage REAL NOT NULL DEFAULT 0.0
);

-- 2. Healthcare Organization Dimension
CREATE TABLE dim_organization (
    organization_id     TEXT PRIMARY KEY,
    organization_name   TEXT NOT NULL,
    address             TEXT,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    zip                 TEXT,
    lat                 REAL,
    lon                 REAL,
    phone               TEXT,
    revenue             REAL DEFAULT 0.0
);

-- 3. Clinician / Provider Dimension
CREATE TABLE dim_provider (
    provider_id         TEXT PRIMARY KEY,
    organization_id     TEXT NOT NULL,
    provider_name       TEXT NOT NULL,
    gender              TEXT,
    speciality          TEXT NOT NULL,
    city                TEXT,
    state               TEXT,
    FOREIGN KEY (organization_id) REFERENCES dim_organization(organization_id)
);

-- 4. Calendar Date Dimension
CREATE TABLE dim_date (
    date_key            INTEGER PRIMARY KEY,
    full_date           TEXT NOT NULL UNIQUE,
    year                INTEGER NOT NULL,
    quarter             INTEGER NOT NULL,
    year_quarter        TEXT NOT NULL,
    month               INTEGER NOT NULL,
    month_name          TEXT NOT NULL,
    year_month          TEXT NOT NULL,
    day_of_week         INTEGER NOT NULL,
    day_name            TEXT NOT NULL,
    is_weekend          INTEGER NOT NULL DEFAULT 0
);

-- 5. Clinical Encounters Fact Table
CREATE TABLE fact_encounter (
    encounter_id                TEXT PRIMARY KEY,
    patient_id                  TEXT NOT NULL,
    organization_id             TEXT NOT NULL,
    provider_id                 TEXT NOT NULL,
    date_key                    INTEGER NOT NULL,
    start_timestamp             TEXT NOT NULL,
    stop_timestamp              TEXT NOT NULL,
    encounter_date              TEXT NOT NULL,
    encounter_class             TEXT NOT NULL,
    code                        TEXT NOT NULL,
    description                 TEXT NOT NULL,
    los_hours                   REAL NOT NULL CHECK (los_hours >= 0),
    los_days                    REAL NOT NULL CHECK (los_days >= 0),
    is_emergency                INTEGER NOT NULL DEFAULT 0,
    is_inpatient                INTEGER NOT NULL DEFAULT 0,
    base_encounter_cost         REAL NOT NULL DEFAULT 0.0,
    total_claim_cost            REAL NOT NULL DEFAULT 0.0,
    payer_coverage              REAL NOT NULL DEFAULT 0.0,
    reason_code                 TEXT,
    reason_description          TEXT,
    is_30d_readmission_index    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (patient_id)      REFERENCES dim_patient(patient_id),
    FOREIGN KEY (organization_id) REFERENCES dim_organization(organization_id),
    FOREIGN KEY (provider_id)     REFERENCES dim_provider(provider_id),
    FOREIGN KEY (date_key)        REFERENCES dim_date(date_key)
);

-- 6. Diagnoses & Conditions Fact Table
CREATE TABLE fact_condition (
    condition_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT NOT NULL,
    date_key            INTEGER NOT NULL,
    start_date          TEXT NOT NULL,
    stop_date           TEXT,
    code                TEXT NOT NULL,
    description         TEXT NOT NULL,
    is_chronic          INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (patient_id)   REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounter(encounter_id),
    FOREIGN KEY (date_key)     REFERENCES dim_date(date_key)
);

-- 7. Clinical Measurements & QoL Observations Fact Table
-- Note: encounter_id is NULLABLE because Synthea Quality-of-Life (QALY/DALY/QOLS)
-- observations are recorded annually at the patient level without an encounter link.
CREATE TABLE fact_observation (
    observation_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT,
    date_key            INTEGER NOT NULL,
    observation_date    TEXT NOT NULL,
    category            TEXT,
    code                TEXT NOT NULL,
    description         TEXT NOT NULL,
    value_raw           TEXT,
    value_numeric       REAL,
    value_text          TEXT,
    units               TEXT,
    value_type          TEXT NOT NULL,
    is_qol_unlinked     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (patient_id)   REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounter(encounter_id),
    FOREIGN KEY (date_key)     REFERENCES dim_date(date_key)
);

-- 8. Medication Orders Fact Table
CREATE TABLE fact_medication (
    medication_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT NOT NULL,
    date_key            INTEGER NOT NULL,
    start_date          TEXT NOT NULL,
    stop_date           TEXT,
    code                TEXT NOT NULL,
    description         TEXT NOT NULL,
    base_cost           REAL NOT NULL DEFAULT 0.0,
    payer_coverage      REAL NOT NULL DEFAULT 0.0,
    dispenses           INTEGER NOT NULL DEFAULT 1,
    total_cost          REAL NOT NULL DEFAULT 0.0,
    reason_code         TEXT,
    reason_description  TEXT,
    FOREIGN KEY (patient_id)   REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounter(encounter_id),
    FOREIGN KEY (date_key)     REFERENCES dim_date(date_key)
);

-- Analytical Performance Indexes
CREATE INDEX idx_enc_patient       ON fact_encounter(patient_id);
CREATE INDEX idx_enc_org           ON fact_encounter(organization_id);
CREATE INDEX idx_enc_date          ON fact_encounter(date_key);
CREATE INDEX idx_enc_class         ON fact_encounter(encounter_class);
CREATE INDEX idx_cond_patient      ON fact_condition(patient_id);
CREATE INDEX idx_cond_code         ON fact_condition(code);
CREATE INDEX idx_obs_patient_code  ON fact_observation(patient_id, code);
CREATE INDEX idx_med_patient       ON fact_medication(patient_id);
