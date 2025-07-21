"""
Simplified Anomaly Detection for Blood Test Results
This module provides robust anomaly detection that handles data structure variations gracefully.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class SimpleAnomalyDetector:
    def __init__(self, database):
        """Initialize anomaly detection system with database connection."""
        self.database = database
        self.scaler = StandardScaler()
        
    def detect_anomalies(self, patient_name: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        Detect anomalies using simplified, robust algorithms.
        Returns comprehensive anomaly analysis.
        """
        try:
            # Get test data
            if patient_name:
                test_data = self._get_patient_data(patient_name, user_id)
            else:
                test_data = self._get_all_data(user_id)
            
            if test_data.empty:
                return {'error': 'No test data available for analysis'}
            
            # Apply simplified anomaly detection
            results = {
                'statistical_outliers': self._statistical_outlier_detection(test_data),
                'temporal_anomalies': self._temporal_anomaly_detection(test_data),
                'isolation_forest': self._simple_isolation_forest(test_data),
                'summary': self._generate_summary(test_data),
                'status': 'success'
            }
            
            return results
            
        except Exception as e:
            return {'error': f'Anomaly detection failed: {str(e)}', 'status': 'error'}
    
    def _get_patient_data(self, patient_name: str, user_id: int) -> pd.DataFrame:
        """Get test data for a specific patient."""
        tests = self.database.get_patient_tests(patient_name, user_id)
        if not tests:
            return pd.DataFrame()
        
        # get_patient_tests returns 5 columns: test_date, test_type, test_value, unit, reference_range
        df = pd.DataFrame(tests, columns=['test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['patient_name'] = patient_name  # Add patient name manually
        df['test_date'] = pd.to_datetime(df['test_date'])
        df['test_value'] = pd.to_numeric(df['test_value'], errors='coerce')
        return df.dropna(subset=['test_value'])
    
    def _get_all_data(self, user_id: int) -> pd.DataFrame:
        """Get all test data for anomaly detection."""
        tests = self.database.get_all_test_results()
        if not tests:
            return pd.DataFrame()
        
        # get_all_test_results returns 6 columns: patient_name, test_date, test_type, test_value, unit, reference_range
        df = pd.DataFrame(tests, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        
        # Filter by user_id if provided (need to query database differently for user filtering)
        if user_id:
            # Get user-specific data using a different method
            user_tests = []
            patients = self.database.get_all_patients(user_id)
            for patient in patients:
                patient_name = patient[1]
                patient_tests = self.database.get_patient_tests(patient_name, user_id)
                for test in patient_tests:
                    user_tests.append([patient_name] + list(test))
            
            if not user_tests:
                return pd.DataFrame()
            
            df = pd.DataFrame(user_tests, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        
        df['test_date'] = pd.to_datetime(df['test_date'])
        df['test_value'] = pd.to_numeric(df['test_value'], errors='coerce')
        return df.dropna(subset=['test_value'])
    
    def _statistical_outlier_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect statistical outliers using Z-score method."""
        try:
            anomalies = []
            
            # Group by test type for more accurate outlier detection
            for test_type in df['test_type'].unique():
                test_data = df[df['test_type'] == test_type]['test_value']
                if len(test_data) < 5:
                    continue
                
                # Calculate Z-scores
                z_scores = np.abs(stats.zscore(test_data))
                outlier_threshold = 2.5
                
                # Find outliers
                outlier_indices = test_data.index[z_scores > outlier_threshold]
                
                for idx in outlier_indices:
                    row = df.loc[idx]
                    anomalies.append({
                        'patient_name': row['patient_name'],
                        'test_date': row['test_date'].strftime('%Y-%m-%d'),
                        'test_type': row['test_type'],
                        'value': float(row['test_value']),
                        'z_score': float(z_scores[test_data.index.get_loc(idx)]),
                        'severity': 'high' if z_scores[test_data.index.get_loc(idx)] > 3.5 else 'medium',
                        'method': 'statistical_outlier'
                    })
            
            return {
                'anomalies': anomalies,
                'method': 'statistical_outliers',
                'total_analyzed': len(df),
                'anomaly_count': len(anomalies),
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'statistical_outliers', 'status': 'error', 'error': str(e)}
    
    def _temporal_anomaly_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect temporal anomalies in test trends."""
        try:
            anomalies = []
            
            for patient in df['patient_name'].unique():
                patient_data = df[df['patient_name'] == patient]
                
                for test_type in patient_data['test_type'].unique():
                    test_data = patient_data[patient_data['test_type'] == test_type].copy()
                    if len(test_data) < 3:
                        continue
                    
                    test_data = test_data.sort_values('test_date')
                    values = test_data['test_value'].values
                    
                    # Detect sudden changes
                    changes = np.diff(values)
                    if len(changes) == 0:
                        continue
                        
                    mean_change = np.mean(np.abs(changes))
                    std_change = np.std(changes)
                    
                    if std_change == 0:
                        continue
                    
                    for i, change in enumerate(changes):
                        if abs(change) > mean_change + 2.5 * std_change:
                            anomalies.append({
                                'patient_name': patient,
                                'test_date': test_data.iloc[i+1]['test_date'].strftime('%Y-%m-%d'),
                                'test_type': test_type,
                                'value': float(values[i+1]),
                                'previous_value': float(values[i]),
                                'change': float(change),
                                'severity': 'high' if abs(change) > mean_change + 3.5 * std_change else 'medium',
                                'method': 'temporal_anomaly'
                            })
            
            return {
                'anomalies': anomalies,
                'method': 'temporal_anomalies',
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'temporal_anomalies', 'status': 'error', 'error': str(e)}
    
    def _simple_isolation_forest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simple Isolation Forest detection for individual test values."""
        try:
            anomalies = []
            
            # Analyze each test type separately to avoid column mismatch
            for test_type in df['test_type'].unique():
                test_data = df[df['test_type'] == test_type].copy()
                if len(test_data) < 5:
                    continue
                
                # Use only test values for isolation forest
                X = test_data['test_value'].values.reshape(-1, 1)
                
                # Apply Isolation Forest
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                anomaly_labels = iso_forest.fit_predict(X)
                anomaly_scores = iso_forest.decision_function(X)
                
                # Identify anomalies
                for i, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                    if label == -1:  # Anomaly detected
                        row = test_data.iloc[i]
                        anomalies.append({
                            'patient_name': row['patient_name'],
                            'test_date': row['test_date'].strftime('%Y-%m-%d'),
                            'test_type': row['test_type'],
                            'value': float(row['test_value']),
                            'anomaly_score': float(score),
                            'severity': 'high' if score < -0.5 else 'medium',
                            'method': 'isolation_forest'
                        })
            
            return {
                'anomalies': anomalies,
                'method': 'isolation_forest',
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'isolation_forest', 'status': 'error', 'error': str(e)}
    
    def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for the analysis."""
        try:
            return {
                'total_patients': df['patient_name'].nunique(),
                'total_tests': len(df),
                'test_types': df['test_type'].nunique(),
                'date_range': {
                    'start': df['test_date'].min().strftime('%Y-%m-%d'),
                    'end': df['test_date'].max().strftime('%Y-%m-%d')
                },
                'value_range': {
                    'min': float(df['test_value'].min()),
                    'max': float(df['test_value'].max()),
                    'mean': float(df['test_value'].mean())
                }
            }
        except Exception as e:
            return {'error': f'Summary generation failed: {str(e)}'}
    
    def get_patient_anomaly_summary(self, patient_name: str, user_id: int = None) -> Dict[str, Any]:
        """Get anomaly summary for a specific patient."""
        try:
            # Get patient-specific anomaly analysis
            results = self.detect_anomalies(patient_name, user_id)
            
            if 'error' in results:
                return results
            
            # Compile summary
            total_anomalies = 0
            severity_counts = {'high': 0, 'medium': 0, 'low': 0}
            anomaly_types = {}
            
            for method, data in results.items():
                if method in ['statistical_outliers', 'temporal_anomalies', 'isolation_forest']:
                    if isinstance(data, dict) and 'anomalies' in data:
                        anomalies = data['anomalies']
                        total_anomalies += len(anomalies)
                        
                        for anomaly in anomalies:
                            severity = anomaly.get('severity', 'medium')
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1
                            
                            method_name = anomaly.get('method', method)
                            if method_name not in anomaly_types:
                                anomaly_types[method_name] = []
                            anomaly_types[method_name].append(anomaly)
            
            # Collect all anomalies for this patient
            patient_anomalies = []
            for method, data in results.items():
                if method in ['statistical_outliers', 'temporal_anomalies', 'isolation_forest']:
                    if isinstance(data, dict) and 'anomalies' in data:
                        patient_anomalies.extend(data['anomalies'])
            
            return {
                'patient_name': patient_name,
                'total_anomalies': total_anomalies,
                'severity_breakdown': severity_counts,
                'severity_distribution': severity_counts,  # Add for backward compatibility
                'anomaly_types': anomaly_types,
                'detailed_results': results,
                'recommendations': self._generate_patient_recommendations(patient_name, results, total_anomalies),
                'anomalies': patient_anomalies,  # Add complete anomalies list for this patient
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'Patient anomaly summary failed: {str(e)}', 'status': 'error'}
    
    def get_all_patients_summary(self, user_id: int = None) -> Dict[str, Any]:
        """Get anomaly summary for all patients."""
        try:
            # Get all patients anomaly analysis
            results = self.detect_anomalies(None, user_id)
            
            if 'error' in results:
                return results
            
            # Compile summary for all patients
            total_anomalies = 0
            severity_counts = {'high': 0, 'medium': 0, 'low': 0}
            patient_summaries = {}
            
            for method, data in results.items():
                if method in ['statistical_outliers', 'temporal_anomalies', 'isolation_forest']:
                    if isinstance(data, dict) and 'anomalies' in data:
                        anomalies = data['anomalies']
                        total_anomalies += len(anomalies)
                        
                        for anomaly in anomalies:
                            severity = anomaly.get('severity', 'medium')
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1
                            
                            patient = anomaly.get('patient_name', 'Unknown')
                            if patient not in patient_summaries:
                                patient_summaries[patient] = {'count': 0, 'high': 0, 'medium': 0, 'low': 0}
                            
                            patient_summaries[patient]['count'] += 1
                            patient_summaries[patient][severity] += 1
            
            # Collect all anomalies for the anomalies field
            all_anomalies = []
            for method, data in results.items():
                if method in ['statistical_outliers', 'temporal_anomalies', 'isolation_forest']:
                    if isinstance(data, dict) and 'anomalies' in data:
                        all_anomalies.extend(data['anomalies'])
            
            return {
                'total_anomalies': total_anomalies,
                'severity_breakdown': severity_counts,
                'severity_distribution': severity_counts,  # Add for backward compatibility  
                'patient_summaries': patient_summaries,
                'detailed_results': results,
                'total_patients': len(patient_summaries),
                'data_summary': {'total_patients': len(patient_summaries)},
                'recommendations': self._generate_recommendations(results, patient_summaries),
                'anomalies': all_anomalies,  # Add complete anomalies list
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'All patients summary failed: {str(e)}', 'status': 'error'}
    
    def get_anomaly_trends(self, user_id: int = None) -> Dict[str, Any]:
        """Get anomaly trends over time."""
        try:
            df = self._get_all_data(user_id)
            if df.empty:
                return {
                    'error': 'No data available for trend analysis', 
                    'status': 'no_data',
                    'trends': []
                }
            
            # Group by month and calculate anomaly counts
            df['month'] = df['test_date'].dt.to_period('M')
            monthly_trends = []
            
            for month in df['month'].unique():
                month_data = df[df['month'] == month]
                month_anomalies = 0
                
                for patient_name in month_data['patient_name'].unique():
                    patient_data = month_data[month_data['patient_name'] == patient_name]
                    for test_type in patient_data['test_type'].unique():
                        test_data = patient_data[patient_data['test_type'] == test_type]['test_value']
                        if len(test_data) >= 2:
                            Q1 = test_data.quantile(0.25)
                            Q3 = test_data.quantile(0.75)
                            IQR = Q3 - Q1
                            lower_bound = Q1 - 1.5 * IQR
                            upper_bound = Q3 + 1.5 * IQR
                            outliers = test_data[(test_data < lower_bound) | (test_data > upper_bound)]
                            month_anomalies += len(outliers)
                
                monthly_trends.append({
                    'month': str(month),
                    'anomaly_count': month_anomalies,
                    'total_tests': len(month_data)
                })
            
            return {
                'trends': monthly_trends,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'error': f'Trend analysis failed: {str(e)}', 
                'status': 'error',
                'trends': []
            }
    
    def _generate_recommendations(self, results: Dict, patient_summaries: Dict) -> List[Dict]:
        """Generate actionable recommendations based on anomaly detection results."""
        recommendations = []
        
        # General recommendations based on total anomalies
        total_anomalies = sum(len(data.get('anomalies', [])) for data in results.values() if isinstance(data, dict))
        
        if total_anomalies > 10:
            recommendations.append({
                'title': 'High Anomaly Alert',
                'description': f'Detected {total_anomalies} anomalies across all patients. Consider reviewing testing protocols and patient care plans.',
                'priority': 'high',
                'action_items': [
                    'Review testing procedures for accuracy',
                    'Identify patterns in abnormal results',
                    'Consider additional diagnostic testing',
                    'Schedule follow-up appointments for affected patients'
                ]
            })
        
        # Patient-specific recommendations
        high_risk_patients = [name for name, summary in patient_summaries.items() if summary.get('high', 0) > 0]
        
        if high_risk_patients:
            recommendations.append({
                'title': 'High-Risk Patient Monitoring',
                'description': f'Found {len(high_risk_patients)} patients with high-severity anomalies requiring immediate attention.',
                'priority': 'high',
                'action_items': [
                    'Contact high-risk patients immediately',
                    'Schedule urgent medical consultations',
                    'Review medication adjustments',
                    'Implement enhanced monitoring protocols'
                ]
            })
        
        # Test-specific recommendations
        if 'statistical_outliers' in results and results['statistical_outliers'].get('anomalies'):
            recommendations.append({
                'title': 'Statistical Outlier Review',
                'description': 'Multiple test results show statistical deviations from normal ranges.',
                'priority': 'medium',
                'action_items': [
                    'Verify laboratory calibration',
                    'Check for systematic testing errors',
                    'Review patient preparation protocols',
                    'Consider retesting abnormal values'
                ]
            })
        
        return recommendations
    
    def _generate_patient_recommendations(self, patient_name: str, results: Dict, total_anomalies: int) -> List[Dict]:
        """Generate recommendations for a specific patient."""
        recommendations = []
        
        if total_anomalies > 3:
            recommendations.append({
                'title': 'Multiple Abnormal Results',
                'description': f'Patient {patient_name} has {total_anomalies} anomalous test results requiring medical review.',
                'priority': 'high',
                'action_items': [
                    'Schedule immediate medical consultation',
                    'Review current medications and dosages',
                    'Consider comprehensive health assessment',
                    'Implement more frequent monitoring'
                ]
            })
        elif total_anomalies > 0:
            recommendations.append({
                'title': 'Monitoring Required',
                'description': f'Patient {patient_name} shows some irregular test patterns.',
                'priority': 'medium',
                'action_items': [
                    'Schedule follow-up appointment',
                    'Retest abnormal values within 2 weeks',
                    'Review lifestyle factors',
                    'Monitor trends closely'
                ]
            })
        
        return recommendations