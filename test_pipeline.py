import os
import sys
import unittest
import pandas as pd
import sqlite3

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import analytics
import ingestion

class TestClinicalPipeline(unittest.TestCase):
    def setUp(self):
        self.db_path = "src/healthcare.db"
        self.dirty_csv = "healthcare_data_dirty.csv"
        
    def test_database_exists(self):
        self.assertTrue(os.path.exists(self.db_path), "Database file should exist.")
        
    def test_kpi_queries(self):
        kpis = analytics.get_kpis(self.db_path)
        self.assertIn("total_patients", kpis)
        self.assertIn("total_revenue", kpis)
        self.assertIn("avg_stay", kpis)
        self.assertIn("readmit_rate", kpis)
        self.assertEqual(kpis["total_patients"], 5000)
        
    def test_department_workload(self):
        df = analytics.get_department_workload(self.db_path)
        self.assertFalse(df.empty, "Department workload should return data.")
        self.assertIn("department_name", df.columns)
        self.assertIn("workload_rank", df.columns)
        
    def test_dirty_ingestion_anomalies(self):
        # Process file upload on the dirty file
        result = ingestion.process_file_upload(self.dirty_csv, "healthcare_data_dirty.csv", self.db_path)
        self.assertTrue(result["success"], "Upload should process successfully (even if warnings are logged).")
        self.assertEqual(result["status"], "Accepted", "Status should be Accepted (98% health score).")
        self.assertIn("invalid_stay_duration", result["issues"], "Should catch invalid discharge dates.")
        self.assertIn("age_sanity", result["issues"], "Should catch age outliers.")
        
    def test_column_mapping(self):
        # Test fuzzy mapping
        df_raw = pd.DataFrame(columns=["PatientID", "full_name", "patient age", "sex", "bloodtype", "disease", "admitted", "discharged", "cost", "dept", "admissiontype", "results"])
        df_mapped = ingestion.map_columns(df_raw)
        self.assertEqual(list(df_mapped.columns), list(ingestion.COLUMN_MAPPING.keys()))

if __name__ == "__main__":
    unittest.main()
