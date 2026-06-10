import csv
import random
from datetime import datetime, timedelta

def generate_healthcare_data(filename, num_records=5000, seed=42, inject_anomalies=False):
    random.seed(seed)
    
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Elizabeth",
                   "William", "Linda", "David", "Elizabeth", "Richard", "Barbara", "Joseph", "Susan",
                   "Thomas", "Jessica", "Charles", "Sarah", "Christopher", "Karen", "Daniel", "Nancy",
                   "Matthew", "Lisa", "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra"]
    
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
                  "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris"]
    
    genders = ["Male", "Female", "Other"]
    blood_types = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
    
    # Conditions and their primary departments/average costs
    conditions_info = {
        "Heart Attack": {"dept": "Cardiology", "avg_cost": 15000, "stay_range": (5, 15)},
        "Stroke": {"dept": "Neurology", "avg_cost": 18000, "stay_range": (7, 20)},
        "Pneumonia": {"dept": "Emergency", "avg_cost": 5000, "stay_range": (3, 10)},
        "Asthma": {"dept": "Emergency", "avg_cost": 2500, "stay_range": (1, 5)},
        "Diabetes": {"dept": "Endocrinology", "avg_cost": 4000, "stay_range": (2, 7)},
        "Hypertension": {"dept": "General Practice", "avg_cost": 1500, "stay_range": (1, 3)},
        "Leukemia": {"dept": "Oncology", "avg_cost": 28000, "stay_range": (10, 30)},
        "Appendicitis": {"dept": "Surgery", "avg_cost": 8000, "stay_range": (2, 5)},
        "Bone Fracture": {"dept": "Orthopedics", "avg_cost": 6000, "stay_range": (2, 7)},
        "Arthritis": {"dept": "Orthopedics", "avg_cost": 2000, "stay_range": (1, 4)}
    }
    
    admission_types = ["Emergency", "Elective", "Urgent"]
    test_results = ["Normal", "Abnormal", "Inconclusive"]
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 5, 30)
    days_range = (end_date - start_date).days
    
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Patient ID", "Patient Name", "Age", "Gender", "Blood Type",
            "Medical Condition", "Admission Date", "Discharge Date",
            "Billing Amount", "Hospital Department", "Admission Type", "Test Results"
        ])
        
        for i in range(num_records):
            patient_num = 10001 + i
            patient_id = f"PT-{patient_num}"
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
            # Age distribution skewing slightly older
            age_rand = random.random()
            if age_rand < 0.15:
                age = random.randint(0, 17) # Pediatrics
            elif age_rand < 0.5:
                age = random.randint(18, 55)
            else:
                age = random.randint(56, 95)
                
            gender = random.choice(genders)
            blood_type = random.choice(blood_types)
            
            condition = random.choice(list(conditions_info.keys()))
            info = conditions_info[condition]
            
            # Dates
            random_days = random.randint(0, days_range)
            adm_date = start_date + timedelta(days=random_days)
            
            stay_days = random.randint(info["stay_range"][0], info["stay_range"][1])
            dis_date = adm_date + timedelta(days=stay_days)
            
            # Billing: base + variability based on stay length
            billing_base = info["avg_cost"]
            billing = billing_base * random.uniform(0.8, 1.3) + (stay_days * 150)
            billing = round(billing, 2)
            
            dept = info["dept"]
            # Correct department for kids under 14 sometimes overrides
            if age < 14 and random.random() < 0.8:
                dept = "Pediatrics"
                
            adm_type = random.choice(admission_types)
            test_res = random.choice(test_results)
            
            # Ingestion fields format
            adm_str = adm_date.strftime("%Y-%m-%d")
            dis_str = dis_date.strftime("%Y-%m-%d")
            
            # Anomalies injection (for testing the pipeline)
            if inject_anomalies and i % 50 == 0:
                anomaly_type = i % 4
                if anomaly_type == 0:
                    # Discharge before admission
                    dis_str = (adm_date - timedelta(days=2)).strftime("%Y-%m-%d")
                elif anomaly_type == 1:
                    # Negative billing amount
                    billing = -1500.00
                elif anomaly_type == 2:
                    # Age sanity outlier
                    age = 135
                elif anomaly_type == 3:
                    # Missing critical values
                    billing = ""
                    dis_str = ""
            
            writer.writerow([
                patient_id, name, age, gender, blood_type,
                condition, adm_str, dis_str, billing,
                dept, adm_type, test_res
            ])

if __name__ == "__main__":
    print("Generating main healthcare analytics seed dataset...")
    generate_healthcare_data("healthcare_data_raw.csv", num_records=5000)
    print("Healthcare dataset generated successfully!")
    
    print("Generating validation test dataset (with anomalies)...")
    generate_healthcare_data("healthcare_data_dirty.csv", num_records=200, seed=99, inject_anomalies=True)
    print("Validation test dataset generated successfully!")
