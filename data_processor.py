from datetime import date
from typing import List, Dict, Any, Optional
import streamlit as st
from database import Database
from investigation_standards import InvestigationStandards

class DataProcessor:
    def __init__(self, database: Database):
        """Initialize data processor with database connection."""
        self.db = database
        self.standards = InvestigationStandards()
    
    def save_test_results(self, patient_name: str, test_date: date, test_results: List[Dict[str, Any]], user_id: int = None) -> bool:
        """Save test results for a patient."""
        try:
            if not patient_name or not test_results:
                st.error("Patient name and test results are required")
                return False
            
            # Validate patient name
            if not self._validate_patient_name(patient_name):
                st.error("Invalid patient name format")
                return False
            
            # Validate test date
            if not self._validate_test_date(test_date):
                st.error("Invalid test date")
                return False
            
            # Add or get patient
            patient_id = self.db.add_patient(patient_name.strip(), user_id)
            
            # Save each test result
            saved_count = 0
            for result in test_results:
                if self._validate_test_result(result):
                    # Use the test type exactly as provided - no additional standardization
                    # The UI layer has already handled standardization vs custom choice
                    test_type_to_save = result['test_type']
                    
                    success = self.db.add_test_result(
                        patient_id=patient_id,
                        test_date=test_date,
                        test_type=test_type_to_save,
                        test_value=result['value'],
                        unit=result.get('unit', ''),
                        user_id=user_id
                    )
                    if success:
                        saved_count += 1
                else:
                    st.warning(f"Skipped invalid test result: {result}")
            
            if saved_count > 0:
                st.success(f"Successfully saved {saved_count} test results for {patient_name}")
                return True
            else:
                st.error("No valid test results were saved")
                return False
                
        except Exception as e:
            st.error(f"Error saving test results: {str(e)}")
            return False
    
    def _validate_patient_name(self, patient_name: str) -> bool:
        """Validate patient name format."""
        if not patient_name or not isinstance(patient_name, str):
            return False
        
        # Remove extra whitespace
        patient_name = patient_name.strip()
        
        # Check length
        if len(patient_name) < 2 or len(patient_name) > 100:
            return False
        
        # Check if it contains at least some alphabetic characters
        if not any(c.isalpha() for c in patient_name):
            return False
        
        # Check for reasonable name format (at least two words)
        words = patient_name.split()
        if len(words) < 2:
            return False
        
        return True
    
    def _validate_test_date(self, test_date: date) -> bool:
        """Validate test date."""
        if not test_date:
            return False
        
        # Check if date is not in the future
        if test_date > date.today():
            return False
        
        # Check if date is not too old (e.g., before 1900)
        if test_date.year < 1900:
            return False
        
        return True
    
    def _validate_test_result(self, result: Dict[str, Any]) -> bool:
        """Validate individual test result."""
        try:
            # Check required fields
            if 'test_type' not in result or 'value' not in result:
                return False
            
            # Validate test type
            test_type = result['test_type']
            if not test_type or not isinstance(test_type, str) or len(test_type.strip()) == 0:
                return False
            
            # Validate value
            value = result['value']
            if not isinstance(value, (int, float)):
                return False
            
            # Check for reasonable value range (not negative, not extremely large)
            if value < 0 or value > 1000000:
                return False
            
            return True
            
        except Exception:
            return False
    
    def process_batch_upload(self, file_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process multiple files in batch."""
        results = {
            'successful': 0,
            'failed': 0,
            'total_tests': 0,
            'errors': []
        }
        
        for file_data in file_data_list:
            try:
                success = self.save_test_results(
                    patient_name=file_data['patient_name'],
                    test_date=file_data['test_date'],
                    test_results=file_data['test_results']
                )
                
                if success:
                    results['successful'] += 1
                    results['total_tests'] += len(file_data['test_results'])
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to process file for {file_data['patient_name']}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing file: {str(e)}")
        
        return results
    
    def validate_test_value_range(self, test_type: str, value: float) -> Dict[str, Any]:
        """Validate if test value is within normal ranges and provide interpretation."""
        # Define normal ranges for common tests
        normal_ranges = {
            'Glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL'},
            'Fasting Glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL'},
            'Random Glucose': {'min': 70, 'max': 140, 'unit': 'mg/dL'},
            'HbA1c': {'min': 4.0, 'max': 5.6, 'unit': '%'},
            'Total Cholesterol': {'min': 0, 'max': 200, 'unit': 'mg/dL'},
            'HDL Cholesterol': {'min': 40, 'max': 1000, 'unit': 'mg/dL'},
            'LDL Cholesterol': {'min': 0, 'max': 100, 'unit': 'mg/dL'},
            'Triglycerides': {'min': 0, 'max': 150, 'unit': 'mg/dL'},
            'Hemoglobin': {'min': 12.0, 'max': 18.0, 'unit': 'g/dL'},
            'Hematocrit': {'min': 36, 'max': 50, 'unit': '%'},
            'WBC Count': {'min': 4.5, 'max': 11.0, 'unit': 'thousand/uL'},
            'RBC Count': {'min': 4.2, 'max': 6.1, 'unit': 'million/uL'},
            'Platelet Count': {'min': 150, 'max': 450, 'unit': 'thousand/uL'},
            'ALT': {'min': 7, 'max': 56, 'unit': 'U/L'},
            'AST': {'min': 10, 'max': 40, 'unit': 'U/L'},
            'Creatinine': {'min': 0.6, 'max': 1.3, 'unit': 'mg/dL'},
            'BUN': {'min': 7, 'max': 20, 'unit': 'mg/dL'},
            'TSH': {'min': 0.4, 'max': 4.0, 'unit': 'μIU/mL'},
            'Sodium': {'min': 136, 'max': 145, 'unit': 'mEq/L'},
            'Potassium': {'min': 3.5, 'max': 5.0, 'unit': 'mEq/L'}
        }
        
        validation_result = {
            'is_normal': True,
            'status': 'Normal',
            'message': '',
            'severity': 'normal'
        }
        
        if test_type in normal_ranges:
            range_info = normal_ranges[test_type]
            min_val = range_info['min']
            max_val = range_info['max']
            
            if value < min_val:
                validation_result.update({
                    'is_normal': False,
                    'status': 'Low',
                    'message': f'Below normal range ({min_val}-{max_val} {range_info["unit"]})',
                    'severity': 'low'
                })
            elif value > max_val:
                validation_result.update({
                    'is_normal': False,
                    'status': 'High',
                    'message': f'Above normal range ({min_val}-{max_val} {range_info["unit"]})',
                    'severity': 'high'
                })
            else:
                validation_result['message'] = f'Within normal range ({min_val}-{max_val} {range_info["unit"]})'
        else:
            validation_result['message'] = 'Reference range not available'
        
        return validation_result
    
    def get_patient_summary(self, patient_name: str) -> Dict[str, Any]:
        """Get comprehensive summary for a patient."""
        try:
            # Get all tests for the patient
            patient_tests = self.db.get_patient_tests(patient_name)
            
            if not patient_tests:
                return {'error': 'No tests found for this patient'}
            
            # Convert to a more workable format
            tests_data = []
            for test in patient_tests:
                tests_data.append({
                    'date': test[0],
                    'test_type': test[1],
                    'value': test[2],
                    'unit': test[3]
                })
            
            # Calculate summary statistics
            summary = {
                'total_tests': len(tests_data),
                'unique_test_types': len(set(test['test_type'] for test in tests_data)),
                'first_test_date': min(test['date'] for test in tests_data),
                'last_test_date': max(test['date'] for test in tests_data),
                'test_type_counts': {},
                'recent_abnormal_results': []
            }
            
            # Count tests by type
            for test in tests_data:
                test_type = test['test_type']
                summary['test_type_counts'][test_type] = summary['test_type_counts'].get(test_type, 0) + 1
            
            # Check for recent abnormal results (last 30 days)
            from datetime import datetime, timedelta
            recent_date = datetime.now().date() - timedelta(days=30)
            
            for test in tests_data:
                test_date = datetime.strptime(test['date'], '%Y-%m-%d').date()
                if test_date >= recent_date:
                    validation = self.validate_test_value_range(test['test_type'], test['value'])
                    if not validation['is_normal']:
                        summary['recent_abnormal_results'].append({
                            'date': test['date'],
                            'test_type': test['test_type'],
                            'value': test['value'],
                            'status': validation['status'],
                            'message': validation['message']
                        })
            
            return summary
            
        except Exception as e:
            return {'error': f'Error generating patient summary: {str(e)}'}
    
    def detect_trends(self, patient_name: str, test_type: str) -> Dict[str, Any]:
        """Detect trends in test results over time."""
        try:
            # Get test history for specific test type
            test_history = self.db.get_patient_test_history(patient_name, test_type)
            
            if len(test_history) < 2:
                return {'error': 'Not enough data points for trend analysis'}
            
            # Extract values and dates
            values = [float(test[1]) for test in test_history]
            dates = [test[0] for test in test_history]
            
            # Calculate trend
            if len(values) >= 2:
                # Simple linear trend calculation
                from datetime import datetime
                
                # Convert dates to days since first test
                first_date = datetime.strptime(dates[0], '%Y-%m-%d')
                x_values = [(datetime.strptime(date, '%Y-%m-%d') - first_date).days for date in dates]
                
                # Calculate slope (trend)
                n = len(values)
                sum_x = sum(x_values)
                sum_y = sum(values)
                sum_xy = sum(x * y for x, y in zip(x_values, values))
                sum_x2 = sum(x * x for x in x_values)
                
                if n * sum_x2 - sum_x * sum_x != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                    
                    trend_result = {
                        'slope': slope,
                        'direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
                        'magnitude': abs(slope),
                        'latest_value': values[-1],
                        'previous_value': values[-2] if len(values) >= 2 else None,
                        'change': values[-1] - values[-2] if len(values) >= 2 else 0,
                        'percent_change': ((values[-1] - values[-2]) / values[-2] * 100) if len(values) >= 2 and values[-2] != 0 else 0
                    }
                    
                    return trend_result
                else:
                    return {'error': 'Unable to calculate trend'}
            
            return {'error': 'Insufficient data for trend calculation'}
            
        except Exception as e:
            return {'error': f'Error calculating trend: {str(e)}'}
