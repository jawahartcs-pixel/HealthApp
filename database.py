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
            
            try:
                cursor.execute('ALTER TABLE patients ADD COLUMN date_of_birth DATE')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Create SMTP configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smtp_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_server TEXT NOT NULL,
                    smtp_port INTEGER NOT NULL,
                    email_username TEXT NOT NULL,
                    email_password TEXT NOT NULL,
                    sender_name TEXT DEFAULT 'Medical Reminder System',
                    use_ssl BOOLEAN DEFAULT 1,
                    check_frequency_minutes INTEGER DEFAULT 1,
                    timezone TEXT DEFAULT 'UTC',
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add new columns if they don't exist
            try:
                cursor.execute('ALTER TABLE smtp_config ADD COLUMN check_frequency_minutes INTEGER DEFAULT 1')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE smtp_config ADD COLUMN timezone TEXT DEFAULT "UTC"')
            except sqlite3.OperationalError:
                pass
            
            # Add email history table for tracking sent emails
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    patient_name TEXT NOT NULL,
                    patient_email TEXT NOT NULL,
                    medication_name TEXT NOT NULL,
                    medication_dosage TEXT,
                    reminder_time TEXT,
                    email_subject TEXT,
                    email_body TEXT,
                    sent_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    email_type TEXT DEFAULT 'reminder',
                    status TEXT DEFAULT 'sent',
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            ''')
            
            # Add custom reminder times table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_reminder_times (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medication_id INTEGER,
                    reminder_time TIME NOT NULL,
                    reminder_date DATE,
                    alert_offset_minutes INTEGER DEFAULT -60,
                    is_recurring BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (medication_id) REFERENCES medications (id)
                )
            ''')
            
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
            
            # Create patient_events table for tracking medical events
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    event_name TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    notes TEXT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            ''')
            
            # Create index for patient events
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_patient_events ON patient_events(patient_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_date ON patient_events(event_date)
            ''')
            
            # Create user preferences table for storing UI settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    patient_name TEXT,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, patient_name, preference_key)
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_prefs ON user_preferences(user_id, patient_name, preference_key)
            ''')
            
            # Create indexes after columns are added
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id ON patients(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_user_id ON test_results(user_id)
            ''')
            
            conn.commit()
    
    def add_patient(self, patient_name: str, user_id: int = None, date_of_birth: str = None,
                   age: int = None, gender: str = None, phone: str = None, email: str = None, 
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
                INSERT INTO patients (patient_name, user_id, date_of_birth, age, gender, phone, email, 
                                    address, medical_history, medications, allergies, 
                                    emergency_contact, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_name, user_id, date_of_birth, age, gender, phone, email, address, 
                  medical_history, medications, allergies, emergency_contact, notes))
            conn.commit()
            return cursor.lastrowid
    
    def update_patient_profile(self, patient_id: int, date_of_birth: str = None, age: int = None, 
                              gender: str = None, phone: str = None, email: str = None, address: str = None, 
                              medical_history: str = None, medications: str = None, 
                              allergies: str = None, emergency_contact: str = None, 
                              notes: str = None) -> bool:
        """Update patient profile information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE patients SET 
                        date_of_birth = ?, age = ?, gender = ?, phone = ?, email = ?, address = ?,
                        medical_history = ?, medications = ?, allergies = ?, 
                        emergency_contact = ?, notes = ?
                    WHERE patient_id = ?
                ''', (date_of_birth, age, gender, phone, email, address, medical_history, 
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
                        SELECT patient_id, patient_name, date_of_birth, age, gender, phone, email, address,
                               medical_history, medications, allergies, emergency_contact, 
                               notes, created_at
                        FROM patients 
                        WHERE patient_name = ? AND user_id = ?
                    ''', (patient_name, user_id))
                else:
                    cursor.execute('''
                        SELECT patient_id, patient_name, date_of_birth, age, gender, phone, email, address,
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
                        'date_of_birth': result[2],
                        'age': result[3],
                        'gender': result[4],
                        'phone': result[5],
                        'email': result[6],
                        'address': result[7],
                        'medical_history': result[8],
                        'medications': result[9],
                        'allergies': result[10],
                        'emergency_contact': result[11],
                        'notes': result[12],
                        'created_at': result[13]
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
    
    def add_patient_event(self, patient_id: int, event_name: str, event_date: date, 
                         notes: str = None, user_id: int = None) -> int:
        """Add a patient event (like surgery, treatment, etc.)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO patient_events (patient_id, event_name, event_date, notes, user_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (patient_id, event_name, event_date, notes, user_id))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error adding patient event: {e}")
            return 0
    
    def get_patient_events(self, patient_id: int, user_id: int = None) -> List[Dict]:
        """Get all events for a specific patient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('''
                        SELECT event_id, event_name, event_date, notes, created_at
                        FROM patient_events 
                        WHERE patient_id = ? AND user_id = ?
                        ORDER BY event_date DESC
                    ''', (patient_id, user_id))
                else:
                    cursor.execute('''
                        SELECT event_id, event_name, event_date, notes, created_at
                        FROM patient_events 
                        WHERE patient_id = ?
                        ORDER BY event_date DESC
                    ''', (patient_id,))
                
                results = cursor.fetchall()
                events = []
                for row in results:
                    events.append({
                        'event_id': row[0],
                        'event_name': row[1],
                        'event_date': row[2],
                        'notes': row[3],
                        'created_at': row[4]
                    })
                return events
        except Exception as e:
            print(f"Error getting patient events: {e}")
            return []
    
    def update_patient_event(self, event_id: int, event_name: str, event_date: date, 
                            notes: str = None, user_id: int = None) -> bool:
        """Update an existing patient event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('''
                        UPDATE patient_events 
                        SET event_name = ?, event_date = ?, notes = ?
                        WHERE event_id = ? AND user_id = ?
                    ''', (event_name, event_date, notes, event_id, user_id))
                else:
                    cursor.execute('''
                        UPDATE patient_events 
                        SET event_name = ?, event_date = ?, notes = ?
                        WHERE event_id = ?
                    ''', (event_name, event_date, notes, event_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating patient event: {e}")
            return False
    
    def delete_patient_event(self, event_id: int, user_id: int = None) -> bool:
        """Delete a patient event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('DELETE FROM patient_events WHERE event_id = ? AND user_id = ?', 
                                 (event_id, user_id))
                else:
                    cursor.execute('DELETE FROM patient_events WHERE event_id = ?', 
                                 (event_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting patient event: {e}")
            return False
    
    def check_duplicate_test_results(self, patient_name: str, test_date: str, test_results: list, user_id: int = None) -> list:
        """Check for duplicate test results (same patient, date, test type, and value)."""
        duplicates = []
        try:
            patient_id = self.get_patient_id(patient_name, user_id)
            if not patient_id:
                return []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for result in test_results:
                    test_type = result.get('test_type', '')
                    test_value = result.get('value', result.get('test_value', 0))
                    
                    try:
                        test_value_float = float(test_value) if test_value else 0
                    except (ValueError, TypeError):
                        test_value_float = 0
                    
                    cursor.execute('''
                        SELECT result_id, test_type, test_value, test_date
                        FROM test_results 
                        WHERE patient_id = ? AND test_date = ? AND test_type = ? AND test_value = ?
                    ''', (patient_id, test_date, test_type, test_value_float))
                    
                    existing = cursor.fetchone()
                    if existing:
                        duplicates.append({
                            'test_type': test_type,
                            'value': test_value_float,
                            'date': test_date,
                            'existing_id': existing[0]
                        })
                        
        except Exception as e:
            print(f"Error checking duplicate test results: {e}")
        
        return duplicates
    
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
    
    def get_patient_id(self, patient_name: str, user_id: int = None) -> Optional[int]:
        """Get patient ID by name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('SELECT patient_id FROM patients WHERE patient_name = ? AND user_id = ?', 
                                 (patient_name, user_id))
                else:
                    cursor.execute('SELECT patient_id FROM patients WHERE patient_name = ? AND user_id IS NULL', 
                                 (patient_name,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting patient ID: {e}")
            return None
    
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
            # Convert numpy types to Python native types for SQLite compatibility
            result_id = int(result_id)
            value = float(value)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE test_results 
                SET test_type = ?, test_value = ?, unit = ?, test_date = ?, reference_range = ?
                WHERE result_id = ?
            ''', (test_type, value, unit, test_date, reference_range, result_id))
            
            rowcount = cursor.rowcount
            conn.commit()
            conn.close()
            return rowcount > 0
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
    
    def save_smtp_config(self, smtp_server: str, smtp_port: int, email_username: str, 
                        email_password: str, sender_name: str = 'Medical Reminder System', 
                        use_ssl: bool = True, check_frequency_minutes: int = 1,
                        timezone: str = "UTC") -> bool:
        """Save or update SMTP configuration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if configuration exists
                cursor.execute('SELECT id FROM smtp_config LIMIT 1')
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing configuration
                    cursor.execute('''
                        UPDATE smtp_config 
                        SET smtp_server = ?, smtp_port = ?, email_username = ?, 
                            email_password = ?, sender_name = ?, use_ssl = ?,
                            check_frequency_minutes = ?, timezone = ?,
                            updated_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (smtp_server, smtp_port, email_username, email_password, 
                          sender_name, use_ssl, check_frequency_minutes, timezone, existing[0]))
                else:
                    # Insert new configuration
                    cursor.execute('''
                        INSERT INTO smtp_config (smtp_server, smtp_port, email_username, 
                                                email_password, sender_name, use_ssl,
                                                check_frequency_minutes, timezone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (smtp_server, smtp_port, email_username, email_password, 
                          sender_name, use_ssl, check_frequency_minutes, timezone))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving SMTP configuration: {e}")
            return False
    
    def get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT smtp_server, smtp_port, email_username, email_password, 
                           sender_name, use_ssl, check_frequency_minutes, timezone
                    FROM smtp_config 
                    ORDER BY updated_date DESC 
                    LIMIT 1
                ''')
                
                result = cursor.fetchone()
                if result:
                    return {
                        'smtp_server': result[0],
                        'smtp_port': result[1],
                        'email_username': result[2],
                        'email_password': result[3],
                        'sender_name': result[4],
                        'use_ssl': bool(result[5]),
                        'check_frequency_minutes': result[6] if result[6] else 1,
                        'timezone': result[7] if result[7] else 'UTC'
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting SMTP configuration: {e}")
            return {}
    
    def get_patient_details(self, patient_id: int) -> Dict[str, Any]:
        """Get detailed patient information by patient ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT patient_id, patient_name, user_id, created_at, age, gender, 
                           phone, email, address, medical_history, medications, 
                           allergies, emergency_contact, notes, date_of_birth
                    FROM patients 
                    WHERE patient_id = ?
                ''', (patient_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'patient_id': result[0],
                        'patient_name': result[1],
                        'user_id': result[2],
                        'created_at': result[3],
                        'age': result[4],
                        'gender': result[5],
                        'phone': result[6],
                        'email': result[7],
                        'address': result[8],
                        'medical_history': result[9],
                        'medications': result[10],
                        'allergies': result[11],
                        'emergency_contact': result[12],
                        'notes': result[13],
                        'date_of_birth': result[14]
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting patient details: {e}")
            return {}
    
    def update_patient_details(self, patient_id: int, updates: Dict[str, Any]) -> bool:
        """Update patient details with provided fields."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                valid_fields = ['patient_name', 'age', 'gender', 'phone', 'email', 
                               'address', 'medical_history', 'medications', 'allergies', 
                               'emergency_contact', 'notes', 'date_of_birth']
                
                for field, value in updates.items():
                    if field in valid_fields:
                        set_clauses.append(f"{field} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                params.append(patient_id)
                query = f"UPDATE patients SET {', '.join(set_clauses)} WHERE patient_id = ?"
                
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating patient details: {e}")
            return False
    
    def add_email_history(self, patient_id: int, patient_name: str, patient_email: str, 
                         medication_name: str, medication_dosage: str, reminder_time: str,
                         email_subject: str, email_body: str, email_type: str = 'reminder') -> bool:
        """Add email history record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO email_history 
                    (patient_id, patient_name, patient_email, medication_name, medication_dosage,
                     reminder_time, email_subject, email_body, email_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (patient_id, patient_name, patient_email, medication_name, medication_dosage,
                      reminder_time, email_subject, email_body, email_type))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding email history: {e}")
            return False
    
    def get_email_history(self, limit: int = 100) -> List[Dict]:
        """Get email history records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, patient_name, patient_email, medication_name, medication_dosage,
                           reminder_time, email_subject, sent_timestamp, email_type, status
                    FROM email_history
                    ORDER BY sent_timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                history = []
                for row in results:
                    history.append({
                        'id': row[0],
                        'patient_name': row[1],
                        'patient_email': row[2],
                        'medication_name': row[3],
                        'medication_dosage': row[4],
                        'reminder_time': row[5],
                        'email_subject': row[6],
                        'sent_timestamp': row[7],
                        'email_type': row[8],
                        'status': row[9]
                    })
                return history
        except Exception as e:
            print(f"Error getting email history: {e}")
            return []
    
    def clear_email_history(self) -> bool:
        """Clear all email history records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM email_history')
                conn.commit()
                return True
        except Exception as e:
            print(f"Error clearing email history: {e}")
            return False
    
    def save_user_preference(self, user_id: int, patient_name: str, preference_key: str, preference_value: str) -> bool:
        """Save a user preference (upsert)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_preferences (user_id, patient_name, preference_key, preference_value, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, patient_name, preference_key) 
                    DO UPDATE SET preference_value = excluded.preference_value, updated_at = CURRENT_TIMESTAMP
                ''', (user_id, patient_name, preference_key, preference_value))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving user preference: {e}")
            return False
    
    def get_user_preference(self, user_id: int, patient_name: str, preference_key: str) -> Optional[str]:
        """Get a user preference value."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT preference_value FROM user_preferences
                    WHERE user_id = ? AND patient_name = ? AND preference_key = ?
                ''', (user_id, patient_name, preference_key))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting user preference: {e}")
            return None
    
    def delete_user_preference(self, user_id: int, patient_name: str, preference_key: str) -> bool:
        """Delete a user preference."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_preferences
                    WHERE user_id = ? AND patient_name = ? AND preference_key = ?
                ''', (user_id, patient_name, preference_key))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting user preference: {e}")
            return False
