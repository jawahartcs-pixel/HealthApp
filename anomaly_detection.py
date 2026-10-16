"Manage Data""""
AI-Powered Anomaly Detection for Blood Test Results
This module provides advanced anomaly detection capabilities using machine learning
to identify unusual patterns in patient blood test results.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.covariance import EllipticEnvelope
from scipy import stats
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class AnomalyDetector:
    def __init__(self, database):
        """Initialize anomaly detection system with database connection."""
        self.database = database
        self.scaler = StandardScaler()
        self.models = {}
        self.reference_ranges = self._load_reference_ranges()
        
    def _load_reference_ranges(self) -> Dict[str, Dict[str, float]]:
        """Load reference ranges for common blood tests."""
        return {
            'glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL'},
            'cholesterol': {'min': 100, 'max': 200, 'unit': 'mg/dL'},
            'hdl': {'min': 40, 'max': 80, 'unit': 'mg/dL'},
            'ldl': {'min': 50, 'max': 130, 'unit': 'mg/dL'},
            'triglycerides': {'min': 50, 'max': 150, 'unit': 'mg/dL'},
            'hemoglobin': {'min': 12.0, 'max': 16.0, 'unit': 'g/dL'},
            'hematocrit': {'min': 36, 'max': 46, 'unit': '%'},
            'wbc': {'min': 4000, 'max': 11000, 'unit': 'cells/μL'},
            'rbc': {'min': 4.2, 'max': 5.4, 'unit': 'million/μL'},
            'platelets': {'min': 150000, 'max': 450000, 'unit': 'cells/μL'},
            'creatinine': {'min': 0.6, 'max': 1.2, 'unit': 'mg/dL'},
            'bun': {'min': 8, 'max': 20, 'unit': 'mg/dL'},
            'alt': {'min': 7, 'max': 40, 'unit': 'U/L'},
            'ast': {'min': 10, 'max': 40, 'unit': 'U/L'},
            'tsh': {'min': 0.4, 'max': 4.0, 'unit': 'mIU/L'},
            'sodium': {'min': 135, 'max': 145, 'unit': 'mEq/L'},
            'potassium': {'min': 3.5, 'max': 5.0, 'unit': 'mEq/L'},
        }
    
    def detect_anomalies(self, patient_name: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        Detect anomalies using multiple AI algorithms.
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
            
            # Prepare data for analysis
            processed_data = self._prepare_data(test_data)
            if processed_data.empty:
                return {'error': 'Insufficient data for anomaly detection'}
            
            # Apply multiple anomaly detection algorithms
            anomalies = {
                'isolation_forest': self._isolation_forest_detection(processed_data),
                'statistical_outliers': self._statistical_outlier_detection(processed_data),
                'clustering_anomalies': self._clustering_anomaly_detection(processed_data),
                'temporal_anomalies': self._temporal_anomaly_detection(test_data),
                'correlation_anomalies': self._correlation_anomaly_detection(processed_data),
                'pattern_anomalies': self._pattern_anomaly_detection(test_data)
            }
            
            # Combine results and generate insights
            combined_results = self._combine_anomaly_results(anomalies, test_data)
            
            return combined_results
            
        except Exception as e:
            return {'error': f'Anomaly detection failed: {str(e)}'}
    
    def _get_patient_data(self, patient_name: str, user_id: int) -> pd.DataFrame:
        """Get test data for a specific patient."""
        tests = self.database.get_patient_tests(patient_name, user_id)
        if not tests:
            return pd.DataFrame()
        
        df = pd.DataFrame(tests, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['test_date'] = pd.to_datetime(df['test_date'])
        return df
    
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
        return df
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for anomaly detection algorithms."""
        try:
            # Normalize test names
            df['test_type'] = df['test_type'].str.lower().str.strip()
            
            # Create pivot table for multi-dimensional analysis
            pivot_data = df.pivot_table(
                index=['patient_name', 'test_date'], 
                columns='test_type', 
                values='test_value', 
                aggfunc='mean'
            ).reset_index()
            
            # Get only numeric columns for analysis
            numeric_columns = pivot_data.select_dtypes(include=[np.number]).columns
            
            # Ensure we have enough numeric data for analysis
            if len(numeric_columns) < 2:
                # Return simplified data structure if not enough test types
                simple_data = df[['patient_name', 'test_date', 'test_value']].copy()
                simple_data = simple_data.groupby(['patient_name', 'test_date'])['test_value'].mean().reset_index()
                return simple_data
            
            # Fill missing values with median for numeric columns only
            for col in numeric_columns:
                if pivot_data[col].isna().any():
                    median_value = pivot_data[col].median()
                    if pd.isna(median_value):
                        pivot_data[col] = pivot_data[col].fillna(0)
                    else:
                        pivot_data[col] = pivot_data[col].fillna(median_value)
            
            return pivot_data
            
        except Exception as e:
            # Fallback to simple data structure if pivoting fails
            simple_data = df[['patient_name', 'test_date', 'test_value']].copy()
            simple_data = simple_data.groupby(['patient_name', 'test_date'])['test_value'].mean().reset_index()
            return simple_data
    
    def _isolation_forest_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies using Isolation Forest algorithm."""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) < 1:
                return {'anomalies': [], 'method': 'isolation_forest', 'status': 'insufficient_data'}
            
            # Prepare data - handle both multi-column and single-column cases
            X = df[numeric_columns].values
            
            # Ensure X is 2D for sklearn
            if X.ndim == 1:
                X = X.reshape(-1, 1)
            elif X.shape[1] == 0:
                return {'anomalies': [], 'method': 'isolation_forest', 'status': 'no_numeric_data'}
                
            X_scaled = self.scaler.fit_transform(X)
            
            # Apply Isolation Forest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            anomaly_labels = iso_forest.fit_predict(X_scaled)
            anomaly_scores = iso_forest.decision_function(X_scaled)
            
            # Identify anomalies
            anomalies = []
            for i, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                if label == -1:  # Anomaly detected
                    anomalies.append({
                        'patient_name': df.iloc[i]['patient_name'],
                        'test_date': df.iloc[i]['test_date'],
                        'anomaly_score': float(score),
                        'severity': 'high' if score < -0.5 else 'medium',
                        'affected_tests': [col for col in numeric_columns if not pd.isna(df.iloc[i][col])]
                    })
            
            return {
                'anomalies': anomalies,
                'method': 'isolation_forest',
                'total_samples': len(df),
                'anomaly_count': len(anomalies),
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'isolation_forest', 'status': 'error', 'error': str(e)}
    
    def _statistical_outlier_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect statistical outliers using Z-score and IQR methods."""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            anomalies = []
            
            for col in numeric_columns:
                values = df[col].dropna()
                if len(values) < 5:
                    continue
                
                # Z-score method
                z_scores = np.abs(stats.zscore(values))
                z_outliers = values[z_scores > 3]
                
                # IQR method
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outliers = values[(values < lower_bound) | (values > upper_bound)]
                
                # Combine outliers
                outlier_indices = set(z_outliers.index) | set(iqr_outliers.index)
                
                for idx in outlier_indices:
                    anomalies.append({
                        'patient_name': df.iloc[idx]['patient_name'],
                        'test_date': df.iloc[idx]['test_date'],
                        'test_type': col,
                        'value': float(df.iloc[idx][col]),
                        'z_score': float(z_scores[idx]) if idx in z_scores.index else None,
                        'severity': 'high' if z_scores[idx] > 4 else 'medium',
                        'method': 'statistical_outlier'
                    })
            
            return {
                'anomalies': anomalies,
                'method': 'statistical_outliers',
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'statistical_outliers', 'status': 'error', 'error': str(e)}
    
    def _clustering_anomaly_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies using DBSCAN clustering."""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) < 1:
                return {'anomalies': [], 'method': 'clustering', 'status': 'insufficient_data'}
            
            X = df[numeric_columns].values
            
            # Ensure X is 2D for sklearn
            if X.ndim == 1:
                X = X.reshape(-1, 1)
            elif X.shape[1] == 0:
                return {'anomalies': [], 'method': 'clustering', 'status': 'no_numeric_data'}
            X_scaled = self.scaler.fit_transform(X)
            
            # Apply DBSCAN
            dbscan = DBSCAN(eps=0.5, min_samples=3)
            cluster_labels = dbscan.fit_predict(X_scaled)
            
            # Identify anomalies (noise points)
            anomalies = []
            for i, label in enumerate(cluster_labels):
                if label == -1:  # Noise point (anomaly)
                    anomalies.append({
                        'patient_name': df.iloc[i]['patient_name'],
                        'test_date': df.iloc[i]['test_date'],
                        'cluster_label': int(label),
                        'severity': 'medium',
                        'method': 'clustering'
                    })
            
            return {
                'anomalies': anomalies,
                'method': 'clustering',
                'total_clusters': len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0),
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'clustering', 'status': 'error', 'error': str(e)}
    
    def _temporal_anomaly_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect temporal anomalies in test trends."""
        try:
            anomalies = []
            
            for patient in df['patient_name'].unique():
                patient_data = df[df['patient_name'] == patient].copy()
                
                for test_type in patient_data['test_type'].unique():
                    test_data = patient_data[patient_data['test_type'] == test_type].copy()
                    if len(test_data) < 3:
                        continue
                    
                    test_data = test_data.sort_values('test_date')
                    values = test_data['test_value'].values
                    
                    # Detect sudden changes
                    changes = np.diff(values)
                    mean_change = np.mean(np.abs(changes))
                    std_change = np.std(changes)
                    
                    for i, change in enumerate(changes):
                        if abs(change) > mean_change + 3 * std_change:
                            anomalies.append({
                                'patient_name': patient,
                                'test_date': test_data.iloc[i+1]['test_date'],
                                'test_type': test_type,
                                'value': float(values[i+1]),
                                'previous_value': float(values[i]),
                                'change': float(change),
                                'severity': 'high' if abs(change) > mean_change + 4 * std_change else 'medium',
                                'method': 'temporal_anomaly'
                            })
            
            return {
                'anomalies': anomalies,
                'method': 'temporal_anomalies',
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'temporal_anomalies', 'status': 'error', 'error': str(e)}
    
    def _correlation_anomaly_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies based on correlation patterns."""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) < 3:
                return {'anomalies': [], 'method': 'correlation', 'status': 'insufficient_data'}
            
            # Calculate correlation matrix
            corr_matrix = df[numeric_columns].corr()
            
            # Use Elliptic Envelope for correlation-based anomaly detection
            X = df[numeric_columns].values
            X_scaled = self.scaler.fit_transform(X)
            
            envelope = EllipticEnvelope(contamination=0.1, random_state=42)
            anomaly_labels = envelope.fit_predict(X_scaled)
            
            anomalies = []
            for i, label in enumerate(anomaly_labels):
                if label == -1:
                    anomalies.append({
                        'patient_name': df.iloc[i]['patient_name'],
                        'test_date': df.iloc[i]['test_date'],
                        'severity': 'medium',
                        'method': 'correlation_anomaly',
                        'correlation_based': True
                    })
            
            return {
                'anomalies': anomalies,
                'method': 'correlation_anomalies',
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'correlation_anomalies', 'status': 'error', 'error': str(e)}
    
    def _pattern_anomaly_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect pattern-based anomalies using medical knowledge."""
        try:
            anomalies = []
            
            # Group by patient and analyze patterns
            for patient in df['patient_name'].unique():
                patient_data = df[df['patient_name'] == patient].copy()
                latest_tests = patient_data.sort_values('test_date').groupby('test_type').last()
                
                # Check for concerning patterns
                patterns = self._analyze_medical_patterns(latest_tests)
                
                for pattern in patterns:
                    anomalies.append({
                        'patient_name': patient,
                        'test_date': pattern.get('test_date'),
                        'pattern_type': pattern['type'],
                        'description': pattern['description'],
                        'severity': pattern['severity'],
                        'method': 'pattern_anomaly',
                        'tests_involved': pattern['tests_involved']
                    })
            
            return {
                'anomalies': anomalies,
                'method': 'pattern_anomalies',
                'status': 'success'
            }
            
        except Exception as e:
            return {'anomalies': [], 'method': 'pattern_anomalies', 'status': 'error', 'error': str(e)}
    
    def _analyze_medical_patterns(self, tests: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze medical patterns in test results."""
        patterns = []
        
        try:
            # Convert test types to lowercase for matching
            test_dict = {}
            for idx, row in tests.iterrows():
                test_key = idx.lower().strip()
                test_dict[test_key] = row['test_value']
            
            # Pattern 1: Diabetes risk
            if 'glucose' in test_dict and test_dict['glucose'] > 125:
                patterns.append({
                    'type': 'diabetes_risk',
                    'description': 'Elevated glucose levels may indicate diabetes risk',
                    'severity': 'high',
                    'test_date': tests.loc['glucose', 'test_date'] if 'glucose' in tests.index else None,
                    'tests_involved': ['glucose']
                })
            
            # Pattern 2: Cardiovascular risk
            if 'cholesterol' in test_dict and 'hdl' in test_dict:
                total_chol = test_dict['cholesterol']
                hdl = test_dict['hdl']
                if total_chol > 240 or hdl < 40:
                    patterns.append({
                        'type': 'cardiovascular_risk',
                        'description': 'Lipid profile suggests cardiovascular risk',
                        'severity': 'medium',
                        'test_date': tests.loc['cholesterol', 'test_date'] if 'cholesterol' in tests.index else None,
                        'tests_involved': ['cholesterol', 'hdl']
                    })
            
            # Pattern 3: Kidney function
            if 'creatinine' in test_dict and 'bun' in test_dict:
                creatinine = test_dict['creatinine']
                bun = test_dict['bun']
                if creatinine > 1.5 or bun > 25:
                    patterns.append({
                        'type': 'kidney_function',
                        'description': 'Kidney function markers are elevated',
                        'severity': 'high',
                        'test_date': tests.loc['creatinine', 'test_date'] if 'creatinine' in tests.index else None,
                        'tests_involved': ['creatinine', 'bun']
                    })
            
            # Pattern 4: Anemia
            if 'hemoglobin' in test_dict and 'hematocrit' in test_dict:
                hb = test_dict['hemoglobin']
                hct = test_dict['hematocrit']
                if hb < 12 or hct < 36:
                    patterns.append({
                        'type': 'anemia',
                        'description': 'Low hemoglobin/hematocrit suggests anemia',
                        'severity': 'medium',
                        'test_date': tests.loc['hemoglobin', 'test_date'] if 'hemoglobin' in tests.index else None,
                        'tests_involved': ['hemoglobin', 'hematocrit']
                    })
            
            # Pattern 5: Liver function
            if 'alt' in test_dict and 'ast' in test_dict:
                alt = test_dict['alt']
                ast = test_dict['ast']
                if alt > 60 or ast > 60:
                    patterns.append({
                        'type': 'liver_function',
                        'description': 'Liver enzymes are elevated',
                        'severity': 'high',
                        'test_date': tests.loc['alt', 'test_date'] if 'alt' in tests.index else None,
                        'tests_involved': ['alt', 'ast']
                    })
            
        except Exception as e:
            # If there's an error, return empty patterns rather than failing
            pass
        
        return patterns
    
    def _combine_anomaly_results(self, anomalies: Dict[str, Any], original_data: pd.DataFrame) -> Dict[str, Any]:
        """Combine results from multiple anomaly detection methods."""
        combined_anomalies = []
        anomaly_summary = {}
        
        # Collect all anomalies
        for method, results in anomalies.items():
            if results.get('status') == 'success' and results.get('anomalies'):
                for anomaly in results['anomalies']:
                    anomaly['detection_method'] = method
                    combined_anomalies.append(anomaly)
        
        # Group by patient for summary
        patient_anomalies = {}
        for anomaly in combined_anomalies:
            patient = anomaly['patient_name']
            if patient not in patient_anomalies:
                patient_anomalies[patient] = []
            patient_anomalies[patient].append(anomaly)
        
        # Generate severity counts
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        for anomaly in combined_anomalies:
            severity = anomaly.get('severity', 'medium')
            severity_counts[severity] += 1
        
        # Generate recommendations
        recommendations = self._generate_recommendations(combined_anomalies)
        
        return {
            'total_anomalies': len(combined_anomalies),
            'anomalies': combined_anomalies,
            'patient_anomalies': patient_anomalies,
            'severity_distribution': severity_counts,
            'recommendations': recommendations,
            'detection_methods_used': list(anomalies.keys()),
            'analysis_timestamp': datetime.now().isoformat(),
            'data_summary': {
                'total_patients': len(original_data['patient_name'].unique()),
                'total_tests': len(original_data),
                'date_range': {
                    'start': original_data['test_date'].min().isoformat(),
                    'end': original_data['test_date'].max().isoformat()
                }
            }
        }
    
    def _generate_recommendations(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on detected anomalies."""
        recommendations = []
        
        # Count anomalies by type
        anomaly_types = {}
        for anomaly in anomalies:
            method = anomaly.get('detection_method', 'unknown')
            pattern_type = anomaly.get('pattern_type', method)
            
            if pattern_type not in anomaly_types:
                anomaly_types[pattern_type] = 0
            anomaly_types[pattern_type] += 1
        
        # Generate recommendations based on patterns
        for anomaly_type, count in anomaly_types.items():
            if anomaly_type == 'diabetes_risk':
                recommendations.append({
                    'type': 'medical_followup',
                    'priority': 'high',
                    'title': 'Diabetes Risk Assessment',
                    'description': f'Found {count} instance(s) of elevated glucose levels. Consider HbA1c testing and diabetes screening.',
                    'action_items': [
                        'Schedule follow-up glucose test',
                        'Consider HbA1c test',
                        'Discuss lifestyle modifications'
                    ]
                })
            
            elif anomaly_type == 'cardiovascular_risk':
                recommendations.append({
                    'type': 'medical_followup',
                    'priority': 'medium',
                    'title': 'Cardiovascular Risk Assessment',
                    'description': f'Found {count} instance(s) of abnormal lipid profiles. Consider cardiovascular risk assessment.',
                    'action_items': [
                        'Repeat lipid panel',
                        'Consider cardiovascular risk calculation',
                        'Discuss diet and exercise'
                    ]
                })
            
            elif anomaly_type == 'kidney_function':
                recommendations.append({
                    'type': 'medical_followup',
                    'priority': 'high',
                    'title': 'Kidney Function Evaluation',
                    'description': f'Found {count} instance(s) of elevated kidney markers. Requires immediate attention.',
                    'action_items': [
                        'Repeat kidney function tests',
                        'Check for medication interactions',
                        'Consider nephrology referral'
                    ]
                })
            
            elif anomaly_type == 'statistical_outliers':
                recommendations.append({
                    'type': 'data_quality',
                    'priority': 'medium',
                    'title': 'Statistical Outliers Detected',
                    'description': f'Found {count} statistical outlier(s). Verify test accuracy and consider retesting.',
                    'action_items': [
                        'Verify test results accuracy',
                        'Consider repeat testing',
                        'Check for external factors'
                    ]
                })
        
        return recommendations
    
    def get_patient_anomaly_summary(self, patient_name: str, user_id: int = None) -> Dict[str, Any]:
        """Get anomaly summary for a specific patient."""
        result = self.detect_anomalies(patient_name, user_id)
        
        if 'error' in result:
            return result
        
        patient_anomalies = result.get('patient_anomalies', {}).get(patient_name, [])
        
        return {
            'patient_name': patient_name,
            'total_anomalies': len(patient_anomalies),
            'anomalies': patient_anomalies,
            'severity_distribution': self._calculate_severity_distribution(patient_anomalies),
            'recommendations': [rec for rec in result.get('recommendations', []) 
                             if any(ano['patient_name'] == patient_name for ano in patient_anomalies)]
        }
    
    def _calculate_severity_distribution(self, anomalies: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate severity distribution for anomalies."""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        for anomaly in anomalies:
            severity = anomaly.get('severity', 'medium')
            distribution[severity] += 1
        return distribution
    
    def get_anomaly_trends(self, user_id: int = None, days: int = 30) -> Dict[str, Any]:
        """Get anomaly trends over time."""
        try:
            # Get recent test data
            cutoff_date = datetime.now() - timedelta(days=days)
            
            all_tests = self.database.get_all_test_results()
            if user_id:
                all_tests = [test for test in all_tests if len(test) > 6 and test[6] == user_id]
            
            if not all_tests:
                return {'error': 'No test data available'}
            
            df = pd.DataFrame(all_tests, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range', 'user_id'])
            df['test_date'] = pd.to_datetime(df['test_date'])
            df = df[df['test_date'] >= cutoff_date]
            
            if df.empty:
                return {'error': f'No test data available for the last {days} days'}
            
            # Group by week and analyze trends
            df['week'] = df['test_date'].dt.isocalendar().week
            weekly_anomalies = []
            
            for week in df['week'].unique():
                week_data = df[df['week'] == week]
                processed_data = self._prepare_data(week_data)
                
                if not processed_data.empty:
                    iso_result = self._isolation_forest_detection(processed_data)
                    weekly_anomalies.append({
                        'week': int(week),
                        'anomaly_count': len(iso_result.get('anomalies', [])),
                        'test_count': len(week_data)
                    })
            
            return {
                'trend_data': weekly_anomalies,
                'period_days': days,
                'total_tests': len(df),
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'Trend analysis failed: {str(e)}'}