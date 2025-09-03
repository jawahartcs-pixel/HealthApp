"""
Smart Medication Reminder System
Handles medication tracking, reminders, adherence monitoring, and integration with blood test results.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional, Any
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pytz

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
                        
                        # Check if any alert should be triggered now (include current date if medication time hasn't passed)
                        alert_due = False
                        for alert_timing in alert_timings:
                            alert_datetime = self._calculate_alert_datetime(medication_datetime, alert_timing)
                            # For current date, include if medication time hasn't passed yet
                            if check_date == date.today():
                                if medication_datetime.time() >= check_time.time():
                                    alert_due = True
                                    break
                            elif check_time >= alert_datetime:
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
                
                # Debug logging
                print(f"DEBUG: update_medication called for ID {medication_id}")
                print(f"DEBUG: medication_data keys: {medication_data.keys()}")
                if 'schedule' in medication_data:
                    print(f"DEBUG: Schedule entries: {len(medication_data['schedule'])}")
                    for i, sched in enumerate(medication_data['schedule']):
                        print(f"DEBUG: Schedule {i}: time={sched.get('time')}, days={sched.get('days')}, interval={sched.get('interval_days')}")
                
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
                    print(f"DEBUG: Deleting existing schedules for medication {medication_id}")
                    cursor.execute('DELETE FROM medication_schedule WHERE medication_id = ?', (medication_id,))
                    
                    # Add new schedules
                    for i, schedule in enumerate(medication_data['schedule']):
                        next_reminder = self._calculate_next_reminder_date(
                            medication_data.get('start_date', datetime.now().strftime('%Y-%m-%d')), 
                            schedule.get('interval_days'), 
                            schedule.get('days', [])
                        )
                        
                        print(f"DEBUG: Inserting schedule {i}: time={schedule['time']}, next_reminder={next_reminder}")
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
                        
                        # Verify insertion
                        cursor.execute('SELECT time_of_day FROM medication_schedule WHERE medication_id = ? ORDER BY id DESC LIMIT 1', (medication_id,))
                        inserted_time = cursor.fetchone()
                        print(f"DEBUG: Verified insertion - time in DB: {inserted_time[0] if inserted_time else 'None'}")
                
                conn.commit()
                print(f"DEBUG: Transaction committed for medication {medication_id}")
                
                # Verify the changes were saved
                cursor.execute('SELECT time_of_day FROM medication_schedule WHERE medication_id = ? ORDER BY id DESC', (medication_id,))
                saved_times = cursor.fetchall()
                print(f"DEBUG: Times saved in database: {[t[0] for t in saved_times]}")
                
                print(f"DEBUG: Successfully updated medication {medication_id}")
                return True
                
        except Exception as e:
            print(f"Error updating medication: {e}")
            import traceback
            print(f"DEBUG: Full error traceback: {traceback.format_exc()}")
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
        """Get schedule for a specific medication including alert timings."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, time_of_day, days_of_week, reminder_enabled, alert_timings
                    FROM medication_schedule
                    WHERE medication_id = ?
                    ORDER BY time_of_day
                ''', (medication_id,))
                
                results = cursor.fetchall()
                schedule = []
                
                for row in results:
                    # Parse alert timings
                    alert_timings = []
                    if row[4]:
                        try:
                            alert_timings = json.loads(row[4])
                        except:
                            alert_timings = ["1 hour before"]
                    else:
                        alert_timings = ["1 hour before"]
                    
                    schedule.append({
                        'id': row[0],
                        'time': row[1],
                        'days': json.loads(row[2]) if row[2] else [1,2,3,4,5,6,7],
                        'reminder_enabled': row[3],
                        'alert_timings': alert_timings
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
    
    def _get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT smtp_server, smtp_port, email_username, email_password, 
                           sender_name, use_ssl
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
                        'use_ssl': bool(result[5])
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting SMTP configuration: {e}")
            return {}
    
    def send_reminder_email(self, patient_name: str, patient_email: str, medication_name: str, 
                           dosage: str, reminder_time: str, alert_type: str = "reminder") -> bool:
        """Send reminder email using database SMTP configuration."""
        smtp_config = self._get_smtp_config()
        if not smtp_config:
            print("No SMTP configuration found")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{smtp_config['sender_name']} <{smtp_config['email_username']}>"
            msg['To'] = patient_email
            
            if alert_type == "reminder":
                msg['Subject'] = f"Medication Reminder: {medication_name}"
                body = f"""
Dear {patient_name},

This is a reminder for your medication:

Medication: {medication_name}
Dosage: {dosage}
Time: {reminder_time}

Please take your medication as prescribed.

Best regards,
{smtp_config['sender_name']}
                """
            else:  # alert_type == "alert"
                msg['Subject'] = f"Medication Alert: {medication_name} - {alert_type}"
                body = f"""
Dear {patient_name},

Alert: Your medication {medication_name} ({dosage}) is due at {reminder_time}.

Please prepare to take your medication.

Best regards,
{smtp_config['sender_name']}
                """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email with improved SSL/TLS handling
            server = None
            try:
                # Try SMTP_SSL first (port 465)
                if smtp_config['smtp_port'] == 465:
                    server = smtplib.SMTP_SSL(smtp_config['smtp_server'], smtp_config['smtp_port'])
                else:
                    # Use SMTP with STARTTLS (port 587)
                    server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
                    server.starttls()
                
                server.login(smtp_config['email_username'], smtp_config['email_password'])
            except smtplib.SMTPException as e:
                # Fallback: try the opposite SSL method
                if server:
                    try:
                        server.quit()
                    except:
                        pass
                
                try:
                    if smtp_config['smtp_port'] == 465:
                        server = smtplib.SMTP(smtp_config['smtp_server'], 587)
                        server.starttls()
                    else:
                        server = smtplib.SMTP_SSL(smtp_config['smtp_server'], 465)
                    
                    server.login(smtp_config['email_username'], smtp_config['email_password'])
                except Exception as fallback_e:
                    print(f"Both SSL methods failed. Original: {e}, Fallback: {fallback_e}")
                    return False
            
            server.send_message(msg)
            server.quit()
            
            print(f"Email reminder sent to {patient_email} for {medication_name}")
            return True
            
        except Exception as e:
            print(f"Error sending email reminder: {e}")
            return False
    
    def send_automatic_reminders(self) -> int:
        """Send automatic reminders for due medications. Returns count of sent reminders."""
        try:
            current_time = datetime.now()
            due_reminders = self.get_due_reminders(current_time.date(), current_time)
            sent_count = 0
            
            # Get patient emails from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT patient_name, email FROM patients WHERE email IS NOT NULL AND email != ""')
                patient_emails = dict(cursor.fetchall())
            
            # Send reminders
            for reminder in due_reminders:
                patient_name = reminder.get('patient_name')
                patient_email = patient_emails.get(patient_name)
                
                if patient_email:
                    success = self.send_reminder_email(
                        patient_name=patient_name,
                        patient_email=patient_email,
                        medication_name=reminder['medication_name'],
                        dosage=reminder['dosage'],
                        reminder_time=reminder['time'],
                        alert_type="reminder"
                    )
                    if success:
                        sent_count += 1
            
            return sent_count
            
        except Exception as e:
            print(f"Error sending automatic reminders: {e}")
            return 0
    
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
    
    def get_pending_email_reminders(self) -> List[Dict]:
        """Get all medications that need email reminders sent based on configured timezone."""
        try:
            # Get timezone from SMTP config
            from database import Database
            db = Database(self.db_path)
            smtp_config = db.get_smtp_config()
            timezone_str = smtp_config.get('timezone', 'UTC') if smtp_config else 'UTC'
            
            # Get current time in configured timezone
            tz = pytz.timezone(timezone_str)
            current_datetime = datetime.now(tz)
            current_date = current_datetime.date()
            current_time = current_datetime.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get medications with their schedules and patient emails
                cursor.execute('''
                    SELECT DISTINCT 
                        m.id as medication_id,
                        m.patient_name,
                        m.medication_name,
                        m.dosage,
                        ms.time_of_day,
                        ms.alert_timings,
                        ms.email_enabled,
                        ms.last_reminder_date,
                        p.patient_id,
                        p.email as patient_email
                    FROM medications m
                    JOIN medication_schedule ms ON m.id = ms.medication_id
                    LEFT JOIN patients p ON m.patient_name = p.patient_name
                    WHERE m.active = 1 
                    AND ms.reminder_enabled = 1 
                    AND ms.email_enabled = 1
                    AND p.email IS NOT NULL
                    AND p.email != ''
                    AND (m.end_date IS NULL OR m.end_date >= ?)
                ''', (current_date,))
                
                results = cursor.fetchall()
                pending_reminders = []
                
                for row in results:
                    medication_id, patient_name, medication_name, dosage, time_of_day, \
                    alert_timings, email_enabled, last_reminder_date, patient_id, patient_email = row
                    
                    # Parse alert timings
                    if alert_timings:
                        try:
                            alert_list = json.loads(alert_timings) if isinstance(alert_timings, str) else alert_timings
                        except:
                            alert_list = ["1 hour before"]
                    else:
                        alert_list = ["1 hour before"]
                    
                    # Parse scheduled time
                    try:
                        scheduled_time = datetime.strptime(time_of_day, '%H:%M:%S').time()
                    except:
                        try:
                            scheduled_time = datetime.strptime(time_of_day, '%H:%M').time()
                        except:
                            continue
                    
                    # Check if we should send reminders for each alert timing
                    for alert_timing in alert_list:
                        offset_minutes = self._parse_alert_offset(alert_timing)
                        
                        # Calculate reminder time (ensure timezone consistency)
                        scheduled_datetime = tz.localize(datetime.combine(current_date, scheduled_time))
                        reminder_datetime = scheduled_datetime + timedelta(minutes=offset_minutes)
                        
                        # Check if it's time to send this reminder
                        if self._should_send_reminder(current_datetime, reminder_datetime, last_reminder_date):
                            pending_reminders.append({
                                'medication_id': medication_id,
                                'patient_id': patient_id,
                                'patient_name': patient_name,
                                'patient_email': patient_email,
                                'medication_name': medication_name,
                                'dosage': dosage,
                                'reminder_time': time_of_day,
                                'alert_timing': alert_timing,
                                'scheduled_datetime': scheduled_datetime,
                                'reminder_datetime': reminder_datetime
                            })
                
                return pending_reminders
                
        except Exception as e:
            print(f"Error getting pending reminders: {e}")
            return []
    
    def _parse_alert_offset(self, alert_timing: str) -> int:
        """Parse alert timing string to minutes offset."""
        alert_timing = alert_timing.lower()
        if "5 minutes before" in alert_timing:
            return -5
        elif "1 hour before" in alert_timing:
            return -60
        elif "1 day before" in alert_timing:
            return -1440  # 24 hours * 60 minutes
        else:
            return -60  # Default 1 hour before
    
    def _should_send_reminder(self, current_datetime: datetime, reminder_datetime: datetime, 
                             last_reminder_date: str = None) -> bool:
        """Check if reminder should be sent based on timing and last sent date."""
        # Ensure both datetimes are timezone-aware for comparison
        if current_datetime.tzinfo is None:
            current_datetime = pytz.UTC.localize(current_datetime)
        if reminder_datetime.tzinfo is None:
            reminder_datetime = pytz.UTC.localize(reminder_datetime)
            
        # Check if reminder time has passed (within 2 minutes window)
        time_diff = (current_datetime - reminder_datetime).total_seconds() / 60
        
        # Send if within 2 minutes of reminder time (past or future)
        if abs(time_diff) <= 2:
            # Check if we already sent a reminder today
            if last_reminder_date:
                try:
                    last_date = datetime.strptime(last_reminder_date, '%Y-%m-%d').date()
                    current_date_only = current_datetime.date() if hasattr(current_datetime, 'date') else current_datetime
                    if hasattr(current_date_only, 'date'):
                        current_date_only = current_date_only.date()
                    if last_date >= current_date_only:
                        return False  # Already sent today
                except:
                    pass
            return True
        
        return False
    
    def process_pending_email_reminders(self) -> Dict[str, Any]:
        """Process all pending email reminders and send emails."""
        try:
            pending_reminders = self.get_pending_email_reminders()
            results = {
                'total_pending': len(pending_reminders),
                'sent_successfully': 0,
                'failed': 0,
                'sent_reminders': [],
                'failed_reminders': []
            }
            
            from database import Database
            db = Database(self.db_path)
            
            for reminder in pending_reminders:
                # Enhanced email sending with history logging
                success = self._send_enhanced_reminder_email(
                    reminder=reminder,
                    db=db
                )
                
                if success:
                    results['sent_successfully'] += 1
                    results['sent_reminders'].append(reminder)
                    
                    # Update last reminder date
                    self._update_last_reminder_date(reminder['medication_id'])
                else:
                    results['failed'] += 1
                    results['failed_reminders'].append(reminder)
            
            return results
            
        except Exception as e:
            print(f"Error processing pending reminders: {e}")
            return {
                'total_pending': 0,
                'sent_successfully': 0,
                'failed': 0,
                'error': str(e)
            }
    
    def test_smtp_connection(self, smtp_config: Dict) -> Dict[str, any]:
        """Test SMTP connection with detailed debugging."""
        results = {
            'success': False,
            'method_used': None,
            'error': None,
            'attempts': []
        }
        
        # List of connection methods to try
        connection_methods = [
            {'name': 'SMTP_SSL_465', 'port': 465, 'ssl_method': 'SSL'},
            {'name': 'SMTP_STARTTLS_587', 'port': 587, 'ssl_method': 'STARTTLS'},
            {'name': 'SMTP_STARTTLS_configured', 'port': smtp_config.get('smtp_port', 587), 'ssl_method': 'STARTTLS'},
            {'name': 'SMTP_SSL_configured', 'port': smtp_config.get('smtp_port', 587), 'ssl_method': 'SSL'}
        ]
        
        for method in connection_methods:
            attempt = {'method': method['name'], 'success': False, 'error': None}
            
            try:
                server = None
                if method['ssl_method'] == 'SSL':
                    server = smtplib.SMTP_SSL(smtp_config['smtp_server'], method['port'], timeout=30)
                else:  # STARTTLS
                    server = smtplib.SMTP(smtp_config['smtp_server'], method['port'], timeout=30)
                    server.starttls()
                
                server.login(smtp_config['email_username'], smtp_config['email_password'])
                server.quit()
                
                attempt['success'] = True
                results['success'] = True
                results['method_used'] = method
                results['attempts'].append(attempt)
                print(f"SMTP connection successful using {method['name']}")
                break
                
            except Exception as e:
                attempt['error'] = str(e)
                results['attempts'].append(attempt)
                print(f"SMTP {method['name']} failed: {e}")
                
                if server:
                    try:
                        server.quit()
                    except:
                        pass
        
        if not results['success']:
            results['error'] = "All connection methods failed"
            
        return results

    def _send_enhanced_reminder_email(self, reminder: Dict, db) -> bool:
        """Send enhanced reminder email with history logging."""
        try:
            smtp_config = db.get_smtp_config()
            if not smtp_config or not smtp_config.get('smtp_server'):
                print("No SMTP configuration found")
                return False
            
            # Create email content
            subject = f"💊 Medication Reminder: {reminder['medication_name']}"
            
            body = f"""
Dear {reminder['patient_name']},

This is your scheduled medication reminder:

Medication: {reminder['medication_name']}
Dosage: {reminder['dosage']}
Scheduled Time: {reminder['reminder_time']}
Alert Type: {reminder['alert_timing']}

Please take your medication as prescribed by your doctor.

If you have any questions about your medication, please consult with your healthcare provider.

Best regards,
Medical Reminder System
"""
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = f"{smtp_config.get('sender_name', 'Medical Reminder System')} <{smtp_config['email_username']}>"
            msg['To'] = reminder['patient_email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email using connection test results
            connection_test = self.test_smtp_connection(smtp_config)
            
            if not connection_test['success']:
                print(f"SMTP connection failed: {connection_test['error']}")
                for attempt in connection_test['attempts']:
                    print(f"  - {attempt['method']}: {attempt.get('error', 'Success')}")
                return False
            
            # Use the successful connection method
            method = connection_test['method_used']
            server = None
            
            if method['ssl_method'] == 'SSL':
                server = smtplib.SMTP_SSL(smtp_config['smtp_server'], method['port'], timeout=30)
            else:  # STARTTLS
                server = smtplib.SMTP(smtp_config['smtp_server'], method['port'], timeout=30)
                server.starttls()
            
            server.login(smtp_config['email_username'], smtp_config['email_password'])
            
            text = msg.as_string()
            server.sendmail(smtp_config['email_username'], reminder['patient_email'], text)
            server.quit()
            
            # Log email to history
            db.add_email_history(
                patient_id=reminder['patient_id'],
                patient_name=reminder['patient_name'],
                patient_email=reminder['patient_email'],
                medication_name=reminder['medication_name'],
                medication_dosage=reminder['dosage'],
                reminder_time=reminder['reminder_time'],
                email_subject=subject,
                email_body=body,
                email_type="automated_reminder"
            )
            
            print(f"Automated email reminder sent to {reminder['patient_email']} for {reminder['medication_name']}")
            return True
            
        except Exception as e:
            print(f"Error sending enhanced reminder email: {e}")
            return False
    
    def _update_last_reminder_date(self, medication_id: int):
        """Update the last reminder date for a medication."""
        try:
            # Get timezone from config
            from database import Database
            db = Database(self.db_path)
            smtp_config = db.get_smtp_config()
            timezone_str = smtp_config.get('timezone', 'UTC') if smtp_config else 'UTC'
            tz = pytz.timezone(timezone_str)
            current_date = datetime.now(tz).date()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE medication_schedule 
                    SET last_reminder_date = ?
                    WHERE medication_id = ?
                ''', (current_date, medication_id))
                conn.commit()
        except Exception as e:
            print(f"Error updating last reminder date: {e}")
    
