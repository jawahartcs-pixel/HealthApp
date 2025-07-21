"""
Smart Medication Reminder System
Handles medication tracking, reminders, adherence monitoring, and integration with blood test results.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class MedicationReminder:
    def __init__(self, db_path: str = "blood_test_results.db"):
        if hasattr(db_path, 'db_path'):
            # If passed a Database object, extract the path
            self.db_path = db_path.db_path
        else:
            self.db_path = db_path
        self.init_medication_tables()
    
    def init_medication_tables(self):
        """Create medication-related tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Medications table - stores medication information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT NOT NULL,
                    medication_name TEXT NOT NULL,
                    dosage TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE,
                    instructions TEXT,
                    indication TEXT,
                    doctor_name TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_name) REFERENCES patients(name)
                )
            ''')
            
            # Medication schedule table - stores reminder schedules
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medication_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medication_id INTEGER NOT NULL,
                    time_of_day TIME NOT NULL,
                    days_of_week TEXT,
                    reminder_enabled BOOLEAN DEFAULT 1,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (medication_id) REFERENCES medications(id)
                )
            ''')
            
            # Medication adherence table - tracks actual medication taking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medication_adherence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medication_id INTEGER NOT NULL,
                    scheduled_date DATE NOT NULL,
                    scheduled_time TIME NOT NULL,
                    taken_date DATE,
                    taken_time TIME,
                    status TEXT CHECK(status IN ('taken', 'missed', 'delayed', 'skipped')) DEFAULT 'missed',
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (medication_id) REFERENCES medications(id)
                )
            ''')
            
            # Medication effectiveness table - links medications to test results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medication_effectiveness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medication_id INTEGER NOT NULL,
                    test_result_id INTEGER NOT NULL,
                    effectiveness_rating INTEGER CHECK(effectiveness_rating BETWEEN 1 AND 5),
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (medication_id) REFERENCES medications(id),
                    FOREIGN KEY (test_result_id) REFERENCES test_results(id)
                )
            ''')
            
            conn.commit()
    
    def add_medication(self, medication_data: Dict) -> bool:
        """Add a new medication for a patient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO medications 
                    (patient_name, medication_name, dosage, frequency, start_date, end_date, 
                     instructions, indication, doctor_name, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    medication_data['patient_name'],
                    medication_data['medication_name'],
                    medication_data['dosage'],
                    medication_data['frequency'],
                    medication_data['start_date'],
                    medication_data.get('end_date'),
                    medication_data.get('instructions', ''),
                    medication_data.get('indication', ''),
                    medication_data.get('doctor_name', ''),
                    medication_data.get('active', True)
                ))
                
                medication_id = cursor.lastrowid
                
                # Add schedule if provided
                if 'schedule' in medication_data:
                    for schedule in medication_data['schedule']:
                        cursor.execute('''
                            INSERT INTO medication_schedule 
                            (medication_id, time_of_day, days_of_week, reminder_enabled)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            medication_id,
                            schedule['time'],
                            json.dumps(schedule.get('days', [1,2,3,4,5,6,7])),  # Default: daily
                            schedule.get('reminder_enabled', True)
                        ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error adding medication: {e}")
            return False
    
    def get_patient_medications(self, patient_name: str, active_only: bool = True) -> List[Dict]:
        """Get all medications for a patient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT m.id, m.medication_name, m.dosage, m.frequency, m.start_date, m.end_date,
                           m.instructions, m.indication, m.doctor_name, m.active, m.created_date
                    FROM medications m
                    WHERE m.patient_name = ?
                '''
                
                params = [patient_name]
                if active_only:
                    query += ' AND m.active = 1'
                
                query += ' ORDER BY m.created_date DESC'
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                medications = []
                for row in results:
                    med_data = {
                        'id': row[0],
                        'medication_name': row[1],
                        'dosage': row[2],
                        'frequency': row[3],
                        'start_date': row[4],
                        'end_date': row[5],
                        'instructions': row[6],
                        'indication': row[7],
                        'doctor_name': row[8],
                        'active': row[9],
                        'created_date': row[10],
                        'schedule': self.get_medication_schedule(row[0])
                    }
                    medications.append(med_data)
                
                return medications
                
        except Exception as e:
            print(f"Error getting patient medications: {e}")
            return []
    
    def get_medication_schedule(self, medication_id: int) -> List[Dict]:
        """Get schedule for a specific medication."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, time_of_day, days_of_week, reminder_enabled
                    FROM medication_schedule
                    WHERE medication_id = ?
                    ORDER BY time_of_day
                ''', (medication_id,))
                
                results = cursor.fetchall()
                schedule = []
                
                for row in results:
                    schedule.append({
                        'id': row[0],
                        'time': row[1],
                        'days': json.loads(row[2]) if row[2] else [1,2,3,4,5,6,7],
                        'reminder_enabled': row[3]
                    })
                
                return schedule
                
        except Exception as e:
            print(f"Error getting medication schedule: {e}")
            return []
    
    def get_due_medications(self, patient_name: str = None, date: datetime = None) -> List[Dict]:
        """Get medications due for today or specific date."""
        if date is None:
            date = datetime.now()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT m.id, m.patient_name, m.medication_name, m.dosage, m.frequency,
                           ms.time_of_day, ms.days_of_week, ms.reminder_enabled
                    FROM medications m
                    JOIN medication_schedule ms ON m.id = ms.medication_id
                    WHERE m.active = 1 AND ms.reminder_enabled = 1
                '''
                
                params = []
                if patient_name:
                    query += ' AND m.patient_name = ?'
                    params.append(patient_name)
                
                # Check if medication is within active date range
                query += ' AND m.start_date <= ? AND (m.end_date IS NULL OR m.end_date >= ?)'
                params.extend([date.strftime('%Y-%m-%d'), date.strftime('%Y-%m-%d')])
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                due_medications = []
                current_weekday = date.weekday() + 1  # Monday = 1
                
                for row in results:
                    days_of_week = json.loads(row[6]) if row[6] else [1,2,3,4,5,6,7]
                    
                    if current_weekday in days_of_week:
                        due_medications.append({
                            'medication_id': row[0],
                            'patient_name': row[1],
                            'medication_name': row[2],
                            'dosage': row[3],
                            'frequency': row[4],
                            'time': row[5],
                            'reminder_enabled': row[7]
                        })
                
                return due_medications
                
        except Exception as e:
            print(f"Error getting due medications: {e}")
            return []
    
    def record_medication_taken(self, medication_id: int, scheduled_date: str, scheduled_time: str, 
                              taken_date: str = None, taken_time: str = None, notes: str = '') -> bool:
        """Record that a medication was taken."""
        try:
            if taken_date is None:
                taken_date = datetime.now().strftime('%Y-%m-%d')
            if taken_time is None:
                taken_time = datetime.now().strftime('%H:%M:%S')
            
            # Determine status based on timing
            scheduled_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", '%Y-%m-%d %H:%M:%S')
            taken_datetime = datetime.strptime(f"{taken_date} {taken_time}", '%Y-%m-%d %H:%M:%S')
            
            time_diff = taken_datetime - scheduled_datetime
            
            if time_diff.total_seconds() <= 900:  # Within 15 minutes
                status = 'taken'
            elif time_diff.total_seconds() <= 3600:  # Within 1 hour
                status = 'delayed'
            else:
                status = 'delayed'
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO medication_adherence 
                    (medication_id, scheduled_date, scheduled_time, taken_date, taken_time, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (medication_id, scheduled_date, scheduled_time, taken_date, taken_time, status, notes))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error recording medication taken: {e}")
            return False
    
    def record_medication_missed(self, medication_id: int, scheduled_date: str, scheduled_time: str, 
                                reason: str = '') -> bool:
        """Record that a medication was missed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO medication_adherence 
                    (medication_id, scheduled_date, scheduled_time, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (medication_id, scheduled_date, scheduled_time, 'missed', reason))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error recording medication missed: {e}")
            return False
    
    def get_adherence_stats(self, patient_name: str, days: int = 30) -> Dict:
        """Get medication adherence statistics for a patient."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get adherence data
                cursor.execute('''
                    SELECT ma.status, COUNT(*) as count
                    FROM medication_adherence ma
                    JOIN medications m ON ma.medication_id = m.id
                    WHERE m.patient_name = ? 
                    AND ma.scheduled_date BETWEEN ? AND ?
                    GROUP BY ma.status
                ''', (patient_name, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                
                adherence_data = dict(cursor.fetchall())
                
                total_scheduled = sum(adherence_data.values())
                taken_count = adherence_data.get('taken', 0) + adherence_data.get('delayed', 0)
                
                adherence_rate = (taken_count / total_scheduled * 100) if total_scheduled > 0 else 0
                
                return {
                    'total_scheduled': total_scheduled,
                    'taken': adherence_data.get('taken', 0),
                    'delayed': adherence_data.get('delayed', 0),
                    'missed': adherence_data.get('missed', 0),
                    'skipped': adherence_data.get('skipped', 0),
                    'adherence_rate': round(adherence_rate, 1),
                    'period_days': days
                }
                
        except Exception as e:
            print(f"Error getting adherence stats: {e}")
            return {}
    
    def get_medication_effectiveness_analysis(self, patient_name: str, medication_name: str) -> Dict:
        """Analyze medication effectiveness based on test results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get medication start date and related test results
                cursor.execute('''
                    SELECT m.start_date, m.indication,
                           tr.test_date, tr.test_type, tr.test_value, tr.unit
                    FROM medications m
                    LEFT JOIN test_results tr ON tr.patient_name = m.patient_name
                    WHERE m.patient_name = ? AND m.medication_name = ?
                    AND tr.test_date >= m.start_date
                    ORDER BY tr.test_date
                ''', (patient_name, medication_name))
                
                results = cursor.fetchall()
                
                if not results:
                    return {'status': 'no_data', 'message': 'No test data available for effectiveness analysis'}
                
                # Group results by test type
                test_data = {}
                start_date = results[0][0]
                indication = results[0][1]
                
                for row in results:
                    test_type = row[3]
                    if test_type not in test_data:
                        test_data[test_type] = []
                    
                    test_data[test_type].append({
                        'date': row[2],
                        'value': row[4],
                        'unit': row[5]
                    })
                
                # Analyze trends
                analysis = {
                    'medication': medication_name,
                    'start_date': start_date,
                    'indication': indication,
                    'test_trends': {},
                    'overall_effectiveness': 'analyzing'
                }
                
                for test_type, values in test_data.items():
                    if len(values) >= 2:
                        # Calculate trend
                        first_value = values[0]['value']
                        latest_value = values[-1]['value']
                        
                        if first_value and latest_value:
                            trend = 'improving' if latest_value < first_value else 'worsening' if latest_value > first_value else 'stable'
                            percent_change = ((latest_value - first_value) / first_value * 100) if first_value != 0 else 0
                            
                            analysis['test_trends'][test_type] = {
                                'trend': trend,
                                'percent_change': round(percent_change, 1),
                                'first_value': first_value,
                                'latest_value': latest_value,
                                'unit': values[0]['unit'],
                                'data_points': len(values)
                            }
                
                return analysis
                
        except Exception as e:
            print(f"Error analyzing medication effectiveness: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def update_medication(self, medication_id: int, updates: Dict) -> bool:
        """Update medication information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                for field, value in updates.items():
                    if field in ['medication_name', 'dosage', 'frequency', 'start_date', 'end_date', 
                               'instructions', 'indication', 'doctor_name', 'active']:
                        set_clauses.append(f"{field} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_date = CURRENT_TIMESTAMP")
                params.append(medication_id)
                
                query = f"UPDATE medications SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating medication: {e}")
            return False
    
    def deactivate_medication(self, medication_id: int) -> bool:
        """Deactivate a medication instead of deleting it."""
        return self.update_medication(medication_id, {'active': False})
    
    def get_missed_medications_summary(self, patient_name: str = None, days: int = 7) -> Dict:
        """Get summary of missed medications for alerts."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT m.patient_name, m.medication_name, m.dosage,
                           COUNT(CASE WHEN ma.status = 'missed' THEN 1 END) as missed_count,
                           COUNT(*) as total_scheduled
                    FROM medications m
                    JOIN medication_adherence ma ON m.id = ma.medication_id
                    WHERE ma.scheduled_date BETWEEN ? AND ?
                '''
                
                params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
                
                if patient_name:
                    query += ' AND m.patient_name = ?'
                    params.append(patient_name)
                
                query += ' GROUP BY m.id, m.patient_name, m.medication_name, m.dosage'
                query += ' HAVING missed_count > 0'
                query += ' ORDER BY missed_count DESC'
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                summary = []
                for row in results:
                    missed_rate = (row[3] / row[4] * 100) if row[4] > 0 else 0
                    summary.append({
                        'patient_name': row[0],
                        'medication_name': row[1],
                        'dosage': row[2],
                        'missed_count': row[3],
                        'total_scheduled': row[4],
                        'missed_rate': round(missed_rate, 1)
                    })
                
                return {
                    'summary': summary,
                    'total_patients_with_missed': len(set(item['patient_name'] for item in summary)),
                    'period_days': days
                }
                
        except Exception as e:
            print(f"Error getting missed medications summary: {e}")
            return {}