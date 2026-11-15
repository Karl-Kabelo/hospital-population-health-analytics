#!/usr/bin/env python3
"""
Automated Unit & Integration Test Suite (test_data_pipeline.py)
Verifies data cleaning rules, referential integrity, star-schema row counts,
dual-value observation handling, and healthcare KPI calculations.
"""

import os
import sqlite3
import unittest
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "data", "processed", "hospital_analytics.db")
DQ_REPORT = os.path.join(REPO_ROOT, "reports", "data_quality_report.csv")


class TestHospitalAnalyticsPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(DB_PATH)
        cls.dq_df = pd.read_csv(DQ_REPORT)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_unique_patient_count_and_deduplication(self):
        cur = self.conn.execute("SELECT COUNT(*), COUNT(DISTINCT patient_id) FROM dim_patient")
        total, distinct = cur.fetchone()
        self.assertEqual(total, 500)
        self.assertEqual(total, distinct)

    def test_02_encounter_integrity_and_positive_los(self):
        cur = self.conn.execute("SELECT COUNT(*), MIN(los_hours) FROM fact_encounter")
        cnt, min_los = cur.fetchone()
        self.assertEqual(cnt, 1676)
        self.assertGreaterEqual(min_los, 0.0)

    def test_03_zero_orphan_encounters(self):
        cur = self.conn.execute("""
            SELECT COUNT(*) FROM fact_encounter e
            LEFT JOIN dim_patient p ON e.patient_id = p.patient_id
            WHERE p.patient_id IS NULL
        """)
        self.assertEqual(cur.fetchone()[0], 0)

    def test_04_standardized_demographics(self):
        cur = self.conn.execute("SELECT COUNT(*) FROM dim_patient WHERE gender NOT IN ('M', 'F')")
        self.assertEqual(cur.fetchone()[0], 0)

    def test_05_dual_type_and_qol_unlinked_observations(self):
        cur = self.conn.execute("""
            SELECT SUM(CASE WHEN is_qol_unlinked = 1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN value_type = 'text' AND value_text IS NOT NULL THEN 1 ELSE 0 END),
                   SUM(CASE WHEN value_type = 'numeric' AND value_numeric IS NOT NULL THEN 1 ELSE 0 END)
            FROM fact_observation
        """)
        qol_cnt, txt_cnt, num_cnt = cur.fetchone()
        self.assertEqual(qol_cnt, 270)
        self.assertEqual(txt_cnt, 500)
        self.assertGreater(num_cnt, 7500)

    def test_06_data_quality_report_all_passed(self):
        failed = self.dq_df[~self.dq_df["status"].str.startswith("PASS")]
        self.assertEqual(len(failed), 0)

    def test_07_kpi_bounds(self):
        cur = self.conn.execute("""
            SELECT ROUND(COUNT(*) * 1.0 / (SELECT COUNT(*) FROM dim_patient), 2),
                   ROUND(SUM(is_emergency) * 100.0 / COUNT(*), 2)
            FROM fact_encounter
        """)
        avg_enc, er_rate = cur.fetchone()
        self.assertEqual(avg_enc, 3.35)
        self.assertEqual(er_rate, 12.53)


if __name__ == "__main__":
    unittest.main(verbosity=2)
