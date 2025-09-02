"""
Smart Medication Reminder System
Handles medication tracking, reminders, adherence monitoring, and integration with blood test results.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

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
            
            # Enhanced medication schedule table - stores reminder schedules with intervals and alert timings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medication_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medication_id INTEGER NOT NULL,
                    time_of_day TIME NOT NULL,
                    days_of_week TEXT,
                    interval_days INTEGER DEFAULT NULL,
                    reminder_enabled BOOLEAN DEFAULT 1,
                    email_enabled BOOLEAN DEFAULT 1,
                    alert_timings TEXT DEFAULT NULL,
                    last_reminder_date DATE DEFAULT NULL,
                    next_reminder_date DATE DEFAULT NULL,
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
            
            # Add new columns if they don't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE medication_schedule ADD COLUMN interval_days INTEGER DEFAULT NULL')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            try:
                cursor.execute('ALTER TABLE medication_schedule ADD COLUMN email_enabled BOOLEAN DEFAULT 1')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            try:
                cursor.execute('ALTER TABLE medication_schedule ADD COLUMN alert_timings TEXT DEFAULT NULL')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            try:
                cursor.execute('ALTER TABLE medication_schedule ADD COLUMN last_reminder_date DATE DEFAULT NULL')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            try:
                cursor.execute('ALTER TABLE medication_schedule ADD COLUMN next_reminder_date DATE DEFAULT NULL')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
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
                
                # Add enhanced schedule if provided
                if 'schedule' in medication_data:
                    for schedule in medication_data['schedule']:
                        next_reminder = self._calculate_next_reminder_date(
                            medication_data['start_date'], 
                            schedule.get('interval_days'), 
                            schedule.get('days', [])
                        )
                        
                        cursor.execute('''
                            INSERT INTO medication_schedule 
                            (medication_id, time_of_day, days_of_week, interval_days, 
                             reminder_enabled, email_enabled, alert_timings, next_reminder_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            medication_id,
                            schedule['time'],
                            json.dumps(schedule.get('days', [])),
                            schedule.get('interval_days'),
                            schedule.get('reminder_enabled', True),
                            schedule.get('email_enabled', True),
                            json.dumps(schedule.get('alert_timings', ["1 hour before"])),
                            next_reminder
                        ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error adding medication: {e}")
            return False
    
    def _calculate_next_reminder_date(self, start_date_str: str, interval_days: int = None, days_of_week: List[int] = None) -> str:
        """Calculate the next reminder date based on interval or days of week."""
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            today = date.today()
            
            if interval_days:
                # For interval-based medications (every X days)
                if start_date <= today:
                    # Calculate how many intervals have passed since start
                    days_passed = (today - start_date).days
                    intervals_passed = days_passed // interval_days
                    next_date = start_date + timedelta(days=(intervals_passed + 1) * interval_days)
                else:
                    next_date = start_date
                return next_date.strftime('%Y-%m-%d')
            
            elif days_of_week:
                # For weekly medications on specific days
                next_date = today + timedelta(days=1)
                while next_date.weekday() + 1 not in days_of_week:
                    next_date += timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            
            else:
                # Default: daily
                return (today + timedelta(days=1)).strftime('%Y-%m-%d')
                
        except Exception as e:
            print(f"Error calculating next reminder date: {e}")
            return (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    def send_email_reminder(self, patient_email: str, patient_name: str, medication_name: str, 
                           dosage: str, scheduled_time: str) -> bool:
        """Send email reminder to patient."""
        try:
            # Email configuration (these should be environment variables)
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            email_username = os.getenv('EMAIL_USERNAME')
            email_password = os.getenv('EMAIL_PASSWORD')
            
            if not email_username or not email_password:
                print("Email credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_username
            msg['To'] = patient_email
            msg['Subject'] = f"Medication Reminder: {medication_name}"
            
            # Email body
            body = f"""
            Dear {patient_name},
            
            This is a friendly reminder to take your medication:
            
            Medication: {medication_name}
            Dosage: {dosage}
            Scheduled Time: {scheduled_time}
            
            Please take your medication as prescribed by your healthcare provider.
            
            If you have any questions or concerns, please contact your doctor.
            
            Best regards,
            Your Healthcare Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_username, email_password)
            text = msg.as_string()
            server.sendmail(email_username, patient_email, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending email reminder: {e}")
            return False
    
    def _calculate_alert_datetime(self, medication_datetime: datetime, alert_timing: str) -> datetime:
        """Calculate the actual alert datetime based on timing preference."""
        if alert_timing == "5 minutes before":
            return medication_datetime - timedelta(minutes=5)
        elif alert_timing == "1 hour before":
            return medication_datetime - timedelta(hours=1)
        elif alert_timing == "1 day before":
            return medication_datetime - timedelta(days=1)
        else:
            return medication_datetime  # Default: at medication time
    
    def get_due_reminders(self, check_date: date = None, check_time: datetime = None) -> List[Dict]:
        """Get all medication reminders due for a specific date and time with alert timing consideration."""
        if check_date is None:
            check_date = date.today()
        if check_time is None:
            check_time = datetime.now()
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get medications with reminders due today
                cursor.execute('''
                    SELECT m.id, m.patient_name, m.medication_name, m.dosage,
                           ms.time_of_day, ms.email_enabled, ms.interval_days,
                           ms.next_reminder_date, ms.days_of_week, ms.alert_timings
                    FROM medications m
                    JOIN medication_schedule ms ON m.id = ms.medication_id
                    JOIN patients p ON m.patient_name = p.patient_name
                    WHERE m.active = 1 
                    AND ms.reminder_enabled = 1
                    AND (
                        (ms.interval_days IS NOT NULL AND ms.next_reminder_date <= ?)
                        OR 
                        (ms.interval_days IS NULL AND ms.days_of_week IS NOT NULL)
                    )
                ''', (check_date.strftime('%Y-%m-%d'),))
                
                results = cursor.fetchall()
                due_reminders = []
                
                for row in results:
                    medication_id, patient_name, medication_name, dosage, time_of_day, email_enabled, interval_days, next_reminder_date, days_of_week_json, alert_timings_json = row
                    
                    # Check if reminder is actually due today
                    is_due = False
                    medication_datetime = None
                    
                    if interval_days:
                        # Interval-based medication
                        if next_reminder_date and next_reminder_date <= check_date.strftime('%Y-%m-%d'):
                            is_due = True
                            medication_datetime = datetime.combine(
                                datetime.strptime(next_reminder_date, '%Y-%m-%d').date(),
                                datetime.strptime(time_of_day, '%H:%M:%S').time()
                            )
                    else:
                        # Weekly medication - check if today is in the allowed days
                        try:
                            days_of_week = json.loads(days_of_week_json) if days_of_week_json else []
                            if check_date.weekday() + 1 in days_of_week:
                                is_due = True
                                medication_datetime = datetime.combine(
                                    check_date,
                                    datetime.strptime(time_of_day, '%H:%M:%S').time()
                                )
                        except:
                            pass
                    
                    if is_due and medication_datetime:
                        # Parse alert timings
                        try:
                            alert_timings = json.loads(alert_timings_json) if alert_timings_json else ["1 hour before"]
                        except:
                            alert_timings = ["1 hour before"]
                        
                        # Check if any alert should be triggered now
                        alert_due = False
                        for alert_timing in alert_timings:
                            alert_datetime = self._calculate_alert_datetime(medication_datetime, alert_timing)
                            if check_time >= alert_datetime:
                                alert_due = True
                                break
                        
                        if alert_due:
                            # Get patient email
                            cursor.execute('SELECT email FROM patients WHERE patient_name = ?', (patient_name,))
                            email_result = cursor.fetchone()
                            patient_email = email_result[0] if email_result and email_result[0] else None
                            
                            due_reminders.append({
                                'medication_id': medication_id,
                                'patient_name': patient_name,
                                'patient_email': patient_email,
                                'medication_name': medication_name,
                                'dosage': dosage,
                                'time': time_of_day,
                                'email_enabled': email_enabled,
                                'alert_timings': alert_timings,
                                'medication_datetime': medication_datetime,
                                'check_date': check_date.strftime('%Y-%m-%d')
                            })
                
                return due_reminders
                
        except Exception as e:
            print(f"Error getting due reminders: {e}")
            return []
    
    def process_daily_reminders(self, send_emails: bool = True) -> Dict[str, int]:
        """Process all due reminders for today and optionally send emails."""
        due_reminders = self.get_due_reminders()
        stats = {'total_due': len(due_reminders), 'emails_sent': 0, 'emails_failed': 0}
        
        for reminder in due_reminders:
            if send_emails and reminder['email_enabled'] and reminder['patient_email']:
                success = self.send_email_reminder(
                    reminder['patient_email'],
                    reminder['patient_name'],
                    reminder['medication_name'],
                    reminder['dosage'],
                    reminder['time']
                )
                
                if success:
                    stats['emails_sent'] += 1
                    # Update next reminder date for interval-based medications
                    self._update_next_reminder_date(reminder['medication_id'])
                else:
                    stats['emails_failed'] += 1
        
        return stats
    
    def _update_next_reminder_date(self, medication_id: int):
        """Update the next reminder date for interval-based medications."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current schedule info
                cursor.execute('''
                    SELECT interval_days, next_reminder_date 
                    FROM medication_schedule 
                    WHERE medication_id = ? AND interval_days IS NOT NULL
                ''', (medication_id,))
                
                result = cursor.fetchone()
                if result:
                    interval_days, current_next_date = result
                    
                    # Calculate new next reminder date
                    current_date = datetime.strptime(current_next_date, '%Y-%m-%d').date()
                    new_next_date = current_date + timedelta(days=interval_days)
                    
                    # Update the schedule
                    cursor.execute('''
                        UPDATE medication_schedule 
                        SET last_reminder_date = ?, next_reminder_date = ?
                        WHERE medication_id = ? AND interval_days IS NOT NULL
                    ''', (date.today().strftime('%Y-%m-%d'), new_next_date.strftime('%Y-%m-%d'), medication_id))
                    
                    conn.commit()
                    
        except Exception as e:
            print(f"Error updating next reminder date: {e}")
    
    def get_all_patients(self) -> List[Tuple]:
        """Get all patients from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT patient_name FROM patients ORDER BY patient_name')
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting patients: {e}")
            return []
    
    def get_medication_schedule_for_year(self, patient_name: str, medication_id: int) -> List[Dict]:
        """Generate medication schedule for the next year from current date."""
        try:
            from datetime import date, timedelta
            import calendar
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get medication and schedule info
                cursor.execute('''
                    SELECT m.medication_name, m.dosage, m.frequency, m.start_date, m.end_date,
                           ms.time_of_day, ms.days_of_week, ms.interval_days, ms.alert_timings
                    FROM medications m
                    JOIN medication_schedule ms ON m.id = ms.medication_id
                    WHERE m.id = ? AND m.patient_name = ? AND m.active = 1
                ''', (medication_id, patient_name))
                
                result = cursor.fetchone()
                if not result:
                    return []
                
                med_name, dosage, frequency, start_date_str, end_date_str, time_of_day, days_of_week_json, interval_days, alert_timings_json = result
                
                # Parse data
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                days_of_week = json.loads(days_of_week_json) if days_of_week_json else []
                alert_timings = json.loads(alert_timings_json) if alert_timings_json else ["1 hour before"]
                
                # Generate schedule for next year
                current_date = date.today()
                end_generate_date = current_date + timedelta(days=365)
                
                if end_date and end_date < end_generate_date:
                    end_generate_date = end_date
                
                schedule = []
                check_date = max(start_date, current_date)
                
                while check_date <= end_generate_date:
                    include_date = False
                    
                    if interval_days:
                        # Interval-based medication
                        days_since_start = (check_date - start_date).days
                        if days_since_start >= 0 and days_since_start % interval_days == 0:
                            include_date = True
                    else:
                        # Weekly medication
                        if check_date.weekday() + 1 in days_of_week:
                            include_date = True
                    
                    if include_date:
                        med_datetime = datetime.combine(check_date, datetime.strptime(time_of_day, '%H:%M:%S').time())
                        
                        # Calculate alert times
                        alerts = []
                        for alert_timing in alert_timings:
                            alert_dt = self._calculate_alert_datetime(med_datetime, alert_timing)
                            alerts.append({
                                'timing': alert_timing,
                                'datetime': alert_dt.strftime('%Y-%m-%d %H:%M:%S')
                            })
                        
                        schedule.append({
                            'date': check_date.strftime('%Y-%m-%d'),
                            'time': time_of_day,
                            'medication_name': med_name,
                            'dosage': dosage,
                            'frequency': frequency,
                            'alerts': alerts,
                            'day_of_week': calendar.day_name[check_date.weekday()],
                            'week_number': check_date.isocalendar()[1]
                        })
                    
                    check_date += timedelta(days=1)
                
                return schedule
                
        except Exception as e:
            print(f"Error generating medication schedule: {e}")
            return []
    
    def delete_medication(self, medication_id: int) -> bool:
        """Delete a medication and its associated schedules."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete schedule first
                cursor.execute('DELETE FROM medication_schedule WHERE medication_id = ?', (medication_id,))
                
                # Delete adherence records
                cursor.execute('DELETE FROM medication_adherence WHERE medication_id = ?', (medication_id,))
                
                # Delete effectiveness records
                cursor.execute('DELETE FROM medication_effectiveness WHERE medication_id = ?', (medication_id,))
                
                # Delete medication
                cursor.execute('DELETE FROM medications WHERE id = ?', (medication_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error deleting medication: {e}")
            return False
    
    def update_medication(self, medication_id: int, medication_data: Dict) -> bool:
        """Update an existing medication."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update medication info
                cursor.execute('''
                    UPDATE medications 
                    SET medication_name = ?, dosage = ?, frequency = ?, end_date = ?,
                        instructions = ?, indication = ?, doctor_name = ?, updated_date = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    medication_data['medication_name'],
                    medication_data['dosage'],
                    medication_data['frequency'],
                    medication_data.get('end_date'),
                    medication_data.get('instructions', ''),
                    medication_data.get('indication', ''),
                    medication_data.get('doctor_name', ''),
                    medication_id
                ))
                
                # Update schedule if provided
                if 'schedule' in medication_data:
                    # Delete existing schedules
                    cursor.execute('DELETE FROM medication_schedule WHERE medication_id = ?', (medication_id,))
                    
                    # Add new schedules
                    for schedule in medication_data['schedule']:
                        next_reminder = self._calculate_next_reminder_date(
                            medication_data.get('start_date', datetime.now().strftime('%Y-%m-%d')), 
                            schedule.get('interval_days'), 
                            schedule.get('days', [])
                        )
                        
                        cursor.execute('''
                            INSERT INTO medication_schedule 
                            (medication_id, time_of_day, days_of_week, interval_days, 
                             reminder_enabled, email_enabled, alert_timings, next_reminder_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            medication_id,
                            schedule['time'],
                            json.dumps(schedule.get('days', [])),
                            schedule.get('interval_days'),
                            schedule.get('reminder_enabled', True),
                            schedule.get('email_enabled', True),
                            json.dumps(schedule.get('alert_timings', ["1 hour before"])),
                            next_reminder
                        ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating medication: {e}")
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