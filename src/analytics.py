import sqlite3
import pandas as pd

def get_connection(db_path="src/healthcare.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_kpis(db_path="src/healthcare.db"):
    conn = get_connection(db_path)
    
    # 1. Total Unique Patients
    total_patients = pd.read_sql_query("SELECT COUNT(*) as count FROM dim_patients", conn).iloc[0]['count']
    
    # 2. Total Admissions
    total_admissions = pd.read_sql_query("SELECT COUNT(*) as count FROM fact_admissions", conn).iloc[0]['count']
    
    # 3. Total Billing / Revenue
    total_revenue = pd.read_sql_query("SELECT SUM(billing_amount) as total FROM fact_admissions", conn).iloc[0]['total']
    total_revenue = total_revenue if total_revenue else 0.0
    
    # 4. Average Length of Stay
    avg_stay_query = """
    SELECT AVG(julianday(discharge_date) - julianday(admission_date)) as avg_stay 
    FROM fact_admissions 
    WHERE discharge_date IS NOT NULL
    """
    avg_stay = pd.read_sql_query(avg_stay_query, conn).iloc[0]['avg_stay']
    avg_stay = avg_stay if avg_stay else 0.0
    
    # 5. Readmission Rate (re-admitted patient count / total patients)
    # A patient is readmitted if they have more than 1 admission
    readmit_query = """
    WITH PatientAdmissions AS (
        SELECT patient_id, COUNT(admission_id) as admission_count
        FROM fact_admissions
        GROUP BY patient_id
    )
    SELECT 
        COUNT(CASE WHEN admission_count > 1 THEN 1 END) * 100.0 / COUNT(*) as readmit_rate
    FROM PatientAdmissions
    """
    readmit_rate = pd.read_sql_query(readmit_query, conn).iloc[0]['readmit_rate']
    readmit_rate = readmit_rate if readmit_rate else 0.0
    
    conn.close()
    
    return {
        "total_patients": int(total_patients),
        "total_admissions": int(total_admissions),
        "total_revenue": float(total_revenue),
        "avg_stay": float(avg_stay),
        "readmit_rate": float(readmit_rate)
    }

def get_patients_by_age_group(db_path="src/healthcare.db"):
    query = """
    WITH PatientAgeGroups AS (
        SELECT 
            patient_id,
            CASE 
                WHEN age < 18 THEN 'Pediatrics (<18)'
                WHEN age BETWEEN 18 AND 35 THEN 'Young Adult (18-35)'
                WHEN age BETWEEN 36 AND 50 THEN 'Adult (36-50)'
                WHEN age BETWEEN 51 AND 65 THEN 'Middle Aged (51-65)'
                ELSE 'Senior (65+)'
            END AS age_group
        FROM dim_patients
    )
    SELECT age_group, COUNT(*) as patient_count
    FROM PatientAgeGroups
    GROUP BY age_group
    ORDER BY 
        CASE age_group
            WHEN 'Pediatrics (<18)' THEN 1
            WHEN 'Young Adult (18-35)' THEN 2
            WHEN 'Adult (36-50)' THEN 3
            WHEN 'Middle Aged (51-65)' THEN 4
            ELSE 5
        END;
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_patients_by_gender(db_path="src/healthcare.db"):
    query = """
    SELECT gender, COUNT(*) as patient_count
    FROM dim_patients
    GROUP BY gender
    ORDER BY patient_count DESC;
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_department_workload(db_path="src/healthcare.db"):
    # Ranking departments using window functions
    query = """
    SELECT 
        d.department_name,
        COUNT(f.admission_id) as total_admissions,
        RANK() OVER (ORDER BY COUNT(f.admission_id) DESC) as workload_rank,
        ROUND(AVG(julianday(f.discharge_date) - julianday(f.admission_date)), 1) as avg_length_of_stay,
        ROUND(SUM(f.billing_amount), 2) as total_revenue
    FROM fact_admissions f
    JOIN dim_departments d ON f.department_id = d.department_id
    WHERE f.discharge_date IS NOT NULL
    GROUP BY d.department_id
    ORDER BY workload_rank;
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_disease_distribution(db_path="src/healthcare.db"):
    query = """
    SELECT 
        c.condition_name,
        COUNT(f.admission_id) as case_count,
        ROUND(SUM(f.billing_amount), 2) as total_revenue,
        ROUND(AVG(julianday(f.discharge_date) - julianday(f.admission_date)), 1) as avg_length_of_stay
    FROM fact_admissions f
    JOIN dim_conditions c ON f.condition_id = c.condition_id
    GROUP BY c.condition_id
    ORDER BY case_count DESC;
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_monthly_admissions(db_path="src/healthcare.db"):
    # Trends over time
    query = """
    SELECT 
        strftime('%Y-%m', admission_date) as month,
        COUNT(*) as admission_count,
        ROUND(SUM(billing_amount), 2) as monthly_revenue
    FROM fact_admissions
    GROUP BY month
    ORDER BY month;
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_top_conditions_by_department(db_path="src/healthcare.db"):
    # CTE & Window Function partitioned by department
    query = """
    WITH ConditionStats AS (
        SELECT 
            d.department_name,
            c.condition_name,
            COUNT(f.admission_id) as case_count,
            SUM(f.billing_amount) as total_revenue,
            ROW_NUMBER() OVER (PARTITION BY d.department_name ORDER BY COUNT(f.admission_id) DESC) as condition_rank
        FROM fact_admissions f
        JOIN dim_departments d ON f.department_id = d.department_id
        JOIN dim_conditions c ON f.condition_id = c.condition_id
        GROUP BY d.department_name, c.condition_name
    )
    SELECT department_name, condition_name, case_count, ROUND(total_revenue, 2) as total_revenue
    FROM ConditionStats
    WHERE condition_rank <= 3
    ORDER BY department_name, case_count DESC;
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    # Test queries
    print("Testing analytics queries...")
    print(get_kpis("src/healthcare.db"))
    print("\nDepartment Workload:")
    print(get_department_workload("src/healthcare.db").head())
