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
                    exclusions TEXT,
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
                pass
            
            # Add exclusions column if it doesn't exist (migration)
            try:
                cursor.execute('ALTER TABLE investigation_standards ADD COLUMN exclusions TEXT')
                conn.commit()
            except sqlite3.OperationalError:
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
                'category': 'Diabetes'
            },
            {
                'standard_name': 'Hemoglobin',
                'aliases': 'hb,haemoglobin,hemoglobin,hgb,blood hemoglobin,blood haemoglobin',
                'male_range_min': 13.8, 'male_range_max': 17.2, 'male_unit': 'g/dL',
                'female_range_min': 12.1, 'female_range_max': 15.1, 'female_unit': 'g/dL',
                'common_unit': 'g/dL',
                'description': 'Oxygen-carrying protein in red blood cells',
                'category': 'Complete Blood Count'
            },
            {
                'standard_name': 'Total Cholesterol',
                'aliases': 'cholesterol,total chol,tc,total cholesterol',
                'male_range_min': 125, 'male_range_max': 200, 'male_unit': 'mg/dL',
                'female_range_min': 125, 'female_range_max': 200, 'female_unit': 'mg/dL',
                'common_unit': 'mg/dL',
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
        test_name_lower = test_name.lower().strip()
        standards = self.get_all_standards()
        
        best_match = None
        best_score = 0
        
        for standard in standards:
            # Check exclusions first - if test name matches any exclusion, skip this standard
            if self._matches_exclusion(test_name_lower, standard.get('exclusions', '')):
                continue
            
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
    
    def _matches_exclusion(self, test_name: str, exclusions: str) -> bool:
        """Check if test name matches any exclusion pattern (non-aliases)."""
        if not exclusions:
            return False
        
        exclusion_list = [exc.strip().lower() for exc in exclusions.split(',') if exc.strip()]
        
        for exclusion in exclusion_list:
            # Check if exclusion pattern is contained in test name or vice versa
            if exclusion in test_name or test_name in exclusion:
                return True
            # Also check fuzzy match for close matches
            if SequenceMatcher(None, exclusion, test_name).ratio() >= 0.85:
                return True
        
        return False
    
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
    
    def fuzzy_match(self, text1: str, text2: str, threshold: float = 0.6) -> bool:
        """Check if two texts match using fuzzy logic."""
        # Clean both texts
        text1_clean = self._clean_test_name(text1)
        text2_clean = self._clean_test_name(text2)
        
        # Calculate similarity
        similarity = self._calculate_similarity(text1_clean, text2_clean)
        
        return similarity >= threshold