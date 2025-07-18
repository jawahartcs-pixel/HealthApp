"""
Investigation Standards Management System
Handles standardization of investigation types with fuzzy matching and reference ranges.
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re

class InvestigationStandards:
    def __init__(self, db_path: str = "blood_test_results.db"):
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
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def populate_default_standards(self):
        """Populate table with common blood test standards."""
        default_standards = [
            {
                'standard_name': 'Glucose (Fasting)',
                'aliases': 'glucose,sugar,fasting glucose,blood sugar,fbs,blood glucose',
                'male_range_min': 70, 'male_range_max': 99, 'male_unit': 'mg/dL',
                'female_range_min': 70, 'female_range_max': 99, 'female_unit': 'mg/dL',
                'description': 'Fasting blood glucose level',
                'category': 'Diabetes'
            },
            {
                'standard_name': 'Hemoglobin',
                'aliases': 'hb,haemoglobin,hemoglobin,hgb',
                'male_range_min': 13.8, 'male_range_max': 17.2, 'male_unit': 'g/dL',
                'female_range_min': 12.1, 'female_range_max': 15.1, 'female_unit': 'g/dL',
                'description': 'Oxygen-carrying protein in red blood cells',
                'category': 'Complete Blood Count'
            },
            {
                'standard_name': 'Total Cholesterol',
                'aliases': 'cholesterol,total chol,tc,total cholesterol',
                'male_range_min': 125, 'male_range_max': 200, 'male_unit': 'mg/dL',
                'female_range_min': 125, 'female_range_max': 200, 'female_unit': 'mg/dL',
                'description': 'Total cholesterol in blood',
                'category': 'Lipid Profile'
            },
            {
                'standard_name': 'HDL Cholesterol',
                'aliases': 'hdl,hdl chol,hdl cholesterol,good cholesterol',
                'male_range_min': 40, 'male_range_max': 60, 'male_unit': 'mg/dL',
                'female_range_min': 50, 'female_range_max': 60, 'female_unit': 'mg/dL',
                'description': 'High-density lipoprotein cholesterol',
                'category': 'Lipid Profile'
            },
            {
                'standard_name': 'LDL Cholesterol',
                'aliases': 'ldl,ldl chol,ldl cholesterol,bad cholesterol',
                'male_range_min': 0, 'male_range_max': 100, 'male_unit': 'mg/dL',
                'female_range_min': 0, 'female_range_max': 100, 'female_unit': 'mg/dL',
                'description': 'Low-density lipoprotein cholesterol',
                'category': 'Lipid Profile'
            },
            {
                'standard_name': 'Triglycerides',
                'aliases': 'tg,triglyceride,trigs',
                'male_range_min': 0, 'male_range_max': 150, 'male_unit': 'mg/dL',
                'female_range_min': 0, 'female_range_max': 150, 'female_unit': 'mg/dL',
                'description': 'Fat molecules in blood',
                'category': 'Lipid Profile'
            },
            {
                'standard_name': 'Creatinine',
                'aliases': 'creat,creatinine,cr',
                'male_range_min': 0.74, 'male_range_max': 1.35, 'male_unit': 'mg/dL',
                'female_range_min': 0.59, 'female_range_max': 1.04, 'female_unit': 'mg/dL',
                'description': 'Kidney function marker',
                'category': 'Kidney Function'
            },
            {
                'standard_name': 'Blood Urea Nitrogen (BUN)',
                'aliases': 'bun,urea,blood urea nitrogen,urea nitrogen',
                'male_range_min': 6, 'male_range_max': 24, 'male_unit': 'mg/dL',
                'female_range_min': 6, 'female_range_max': 21, 'female_unit': 'mg/dL',
                'description': 'Kidney function and protein metabolism marker',
                'category': 'Kidney Function'
            },
            {
                'standard_name': 'ALT (Alanine Aminotransferase)',
                'aliases': 'alt,alanine aminotransferase,sgpt,alat',
                'male_range_min': 10, 'male_range_max': 40, 'male_unit': 'U/L',
                'female_range_min': 7, 'female_range_max': 35, 'female_unit': 'U/L',
                'description': 'Liver enzyme',
                'category': 'Liver Function'
            },
            {
                'standard_name': 'AST (Aspartate Aminotransferase)',
                'aliases': 'ast,aspartate aminotransferase,sgot,asat',
                'male_range_min': 10, 'male_range_max': 40, 'male_unit': 'U/L',
                'female_range_min': 10, 'female_range_max': 35, 'female_unit': 'U/L',
                'description': 'Liver enzyme',
                'category': 'Liver Function'
            },
            {
                'standard_name': 'TSH (Thyroid Stimulating Hormone)',
                'aliases': 'tsh,thyroid stimulating hormone,thyrotropin',
                'male_range_min': 0.27, 'male_range_max': 4.2, 'male_unit': 'mIU/L',
                'female_range_min': 0.27, 'female_range_max': 4.2, 'female_unit': 'mIU/L',
                'description': 'Thyroid function hormone',
                'category': 'Thyroid Function'
            },
            {
                'standard_name': 'White Blood Cell Count (WBC)',
                'aliases': 'wbc,white blood cells,leukocytes,wcc',
                'male_range_min': 3.4, 'male_range_max': 10.8, 'male_unit': '10³/μL',
                'female_range_min': 3.4, 'female_range_max': 10.8, 'female_unit': '10³/μL',
                'description': 'White blood cell count',
                'category': 'Complete Blood Count'
            },
            {
                'standard_name': 'Red Blood Cell Count (RBC)',
                'aliases': 'rbc,red blood cells,erythrocytes,rcc',
                'male_range_min': 4.7, 'male_range_max': 6.1, 'male_unit': '10⁶/μL',
                'female_range_min': 4.2, 'female_range_max': 5.4, 'female_unit': '10⁶/μL',
                'description': 'Red blood cell count',
                'category': 'Complete Blood Count'
            },
            {
                'standard_name': 'Platelet Count',
                'aliases': 'platelets,plt,platelet count,thrombocytes',
                'male_range_min': 150, 'male_range_max': 450, 'male_unit': '10³/μL',
                'female_range_min': 150, 'female_range_max': 450, 'female_unit': '10³/μL',
                'description': 'Blood clotting cells',
                'category': 'Complete Blood Count'
            },
            {
                'standard_name': 'Hematocrit',
                'aliases': 'hct,hematocrit,haematocrit,pcv,packed cell volume',
                'male_range_min': 41.0, 'male_range_max': 50.0, 'male_unit': '%',
                'female_range_min': 36.0, 'female_range_max': 46.0, 'female_unit': '%',
                'description': 'Percentage of blood volume occupied by red blood cells',
                'category': 'Complete Blood Count'
            }
        ]
        
        # Insert default standards if they don't exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for standard in default_standards:
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
    
    def get_all_standards(self) -> List[Dict]:
        """Get all investigation standards."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
                    'category': row[10]
                })
            return standards
    
    def add_standard(self, standard_data: Dict) -> bool:
        """Add a new investigation standard."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
        """Update an existing investigation standard."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating standard: {e}")
            return False
    
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
    
    def find_best_match(self, test_name: str, threshold: float = 0.6) -> Optional[Dict]:
        """Find the best matching standard for a given test name using fuzzy logic."""
        test_name_clean = self._clean_test_name(test_name)
        standards = self.get_all_standards()
        
        best_match = None
        best_score = 0
        
        for standard in standards:
            # Check direct match with standard name
            standard_name_clean = self._clean_test_name(standard['standard_name'])
            score = self._calculate_similarity(test_name_clean, standard_name_clean)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = standard
            
            # Check aliases
            if standard['aliases']:
                aliases = [alias.strip() for alias in standard['aliases'].split(',')]
                for alias in aliases:
                    alias_clean = self._clean_test_name(alias)
                    score = self._calculate_similarity(test_name_clean, alias_clean)
                    
                    if score > best_score and score >= threshold:
                        best_score = score
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
    
    def standardize_test_name(self, test_name: str) -> Tuple[str, Optional[Dict]]:
        """Standardize a test name and return the standard name and reference ranges."""
        match = self.find_best_match(test_name)
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