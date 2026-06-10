import os
import sqlite3
import pandas as pd

def init_database(db_path, raw_csv_path):
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Drop existing tables to start fresh
    cursor.execute("DROP TABLE IF EXISTS fact_admissions;")
    cursor.execute("DROP TABLE IF EXISTS dim_patients;")
    cursor.execute("DROP TABLE IF EXISTS dim_departments;")
    cursor.execute("DROP TABLE IF EXISTS dim_conditions;")
    cursor.execute("DROP TABLE IF EXISTS ingestion_log;")
    
    # Create tables
    cursor.execute("""
    CREATE TABLE dim_patients (
        patient_id TEXT PRIMARY KEY,
        patient_name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        blood_type TEXT
    );
    """)
    
    cursor.execute("""
    CREATE TABLE dim_departments (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_name TEXT UNIQUE NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE dim_conditions (
        condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition_name TEXT UNIQUE NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE fact_admissions (
        admission_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        admission_date TEXT NOT NULL,
        discharge_date TEXT,
        department_id INTEGER,
        condition_id INTEGER,
        billing_amount REAL,
        admission_type TEXT,
        test_result TEXT,
        FOREIGN KEY(patient_id) REFERENCES dim_patients(patient_id),
        FOREIGN KEY(department_id) REFERENCES dim_departments(department_id),
        FOREIGN KEY(condition_id) REFERENCES dim_conditions(condition_id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE ingestion_log (
        batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
        submitted_at TEXT NOT NULL,
        filename TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        status TEXT NOT NULL,          -- Accepted, Needs Review, Rejected
        health_score REAL NOT NULL,    -- 0.0 to 1.0
        issues_json TEXT NOT NULL,      -- JSON summary of failures
        accepted_rows INTEGER,
        rejected_rows INTEGER
    );
    """)
    
    conn.commit()
    print("Tables created successfully.")
    
    # Seed data ingestion from raw CSV
    if not os.path.exists(raw_csv_path):
        print(f"Error: Raw seed data file not found at: {raw_csv_path}")
        conn.close()
        return
        
    print(f"Seeding database from: {raw_csv_path}")
    df = pd.read_csv(raw_csv_path)
    
    # 1. Insert unique patients
    patients_df = df[["Patient ID", "Patient Name", "Age", "Gender", "Blood Type"]].drop_duplicates(subset=["Patient ID"])
    for _, row in patients_df.iterrows():
        cursor.execute("""
        INSERT OR IGNORE INTO dim_patients (patient_id, patient_name, age, gender, blood_type)
        VALUES (?, ?, ?, ?, ?)
        """, (row["Patient ID"], row["Patient Name"], int(row["Age"]) if pd.notna(row["Age"]) else None, row["Gender"], row["Blood Type"]))
    
    # 2. Insert unique departments
    departments = df["Hospital Department"].dropna().unique()
    for dept in departments:
        cursor.execute("INSERT OR IGNORE INTO dim_departments (department_name) VALUES (?)", (dept,))
        
    # 3. Insert unique conditions
    conditions = df["Medical Condition"].dropna().unique()
    for cond in conditions:
        cursor.execute("INSERT OR IGNORE INTO dim_conditions (condition_name) VALUES (?)", (cond,))
        
    conn.commit()
    
    # Fetch lookups for departments and conditions to map in memory for speed
    cursor.execute("SELECT department_id, department_name FROM dim_departments")
    dept_lookup = {name: id for id, name in cursor.fetchall()}
    
    cursor.execute("SELECT condition_id, condition_name FROM dim_conditions")
    cond_lookup = {name: id for id, name in cursor.fetchall()}
    
    # 4. Insert Admissions facts
    admissions_data = []
    for _, row in df.iterrows():
        dept_id = dept_lookup.get(row["Hospital Department"])
        cond_id = cond_lookup.get(row["Medical Condition"])
        
        # Format billing
        billing = float(row["Billing Amount"]) if pd.notna(row["Billing Amount"]) else 0.0
        
        admissions_data.append((
            row["Patient ID"],
            row["Admission Date"],
            row["Discharge Date"] if pd.notna(row["Discharge Date"]) else None,
            dept_id,
            cond_id,
            billing,
            row["Admission Type"],
            row["Test Results"]
        ))
        
    cursor.executemany("""
    INSERT INTO fact_admissions (
        patient_id, admission_date, discharge_date, department_id, condition_id, billing_amount, admission_type, test_result
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, admissions_data)
    
    conn.commit()
    
    # Log initial seed batch in ingestion log
    from datetime import datetime
    cursor.execute("""
    INSERT INTO ingestion_log (submitted_at, filename, row_count, status, health_score, issues_json, accepted_rows, rejected_rows)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        os.path.basename(raw_csv_path),
        len(df),
        "Accepted",
        1.0,
        "[]",
        len(df),
        0
    ))
    
    conn.commit()
    print(f"Seeded {len(df)} admissions records. Database seed complete.")
    conn.close()

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "healthcare.db")
    csv_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "healthcare_data_raw.csv")
    
    # Make sure src dir exists
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    init_database(db_file, csv_file)
