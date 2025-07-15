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
                    patient_name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            conn.commit()
    
    def add_patient(self, patient_name: str) -> int:
        """Add a new patient or get existing patient ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to get existing patient
            cursor.execute('SELECT patient_id FROM patients WHERE patient_name = ?', (patient_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Add new patient
            cursor.execute('INSERT INTO patients (patient_name) VALUES (?)', (patient_name,))
            conn.commit()
            return cursor.lastrowid
    
    def add_test_result(self, patient_id: int, test_date: date, test_type: str, 
                       test_value: float, unit: str = None, reference_range: str = None) -> bool:
        """Add a test result to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO test_results (patient_id, test_date, test_type, test_value, unit, reference_range)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (patient_id, test_date, test_type, test_value, unit, reference_range))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding test result: {e}")
            return False
    
    def get_all_patients(self) -> List[Tuple]:
        """Get all patients with summary information."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    p.patient_id,
                    p.patient_name,
                    MIN(tr.test_date) as first_test,
                    MAX(tr.test_date) as last_test,
                    COUNT(tr.result_id) as total_tests
                FROM patients p
                LEFT JOIN test_results tr ON p.patient_id = tr.patient_id
                GROUP BY p.patient_id, p.patient_name
                ORDER BY p.patient_name
            ''')
            return cursor.fetchall()
    
    def get_patient_tests(self, patient_name: str) -> List[Tuple]:
        """Get all test results for a specific patient."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
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
