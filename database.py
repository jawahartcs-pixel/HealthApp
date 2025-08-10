import sqlite3
import os
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict, Any
import pandas as pd

class Database:
    def __init__(self, db_path: str = "blood_test_results.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create patients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT NOT NULL,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(patient_name, user_id)
                )
            ''')
            
            # Create test_results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    test_date DATE NOT NULL,
                    test_type TEXT NOT NULL,
                    test_value REAL NOT NULL,
                    unit TEXT,
                    reference_range TEXT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_patient_name ON patients(patient_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_date ON test_results(test_date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_type ON test_results(test_type)
            ''')
            
            # Handle migration - add user_id columns if they don't exist
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN user_id INTEGER')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE test_results ADD COLUMN user_id INTEGER')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Add new patient profile columns
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN age INTEGER')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN gender TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN phone TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN email TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN address TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN medical_history TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN medications TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN allergies TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN emergency_contact TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN notes TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Create patient_documents table for uploaded reports
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_documents (
                    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    document_name TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT,
                    file_size INTEGER,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    description TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            ''')
            
            # Create index for patient documents
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_patient_documents ON patient_documents(patient_id)
            ''')
            
            # Create indexes after columns are added
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id ON patients(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_user_id ON test_results(user_id)
            ''')
            
            conn.commit()
    
    def add_patient(self, patient_name: str, user_id: int = None, age: int = None, 
                   gender: str = None, phone: str = None, email: str = None, 
                   address: str = None, medical_history: str = None, 
                   medications: str = None, allergies: str = None, 
                   emergency_contact: str = None, notes: str = None) -> int:
        """Add a new patient or get existing patient ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to get existing patient for this user
            if user_id:
                cursor.execute('SELECT patient_id FROM patients WHERE patient_name = ? AND user_id = ?', (patient_name, user_id))
            else:
                cursor.execute('SELECT patient_id FROM patients WHERE patient_name = ? AND user_id IS NULL', (patient_name,))
            
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Add new patient with profile data
            cursor.execute('''
                INSERT INTO patients (patient_name, user_id, age, gender, phone, email, 
                                    address, medical_history, medications, allergies, 
                                    emergency_contact, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_name, user_id, age, gender, phone, email, address, 
                  medical_history, medications, allergies, emergency_contact, notes))
            conn.commit()
            return cursor.lastrowid
    
    def update_patient_profile(self, patient_id: int, age: int = None, gender: str = None, 
                              phone: str = None, email: str = None, address: str = None, 
                              medical_history: str = None, medications: str = None, 
                              allergies: str = None, emergency_contact: str = None, 
                              notes: str = None) -> bool:
        """Update patient profile information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE patients SET 
                        age = ?, gender = ?, phone = ?, email = ?, address = ?,
                        medical_history = ?, medications = ?, allergies = ?, 
                        emergency_contact = ?, notes = ?
                    WHERE patient_id = ?
                ''', (age, gender, phone, email, address, medical_history, 
                      medications, allergies, emergency_contact, notes, patient_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating patient profile: {e}")
            return False
    
    def get_patient_profile(self, patient_name: str, user_id: int = None) -> Optional[Dict]:
        """Get complete patient profile including all fields."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('''
                        SELECT patient_id, patient_name, age, gender, phone, email, address,
                               medical_history, medications, allergies, emergency_contact, 
                               notes, created_at
                        FROM patients 
                        WHERE patient_name = ? AND user_id = ?
                    ''', (patient_name, user_id))
                else:
                    cursor.execute('''
                        SELECT patient_id, patient_name, age, gender, phone, email, address,
                               medical_history, medications, allergies, emergency_contact, 
                               notes, created_at
                        FROM patients 
                        WHERE patient_name = ? AND user_id IS NULL
                    ''', (patient_name,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'patient_id': result[0],
                        'patient_name': result[1],
                        'age': result[2],
                        'gender': result[3],
                        'phone': result[4],
                        'email': result[5],
                        'address': result[6],
                        'medical_history': result[7],
                        'medications': result[8],
                        'allergies': result[9],
                        'emergency_contact': result[10],
                        'notes': result[11],
                        'created_at': result[12]
                    }
                return None
        except Exception as e:
            print(f"Error getting patient profile: {e}")
            return None
    
    def add_patient_document(self, patient_id: int, document_name: str, 
                           original_filename: str, file_path: str, file_type: str, 
                           file_size: int, user_id: int = None, 
                           description: str = None) -> bool:
        """Add a document for a patient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO patient_documents 
                    (patient_id, document_name, original_filename, file_path, 
                     file_type, file_size, user_id, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (patient_id, document_name, original_filename, file_path, 
                      file_type, file_size, user_id, description))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding patient document: {e}")
            return False
    
    def get_patient_documents(self, patient_id: int, user_id: int = None) -> List[Dict]:
        """Get all documents for a patient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('''
                        SELECT document_id, document_name, original_filename, file_path,
                               file_type, file_size, upload_date, description
                        FROM patient_documents 
                        WHERE patient_id = ? AND user_id = ?
                        ORDER BY upload_date DESC
                    ''', (patient_id, user_id))
                else:
                    cursor.execute('''
                        SELECT document_id, document_name, original_filename, file_path,
                               file_type, file_size, upload_date, description
                        FROM patient_documents 
                        WHERE patient_id = ?
                        ORDER BY upload_date DESC
                    ''', (patient_id,))
                
                results = cursor.fetchall()
                documents = []
                for row in results:
                    documents.append({
                        'document_id': row[0],
                        'document_name': row[1],
                        'original_filename': row[2],
                        'file_path': row[3],
                        'file_type': row[4],
                        'file_size': row[5],
                        'upload_date': row[6],
                        'description': row[7]
                    })
                return documents
        except Exception as e:
            print(f"Error getting patient documents: {e}")
            return []
    
    def delete_patient_document(self, document_id: int, user_id: int = None) -> bool:
        """Delete a patient document."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('DELETE FROM patient_documents WHERE document_id = ? AND user_id = ?', 
                                 (document_id, user_id))
                else:
                    cursor.execute('DELETE FROM patient_documents WHERE document_id = ?', 
                                 (document_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting patient document: {e}")
            return False
    
    def add_test_result(self, patient_id: int, test_date: date, test_type: str, 
                       test_value: float, unit: str = None, reference_range: str = None, user_id: int = None) -> bool:
        """Add a test result to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO test_results (patient_id, test_date, test_type, test_value, unit, reference_range, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (patient_id, test_date, test_type, test_value, unit, reference_range, user_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding test result: {e}")
            return False
    
    def get_all_patients(self, user_id: int = None) -> List[Tuple]:
        """Get all patients with summary information."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT 
                        p.patient_id,
                        p.patient_name,
                        MIN(tr.test_date) as first_test,
                        MAX(tr.test_date) as last_test,
                        COUNT(tr.result_id) as total_tests
                    FROM patients p
                    LEFT JOIN test_results tr ON p.patient_id = tr.patient_id
                    WHERE p.user_id = ?
                    GROUP BY p.patient_id, p.patient_name
                    ORDER BY p.patient_name
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT 
                        p.patient_id,
                        p.patient_name,
                        MIN(tr.test_date) as first_test,
                        MAX(tr.test_date) as last_test,
                        COUNT(tr.result_id) as total_tests
                    FROM patients p
                    LEFT JOIN test_results tr ON p.patient_id = tr.patient_id
                    WHERE p.user_id IS NULL
                    GROUP BY p.patient_id, p.patient_name
                    ORDER BY p.patient_name
                ''')
            
            return cursor.fetchall()
    
    def get_patient_tests(self, patient_name: str, user_id: int = None) -> List[Tuple]:
        """Get all test results for a specific patient."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT 
                        tr.test_date,
                        tr.test_type,
                        tr.test_value,
                        tr.unit,
                        tr.reference_range
                    FROM test_results tr
                    JOIN patients p ON tr.patient_id = p.patient_id
                    WHERE p.patient_name = ? AND p.user_id = ?
                    ORDER BY tr.test_date DESC, tr.test_type
                ''', (patient_name, user_id))
            else:
                cursor.execute('''
                    SELECT 
                        tr.test_date,
                        tr.test_type,
                        tr.test_value,
                        tr.unit,
                        tr.reference_range
                    FROM test_results tr
                    JOIN patients p ON tr.patient_id = p.patient_id
                    WHERE p.patient_name = ? AND p.user_id IS NULL
                    ORDER BY tr.test_date DESC, tr.test_type
                ''', (patient_name,))
            
            return cursor.fetchall()
    
    def get_all_test_types(self) -> List[str]:
        """Get all unique test types in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT test_type FROM test_results ORDER BY test_type')
            return [row[0] for row in cursor.fetchall()]
    
    def search_test_results(self, patient_names: List[str] = None, test_types: List[str] = None,
                           start_date: date = None, end_date: date = None) -> List[Tuple]:
        """Search test results with filters."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    p.patient_name,
                    tr.test_date,
                    tr.test_type,
                    tr.test_value,
                    tr.unit,
                    tr.reference_range
                FROM test_results tr
                JOIN patients p ON tr.patient_id = p.patient_id
                WHERE 1=1
            '''
            params = []
            
            if patient_names:
                placeholders = ','.join(['?' for _ in patient_names])
                query += f' AND p.patient_name IN ({placeholders})'
                params.extend(patient_names)
            
            if test_types:
                placeholders = ','.join(['?' for _ in test_types])
                query += f' AND tr.test_type IN ({placeholders})'
                params.extend(test_types)
            
            if start_date:
                query += ' AND tr.test_date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND tr.test_date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY tr.test_date DESC, p.patient_name, tr.test_type'
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_all_test_results(self) -> List[Tuple]:
        """Get all test results from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    p.patient_name,
                    tr.test_date,
                    tr.test_type,
                    tr.test_value,
                    tr.unit,
                    tr.reference_range
                FROM test_results tr
                JOIN patients p ON tr.patient_id = p.patient_id
                ORDER BY tr.test_date DESC, p.patient_name, tr.test_type
            ''')
            return cursor.fetchall()
    
    def get_patient_test_history(self, patient_name: str, test_type: str) -> List[Tuple]:
        """Get test history for a specific patient and test type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    tr.test_date,
                    tr.test_value,
                    tr.unit,
                    tr.reference_range
                FROM test_results tr
                JOIN patients p ON tr.patient_id = p.patient_id
                WHERE p.patient_name = ? AND tr.test_type = ?
                ORDER BY tr.test_date
            ''', (patient_name, test_type))
            return cursor.fetchall()
    
    def delete_patient(self, patient_name: str) -> bool:
        """Delete a patient and all their test results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get patient ID
                cursor.execute('SELECT patient_id FROM patients WHERE patient_name = ?', (patient_name,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                patient_id = result[0]
                
                # Delete test results first (foreign key constraint)
                cursor.execute('DELETE FROM test_results WHERE patient_id = ?', (patient_id,))
                
                # Delete patient
                cursor.execute('DELETE FROM patients WHERE patient_id = ?', (patient_id,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting patient: {e}")
            return False
    
    def delete_test_result(self, result_id: int) -> bool:
        """Delete a specific test result by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM test_results WHERE result_id = ?', (result_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting test result: {e}")
            return False
    
    def update_test_result(self, result_id: int, test_type: str, value: float, 
                          unit: str, test_date: date, reference_range: str = None) -> bool:
        """Update a specific test result by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE test_results 
                    SET test_type = ?, test_value = ?, unit = ?, test_date = ?, reference_range = ?
                    WHERE result_id = ?
                ''', (test_type, value, unit, test_date, reference_range, result_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating test result: {e}")
            return False
    
    def delete_test_results_by_date(self, patient_name: str, test_date: date) -> bool:
        """Delete all test results for a patient on a specific date."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM test_results 
                    WHERE patient_id = (SELECT patient_id FROM patients WHERE patient_name = ?)
                    AND test_date = ?
                ''', (patient_name, test_date))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting test results by date: {e}")
            return False
    
    def delete_test_results_by_type(self, patient_name: str, test_type: str) -> bool:
        """Delete all test results of a specific type for a patient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM test_results 
                    WHERE patient_id = (SELECT patient_id FROM patients WHERE patient_name = ?)
                    AND test_type = ?
                ''', (patient_name, test_type))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting test results by type: {e}")
            return False
    
    def delete_all_data(self) -> bool:
        """Delete all data from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM test_results')
                cursor.execute('DELETE FROM patients')
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting all data: {e}")
            return False
    
    def get_patient_test_results_with_ids(self, patient_name: str) -> List[Tuple]:
        """Get all test results for a patient with result IDs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    tr.result_id,
                    tr.test_date,
                    tr.test_type,
                    tr.test_value,
                    tr.unit,
                    tr.reference_range
                FROM test_results tr
                JOIN patients p ON tr.patient_id = p.patient_id
                WHERE p.patient_name = ?
                ORDER BY tr.test_date DESC, tr.test_type
            ''', (patient_name,))
            return cursor.fetchall()
    
    def get_test_results_by_date(self, patient_name: str) -> Dict[str, List[Tuple]]:
        """Get test results grouped by date for a patient."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    tr.test_date,
                    tr.test_type,
                    tr.test_value,
                    tr.unit,
                    tr.reference_range,
                    COUNT(*) as count
                FROM test_results tr
                JOIN patients p ON tr.patient_id = p.patient_id
                WHERE p.patient_name = ?
                GROUP BY tr.test_date, tr.test_type
                ORDER BY tr.test_date DESC
            ''', (patient_name,))
            
            results = cursor.fetchall()
            grouped = {}
            
            for result in results:
                date_str = result[0]
                if date_str not in grouped:
                    grouped[date_str] = []
                grouped[date_str].append(result[1:])  # Exclude date from tuple
            
            return grouped

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total patients
            cursor.execute('SELECT COUNT(*) FROM patients')
            total_patients = cursor.fetchone()[0]
            
            # Get total test results
            cursor.execute('SELECT COUNT(*) FROM test_results')
            total_tests = cursor.fetchone()[0]
            
            # Get unique test types
            cursor.execute('SELECT COUNT(DISTINCT test_type) FROM test_results')
            unique_test_types = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute('SELECT MIN(test_date), MAX(test_date) FROM test_results')
            date_range = cursor.fetchone()
            
            return {
                'total_patients': total_patients,
                'total_tests': total_tests,
                'unique_test_types': unique_test_types,
                'earliest_test': date_range[0],
                'latest_test': date_range[1]
            }
