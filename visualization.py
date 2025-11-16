import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
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
    
    def add_event_lines(self, fig: go.Figure, events: List[Dict], x_range: tuple = None):
        """Add vertical lines for patient events to a chart.
        
        Args:
            fig: Plotly figure to add event lines to
            events: List of event dictionaries with 'event_date' and 'event_name'
            x_range: Optional tuple of (min_date, max_date) to filter visible events
        """
        if not events:
            return
        
        for event in events:
            event_date = pd.to_datetime(event['event_date'])
            
            # If x_range is provided, only show events within the visible range
            if x_range:
                # Convert both to pandas Timestamp for compatible comparison
                min_date = pd.Timestamp(x_range[0])
                max_date = pd.Timestamp(x_range[1])
                # Use timestamp comparison to avoid deprecated integer arithmetic
                if event_date < min_date or event_date > max_date:
                    continue
            
            # Add vertical line for the event
            fig.add_vline(
                x=event_date,
                line_dash="dash",
                line_color="rgba(255, 0, 0, 0.5)",
                line_width=2,
                annotation_text=event['event_name'],
                annotation_position="top",
                annotation=dict(
                    font=dict(size=10, color="red"),
                    textangle=-90,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="red",
                    borderwidth=1
                )
            )
    
    def create_trend_chart(self, test_data: pd.DataFrame, test_type: str, patient_name: str, 
                          patient_gender: Optional[str] = None, events: List[Dict] = None) -> go.Figure:
        """Create a trend chart for a specific test type and patient.
        
        Args:
            test_data: DataFrame with test results
            test_type: Type of test to display
            patient_name: Name of the patient
            patient_gender: Gender of the patient for reference ranges
            events: List of patient events to display as vertical lines
        """
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
                fig.update_layout(title=f"{test_type} Trend for {patient_name or 'Unknown'}")
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
                mode='markers+lines',
                name=test_type,
                line=dict(color=color, width=2, dash='solid'),
                marker=dict(
                    size=10, 
                    color=color,
                    symbol='circle',
                    line=dict(width=2, color='white')
                ),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Date: %{x|%Y-%m-%d}<br>' +
                              'Value: %{y}<br>' +
                              'Unit: ' + (str(filtered_data['Unit'].iloc[0]) if not filtered_data['Unit'].isna().all() and filtered_data['Unit'].iloc[0] is not None else '') + '<br>' +
                              '<extra></extra>'
            ))
            
            # Add reference range if available
            if not filtered_data['Reference Range'].isna().all():
                ref_range = filtered_data['Reference Range'].iloc[0]
                if ref_range and ref_range != '':
                    self._add_reference_range(fig, ref_range, filtered_data['Date'].min(), 
                                           filtered_data['Date'].max(), test_type, patient_gender)
            
            # Remove trend line to show all individual data points clearly
            # Focus on actual data points rather than averaged trend
            
            # Update layout with proper date handling
            unit = filtered_data['Unit'].iloc[0] if not filtered_data['Unit'].isna().all() else ''
            
            fig.update_layout(
                title=dict(
                    text=f"<b>{test_type}</b> - {patient_name or 'Unknown'}",
                    font=dict(size=14),
                    x=0.5,
                    xanchor='center'
                ),
                xaxis_title="Date",
                yaxis_title=f"Value ({unit})" if unit else "Value",
                hovermode='x unified',
                showlegend=False,
                template='plotly_white',
                height=280,
                margin=dict(l=50, r=50, t=50, b=50),
                xaxis=dict(
                    type='date',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='#E8E8E8',
                    tickformat='%m/%d',
                    tickfont=dict(size=10),
                    autorange=True,
                    range=[filtered_data['Date'].min(), filtered_data['Date'].max()]
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='#E8E8E8',
                    zeroline=False,
                    tickfont=dict(size=10)
                )
            )
            
            # Add value annotations for ALL data points
            for i, row in filtered_data.iterrows():
                fig.add_annotation(
                    x=row['Date'],
                    y=row['Value'],
                    text=f"{row['Value']:.1f}",
                    showarrow=False,
                    yshift=15,
                    font=dict(size=9, color=color),
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor=color,
                    borderwidth=1
                )
            
            # Add patient events as vertical lines
            if events:
                self.add_event_lines(fig, events, (filtered_data['Date'].min(), filtered_data['Date'].max()))
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating trend chart: {str(e)}")
            return go.Figure()
    
    def create_3d_trend_chart(self, test_data: pd.DataFrame, test_type: str, patient_name: str) -> go.Figure:
        """Create a 3D trend chart for a specific test type and patient."""
        try:
            # Filter data for the specific test type
            filtered_data = test_data[test_data['Test Type'] == test_type].copy()
            
            if filtered_data.empty:
                return go.Figure().add_annotation(
                    text=f"No data available for {test_type}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font=dict(size=16)
                )
            
            # Sort by date
            filtered_data = filtered_data.sort_values('Date')
            
            # Create 3D coordinates
            dates = pd.to_datetime(filtered_data['Date'])
            values = filtered_data['Value']
            
            # Create Z-axis based on index (time progression)
            z_coords = np.arange(len(dates))
            
            # Add some 3D depth by creating multiple layers
            x_coords = np.arange(len(dates))
            y_coords = values
            
            # Get color for this test type
            color = self.color_scheme.get(test_type, '#636EFA')
            
            # Create 3D scatter plot
            fig = go.Figure()
            
            # Main 3D line
            fig.add_trace(go.Scatter3d(
                x=x_coords,
                y=y_coords,
                z=z_coords,
                mode='lines+markers',
                line=dict(color=color, width=6),
                marker=dict(
                    size=8,
                    color=values,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Test Value")
                ),
                name=test_type,
                text=[f"Date: {date.strftime('%Y-%m-%d')}<br>Value: {val}" 
                      for date, val in zip(dates, values)],
                hovertemplate="<b>%{text}</b><extra></extra>"
            ))
            
            # Add surface for better 3D effect
            if len(filtered_data) > 2:
                # Create a mesh surface
                x_mesh = np.array([x_coords, x_coords])
                y_mesh = np.array([y_coords, y_coords])
                z_mesh = np.array([z_coords - 0.5, z_coords + 0.5])
                
                fig.add_trace(go.Surface(
                    x=x_mesh,
                    y=y_mesh, 
                    z=z_mesh,
                    opacity=0.3,
                    colorscale='Blues',
                    showscale=False,
                    name="Trend Surface"
                ))
            
            # Update layout for 3D
            fig.update_layout(
                title=f"3D Trend Analysis: {test_type} for {patient_name}",
                scene=dict(
                    xaxis_title="Time Index",
                    yaxis_title=f"{test_type} Value",
                    zaxis_title="Chronological Order",
                    camera=dict(
                        eye=dict(x=1.2, y=1.2, z=1.2)
                    ),
                    bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="lightgray"),
                    yaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="lightgray"),
                    zaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="lightgray")
                ),
                height=500,
                margin=dict(l=0, r=0, t=50, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating 3D trend chart: {str(e)}")
            return go.Figure()
    
    def create_3d_multi_test_chart(self, test_data: pd.DataFrame, patient_name: str, test_types: List[str]) -> go.Figure:
        """Create a 3D chart showing multiple test types for comparison."""
        try:
            fig = go.Figure()
            
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
            
            for i, test_type in enumerate(test_types[:6]):  # Limit to 6 test types
                filtered_data = test_data[test_data['Test Type'] == test_type].copy()
                
                if filtered_data.empty:
                    continue
                
                filtered_data = filtered_data.sort_values('Date')
                dates = pd.to_datetime(filtered_data['Date'])
                values = filtered_data['Value']
                
                # Normalize values for better 3D visualization
                normalized_values = (values - values.min()) / (values.max() - values.min()) if values.max() != values.min() else values
                
                x_coords = np.arange(len(dates))
                y_coords = normalized_values
                z_coords = np.full(len(dates), i)  # Different z-level for each test type
                
                fig.add_trace(go.Scatter3d(
                    x=x_coords,
                    y=y_coords,
                    z=z_coords,
                    mode='lines+markers',
                    line=dict(color=colors[i % len(colors)], width=4),
                    marker=dict(size=6, color=colors[i % len(colors)]),
                    name=test_type,
                    text=[f"Date: {date.strftime('%Y-%m-%d')}<br>Value: {val}" 
                          for date, val in zip(dates, values)],
                    hovertemplate="<b>%{fullData.name}</b><br>%{text}<extra></extra>"
                ))
            
            fig.update_layout(
                title=f"3D Multi-Test Comparison for {patient_name}",
                scene=dict(
                    xaxis_title="Time Index",
                    yaxis_title="Normalized Values",
                    zaxis_title="Test Types",
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=1.5)
                    ),
                    bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="lightgray"),
                    yaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="lightgray"),
                    zaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="lightgray")
                ),
                height=600,
                margin=dict(l=0, r=0, t=50, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating 3D multi-test chart: {str(e)}")
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
                    self._add_reference_range(fig, ref_range, filtered_data['Date'].min(), 
                                           filtered_data['Date'].max(), test_type, patient_gender)
            
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
    
    def _add_reference_range(self, fig: go.Figure, ref_range: str, start_date: str, end_date: str, 
                           test_type: Optional[str] = None, patient_gender: Optional[str] = None):
        """Add reference range as shaded area to the chart, with gender-specific support."""
        try:
            # First try to get gender-specific reference range from standards
            if test_type and patient_gender:
                gender_range = self._get_gender_specific_range(test_type, patient_gender)
                if gender_range:
                    ref_range = gender_range
            
            # Parse reference range (e.g., "70-100 mg/dL" or "<200 mg/dL")
            import re
            
            # Extract numeric values from reference range
            numbers = re.findall(r'\d+(?:\.\d+)?', ref_range)
            
            if len(numbers) >= 2:
                # Range format (e.g., "70-100")
                min_val = float(numbers[0])
                max_val = float(numbers[1])
                
                # Use gender-specific color coding
                color = "lightblue" if patient_gender == "Female" else "lightgreen" if patient_gender == "Male" else "lightgray"
                annotation = f"Normal Range ({patient_gender})" if patient_gender else "Normal Range"
                
                fig.add_hrect(
                    y0=min_val, y1=max_val,
                    fillcolor=color, opacity=0.2,
                    layer="below", line_width=0,
                    annotation_text=annotation,
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
    
    def _get_gender_specific_range(self, test_type: str, gender: str) -> Optional[str]:
        """Get gender-specific reference range from investigation standards."""
        try:
            # Get investigation standards
            standards = self.db.get_investigation_standards()
            
            if not standards:
                return None
            
            # Convert to DataFrame for easier searching
            standards_df = pd.DataFrame(standards)
            
            # Find matching test standard (case-insensitive)
            match = standards_df[standards_df['standard_name'].str.lower() == test_type.lower()]
            
            if match.empty:
                # Try with aliases if available
                for _, row in standards_df.iterrows():
                    aliases = row.get('aliases', '').split(',') if row.get('aliases') else []
                    if any(alias.strip().lower() == test_type.lower() for alias in aliases):
                        match = pd.DataFrame([row])
                        break
            
            if not match.empty:
                standard = match.iloc[0]
                
                # Get gender-specific range
                if gender.lower() == 'male':
                    min_val = standard.get('male_range_min')
                    max_val = standard.get('male_range_max')
                    unit = standard.get('male_unit', '')
                elif gender.lower() == 'female':
                    min_val = standard.get('female_range_min')
                    max_val = standard.get('female_range_max')
                    unit = standard.get('female_unit', '')
                else:
                    # Use general range or male as default
                    min_val = standard.get('male_range_min') or standard.get('range_min')
                    max_val = standard.get('male_range_max') or standard.get('range_max')
                    unit = standard.get('male_unit', '') or standard.get('unit', '')
                
                # Format range if both values exist
                if min_val is not None and max_val is not None:
                    return f"{min_val}-{max_val} {unit}".strip()
                elif max_val is not None:
                    return f"<{max_val} {unit}".strip()
                elif min_val is not None:
                    return f">{min_val} {unit}".strip()
            
            return None
        except Exception:
            return None
    
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
    
    def create_beautiful_2d_chart(self, test_data: pd.DataFrame, test_type: str, patient_name: str, 
                                 patient_gender: Optional[str] = None, events: List[Dict] = None) -> go.Figure:
        """Create a beautiful 2D chart with enhanced styling.
        
        Args:
            test_data: DataFrame with test results
            test_type: Type of test to display
            patient_name: Name of the patient
            patient_gender: Gender of the patient for reference ranges
            events: List of patient events to display as vertical lines
        """
        try:
            # Filter data for the specific test type
            filtered_data = test_data[test_data['Test Type'] == test_type].copy()
            
            if filtered_data.empty:
                return go.Figure().add_annotation(
                    text=f"No data available for {test_type}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font=dict(size=16)
                )
            
            # Sort by date
            filtered_data = filtered_data.sort_values('Date')
            
            # Get color for this test type
            color = self.color_scheme.get(test_type, '#636EFA')
            
            # Create beautiful 2D plot
            fig = go.Figure()
            
            # Add filled area under the curve
            fig.add_trace(go.Scatter(
                x=filtered_data['Date'],
                y=filtered_data['Value'],
                fill='tonexty',
                fillcolor='rgba(99, 110, 250, 0.1)',
                line=dict(color=color, width=0),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            # Add main line with enhanced markers
            fig.add_trace(go.Scatter(
                x=filtered_data['Date'],
                y=filtered_data['Value'],
                mode='lines+markers',
                name=test_type,
                line=dict(color=color, width=4),
                marker=dict(
                    size=12,
                    color='white',
                    line=dict(width=3, color=color),
                    symbol='circle'
                ),
                hovertemplate='<b>%{y}</b><br>%{x|%Y-%m-%d}<br>Patient: ' + (patient_name or 'Unknown') + '<extra></extra>'
            ))
            
            # Enhanced styling
            fig.update_layout(
                title=dict(
                    text=f"<b>{test_type}</b><br><sub>Patient: {patient_name or 'Unknown'}</sub>",
                    font=dict(size=16, color='#2c3e50'),
                    x=0.5
                ),
                height=300,
                margin=dict(l=50, r=50, t=80, b=50),
                plot_bgcolor='rgba(248, 249, 250, 0.8)',
                paper_bgcolor='white',
                showlegend=False,
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    title=dict(text="Date", font=dict(size=12, color='#34495e')),
                    tickfont=dict(size=10, color='#7f8c8d'),
                    linecolor='#bdc3c7',
                    linewidth=2,
                    showline=True
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    title=dict(text="Value", font=dict(size=12, color='#34495e')),
                    tickfont=dict(size=10, color='#7f8c8d'),
                    linecolor='#bdc3c7',
                    linewidth=2,
                    showline=True
                )
            )
            
            # Add value annotations for ALL data points
            for i, row in filtered_data.iterrows():
                fig.add_annotation(
                    x=row['Date'],
                    y=row['Value'],
                    text=f"{row['Value']:.1f}",
                    showarrow=False,
                    yshift=15,
                    font=dict(size=10, color=color, weight='bold'),
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor=color,
                    borderwidth=1
                )
            
            # Add patient events as vertical lines
            if events:
                self.add_event_lines(fig, events, (filtered_data['Date'].min(), filtered_data['Date'].max()))
            
            return fig
            
        except Exception as e:
            print(f"Error creating beautiful 2D chart for {test_type}: {e}")
            return go.Figure()
    
    def create_grouped_chart(self, category_data: pd.DataFrame, patient_name: str, test_types: list, 
                           category: str, patient_gender: Optional[str] = None, events: List[Dict] = None) -> go.Figure:
        """Create a grouped comparison chart for multiple tests in a category.
        
        Args:
            category_data: DataFrame with test results
            patient_name: Name of the patient
            test_types: List of test types to display
            category: Category name
            patient_gender: Gender of the patient for reference ranges
            events: List of patient events to display as vertical lines
        """
        try:
            fig = go.Figure()
            
            # Use a color palette for different tests
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
            
            for i, test_type in enumerate(test_types):
                test_data = category_data[category_data['Test Type'] == test_type].copy()
                if not test_data.empty:
                    test_data = test_data.sort_values('Date')
                    color = colors[i % len(colors)]
                    
                    # Add line with markers for each test
                    fig.add_trace(go.Scatter(
                        x=test_data['Date'],
                        y=test_data['Value'],
                        mode='lines+markers',
                        name=test_type,
                        line=dict(color=color, width=3),
                        marker=dict(
                            size=8,
                            color=color,
                            line=dict(width=2, color='white')
                        ),
                        hovertemplate=f'<b>{test_type}</b><br>Value: %{{y}}<br>Date: %{{x|%Y-%m-%d}}<extra></extra>'
                    ))
                    
                    # Add value annotations for this test type
                    for idx, row in test_data.iterrows():
                        fig.add_annotation(
                            x=row['Date'],
                            y=row['Value'],
                            text=f"{row['Value']:.1f}",
                            showarrow=False,
                            yshift=12,
                            font=dict(size=8, color=color),
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor=color,
                            borderwidth=1
                        )
            
            # Enhanced styling for grouped chart
            fig.update_layout(
                title=dict(
                    text=f"<b>{category} Tests Comparison</b><br><sub>Patient: {patient_name or 'Unknown'}</sub>",
                    font=dict(size=18, color='#2c3e50'),
                    x=0.5
                ),
                height=400,
                margin=dict(l=60, r=60, t=100, b=60),
                plot_bgcolor='rgba(248, 249, 250, 0.9)',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=11)
                ),
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    title=dict(text="Date", font=dict(size=14, color='#34495e')),
                    tickfont=dict(size=12, color='#7f8c8d'),
                    linecolor='#bdc3c7',
                    linewidth=2,
                    showline=True
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    title=dict(text="Values", font=dict(size=14, color='#34495e')),
                    tickfont=dict(size=12, color='#7f8c8d'),
                    linecolor='#bdc3c7',
                    linewidth=2,
                    showline=True
                )
            )
            
            # Add patient events as vertical lines
            if events and not category_data.empty:
                self.add_event_lines(fig, events, (category_data['Date'].min(), category_data['Date'].max()))
            
            return fig
            
        except Exception as e:
            print(f"Error creating grouped chart for {category}: {e}")
            return go.Figure()
