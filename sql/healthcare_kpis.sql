-- ============================================================================
-- Module 4: Healthcare Performance KPIs & Demographic Breakdowns
-- Note: Encounter metrics represent clinical service utilization across the
-- 24-month observation window (2024-01-01 to 2025-12-31), NOT physical bed
-- occupancy or licensed inpatient capacity.
-- ============================================================================

-- 1. Executive Summary KPI Card Query
WITH patient_enc_counts AS (
    SELECT p.patient_id,
           COUNT(e.encounter_id) AS enc_count
    FROM dim_patient p
    LEFT JOIN fact_encounter e ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
),
inpatient_stats AS (
    SELECT AVG(los_days) AS avg_inpatient_los_days,
           AVG(los_hours) AS avg_inpatient_los_hours,
           SUM(is_30d_readmission_index) * 100.0 / NULLIF(COUNT(*), 0) AS readmission_rate_30d_pct
    FROM fact_encounter
    WHERE is_inpatient = 1
)
SELECT
    (SELECT COUNT(DISTINCT patient_id) FROM dim_patient) AS total_unique_patients,
    COUNT(e.encounter_id) AS total_encounters,
    ROUND(COUNT(e.encounter_id) * 1.0 / (SELECT COUNT(DISTINCT patient_id) FROM dim_patient), 2) AS avg_encounters_per_patient,
    ROUND(AVG(e.los_hours), 2) AS overall_avg_los_hours,
    ROUND(AVG(e.los_days), 2) AS overall_avg_los_days,
    ROUND((SELECT avg_inpatient_los_days FROM inpatient_stats), 2) AS inpatient_avg_los_days,
    ROUND(SUM(e.is_emergency) * 100.0 / COUNT(e.encounter_id), 2) AS emergency_encounter_rate_pct,
    ROUND((SELECT COUNT(*) FROM patient_enc_counts WHERE enc_count >= 2) * 100.0 /
          (SELECT COUNT(*) FROM patient_enc_counts), 2) AS repeat_patient_rate_pct,
    ROUND((SELECT readmission_rate_30d_pct FROM inpatient_stats), 2) AS inpatient_30d_readmission_rate_pct,
    ROUND(SUM(e.total_claim_cost), 2) AS total_claim_cost_usd,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_claim_cost_per_encounter_usd
FROM fact_encounter e;

-- 2. Monthly Encounter Growth & 3-Month Rolling Average (Window Functions)
WITH monthly_counts AS (
    SELECT d.year_month,
           COUNT(e.encounter_id) AS monthly_encounters,
           SUM(e.is_emergency) AS emergency_encounters,
           SUM(e.is_inpatient) AS inpatient_encounters,
           ROUND(SUM(e.total_claim_cost), 2) AS monthly_claim_cost
    FROM fact_encounter e
    JOIN dim_date d ON e.date_key = d.date_key
    GROUP BY d.year_month
)
SELECT year_month,
       monthly_encounters,
       LAG(monthly_encounters) OVER (ORDER BY year_month) AS prev_month_encounters,
       ROUND((monthly_encounters - LAG(monthly_encounters) OVER (ORDER BY year_month)) * 100.0 /
             NULLIF(LAG(monthly_encounters) OVER (ORDER BY year_month), 0), 2) AS mom_growth_pct,
       ROUND(AVG(monthly_encounters) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_3m_avg_encounters,
       emergency_encounters,
       inpatient_encounters,
       monthly_claim_cost
FROM monthly_counts
ORDER BY year_month;

-- 3. Demographic Utilization Breakdown by Age Group & Gender
SELECT p.age_group,
       p.gender,
       COUNT(DISTINCT p.patient_id) AS patient_count,
       COUNT(e.encounter_id) AS encounter_count,
       ROUND(COUNT(e.encounter_id) * 1.0 / COUNT(DISTINCT p.patient_id), 2) AS encounters_per_patient,
       ROUND(AVG(e.los_hours), 2) AS avg_los_hours,
       ROUND(SUM(e.is_emergency) * 100.0 / COUNT(e.encounter_id), 2) AS emergency_rate_pct,
       ROUND(SUM(e.total_claim_cost), 2) AS total_cost_usd
FROM dim_patient p
LEFT JOIN fact_encounter e ON p.patient_id = e.patient_id
GROUP BY p.age_group, p.gender
ORDER BY p.age_group, p.gender;

-- 4. Chronic Condition Prevalence Across Patient Population (N = 500)
SELECT c.code,
       c.description AS chronic_condition,
       COUNT(DISTINCT c.patient_id) AS affected_patients,
       ROUND(COUNT(DISTINCT c.patient_id) * 100.0 / (SELECT COUNT(*) FROM dim_patient), 2) AS population_prevalence_pct,
       RANK() OVER (ORDER BY COUNT(DISTINCT c.patient_id) DESC) AS prevalence_rank
FROM fact_condition c
WHERE c.is_chronic = 1
GROUP BY c.code, c.description
ORDER BY affected_patients DESC;
