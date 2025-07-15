import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import streamlit as st
from database import Database

class Visualization:
    def __init__(self, database: Database):
        """Initialize visualization component with database connection."""
        self.db = database
        
        # Define color scheme for different test types
        self.color_scheme = {
            'Glucose': '#FF6B6B',
            'Fasting Glucose': '#FF8E8E',
            'Random Glucose': '#FFB1B1',
            'HbA1c': '#4ECDC4',
            'Total Cholesterol': '#45B7D1',
            'HDL Cholesterol': '#96CEB4',
            'LDL Cholesterol': '#FFEAA7',
            'Triglycerides': '#DDA0DD',
            'Hemoglobin': '#98D8C8',
            'Hematocrit': '#F7DC6F',
            'WBC Count': '#BB8FCE',
            'RBC Count': '#85C1E9',
            'Platelet Count': '#F8C471',
            'ALT': '#82E0AA',
            'AST': '#F9E79F',
            'Creatinine': '#D7BDE2',
            'BUN': '#A9DFBF',
            'TSH': '#F5B7B1',
            'Sodium': '#AED6F1',
            'Potassium': '#A9CCE3'
        }
    
    def create_trend_chart(self, test_data: pd.DataFrame, test_type: str, patient_name: str) -> go.Figure:
        """Create a trend chart for a specific test type and patient."""
        try:
            # Filter data for the specific test type
            filtered_data = test_data[test_data['Test Type'] == test_type].copy()
            
            if filtered_data.empty:
                # Return empty chart with message
                fig = go.Figure()
                fig.add_annotation(
                    text=f"No data available for {test_type}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font_size=16
                )
                fig.update_layout(title=f"{test_type} Trend for {patient_name}")
                return fig
            
            # Sort by date
            filtered_data = filtered_data.sort_values('Date')
            
            # Get color for this test type
            color = self.color_scheme.get(test_type, '#3366CC')
            
            # Create the main trend line
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=filtered_data['Date'],
                y=filtered_data['Value'],
                mode='lines+markers',
                name=test_type,
                line=dict(color=color, width=3),
                marker=dict(size=8, color=color),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Date: %{x}<br>' +
                              'Value: %{y}<br>' +
                              '<extra></extra>'
            ))
            
            # Add reference range if available
            if not filtered_data['Reference Range'].isna().all():
                ref_range = filtered_data['Reference Range'].iloc[0]
                if ref_range and ref_range != '':
                    self._add_reference_range(fig, ref_range, filtered_data['Date'].min(), filtered_data['Date'].max())
            
            # Calculate trend line
            if len(filtered_data) >= 2:
                self._add_trend_line(fig, filtered_data, color)
            
            # Update layout
            unit = filtered_data['Unit'].iloc[0] if not filtered_data['Unit'].isna().all() else ''
            
            fig.update_layout(
                title=f"{test_type} Trend for {patient_name}",
                xaxis_title="Date",
                yaxis_title=f"{test_type} ({unit})" if unit else test_type,
                hovermode='x unified',
                showlegend=True,
                template='plotly_white',
                height=400
            )
            
            # Add annotations for latest value and trend
            self._add_trend_annotations(fig, filtered_data, test_type)
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating trend chart: {str(e)}")
            return go.Figure()
    
    def create_multi_patient_chart(self, test_data: pd.DataFrame, test_type: str) -> go.Figure:
        """Create a chart comparing multiple patients for a specific test type."""
        try:
            # Filter data for the specific test type
            filtered_data = test_data[test_data['Test Type'] == test_type].copy()
            
            if filtered_data.empty:
                fig = go.Figure()
                fig.add_annotation(
                    text=f"No data available for {test_type}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font_size=16
                )
                fig.update_layout(title=f"{test_type} Comparison Across Patients")
                return fig
            
            # Sort by date
            filtered_data = filtered_data.sort_values('Date')
            
            # Create line chart with different line for each patient
            fig = px.line(
                filtered_data,
                x='Date',
                y='Value',
                color='Patient Name',
                title=f"{test_type} Comparison Across Patients",
                markers=True
            )
            
            # Update traces for better styling
            for trace in fig.data:
                trace.line.width = 3
                trace.marker.size = 8
            
            # Add reference range if available
            if not filtered_data['Reference Range'].isna().all():
                ref_range = filtered_data['Reference Range'].iloc[0]
                if ref_range and ref_range != '':
                    self._add_reference_range(fig, ref_range, filtered_data['Date'].min(), filtered_data['Date'].max())
            
            # Update layout
            unit = filtered_data['Unit'].iloc[0] if not filtered_data['Unit'].isna().all() else ''
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title=f"{test_type} ({unit})" if unit else test_type,
                hovermode='x unified',
                template='plotly_white',
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating multi-patient chart: {str(e)}")
            return go.Figure()
    
    def create_patient_overview_dashboard(self, patient_name: str) -> Dict[str, go.Figure]:
        """Create a dashboard with multiple charts for a patient."""
        try:
            # Get patient data
            patient_tests = self.db.get_patient_tests(patient_name)
            
            if not patient_tests:
                return {}
            
            # Convert to DataFrame
            df = pd.DataFrame(patient_tests, columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
            df['Date'] = pd.to_datetime(df['Date'])
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            
            # Get unique test types
            test_types = df['Test Type'].unique()
            
            charts = {}
            
            # Create individual charts for each test type
            for test_type in test_types:
                charts[test_type] = self.create_trend_chart(df, test_type, patient_name)
            
            # Create summary chart with latest values
            charts['summary'] = self._create_latest_values_chart(df, patient_name)
            
            return charts
            
        except Exception as e:
            st.error(f"Error creating patient dashboard: {str(e)}")
            return {}
    
    def create_test_distribution_chart(self, test_type: str) -> go.Figure:
        """Create a distribution chart for a specific test type across all patients."""
        try:
            # Get all results for this test type
            results = self.db.search_test_results(test_types=[test_type])
            
            if not results:
                fig = go.Figure()
                fig.add_annotation(
                    text=f"No data available for {test_type}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font_size=16
                )
                fig.update_layout(title=f"{test_type} Distribution")
                return fig
            
            # Convert to DataFrame
            df = pd.DataFrame(results, columns=['Patient Name', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            
            # Create histogram
            fig = px.histogram(
                df,
                x='Value',
                nbins=20,
                title=f"{test_type} Distribution Across All Patients",
                labels={'Value': f"{test_type} Value", 'count': 'Frequency'}
            )
            
            # Add vertical lines for reference range if available
            if not df['Reference Range'].isna().all():
                ref_range = df['Reference Range'].iloc[0]
                if ref_range and ref_range != '':
                    self._add_reference_lines_to_histogram(fig, ref_range)
            
            # Update layout
            unit = df['Unit'].iloc[0] if not df['Unit'].isna().all() else ''
            fig.update_layout(
                xaxis_title=f"{test_type} ({unit})" if unit else test_type,
                yaxis_title="Number of Tests",
                template='plotly_white',
                height=400
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating distribution chart: {str(e)}")
            return go.Figure()
    
    def _add_reference_range(self, fig: go.Figure, ref_range: str, start_date: str, end_date: str):
        """Add reference range as shaded area to the chart."""
        try:
            # Parse reference range (e.g., "70-100 mg/dL" or "<200 mg/dL")
            import re
            
            # Extract numeric values from reference range
            numbers = re.findall(r'\d+(?:\.\d+)?', ref_range)
            
            if len(numbers) >= 2:
                # Range format (e.g., "70-100")
                min_val = float(numbers[0])
                max_val = float(numbers[1])
                
                fig.add_hrect(
                    y0=min_val, y1=max_val,
                    fillcolor="lightgreen", opacity=0.2,
                    layer="below", line_width=0,
                    annotation_text="Normal Range",
                    annotation_position="top left"
                )
            elif len(numbers) == 1 and ('<' in ref_range or '>' in ref_range):
                # Single boundary format (e.g., "<200" or ">40")
                value = float(numbers[0])
                if '<' in ref_range:
                    fig.add_hline(
                        y=value, line_dash="dash", line_color="orange",
                        annotation_text=f"Upper limit: {value}"
                    )
                elif '>' in ref_range:
                    fig.add_hline(
                        y=value, line_dash="dash", line_color="orange",
                        annotation_text=f"Lower limit: {value}"
                    )
        except:
            # If parsing fails, skip adding reference range
            pass
    
    def _add_trend_line(self, fig: go.Figure, data: pd.DataFrame, color: str):
        """Add trend line to the chart."""
        try:
            from datetime import datetime
            import numpy as np
            
            # Convert dates to numeric values for trend calculation
            dates_numeric = [(date - data['Date'].min()).days for date in data['Date']]
            values = data['Value'].values
            
            # Calculate linear trend
            z = np.polyfit(dates_numeric, values, 1)
            trend_values = np.poly1d(z)(dates_numeric)
            
            # Add trend line
            fig.add_trace(go.Scatter(
                x=data['Date'],
                y=trend_values,
                mode='lines',
                name='Trend',
                line=dict(color=color, width=2, dash='dash'),
                opacity=0.7,
                hovertemplate='Trend line<extra></extra>'
            ))
        except:
            # If trend calculation fails, skip
            pass
    
    def _add_trend_annotations(self, fig: go.Figure, data: pd.DataFrame, test_type: str):
        """Add annotations showing latest value and trend information."""
        try:
            if len(data) < 2:
                return
            
            latest_value = data['Value'].iloc[-1]
            previous_value = data['Value'].iloc[-2]
            change = latest_value - previous_value
            percent_change = (change / previous_value * 100) if previous_value != 0 else 0
            
            # Determine trend direction
            if change > 0:
                arrow = "↗"
                color = "red"
            elif change < 0:
                arrow = "↘"
                color = "green"
            else:
                arrow = "→"
                color = "gray"
            
            # Add annotation
            fig.add_annotation(
                x=data['Date'].iloc[-1],
                y=latest_value,
                text=f"{arrow} {change:.1f} ({percent_change:.1f}%)",
                showarrow=True,
                arrowhead=2,
                arrowcolor=color,
                font=dict(color=color, size=12),
                bgcolor="white",
                bordercolor=color,
                borderwidth=1
            )
        except:
            pass
    
    def _create_latest_values_chart(self, df: pd.DataFrame, patient_name: str) -> go.Figure:
        """Create a chart showing the latest values for all test types."""
        try:
            # Get latest value for each test type
            latest_values = df.groupby('Test Type').apply(
                lambda x: x.loc[x['Date'].idxmax()]
            ).reset_index(drop=True)
            
            # Create bar chart
            fig = px.bar(
                latest_values,
                x='Test Type',
                y='Value',
                title=f"Latest Test Results for {patient_name}",
                color='Test Type',
                color_discrete_map=self.color_scheme
            )
            
            # Update layout
            fig.update_layout(
                xaxis_title="Test Type",
                yaxis_title="Value",
                template='plotly_white',
                height=400,
                showlegend=False,
                xaxis_tickangle=-45
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating latest values chart: {str(e)}")
            return go.Figure()
    
    def _add_reference_lines_to_histogram(self, fig: go.Figure, ref_range: str):
        """Add reference range lines to histogram."""
        try:
            import re
            
            # Extract numeric values from reference range
            numbers = re.findall(r'\d+(?:\.\d+)?', ref_range)
            
            if len(numbers) >= 2:
                # Range format (e.g., "70-100")
                min_val = float(numbers[0])
                max_val = float(numbers[1])
                
                fig.add_vline(
                    x=min_val, line_dash="dash", line_color="green",
                    annotation_text="Normal Min"
                )
                fig.add_vline(
                    x=max_val, line_dash="dash", line_color="green",
                    annotation_text="Normal Max"
                )
        except:
            pass
