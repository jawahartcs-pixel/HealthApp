"""
Investigation Standards Management System
Handles standardization of investigation types with fuzzy matching and reference ranges.
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re
import os
import json

class InvestigationStandards:
    def __init__(self, db_path: str = "blood_test_results.db"):
        if hasattr(db_path, 'db_path'):
            # If passed a Database object, extract the path
            self.db_path = db_path.db_path
        else:
            self.db_path = db_path
        self.init_standards_table()
        self.populate_default_standards()
    
    def init_standards_table(self):
        """Create investigation standards table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS investigation_standards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    standard_name TEXT UNIQUE NOT NULL,
                    aliases TEXT,
                    male_range_min REAL,
                    male_range_max REAL,
                    male_unit TEXT,
                    female_range_min REAL,
                    female_range_max REAL,
                    female_unit TEXT,
                    description TEXT,
                    category TEXT,
                    common_unit TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add common_unit column if it doesn't exist (migration)
            try:
                cursor.execute('ALTER TABLE investigation_standards ADD COLUMN common_unit TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Add high_causes column if it doesn't exist (migration for medical causes)
            try:
                cursor.execute('ALTER TABLE investigation_standards ADD COLUMN high_causes TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Add low_causes column if it doesn't exist (migration for medical causes)
            try:
                cursor.execute('ALTER TABLE investigation_standards ADD COLUMN low_causes TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
    
    def populate_default_standards(self):
        """Populate table with common blood test standards."""
        default_standards = [
            {
                'standard_name': 'Glucose (Fasting)',
                'aliases': 'glucose,sugar,fasting glucose,blood sugar,fbs,blood glucose',
                'male_range_min': 70, 'male_range_max': 99, 'male_unit': 'mg/dL',
                'female_range_min': 70, 'female_range_max': 99, 'female_unit': 'mg/dL',
                'common_unit': 'mg/dL',
                'description': 'Fasting blood glucose level',
                'category': 'Diabetes',
                'high_causes': 'Diabetes or prediabetes|Stress or illness|Certain medications (steroids, diuretics)|Pancreatitis|Hormonal disorders (Cushing syndrome, acromegaly)',
                'low_causes': 'Excessive insulin or diabetes medication|Prolonged fasting or malnutrition|Excessive alcohol consumption|Liver disease|Adrenal or pituitary gland disorders'
            },
            {
                'standard_name': 'Hemoglobin',
                'aliases': 'hb,haemoglobin,hemoglobin,hgb,blood hemoglobin,blood haemoglobin',
                'male_range_min': 13.8, 'male_range_max': 17.2, 'male_unit': 'g/dL',
                'female_range_min': 12.1, 'female_range_max': 15.1, 'female_unit': 'g/dL',
                'common_unit': 'g/dL',
                'description': 'Oxygen-carrying protein in red blood cells',
                'category': 'Complete Blood Count',
                'high_causes': 'Polycythemia vera|Dehydration|Living at high altitude|Lung disease (COPD)|Heart disease|Smoking',
                'low_causes': 'Anemia (iron deficiency, vitamin B12 deficiency, folate deficiency)|Blood loss|Chronic kidney disease|Bone marrow disorders|Hemolytic conditions'
            },
            {
                'standard_name': 'Total Cholesterol',
                'aliases': 'cholesterol,total chol,tc,total cholesterol',
                'male_range_min': 125, 'male_range_max': 200, 'male_unit': 'mg/dL',
                'female_range_min': 125, 'female_range_max': 200, 'female_unit': 'mg/dL',
                'common_unit': 'mg/dL',
                'description': 'Total cholesterol in blood',
                'category': 'Lipid Profile',
                'high_causes': 'Unhealthy diet high in saturated and trans fats|Lack of physical activity|Obesity|Genetic factors (familial hypercholesterolemia)|Hypothyroidism|Diabetes',
                'low_causes': 'Malnutrition or malabsorption|Hyperthyroidism|Liver disease|Chronic infections|Certain medications (statins)'
            },
            {
                'standard_name': 'HDL Cholesterol',
                'aliases': 'hdl,hdl chol,hdl cholesterol,good cholesterol',
                'male_range_min': 40, 'male_range_max': 60, 'male_unit': 'mg/dL',
                'female_range_min': 50, 'female_range_max': 60, 'female_unit': 'mg/dL',
                'description': 'High-density lipoprotein cholesterol',
                'category': 'Lipid Profile',
                'high_causes': 'Regular physical activity|Moderate alcohol consumption|Healthy diet rich in omega-3 fatty acids|Genetic factors|Weight loss',
                'low_causes': 'Sedentary lifestyle|Smoking|Obesity|Type 2 diabetes|Metabolic syndrome|Genetic factors'
            },
            {
                'standard_name': 'LDL Cholesterol',
                'aliases': 'ldl,ldl chol,ldl cholesterol,bad cholesterol',
                'male_range_min': 0, 'male_range_max': 100, 'male_unit': 'mg/dL',
                'female_range_min': 0, 'female_range_max': 100, 'female_unit': 'mg/dL',
                'description': 'Low-density lipoprotein cholesterol',
                'category': 'Lipid Profile',
                'high_causes': 'Diet high in saturated and trans fats|Lack of exercise|Obesity|Smoking|Genetic factors (familial hypercholesterolemia)|Diabetes',
                'low_causes': 'Malnutrition|Hyperthyroidism|Liver disease|Malabsorption syndromes|Statin medications'
            },
            {
                'standard_name': 'Triglycerides',
                'aliases': 'tg,triglyceride,trigs',
                'male_range_min': 0, 'male_range_max': 150, 'male_unit': 'mg/dL',
                'female_range_min': 0, 'female_range_max': 150, 'female_unit': 'mg/dL',
                'description': 'Fat molecules in blood',
                'category': 'Lipid Profile',
                'high_causes': 'Obesity|Uncontrolled diabetes|Excessive alcohol consumption|High carbohydrate diet|Sedentary lifestyle|Hypothyroidism|Kidney disease',
                'low_causes': 'Malnutrition|Malabsorption|Hyperthyroidism|Low-fat diet|Certain medications'
            },
            {
                'standard_name': 'Creatinine',
                'aliases': 'creat,creatinine,cr',
                'male_range_min': 0.74, 'male_range_max': 1.35, 'male_unit': 'mg/dL',
                'female_range_min': 0.59, 'female_range_max': 1.04, 'female_unit': 'mg/dL',
                'description': 'Kidney function marker',
                'category': 'Kidney Function',
                'high_causes': 'Chronic kidney disease|Acute kidney injury|Dehydration|High protein diet|Urinary tract obstruction|Muscle disorders (rhabdomyolysis)',
                'low_causes': 'Low muscle mass|Malnutrition|Pregnancy|Chronic illness|Liver disease'
            },
            {
                'standard_name': 'Blood Urea Nitrogen (BUN)',
                'aliases': 'bun,urea,blood urea nitrogen,urea nitrogen',
                'male_range_min': 6, 'male_range_max': 24, 'male_unit': 'mg/dL',
                'female_range_min': 6, 'female_range_max': 21, 'female_unit': 'mg/dL',
                'description': 'Kidney function and protein metabolism marker',
                'category': 'Kidney Function',
                'high_causes': 'Kidney disease or failure|Dehydration|Heart failure|High protein diet|GI bleeding|Urinary tract obstruction',
                'low_causes': 'Liver disease|Malnutrition|Overhydration|Pregnancy|Low protein diet'
            },
            {
                'standard_name': 'ALT (Alanine Aminotransferase)',
                'aliases': 'alt,alanine aminotransferase,sgpt,alat',
                'male_range_min': 10, 'male_range_max': 40, 'male_unit': 'U/L',
                'female_range_min': 7, 'female_range_max': 35, 'female_unit': 'U/L',
                'description': 'Liver enzyme',
                'category': 'Liver Function',
                'high_causes': 'Fatty liver disease (NAFLD)|Hepatitis (viral, alcoholic, autoimmune)|Liver cirrhosis|Certain medications|Muscle injury|Hemochromatosis',
                'low_causes': 'Vitamin B6 deficiency|Chronic kidney disease|Usually not clinically significant when low'
            },
            {
                'standard_name': 'AST (Aspartate Aminotransferase)',
                'aliases': 'ast,aspartate aminotransferase,sgot,asat',
                'male_range_min': 10, 'male_range_max': 40, 'male_unit': 'U/L',
                'female_range_min': 10, 'female_range_max': 35, 'female_unit': 'U/L',
                'description': 'Liver enzyme',
                'category': 'Liver Function',
                'high_causes': 'Liver disease (hepatitis, cirrhosis, fatty liver)|Heart attack|Muscle injury or disorders|Pancreatitis|Certain medications|Hemolysis',
                'low_causes': 'Vitamin B6 deficiency|Usually not clinically significant when low|Azotemia'
            },
            {
                'standard_name': 'TSH (Thyroid Stimulating Hormone)',
                'aliases': 'tsh,thyroid stimulating hormone,thyrotropin',
                'male_range_min': 0.27, 'male_range_max': 4.2, 'male_unit': 'mIU/L',
                'female_range_min': 0.27, 'female_range_max': 4.2, 'female_unit': 'mIU/L',
                'description': 'Thyroid function hormone',
                'category': 'Thyroid Function',
                'high_causes': 'Hypothyroidism (underactive thyroid)|Hashimoto thyroiditis|Iodine deficiency|Pituitary tumor|Thyroid hormone resistance',
                'low_causes': 'Hyperthyroidism (overactive thyroid)|Graves disease|Thyroid nodules|Excessive thyroid medication|Pituitary gland dysfunction'
            },
            {
                'standard_name': 'White Blood Cell Count (WBC)',
                'aliases': 'wbc,white blood cells,leukocytes,wcc',
                'male_range_min': 3.4, 'male_range_max': 10.8, 'male_unit': '10³/μL',
                'female_range_min': 3.4, 'female_range_max': 10.8, 'female_unit': '10³/μL',
                'description': 'White blood cell count',
                'category': 'Complete Blood Count',
                'high_causes': 'Infection (bacterial, viral, fungal)|Inflammation|Leukemia|Stress|Smoking|Allergic reactions|Certain medications (corticosteroids)',
                'low_causes': 'Bone marrow disorders|Autoimmune diseases|Severe infections|Chemotherapy or radiation|Vitamin deficiencies (B12, folate)|HIV/AIDS'
            },
            {
                'standard_name': 'Red Blood Cell Count (RBC)',
                'aliases': 'rbc,red blood cells,erythrocytes,rcc',
                'male_range_min': 4.7, 'male_range_max': 6.1, 'male_unit': '10⁶/μL',
                'female_range_min': 4.2, 'female_range_max': 5.4, 'female_unit': '10⁶/μL',
                'description': 'Red blood cell count',
                'category': 'Complete Blood Count',
                'high_causes': 'Dehydration|Polycythemia vera|Lung disease (COPD)|Smoking|Living at high altitude|Heart disease',
                'low_causes': 'Anemia (iron, B12, or folate deficiency)|Blood loss|Bone marrow disorders|Chronic kidney disease|Hemolysis|Pregnancy'
            },
            {
                'standard_name': 'Platelet Count',
                'aliases': 'platelets,plt,platelet count,thrombocytes',
                'male_range_min': 150, 'male_range_max': 450, 'male_unit': '10³/μL',
                'female_range_min': 150, 'female_range_max': 450, 'female_unit': '10³/μL',
                'description': 'Blood clotting cells',
                'category': 'Complete Blood Count',
                'high_causes': 'Essential thrombocythemia|Polycythemia vera|Iron deficiency|Inflammation|Cancer|Recent surgery|Splenectomy',
                'low_causes': 'Immune thrombocytopenia (ITP)|Bone marrow disorders|Viral infections|Chemotherapy|Excessive alcohol|Enlarged spleen|Certain medications'
            },
            {
                'standard_name': 'Hematocrit',
                'aliases': 'hct,hematocrit,haematocrit,pcv,packed cell volume',
                'male_range_min': 41.0, 'male_range_max': 50.0, 'male_unit': '%',
                'female_range_min': 36.0, 'female_range_max': 46.0, 'female_unit': '%',
                'description': 'Percentage of blood volume occupied by red blood cells',
                'category': 'Complete Blood Count',
                'high_causes': 'Dehydration|Polycythemia vera|Lung disease (COPD)|Smoking|Living at high altitude|Heart disease',
                'low_causes': 'Anemia (iron, B12, or folate deficiency)|Blood loss|Bone marrow disorders|Chronic kidney disease|Overhydration|Pregnancy'
            }
        ]
        
        # Insert default standards if they don't exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for standard in default_standards:
                # Check if high_causes and low_causes columns exist
                cursor.execute("PRAGMA table_info(investigation_standards)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'high_causes' in columns and 'low_causes' in columns:
                    cursor.execute('''
                        INSERT OR IGNORE INTO investigation_standards 
                        (standard_name, aliases, male_range_min, male_range_max, male_unit,
                         female_range_min, female_range_max, female_unit, description, category,
                         high_causes, low_causes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        standard['standard_name'], standard['aliases'],
                        standard['male_range_min'], standard['male_range_max'], standard['male_unit'],
                        standard['female_range_min'], standard['female_range_max'], standard['female_unit'],
                        standard['description'], standard['category'],
                        standard.get('high_causes', ''), standard.get('low_causes', '')
                    ))
                else:
                    # Fallback to old schema without causes
                    cursor.execute('''
                        INSERT OR IGNORE INTO investigation_standards 
                        (standard_name, aliases, male_range_min, male_range_max, male_unit,
                         female_range_min, female_range_max, female_unit, description, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        standard['standard_name'], standard['aliases'],
                        standard['male_range_min'], standard['male_range_max'], standard['male_unit'],
                        standard['female_range_min'], standard['female_range_max'], standard['female_unit'],
                        standard['description'], standard['category']
                    ))
            conn.commit()
            
            # Update existing records with medical causes if they don't have them
            if 'high_causes' in [col[1] for col in cursor.execute("PRAGMA table_info(investigation_standards)").fetchall()]:
                for standard in default_standards:
                    if 'high_causes' in standard and 'low_causes' in standard:
                        cursor.execute('''
                            UPDATE investigation_standards
                            SET high_causes = ?, low_causes = ?
                            WHERE standard_name = ? AND (high_causes IS NULL OR high_causes = '')
                        ''', (
                            standard.get('high_causes', ''),
                            standard.get('low_causes', ''),
                            standard['standard_name']
                        ))
                conn.commit()
    
    def get_all_standards(self) -> List[Dict]:
        """Get all investigation standards."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Check if common_unit column exists
            cursor.execute("PRAGMA table_info(investigation_standards)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'common_unit' in columns:
                cursor.execute('''
                    SELECT id, standard_name, aliases, male_range_min, male_range_max, male_unit,
                           female_range_min, female_range_max, female_unit, description, category, common_unit
                    FROM investigation_standards
                    ORDER BY category, standard_name
                ''')
                
                results = cursor.fetchall()
                standards = []
                for row in results:
                    standards.append({
                        'id': row[0],
                        'standard_name': row[1],
                        'aliases': row[2],
                        'male_range_min': row[3],
                        'male_range_max': row[4],
                        'male_unit': row[5],
                        'female_range_min': row[6],
                        'female_range_max': row[7],
                        'female_unit': row[8],
                        'description': row[9],
                        'category': row[10],
                        'common_unit': row[11]
                    })
            else:
                # Fallback to old schema
                cursor.execute('''
                    SELECT id, standard_name, aliases, male_range_min, male_range_max, male_unit,
                           female_range_min, female_range_max, female_unit, description, category
                    FROM investigation_standards
                    ORDER BY category, standard_name
                ''')
                
                results = cursor.fetchall()
                standards = []
                for row in results:
                    standards.append({
                        'id': row[0],
                        'standard_name': row[1],
                        'aliases': row[2],
                        'male_range_min': row[3],
                        'male_range_max': row[4],
                        'male_unit': row[5],
                        'female_range_min': row[6],
                        'female_range_max': row[7],
                        'female_unit': row[8],
                        'description': row[9],
                        'category': row[10],
                        'common_unit': None  # Add for compatibility
                    })
            return standards
    
    def get_test_category(self, test_name: str) -> str:
        """Get the medical category for a test name."""
        # First try to find exact match or standardize the name
        standardized_name, match_info = self.standardize_test_name(test_name)
        
        if match_info and 'category' in match_info:
            return match_info['category']
        
        # If no match found, return a default category
        return 'Other'
    
    def add_standard(self, standard_data: Dict) -> bool:
        """Add a new investigation standard."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if common_unit column exists
                cursor.execute("PRAGMA table_info(investigation_standards)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'common_unit' in columns:
                    cursor.execute('''
                        INSERT INTO investigation_standards 
                        (standard_name, aliases, male_range_min, male_range_max, male_unit,
                         female_range_min, female_range_max, female_unit, description, category, common_unit)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        standard_data['standard_name'], standard_data['aliases'],
                        standard_data['male_range_min'], standard_data['male_range_max'], standard_data['male_unit'],
                        standard_data['female_range_min'], standard_data['female_range_max'], standard_data['female_unit'],
                        standard_data['description'], standard_data['category'], standard_data.get('common_unit', '')
                    ))
                else:
                    # Fallback to old schema
                    cursor.execute('''
                        INSERT INTO investigation_standards 
                        (standard_name, aliases, male_range_min, male_range_max, male_unit,
                         female_range_min, female_range_max, female_unit, description, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        standard_data['standard_name'], standard_data['aliases'],
                        standard_data['male_range_min'], standard_data['male_range_max'], standard_data['male_unit'],
                        standard_data['female_range_min'], standard_data['female_range_max'], standard_data['female_unit'],
                        standard_data['description'], standard_data['category']
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding standard: {e}")
            return False
    
    def update_standard(self, standard_id: int, standard_data: Dict) -> bool:
        """Update an existing investigation standard and sync changes to test results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the current standard data before update for comparison
                current_standard = self.get_standard_by_id(standard_id)
                if not current_standard:
                    print(f"Error updating standard: Standard with ID {standard_id} not found")
                    return False
                
                # Check if the new standard name already exists for a different record
                cursor.execute('''
                    SELECT id FROM investigation_standards 
                    WHERE standard_name = ? AND id != ?
                ''', (standard_data['standard_name'], standard_id))
                
                existing_record = cursor.fetchone()
                if existing_record:
                    print(f"Error updating standard: Standard name '{standard_data['standard_name']}' already exists (ID: {existing_record[0]})")
                    return False
                
                # Check if common_unit column exists
                cursor.execute("PRAGMA table_info(investigation_standards)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'common_unit' in columns:
                    cursor.execute('''
                        UPDATE investigation_standards 
                        SET standard_name=?, aliases=?, male_range_min=?, male_range_max=?, male_unit=?,
                            female_range_min=?, female_range_max=?, female_unit=?, description=?, category=?,
                            common_unit=?, updated_date=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (
                        standard_data['standard_name'], standard_data['aliases'],
                        standard_data['male_range_min'], standard_data['male_range_max'], standard_data['male_unit'],
                        standard_data['female_range_min'], standard_data['female_range_max'], standard_data['female_unit'],
                        standard_data['description'], standard_data['category'], standard_data.get('common_unit', ''),
                        standard_id
                    ))
                else:
                    # Fallback to old schema
                    cursor.execute('''
                        UPDATE investigation_standards 
                        SET standard_name=?, aliases=?, male_range_min=?, male_range_max=?, male_unit=?,
                            female_range_min=?, female_range_max=?, female_unit=?, description=?, category=?,
                            updated_date=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (
                        standard_data['standard_name'], standard_data['aliases'],
                        standard_data['male_range_min'], standard_data['male_range_max'], standard_data['male_unit'],
                        standard_data['female_range_min'], standard_data['female_range_max'], standard_data['female_unit'],
                        standard_data['description'], standard_data['category'], standard_id
                    ))
                
                # Now sync changes to test results if reference ranges or units were updated
                self._sync_standard_changes_to_test_results(cursor, current_standard, standard_data)
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating standard: {e}")
            return False
    
    def get_predefined_categories(self) -> List[str]:
        """Get predefined medical categories for investigation standards."""
        return [
            'Complete Blood Count',
            'Lipid Profile',
            'Liver Function',
            'Kidney Function',
            'Thyroid Function',
            'Diabetes',
            'Cardiac Markers',
            'Electrolytes',
            'Vitamins & Minerals',
            'Hormones',
            'Inflammatory Markers',
            'Coagulation Studies',
            'Tumor Markers',
            'Immunology',
            'Infectious Disease',
            'Toxicology',
            'Metabolic Panel',
            'Bone Markers',
            'Autoimmune',
            'Hematology',
            'Other'
        ]
    
    def check_standard_name_exists(self, name: str, exclude_id: int = None) -> bool:
        """Check if a standard name already exists (case-insensitive)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if exclude_id:
                cursor.execute('''
                    SELECT id FROM investigation_standards 
                    WHERE LOWER(standard_name) = LOWER(?) AND id != ?
                ''', (name, exclude_id))
            else:
                cursor.execute('''
                    SELECT id FROM investigation_standards 
                    WHERE LOWER(standard_name) = LOWER(?)
                ''', (name,))
            return cursor.fetchone() is not None
    
    def get_similar_standard_names(self, name: str, limit: int = 5) -> List[str]:
        """Get standard names similar to the provided name."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT standard_name FROM investigation_standards')
            all_names = [row[0] for row in cursor.fetchall()]
            
            # Simple similarity check based on common words
            name_lower = name.lower()
            similar = []
            
            for existing_name in all_names:
                existing_lower = existing_name.lower()
                # Check if names share common words or substrings
                if (name_lower in existing_lower or existing_lower in name_lower or
                    any(word in existing_lower for word in name_lower.split() if len(word) > 2)):
                    similar.append(existing_name)
            
            return similar[:limit]
    
    def delete_standard(self, standard_id: int) -> bool:
        """Delete an investigation standard."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM investigation_standards WHERE id=?', (standard_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting standard: {e}")
            return False
    
    def find_best_match(self, test_name: str, unit: str = '', threshold: float = 0.6) -> Optional[Dict]:
        """Find the best matching standard for a given test name and unit using fuzzy logic."""
        test_name_clean = self._clean_test_name(test_name)
        standards = self.get_all_standards()
        
        best_match = None
        best_score = 0
        
        for standard in standards:
            # Check direct match with standard name
            standard_name_clean = self._clean_test_name(standard['standard_name'])
            text_score = self._calculate_similarity(test_name_clean, standard_name_clean)
            
            # Calculate unit compatibility score
            unit_score = self._calculate_unit_compatibility(unit, standard)
            
            # Combine text and unit scores (weighted: 70% text, 30% unit)
            combined_score = (text_score * 0.7) + (unit_score * 0.3)
            
            if combined_score > best_score and combined_score >= threshold:
                best_score = combined_score
                best_match = standard
            
            # Check aliases
            if standard['aliases']:
                aliases = [alias.strip() for alias in standard['aliases'].split(',')]
                for alias in aliases:
                    alias_clean = self._clean_test_name(alias)
                    text_score = self._calculate_similarity(test_name_clean, alias_clean)
                    unit_score = self._calculate_unit_compatibility(unit, standard)
                    
                    # Combine text and unit scores
                    combined_score = (text_score * 0.7) + (unit_score * 0.3)
                    
                    if combined_score > best_score and combined_score >= threshold:
                        best_score = combined_score
                        best_match = standard
        
        if best_match:
            best_match['match_score'] = best_score
        
        return best_match
    
    def _clean_test_name(self, name: str) -> str:
        """Clean test name for better matching."""
        name = name.lower().strip()
        # Remove common prefixes/suffixes
        name = re.sub(r'\b(test|level|count|total|serum|plasma|blood)\b', '', name)
        # Remove parentheses and brackets
        name = re.sub(r'[\(\)\[\]]', '', name)
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Exact match
        if text1 == text2:
            return 1.0
        
        # Substring match
        if text1 in text2 or text2 in text1:
            return 0.9
        
        # Sequence matcher
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _sync_standard_changes_to_test_results(self, cursor, current_standard: Dict, updated_data: Dict):
        """Synchronize changes from investigation standards to matching test results."""
        try:
            # Check if reference ranges or units changed
            unit_changed = False
            reference_changed = False
            
            # Get the unit to use (common_unit or male_unit as fallback)
            old_unit = current_standard.get('common_unit') or current_standard.get('male_unit', '')
            new_unit = updated_data.get('common_unit') or updated_data.get('male_unit', '')
            
            if old_unit != new_unit:
                unit_changed = True
            
            # Check if reference ranges changed
            old_male_min = current_standard.get('male_range_min')
            old_male_max = current_standard.get('male_range_max')
            old_female_min = current_standard.get('female_range_min')
            old_female_max = current_standard.get('female_range_max')
            
            new_male_min = updated_data.get('male_range_min')
            new_male_max = updated_data.get('male_range_max')
            new_female_min = updated_data.get('female_range_min')
            new_female_max = updated_data.get('female_range_max')
            
            if (old_male_min != new_male_min or old_male_max != new_male_max or 
                old_female_min != new_female_min or old_female_max != new_female_max):
                reference_changed = True
            
            # If either unit or reference range changed, update test results
            if unit_changed or reference_changed:
                # Get all test names that match this standard (including aliases)
                test_names_to_update = [current_standard['standard_name']]
                
                # Add aliases
                if current_standard.get('aliases'):
                    aliases = [alias.strip() for alias in current_standard['aliases'].split(',')]
                    test_names_to_update.extend(aliases)
                
                # Update test results for each matching test name
                for test_name in test_names_to_update:
                    if unit_changed:
                        # Update unit
                        cursor.execute('''
                            UPDATE test_results 
                            SET unit = ? 
                            WHERE LOWER(test_type) = LOWER(?)
                        ''', (new_unit, test_name))
                        
                        print(f"Updated unit for '{test_name}' from '{old_unit}' to '{new_unit}'")
                    
                    if reference_changed:
                        # Format new reference range
                        new_reference_range = self._format_reference_range(
                            new_male_min, new_male_max, new_female_min, new_female_max, new_unit
                        )
                        
                        # Update reference range
                        cursor.execute('''
                            UPDATE test_results 
                            SET reference_range = ? 
                            WHERE LOWER(test_type) = LOWER(?)
                        ''', (new_reference_range, test_name))
                        
                        print(f"Updated reference range for '{test_name}' to '{new_reference_range}'")
                        
        except Exception as e:
            print(f"Error syncing standard changes to test results: {e}")
    
    def _format_reference_range(self, male_min, male_max, female_min, female_max, unit):
        """Format reference range string from individual components."""
        try:
            # If male and female ranges are the same, show single range
            if (male_min == female_min and male_max == female_max):
                if male_min is not None and male_max is not None:
                    return f"{male_min}-{male_max} {unit}".strip()
            
            # Show separate ranges for male and female
            range_parts = []
            if male_min is not None and male_max is not None:
                range_parts.append(f"M: {male_min}-{male_max}")
            if female_min is not None and female_max is not None:
                range_parts.append(f"F: {female_min}-{female_max}")
            
            if range_parts:
                return f"{', '.join(range_parts)} {unit}".strip()
            
            return ""
        except:
            return ""

    def get_standard_by_id(self, standard_id: int) -> Optional[Dict]:
        """Get a single investigation standard by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Check if common_unit column exists
                cursor.execute("PRAGMA table_info(investigation_standards)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'common_unit' in columns:
                    cursor.execute('''
                        SELECT id, standard_name, aliases, male_range_min, male_range_max, male_unit,
                               female_range_min, female_range_max, female_unit, description, category, common_unit
                        FROM investigation_standards
                        WHERE id = ?
                    ''', (standard_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': row[0],
                            'standard_name': row[1],
                            'aliases': row[2],
                            'male_range_min': row[3],
                            'male_range_max': row[4],
                            'male_unit': row[5],
                            'female_range_min': row[6],
                            'female_range_max': row[7],
                            'female_unit': row[8],
                            'description': row[9],
                            'category': row[10],
                            'common_unit': row[11]
                        }
                else:
                    cursor.execute('''
                        SELECT id, standard_name, aliases, male_range_min, male_range_max, male_unit,
                               female_range_min, female_range_max, female_unit, description, category
                        FROM investigation_standards
                        WHERE id = ?
                    ''', (standard_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': row[0],
                            'standard_name': row[1],
                            'aliases': row[2],
                            'male_range_min': row[3],
                            'male_range_max': row[4],
                            'male_unit': row[5],
                            'female_range_min': row[6],
                            'female_range_max': row[7],
                            'female_unit': row[8],
                            'description': row[9],
                            'category': row[10],
                            'common_unit': None
                        }
                return None
        except Exception as e:
            print(f"Error getting standard by ID: {e}")
            return None
    
    def sync_all_standards_to_test_results(self) -> Dict[str, int]:
        """Manually synchronize all investigation standards to test results.
        Overwrites existing values to ensure data consistency.
        Returns count of updated records."""
        try:
            updated_counts = {'units': 0, 'reference_ranges': 0}
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all standards
                standards = self.get_all_standards()
                
                for standard in standards:
                    # Get all test names that match this standard
                    test_names_to_update = [standard['standard_name']]
                    
                    # Add aliases
                    if standard.get('aliases'):
                        aliases = [alias.strip() for alias in standard['aliases'].split(',')]
                        test_names_to_update.extend(aliases)
                    
                    # Get the unit to use
                    unit = standard.get('common_unit') or standard.get('male_unit', '')
                    
                    # Format reference range
                    reference_range = self._format_reference_range(
                        standard.get('male_range_min'),
                        standard.get('male_range_max'),
                        standard.get('female_range_min'),
                        standard.get('female_range_max'),
                        unit
                    )
                    
                    # Update test results for each matching test name
                    for test_name in test_names_to_update:
                        if unit:
                            cursor.execute('''
                                UPDATE test_results 
                                SET unit = ? 
                                WHERE LOWER(test_type) = LOWER(?)
                            ''', (unit, test_name))
                            updated_counts['units'] += cursor.rowcount
                        
                        if reference_range:
                            cursor.execute('''
                                UPDATE test_results 
                                SET reference_range = ? 
                                WHERE LOWER(test_type) = LOWER(?)
                            ''', (reference_range, test_name))
                            updated_counts['reference_ranges'] += cursor.rowcount
                
                conn.commit()
                return updated_counts
                
        except Exception as e:
            print(f"Error syncing all standards to test results: {e}")
            return {'units': 0, 'reference_ranges': 0}

    def _calculate_unit_compatibility(self, extracted_unit: str, standard: Dict) -> float:
        """Calculate how compatible the extracted unit is with the standard's unit."""
        if not extracted_unit:
            return 0.5  # Neutral score if no unit provided
        
        # Get the standard's unit (use common_unit if available, otherwise fallback)
        standard_unit = standard.get('common_unit') or standard.get('male_unit') or standard.get('female_unit') or ''
        
        if not standard_unit:
            return 0.5  # Neutral score if standard has no unit
        
        # Normalize both units for comparison
        extracted_clean = self._normalize_unit_for_comparison(extracted_unit)
        standard_clean = self._normalize_unit_for_comparison(standard_unit)
        
        # Exact match
        if extracted_clean == standard_clean:
            return 1.0
        
        # Check for equivalent units
        unit_equivalents = {
            'mg/dl': ['mg/dl', 'mg/100ml'],
            'mmol/l': ['mmol/l', 'mmol/litre'],
            'g/dl': ['g/dl', 'g/100ml'],
            'u/l': ['u/l', 'iu/l', 'units/l'],
            '%': ['%', 'percent', 'per cent'],
            'ng/ml': ['ng/ml', 'ng/millilitre'],
            'pg/ml': ['pg/ml', 'pg/millilitre'],
            'meq/l': ['meq/l', 'mmol/l']  # Sometimes used interchangeably
        }
        
        for unit_group in unit_equivalents.values():
            if extracted_clean in unit_group and standard_clean in unit_group:
                return 0.9
        
        # Partial match (contains similar elements)
        if extracted_clean in standard_clean or standard_clean in extracted_clean:
            return 0.7
        
        # Different units but both are medical units
        if self._is_medical_unit(extracted_clean) and self._is_medical_unit(standard_clean):
            return 0.3
        
        return 0.0
    
    def _normalize_unit_for_comparison(self, unit: str) -> str:
        """Normalize unit for comparison purposes."""
        if not unit:
            return ''
        
        unit = unit.lower().strip()
        
        # Remove common variations
        unit = unit.replace('/', 'per')
        unit = unit.replace(' ', '')
        unit = unit.replace('.', '')
        
        return unit
    
    def _is_medical_unit(self, unit: str) -> bool:
        """Check if a unit appears to be a medical unit."""
        medical_units = [
            'mg', 'dl', 'mmol', 'l', 'g', 'ng', 'ml', 'pg', 'u', 'iu', 'meq',
            'percent', '%', 'cells', 'ul', 'thousand', 'million'
        ]
        
        unit_lower = unit.lower()
        return any(med_unit in unit_lower for med_unit in medical_units)
    
    def standardize_test_name(self, test_name: str, unit: str = '') -> Tuple[str, Optional[Dict]]:
        """Standardize a test name and return the standard name and reference ranges."""
        match = self.find_best_match(test_name, unit)
        if match:
            return match['standard_name'], match
        else:
            return test_name, None
    
    def get_reference_range(self, standard_name: str, gender: str = 'both') -> Optional[str]:
        """Get reference range for a standard test."""
        standards = self.get_all_standards()
        for standard in standards:
            if standard['standard_name'] == standard_name:
                if gender.lower() == 'male':
                    return f"{standard['male_range_min']}-{standard['male_range_max']} {standard['male_unit']}"
                elif gender.lower() == 'female':
                    return f"{standard['female_range_min']}-{standard['female_range_max']} {standard['female_unit']}"
                else:
                    male_range = f"M: {standard['male_range_min']}-{standard['male_range_max']} {standard['male_unit']}"
                    female_range = f"F: {standard['female_range_min']}-{standard['female_range_max']} {standard['female_unit']}"
                    return f"{male_range}, {female_range}"
        return None
    
    def get_medical_causes(self, test_name: str, status: str = 'high') -> List[str]:
        """Get medical causes for abnormal test values.
        
        Args:
            test_name: The test name (will be standardized)
            status: 'high' or 'low' to indicate which causes to retrieve
        
        Returns:
            List of possible medical causes
        """
        # Standardize the test name to match against standards
        standardized_name, match_info = self.standardize_test_name(test_name)
        
        if not match_info:
            return []
        
        # Get the causes from the database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if causes columns exist
            cursor.execute("PRAGMA table_info(investigation_standards)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'high_causes' not in columns or 'low_causes' not in columns:
                return []
            
            # Retrieve causes based on status
            column = 'high_causes' if status.lower() == 'high' else 'low_causes'
            cursor.execute(f'''
                SELECT {column}
                FROM investigation_standards
                WHERE standard_name = ?
            ''', (standardized_name,))
            
            result = cursor.fetchone()
            if result and result[0]:
                # Split the pipe-separated causes into a list
                causes = result[0].split('|')
                return [cause.strip() for cause in causes if cause.strip()]
        
        return []
    
    def research_medical_causes_with_ai(self, test_name: str) -> Dict[str, List[str]]:
        """Research medical causes using OpenAI when not in database.
        
        Args:
            test_name: The standardized test name
        
        Returns:
            Dictionary with 'high' and 'low' keys containing lists of medical causes
        """
        try:
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            from openai import OpenAI
            
            AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
            AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
            
            if not AI_INTEGRATIONS_OPENAI_API_KEY or not AI_INTEGRATIONS_OPENAI_BASE_URL:
                print("OpenAI integration not configured. Skipping AI research.")
                return {'high': [], 'low': []}
            
            openai = OpenAI(
                api_key=AI_INTEGRATIONS_OPENAI_API_KEY,
                base_url=AI_INTEGRATIONS_OPENAI_BASE_URL
            )
            
            prompt = f"""You are a medical expert. Provide common medical causes for abnormal blood test values.

Blood Test: {test_name}

Please provide:
1. 5-7 common medical causes for HIGH values
2. 5-7 common medical causes for LOW values

Format your response as a JSON object with this exact structure:
{{
  "high": ["cause 1", "cause 2", "cause 3", ...],
  "low": ["cause 1", "cause 2", "cause 3", ...]
}}

Keep each cause concise (under 50 characters). Focus on the most common and clinically relevant causes."""

            response = openai.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_completion_tokens=2048
            )
            
            content = response.choices[0].message.content or "{}"
            causes_data = json.loads(content)
            
            return {
                'high': causes_data.get('high', []),
                'low': causes_data.get('low', [])
            }
            
        except Exception as e:
            print(f"Error researching medical causes with AI: {e}")
            return {'high': [], 'low': []}
    
    def update_medical_causes(self, standard_name: str, high_causes: List[str], low_causes: List[str]) -> bool:
        """Update medical causes in the database for a specific test.
        
        Args:
            standard_name: The standardized test name
            high_causes: List of causes for high values
            low_causes: List of causes for low values
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if causes columns exist
                cursor.execute("PRAGMA table_info(investigation_standards)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'high_causes' not in columns or 'low_causes' not in columns:
                    return False
                
                # Convert lists to pipe-separated strings
                high_causes_str = '|'.join(high_causes) if high_causes else ''
                low_causes_str = '|'.join(low_causes) if low_causes else ''
                
                # Update the database
                cursor.execute('''
                    UPDATE investigation_standards
                    SET high_causes = ?, low_causes = ?
                    WHERE standard_name = ?
                ''', (high_causes_str, low_causes_str, standard_name))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating medical causes in database: {e}")
            return False
    
    def get_medical_causes_with_ai_fallback(self, test_name: str, status: str = 'high') -> List[str]:
        """Get medical causes with automatic AI research fallback.
        
        This method first tries to get causes from the database. If not found,
        it uses AI to research the causes and saves them for future use.
        
        Args:
            test_name: The test name (will be standardized)
            status: 'high' or 'low' to indicate which causes to retrieve
        
        Returns:
            List of possible medical causes
        """
        # First try to get from database
        causes = self.get_medical_causes(test_name, status)
        
        if causes:
            return causes
        
        # If not found, standardize the test name
        standardized_name, match_info = self.standardize_test_name(test_name)
        
        if not match_info:
            return []
        
        # Research using AI
        print(f"Researching medical causes for {standardized_name} using AI...")
        causes_data = self.research_medical_causes_with_ai(standardized_name)
        
        if causes_data['high'] or causes_data['low']:
            # Save to database for future use
            self.update_medical_causes(standardized_name, causes_data['high'], causes_data['low'])
            print(f"Medical causes for {standardized_name} saved to database")
            
            # Return the requested causes
            return causes_data.get(status.lower(), [])
        
        return []
    
    def fuzzy_match(self, text1: str, text2: str, threshold: float = 0.6) -> bool:
        """Check if two texts match using fuzzy logic."""
        # Clean both texts
        text1_clean = self._clean_test_name(text1)
        text2_clean = self._clean_test_name(text2)
        
        # Calculate similarity
        similarity = self._calculate_similarity(text1_clean, text2_clean)
        
        return similarity >= threshold