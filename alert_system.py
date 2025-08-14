import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from database import Database
from utils import parse_reference_range, is_value_normal

class AlertSystem:
    def __init__(self, database: Database):
        """Initialize alert system with database connection."""
        self.database = database
        
        # Define critical value thresholds (values that require immediate attention)
        self.critical_thresholds = {
            'glucose': {'low': 40, 'high': 400},
            'fasting_glucose': {'low': 40, 'high': 300},
            'random_glucose': {'low': 40, 'high': 400},
            'potassium': {'low': 2.5, 'high': 6.0},
            'sodium': {'low': 120, 'high': 160},
            'hemoglobin': {'low': 6.0, 'high': 20.0},
            'creatinine': {'low': 0.3, 'high': 5.0},
            'platelet_count': {'low': 50, 'high': 1000},
            'wbc_count': {'low': 1.0, 'high': 50.0},
            'alt': {'low': 0, 'high': 300},
            'ast': {'low': 0, 'high': 300},
            'bilirubin_total': {'low': 0, 'high': 10.0},
            'tsh': {'low': 0.01, 'high': 50.0}
        }
        
        # Define alert severity levels
        self.alert_levels = {
            'CRITICAL': {'color': '#dc3545', 'icon': '🚨', 'priority': 1, 'label': 'Critical Alert'},
            'HIGH': {'color': '#fd7e14', 'icon': '⚠️', 'priority': 2, 'label': 'Major Alert'},
            'MEDIUM': {'color': '#ffc107', 'icon': '⚡', 'priority': 3, 'label': 'Medium Alert'},
            'MINOR': {'color': '#17a2b8', 'icon': 'ℹ️', 'priority': 4, 'label': 'Minor Alert'}
        }
    
    def check_test_result(self, test_type: str, value: float, reference_range: str = None, 
                         test_date: str = None) -> Dict[str, Any]:
        """Check a single test result and return alert information."""
        alert = {
            'has_alert': False,
            'level': None,
            'message': '',
            'color': '#28a745',  # Green for normal
            'icon': '✅',
            'recommendations': []
        }
        
        # Check for critical values first
        if self._is_critical_value(test_type, value):
            date_str = f" on {test_date}" if test_date else ""
            header_text = f'{test_type} is critical: {value}{date_str}'
            alert.update({
                'has_alert': True,
                'level': 'CRITICAL',
                'message': f'Critical value requiring immediate attention',
                'header': header_text,
                'color': self.alert_levels['CRITICAL']['color'],
                'icon': self.alert_levels['CRITICAL']['icon'],
                'label': self.alert_levels['CRITICAL']['label'],
                'recommendations': [
                    'Contact healthcare provider immediately',
                    'Do not delay medical attention',
                    'This value may require emergency intervention'
                ]
            })
            return alert
        
        # Check against reference range if provided
        if reference_range:
            is_normal, status = is_value_normal(value, reference_range)
            if not is_normal:
                severity = self._determine_severity(test_type, value, reference_range, status)
                # Enhanced header with status, value and date - move from message to header
                date_str = f" on {test_date}" if test_date else ""
                header_text = f'{test_type} is {status.lower()}: {value}{date_str}'
                alert.update({
                    'has_alert': True,
                    'level': severity,
                    'message': f'Value outside normal range',  # Simple message since detail is in header
                    'header': header_text,
                    'color': self.alert_levels[severity]['color'],
                    'icon': self.alert_levels[severity]['icon'],
                    'label': self.alert_levels[severity]['label'],
                    'recommendations': self._get_recommendations(test_type, status, value)
                })
        
        return alert
    
    def _is_critical_value(self, test_type: str, value: float) -> bool:
        """Check if value is in critical range."""
        test_key = test_type.lower().replace(' ', '_')
        
        if test_key in self.critical_thresholds:
            thresholds = self.critical_thresholds[test_key]
            return value <= thresholds['low'] or value >= thresholds['high']
        
        return False
    
    def _determine_severity(self, test_type: str, value: float, reference_range: str, status: str) -> str:
        """Determine alert severity based on how far outside normal range."""
        try:
            range_info = parse_reference_range(reference_range)
            if not range_info:
                return 'MEDIUM'
            
            min_val = range_info.get('min')
            max_val = range_info.get('max')
            
            if min_val is not None and max_val is not None:
                range_width = max_val - min_val
                
                if status == 'High':
                    deviation = (value - max_val) / range_width
                elif status == 'Low':
                    deviation = (min_val - value) / range_width
                else:
                    return 'MEDIUM'
                
                # Determine severity based on deviation
                if deviation >= 2.0:  # More than 2x range width outside
                    return 'CRITICAL'
                elif deviation >= 1.0:  # More than 1x range width outside
                    return 'HIGH'
                elif deviation >= 0.5:  # More than 0.5x range width outside
                    return 'MEDIUM'
                else:
                    return 'MINOR'
            
            return 'MEDIUM'
        except:
            return 'MEDIUM'
    
    def _get_recommendations(self, test_type: str, status: str, value: float) -> List[str]:
        """Get recommendations based on test type and abnormal status."""
        recommendations = []
        test_key = test_type.lower().replace(' ', '_')
        
        # General recommendations
        if status == 'High':
            recommendations.append(f"Consult healthcare provider about elevated {test_type}")
        elif status == 'Low':
            recommendations.append(f"Consult healthcare provider about low {test_type}")
        
        # Specific recommendations by test type
        if test_key in ['glucose', 'fasting_glucose', 'random_glucose']:
            if status == 'High':
                recommendations.extend([
                    "Monitor blood sugar levels closely",
                    "Follow diabetic diet if applicable",
                    "Check medication timing and dosage"
                ])
            elif status == 'Low':
                recommendations.extend([
                    "Consider eating a balanced meal",
                    "Monitor for hypoglycemia symptoms",
                    "Check medication timing"
                ])
        
        elif test_key in ['total_cholesterol', 'ldl_cholesterol']:
            if status == 'High':
                recommendations.extend([
                    "Consider heart-healthy diet",
                    "Increase physical activity",
                    "Discuss statin therapy options"
                ])
        
        elif test_key == 'hemoglobin':
            if status == 'Low':
                recommendations.extend([
                    "Consider iron-rich foods",
                    "Check for signs of anemia",
                    "Evaluate for underlying bleeding"
                ])
        
        elif test_key in ['alt', 'ast']:
            if status == 'High':
                recommendations.extend([
                    "Avoid alcohol consumption",
                    "Review current medications",
                    "Consider liver function evaluation"
                ])
        
        elif test_key == 'creatinine':
            if status == 'High':
                recommendations.extend([
                    "Stay well hydrated",
                    "Monitor kidney function",
                    "Review medications affecting kidneys"
                ])
        
        elif test_key == 'tsh':
            if status == 'High':
                recommendations.extend([
                    "Thyroid function evaluation needed",
                    "Consider hypothyroidism symptoms",
                    "Monitor energy levels and weight"
                ])
            elif status == 'Low':
                recommendations.extend([
                    "Consider hyperthyroidism symptoms",
                    "Monitor heart rate and weight",
                    "Evaluate thyroid medication dosage"
                ])
        
        # Always add follow-up recommendation
        recommendations.append("Schedule follow-up testing as advised")
        
        return recommendations
    
    def get_patient_alerts(self, patient_name: str) -> List[Dict[str, Any]]:
        """Get all alerts for a specific patient."""
        alerts = []
        
        # Get all test results for patient
        test_results = self.database.get_patient_tests(patient_name)
        
        for test_date, test_type, value, unit, reference_range in test_results:
            alert = self.check_test_result(test_type, value, reference_range, test_date)
            if alert['has_alert']:
                alert.update({
                    'patient_name': patient_name,
                    'test_date': test_date,
                    'test_type': test_type,
                    'value': value,
                    'unit': unit,
                    'reference_range': reference_range
                })
                alerts.append(alert)
        
        # Sort by priority (critical first) and then by date
        alerts.sort(key=lambda x: (self.alert_levels[x['level']]['priority'], x['test_date']), reverse=True)
        
        return alerts
    
    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts across all patients."""
        alerts = []
        
        # Get all patients
        patients = self.database.get_all_patients()
        
        for patient_data in patients:
            patient_id, patient_name = patient_data[0], patient_data[1]
            patient_alerts = self.get_patient_alerts(patient_name)
            alerts.extend(patient_alerts)
        
        # Sort by priority and date
        alerts.sort(key=lambda x: (self.alert_levels[x['level']]['priority'], x['test_date']), reverse=True)
        
        return alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts in the system."""
        all_alerts = self.get_all_alerts()
        
        summary = {
            'total_alerts': len(all_alerts),
            'critical_alerts': len([a for a in all_alerts if a['level'] == 'CRITICAL']),
            'high_alerts': len([a for a in all_alerts if a['level'] == 'HIGH']),
            'medium_alerts': len([a for a in all_alerts if a['level'] == 'MEDIUM']),
            'low_alerts': len([a for a in all_alerts if a['level'] == 'LOW']),
            'patients_with_alerts': len(set([a['patient_name'] for a in all_alerts])),
            'most_recent_alert': all_alerts[0] if all_alerts else None
        }
        
        return summary
    
    def get_trending_alerts(self, patient_name: str, test_type: str) -> List[Dict[str, Any]]:
        """Get trending alerts for a specific test type over time."""
        test_history = self.database.get_patient_test_history(patient_name, test_type)
        
        alerts = []
        for test_date, value, unit, reference_range in test_history:
            alert = self.check_test_result(test_type, value, reference_range)
            if alert['has_alert']:
                alert.update({
                    'patient_name': patient_name,
                    'test_date': test_date,
                    'test_type': test_type,
                    'value': value,
                    'unit': unit,
                    'reference_range': reference_range
                })
                alerts.append(alert)
        
        return alerts
    
    def check_recent_alerts(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get alerts from recent test results."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        all_alerts = self.get_all_alerts()
        recent_alerts = []
        
        for alert in all_alerts:
            try:
                test_date = datetime.strptime(alert['test_date'], '%Y-%m-%d').date()
                if test_date >= cutoff_date:
                    recent_alerts.append(alert)
            except:
                continue
        
        return recent_alerts