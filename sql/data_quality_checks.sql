-- ============================================================================
-- Module 2 & 3: Post-Load Relational Data Quality Verification Queries
-- Database: hospital_analytics.db (SQLite / PostgreSQL Compatible)
-- ============================================================================

-- Check 1: Verify zero duplicate patient IDs
SELECT 'DQ-01: Duplicate Patient IDs' AS check_name,
       COUNT(*) - COUNT(DISTINCT patient_id) AS violation_count
FROM dim_patient;

-- Check 2: Verify zero duplicate encounter IDs
SELECT 'DQ-02: Duplicate Encounter IDs' AS check_name,
       COUNT(*) - COUNT(DISTINCT encounter_id) AS violation_count
FROM fact_encounter;

-- Check 3: Verify zero invalid date sequences (stop_timestamp < start_timestamp)
SELECT 'DQ-03: Invalid Encounter Date Sequences (los_hours < 0)' AS check_name,
       COUNT(*) AS violation_count
FROM fact_encounter
WHERE los_hours < 0;

-- Check 4: Verify zero orphan encounter records (missing dim_patient parent)
SELECT 'DQ-04: Orphan Encounter Records' AS check_name,
       COUNT(*) AS violation_count
FROM fact_encounter e
LEFT JOIN dim_patient p ON e.patient_id = p.patient_id
WHERE p.patient_id IS NULL;

-- Check 5: Verify zero missing patient IDs on encounters
SELECT 'DQ-05: Missing Patient IDs in Fact Encounter' AS check_name,
       COUNT(*) AS violation_count
FROM fact_encounter
WHERE patient_id IS NULL OR TRIM(patient_id) = '';

-- Check 6: Verify standardized demographic gender values ('M' or 'F')
SELECT 'DQ-06: Invalid Demographic Gender Codes' AS check_name,
       COUNT(*) AS violation_count
FROM dim_patient
WHERE gender NOT IN ('M', 'F');

-- Check 7: Verify zero duplicate diagnosis records per (patient, encounter, code, start_date)
SELECT 'DQ-07: Duplicate Diagnosis Records' AS check_name,
       COUNT(*) - COUNT(DISTINCT patient_id || '|' || encounter_id || '|' || code || '|' || start_date) AS violation_count
FROM fact_condition;

-- Check 8: Audit Quality-of-Life (QALY/DALY/QOLS) unlinked observations vs clinical encounter observations
SELECT 'DQ-08: Unlinked Non-Survey Observations' AS check_name,
       COUNT(*) AS violation_count
FROM fact_observation
WHERE encounter_id IS NULL AND is_qol_unlinked = 0;
