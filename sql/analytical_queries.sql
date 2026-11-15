-- ============================================================================
-- Module 3: 12 Healthcare Business & Operational SQL Queries
-- Database: hospital_analytics.db
-- Demonstrates joins, aggregations, CTEs, CASE expressions, and window functions
-- ============================================================================

-- Q1: How many unique patients are in the database (with living vs deceased breakdown)?
SELECT COUNT(DISTINCT patient_id) AS total_unique_patients,
       SUM(CASE WHEN is_deceased = 0 THEN 1 ELSE 0 END) AS living_patients,
       SUM(CASE WHEN is_deceased = 1 THEN 1 ELSE 0 END) AS deceased_patients,
       ROUND(AVG(age_years), 1) AS mean_patient_age_years
FROM dim_patient;

-- Q2: How many encounters occur per month (with MoM % change and 3-month rolling average)?
WITH monthly_vol AS (
    SELECT d.year_month,
           COUNT(e.encounter_id) AS encounter_count,
           COUNT(DISTINCT e.patient_id) AS distinct_patients_seen
    FROM fact_encounter e
    JOIN dim_date d ON e.date_key = d.date_key
    GROUP BY d.year_month
)
SELECT year_month,
       encounter_count,
       distinct_patients_seen,
       LAG(encounter_count) OVER (ORDER BY year_month) AS prev_month_count,
       ROUND((encounter_count - LAG(encounter_count) OVER (ORDER BY year_month)) * 100.0 /
             NULLIF(LAG(encounter_count) OVER (ORDER BY year_month), 0), 2) AS mom_change_pct,
       ROUND(AVG(encounter_count) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS rolling_3m_avg
FROM monthly_vol
ORDER BY year_month;

-- Q3: Which diagnoses are most common (ranked by total diagnosis occurrences and unique patient prevalence)?
SELECT c.code AS snomed_code,
       c.description AS diagnosis_description,
       CASE WHEN c.is_chronic = 1 THEN 'Chronic' ELSE 'Acute' END AS condition_type,
       COUNT(c.condition_id) AS total_diagnosis_records,
       COUNT(DISTINCT c.patient_id) AS unique_patients_affected,
       ROUND(COUNT(DISTINCT c.patient_id) * 100.0 / (SELECT COUNT(*) FROM dim_patient), 2) AS patient_prevalence_pct,
       DENSE_RANK() OVER (ORDER BY COUNT(c.condition_id) DESC) AS diagnosis_rank
FROM fact_condition c
GROUP BY c.code, c.description, c.is_chronic
ORDER BY total_diagnosis_records DESC
LIMIT 15;

-- Q4: Which organisations have the highest encounter volumes (and what is their market share & emergency mix)?
SELECT o.organization_name,
       o.city,
       COUNT(e.encounter_id) AS total_encounters,
       COUNT(DISTINCT e.patient_id) AS unique_patients_served,
       ROUND(COUNT(e.encounter_id) * 100.0 / SUM(COUNT(e.encounter_id)) OVER (), 2) AS encounter_share_pct,
       SUM(e.is_emergency) AS emergency_visits,
       SUM(e.is_inpatient) AS inpatient_admissions,
       ROUND(AVG(e.los_hours), 2) AS avg_los_hours,
       ROUND(SUM(e.total_claim_cost), 2) AS total_claim_cost_usd
FROM fact_encounter e
JOIN dim_organization o ON e.organization_id = o.organization_id
GROUP BY o.organization_id, o.organization_name, o.city
ORDER BY total_encounters DESC;

-- Q5: What is the average length of stay (overall and stratified by encounter class)?
SELECT encounter_class,
       COUNT(encounter_id) AS encounter_count,
       ROUND(AVG(los_hours), 2) AS avg_los_hours,
       ROUND(AVG(los_days), 2) AS avg_los_days,
       ROUND(MIN(los_hours), 2) AS min_los_hours,
       ROUND(MAX(los_hours), 2) AS max_los_hours,
       ROUND(AVG(total_claim_cost), 2) AS avg_claim_cost_usd
FROM fact_encounter
GROUP BY encounter_class
ORDER BY avg_los_hours DESC;

-- Q6: Which age groups have the highest encounter frequency (encounters per patient & share of total visits)?
SELECT p.age_group,
       COUNT(DISTINCT p.patient_id) AS cohort_patients,
       COUNT(e.encounter_id) AS total_encounters,
       ROUND(COUNT(e.encounter_id) * 1.0 / COUNT(DISTINCT p.patient_id), 2) AS encounters_per_patient,
       ROUND(COUNT(e.encounter_id) * 100.0 / SUM(COUNT(e.encounter_id)) OVER (), 2) AS share_of_all_encounters_pct,
       ROUND(SUM(e.is_emergency) * 100.0 / COUNT(e.encounter_id), 2) AS emergency_visit_rate_pct,
       ROUND(AVG(CASE WHEN e.is_inpatient = 1 THEN e.los_days END), 2) AS avg_inpatient_los_days
FROM dim_patient p
LEFT JOIN fact_encounter e ON p.patient_id = e.patient_id
GROUP BY p.age_group
ORDER BY encounters_per_patient DESC;

-- Q7: What percentage of patients have multiple encounters (repeat utilization distribution)?
WITH pat_utilization AS (
    SELECT p.patient_id,
           COUNT(e.encounter_id) AS enc_count,
           CASE
               WHEN COUNT(e.encounter_id) = 1 THEN '1 Encounter (Single Visit)'
               WHEN COUNT(e.encounter_id) BETWEEN 2 AND 3 THEN '2-3 Encounters (Moderate)'
               WHEN COUNT(e.encounter_id) BETWEEN 4 AND 5 THEN '4-5 Encounters (Frequent)'
               ELSE '6+ Encounters (High Utilizer / Super-Utilizer)'
           END AS utilization_tier
    FROM dim_patient p
    LEFT JOIN fact_encounter e ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
)
SELECT utilization_tier,
       COUNT(patient_id) AS patient_count,
       ROUND(COUNT(patient_id) * 100.0 / SUM(COUNT(patient_id)) OVER (), 2) AS pct_of_patients,
       SUM(enc_count) AS total_encounters_in_tier,
       ROUND(SUM(enc_count) * 100.0 / SUM(SUM(enc_count)) OVER (), 2) AS pct_of_all_encounters
FROM pat_utilization
GROUP BY utilization_tier
ORDER BY MIN(enc_count);

-- Q8: Which patients have the highest healthcare utilisation (top 15 super-utilizers for care management)?
WITH pat_chronic AS (
    SELECT patient_id,
           COUNT(DISTINCT code) AS chronic_condition_count
    FROM fact_condition
    WHERE is_chronic = 1
    GROUP BY patient_id
)
SELECT p.patient_id,
       p.full_name,
       p.age_years,
       p.age_group,
       p.gender,
       p.city,
       COALESCE(pc.chronic_condition_count, 0) AS chronic_conditions,
       COUNT(e.encounter_id) AS total_encounters,
       SUM(e.is_emergency) AS emergency_visits,
       SUM(e.is_inpatient) AS inpatient_admissions,
       SUM(e.is_30d_readmission_index) AS readmissions_30d,
       ROUND(SUM(e.los_days), 2) AS cumulative_los_days,
       ROUND(SUM(e.total_claim_cost), 2) AS total_claim_cost_usd
FROM dim_patient p
JOIN fact_encounter e ON p.patient_id = e.patient_id
LEFT JOIN pat_chronic pc ON p.patient_id = pc.patient_id
GROUP BY p.patient_id, p.full_name, p.age_years, p.age_group, p.gender, p.city, pc.chronic_condition_count
ORDER BY total_encounters DESC, total_claim_cost_usd DESC
LIMIT 15;

-- Q9: How do encounter volumes and clinical costs differ by encounter type?
SELECT encounter_class,
       COUNT(encounter_id) AS encounter_volume,
       ROUND(COUNT(encounter_id) * 100.0 / SUM(COUNT(encounter_id)) OVER (), 2) AS volume_share_pct,
       COUNT(DISTINCT patient_id) AS distinct_patients,
       ROUND(SUM(total_claim_cost), 2) AS total_claim_cost_usd,
       ROUND(SUM(total_claim_cost) * 100.0 / SUM(SUM(total_claim_cost)) OVER (), 2) AS cost_share_pct,
       ROUND(AVG(total_claim_cost), 2) AS mean_cost_per_visit_usd,
       ROUND(AVG(payer_coverage * 100.0 / NULLIF(total_claim_cost, 0)), 2) AS avg_payer_coverage_pct
FROM fact_encounter
GROUP BY encounter_class
ORDER BY encounter_volume DESC;

-- Q10: How do diagnosis patterns vary across age groups (Top 3 diagnoses per age group using ROW_NUMBER)?
WITH age_diag_counts AS (
    SELECT p.age_group,
           c.code,
           c.description AS diagnosis,
           COUNT(c.condition_id) AS diag_occurrences,
           COUNT(DISTINCT c.patient_id) AS affected_patients,
           ROW_NUMBER() OVER (PARTITION BY p.age_group ORDER BY COUNT(c.condition_id) DESC) AS rn
    FROM fact_condition c
    JOIN dim_patient p ON c.patient_id = p.patient_id
    GROUP BY p.age_group, c.code, c.description
)
SELECT age_group,
       rn AS rank_in_age_group,
       code AS snomed_code,
       diagnosis,
       diag_occurrences,
       affected_patients
FROM age_diag_counts
WHERE rn <= 3
ORDER BY age_group, rn;

-- Q11: What is the average number of encounters per patient (overall, by chronic burden, and median/IQR stats)?
WITH pat_summary AS (
    SELECT p.patient_id,
           COUNT(DISTINCT e.encounter_id) AS enc_count,
           COUNT(DISTINCT CASE WHEN c.is_chronic = 1 THEN c.code END) AS chronic_count
    FROM dim_patient p
    LEFT JOIN fact_encounter e ON p.patient_id = e.patient_id
    LEFT JOIN fact_condition c ON p.patient_id = c.patient_id
    GROUP BY p.patient_id
)
SELECT CASE
           WHEN chronic_count = 0 THEN '0 Chronic Conditions'
           WHEN chronic_count = 1 THEN '1 Chronic Condition'
           WHEN chronic_count = 2 THEN '2 Chronic Conditions'
           ELSE '3+ Chronic Conditions (Multimorbid)'
       END AS chronic_burden_tier,
       COUNT(patient_id) AS patient_count,
       SUM(enc_count) AS total_encounters,
       ROUND(AVG(enc_count), 2) AS avg_encounters_per_patient,
       MIN(enc_count) AS min_encounters,
       MAX(enc_count) AS max_encounters
FROM pat_summary
GROUP BY chronic_burden_tier
ORDER BY MIN(chronic_count);

-- Q12: What percentage of encounters are emergency visits (overall, by organization, and by age group)?
SELECT o.organization_name,
       COUNT(e.encounter_id) AS total_encounters,
       SUM(e.is_emergency) AS emergency_encounters,
       ROUND(SUM(e.is_emergency) * 100.0 / COUNT(e.encounter_id), 2) AS emergency_visit_pct,
       SUM(e.is_inpatient) AS inpatient_encounters,
       SUM(e.is_30d_readmission_index) AS readmissions_30d,
       ROUND(SUM(e.is_30d_readmission_index) * 100.0 / NULLIF(SUM(e.is_inpatient), 0), 2) AS inpatient_30d_readm_pct
FROM fact_encounter e
JOIN dim_organization o ON e.organization_id = o.organization_id
GROUP BY o.organization_id, o.organization_name
ORDER BY emergency_visit_pct DESC;
