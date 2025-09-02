"""
Background Email Processor
Runs every minute to check for and send pending medication reminders.
"""

import time
import sys
import os
from datetime import datetime
from medication_reminder import MedicationReminder

def process_email_reminders():
    """Process pending email reminders."""
    try:
        medication_reminder = MedicationReminder()
        results = medication_reminder.process_pending_email_reminders()
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if results['total_pending'] > 0:
            print(f"[{current_time}] Email Processing Results:")
            print(f"  - Pending: {results['total_pending']}")
            print(f"  - Sent: {results['sent_successfully']}")
            print(f"  - Failed: {results['failed']}")
            
            if results['sent_reminders']:
                for reminder in results['sent_reminders']:
                    print(f"  ✅ Sent to {reminder['patient_name']} for {reminder['medication_name']}")
                    
            if results['failed_reminders']:
                for reminder in results['failed_reminders']:
                    print(f"  ❌ Failed for {reminder['patient_name']} - {reminder['medication_name']}")
        else:
            print(f"[{current_time}] No pending email reminders")
            
        return results
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing reminders: {e}")
        return {'error': str(e)}

def main():
    """Main background processor loop."""
    print("Starting background email reminder processor...")
    print("Checking for pending reminders every minute...")
    
    while True:
        try:
            process_email_reminders()
            time.sleep(60)  # Wait 1 minute before next check
        except KeyboardInterrupt:
            print("\nStopping background email processor...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)  # Continue after error

if __name__ == "__main__":
    main()