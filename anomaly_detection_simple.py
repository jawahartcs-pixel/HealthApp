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
        
        df = pd.DataFrame(tests, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['test_date'] = pd.to_datetime(df['test_date'])
        df['test_value'] = pd.to_numeric(df['test_value'], errors='coerce')
        return df.dropna(subset=['test_value'])
    
    def _get_all_data(self, user_id: int) -> pd.DataFrame:
        """Get all test data for anomaly detection."""
        tests = self.database.get_all_test_results()
        if not tests:
            return pd.DataFrame()
        
        # Filter by user_id if provided
        if user_id:
            tests = [test for test in tests if len(test) > 6 and test[6] == user_id]
        
        if not tests:
            return pd.DataFrame()
        
        df = pd.DataFrame(tests, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range', 'user_id'])
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