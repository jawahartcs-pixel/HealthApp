"""
PDF Report Generator for Patient Blood Test Results
Creates comprehensive, shareable PDF reports with data and visualizations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime, date
import io
import base64
from typing import Dict, List, Any, Optional, Tuple
import tempfile
import os

class PDFReportGenerator:
    def __init__(self, database):
        """Initialize PDF report generator with database connection."""
        self.database = database
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for the report."""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        )
        
        self.subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=8,
            textColor=colors.navy
        )
    
    def generate_patient_report(self, patient_name: str, user_id: int = None) -> bytes:
        """Generate comprehensive PDF report for a patient."""
        # Initialize temp files list for cleanup
        self._temp_files = []
        
        try:
            # Create PDF buffer
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
            
            # Collect report elements
            story = []
            
            # Title page
            story.extend(self._create_title_page(patient_name, user_id))
            story.append(PageBreak())
            
            # Patient summary
            story.extend(self._create_patient_summary(patient_name, user_id))
            
            # Test results table
            story.extend(self._create_test_results_table(patient_name, user_id))
            story.append(PageBreak())
            
            # Charts and visualizations
            story.extend(self._create_visualization_section(patient_name, user_id))
            
            # Alert summary
            story.extend(self._create_alert_summary(patient_name, user_id))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            buffer.seek(0)
            pdf_bytes = buffer.getvalue()
            
            # Clean up temporary files
            if hasattr(self, '_temp_files'):
                for temp_file in self._temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except Exception:
                        pass  # Ignore cleanup errors
                self._temp_files = []
            
            return pdf_bytes
            
        except Exception as e:
            # Clean up temporary files on error
            if hasattr(self, '_temp_files'):
                for temp_file in self._temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except Exception:
                        pass
            raise Exception(f"Failed to generate PDF report: {str(e)}")
    
    def _create_title_page(self, patient_name: str, user_id: int = None) -> List:
        """Create title page for the report with patient profile."""
        elements = []
        
        # Main title
        title = Paragraph("Blood Test Results Report", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Patient name
        patient_heading = Paragraph(f"Patient: {patient_name}", self.heading_style)
        elements.append(patient_heading)
        elements.append(Spacer(1, 20))
        
        # Get patient profile for comprehensive information
        profile = self.database.get_patient_profile(patient_name, user_id)
        
        if profile:
            # Patient profile table
            profile_data = [
                ['Patient Information', ''],
                ['Name:', profile['patient_name']],
                ['Age:', f"{profile['age']} years" if profile['age'] else 'Not specified'],
                ['Gender:', profile['gender'] if profile['gender'] else 'Not specified'],
                ['Phone:', profile['phone'] if profile['phone'] else 'Not provided'],
                ['Email:', profile['email'] if profile['email'] else 'Not provided'],
                ['Patient Since:', profile['created_at'][:10] if profile['created_at'] else 'Unknown']
            ]
            
            if profile['address']:
                profile_data.append(['Address:', profile['address']])
            
            if profile['emergency_contact']:
                profile_data.append(['Emergency Contact:', profile['emergency_contact']])
            
            # Create profile table
            profile_table = Table(profile_data, colWidths=[2*inch, 4*inch])
            profile_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(profile_table)
            elements.append(Spacer(1, 20))
            
            # Medical Information Section (if available)
            medical_sections = []
            
            if profile['medical_history']:
                medical_sections.append(['Medical History:', profile['medical_history']])
            
            if profile['medications']:
                medical_sections.append(['Current Medications:', profile['medications']])
            
            if profile['allergies']:
                medical_sections.append(['Allergies:', profile['allergies']])
            
            if profile['notes']:
                medical_sections.append(['Additional Notes:', profile['notes']])
            
            if medical_sections:
                # Add medical information heading
                medical_heading = Paragraph("Medical Information", self.subheading_style)
                elements.append(medical_heading)
                elements.append(Spacer(1, 10))
                
                # Create medical info table
                medical_table = Table(medical_sections, colWidths=[2*inch, 4*inch])
                medical_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.lightyellow),
                    ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
                ]))
                
                elements.append(medical_table)
                elements.append(Spacer(1, 20))
        
        # Report generation date
        generation_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        date_paragraph = Paragraph(f"<i>Report generated on {generation_date}</i>", self.styles['Normal'])
        elements.append(date_paragraph)
        
        return elements
        
        # Patient name
        patient_title = Paragraph(f"Patient: {patient_name}", self.heading_style)
        elements.append(patient_title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Report date
        report_date = Paragraph(f"Report Generated: {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal'])
        elements.append(report_date)
        elements.append(Spacer(1, 0.5*inch))
        
        # Report description
        description = Paragraph(
            "This report contains a comprehensive analysis of blood test results, "
            "including trends, alerts, and clinical insights based on the latest "
            "test data available in the system.",
            self.styles['Normal']
        )
        elements.append(description)
        
        return elements
    
    def _create_patient_summary(self, patient_name: str, user_id: int) -> List:
        """Create patient summary section."""
        elements = []
        
        # Section header
        elements.append(Paragraph("Patient Summary", self.heading_style))
        
        # Get patient data
        test_data = self.database.get_patient_tests(patient_name, user_id)
        
        if not test_data:
            elements.append(Paragraph("No test data available for this patient.", self.styles['Normal']))
            return elements
        
        # get_patient_tests returns 5 columns: test_date, test_type, test_value, unit, reference_range
        df = pd.DataFrame(test_data, columns=['test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['test_date'] = pd.to_datetime(df['test_date'])
        
        # Summary statistics
        total_tests = len(df)
        test_types = df['test_type'].nunique()
        date_range = f"{df['test_date'].min().strftime('%Y-%m-%d')} to {df['test_date'].max().strftime('%Y-%m-%d')}"
        
        summary_data = [
            ['Total Test Results', str(total_tests)],
            ['Unique Test Types', str(test_types)],
            ['Date Range', date_range],
            ['Most Recent Test', df['test_date'].max().strftime('%Y-%m-%d')]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_test_results_table(self, patient_name: str, user_id: int) -> List:
        """Create detailed test results table."""
        elements = []
        
        # Section header
        elements.append(Paragraph("Recent Test Results", self.heading_style))
        
        # Get patient data
        test_data = self.database.get_patient_tests(patient_name, user_id)
        
        if not test_data:
            elements.append(Paragraph("No test data available.", self.styles['Normal']))
            return elements
        
        # get_patient_tests returns 5 columns: test_date, test_type, test_value, unit, reference_range
        df = pd.DataFrame(test_data, columns=['test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['test_date'] = pd.to_datetime(df['test_date'])
        
        # Sort by date (most recent first) and limit to last 20 results
        df_sorted = df.sort_values('test_date', ascending=False).head(20)
        
        # Prepare table data
        table_data = [['Date', 'Test Type', 'Value', 'Unit', 'Reference Range']]
        
        for _, row in df_sorted.iterrows():
            table_data.append([
                row['test_date'].strftime('%Y-%m-%d'),
                str(row['test_type']),
                str(row['test_value']),
                str(row['unit']) if pd.notna(row['unit']) else '',
                str(row['reference_range']) if pd.notna(row['reference_range']) else ''
            ])
        
        # Create table
        results_table = Table(table_data, colWidths=[1.2*inch, 1.8*inch, 1*inch, 0.8*inch, 1.5*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        
        elements.append(results_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_visualization_section(self, patient_name: str, user_id: int) -> List:
        """Create charts and visualizations section."""
        elements = []
        
        # Section header
        elements.append(Paragraph("Test Trends and Visualizations", self.heading_style))
        
        # Get patient data
        test_data = self.database.get_patient_tests(patient_name, user_id)
        
        if not test_data:
            elements.append(Paragraph("No data available for visualization.", self.styles['Normal']))
            return elements
        
        # get_patient_tests returns 5 columns: test_date, test_type, test_value, unit, reference_range
        df = pd.DataFrame(test_data, columns=['test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['test_date'] = pd.to_datetime(df['test_date'])
        df['test_value'] = pd.to_numeric(df['test_value'], errors='coerce')
        
        # Group test types by medical category using investigation standards
        try:
            from investigation_standards import InvestigationStandards
            standards = InvestigationStandards(self.database)
            
            # Get all test types and group by category
            test_types = df['test_type'].unique()
            categorized_tests = {}
            
            for test_type in test_types:
                category = standards.get_test_category(test_type)
                if category not in categorized_tests:
                    categorized_tests[category] = []
                categorized_tests[category].append(test_type)
            
            # Sort categories and create charts in order
            for category in sorted(categorized_tests.keys()):
                # Add category header
                if len(categorized_tests) > 1:  # Only show category headers if multiple categories
                    elements.append(Paragraph(f"{category} Tests", self.subheading_style))
                    elements.append(Spacer(1, 0.1*inch))
                
                # Create charts for tests in this category
                for test_type in sorted(categorized_tests[category]):
                    test_df = df[df['test_type'] == test_type].sort_values('test_date')
                    
                    if len(test_df) >= 1:  # Show charts even for single data points
                        chart_image = self._create_trend_chart(test_df, test_type)
                        if chart_image:
                            elements.append(Paragraph(f"{test_type} Trend", 
                                ParagraphStyle('TestTitle', parent=self.styles['Normal'], 
                                             fontSize=12, spaceBefore=6, spaceAfter=6)))
                            elements.append(chart_image)
                            elements.append(Spacer(1, 0.15*inch))
                
                # Add space between categories
                if len(categorized_tests) > 1:
                    elements.append(Spacer(1, 0.2*inch))
                    
        except Exception as e:
            # Fallback to alphabetical order if categorization fails
            test_types = sorted(df['test_type'].unique())
            
            for test_type in test_types:
                test_df = df[df['test_type'] == test_type].sort_values('test_date')
                
                if len(test_df) >= 1:
                    chart_image = self._create_trend_chart(test_df, test_type)
                    if chart_image:
                        elements.append(Paragraph(f"{test_type} Trend", self.subheading_style))
                        elements.append(chart_image)
                        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_trend_chart(self, df: pd.DataFrame, test_type: str) -> Optional[Image]:
        """Create trend chart for a specific test type."""
        try:
            # Ensure matplotlib uses non-interactive backend
            import matplotlib
            if matplotlib.get_backend() != 'Agg':
                matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            # Create matplotlib figure
            plt.figure(figsize=(8, 4))
            
            # Add reference range shading first (so it appears behind the line)
            self._add_reference_range_to_chart(plt, df, test_type)
            
            plt.plot(df['test_date'], df['test_value'], marker='o', linewidth=2, markersize=6, color='#1f77b4', zorder=3)
            
            # Add value labels on each data point
            for i, (date, value) in enumerate(zip(df['test_date'], df['test_value'])):
                plt.annotate(f'{value:.2f}', (date, value), 
                           textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, zorder=4)
            
            plt.title(f'{test_type} Trend Over Time', fontsize=14, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Value', fontsize=12)
            plt.grid(True, alpha=0.3, zorder=1)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to temporary file with proper cleanup
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_filename = temp_file.name
            temp_file.close()
            
            plt.savefig(temp_filename, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            
            # Create ReportLab Image from file
            image = Image(temp_filename, width=6*inch, height=3*inch)
            
            # Store temp file path for later cleanup
            if not hasattr(self, '_temp_files'):
                self._temp_files = []
            self._temp_files.append(temp_filename)
            
            return image
            
        except Exception as e:
            print(f"Error creating chart for {test_type}: {e}")
            return None
    
    def _add_reference_range_to_chart(self, plt, df: pd.DataFrame, test_type: str):
        """Add reference range shading to matplotlib chart."""
        try:
            # Get reference range from the first row (should be consistent for same test type)
            if not df.empty and pd.notna(df.iloc[0]['reference_range']):
                ref_range = str(df.iloc[0]['reference_range'])
                
                # Parse reference range using regex (similar to visualization.py)
                import re
                numbers = re.findall(r'\d+(?:\.\d+)?', ref_range)
                
                if len(numbers) >= 2:
                    # Range format (e.g., "70-100")
                    min_val = float(numbers[0])
                    max_val = float(numbers[1])
                    
                    # Add shaded area for normal range
                    plt.axhspan(min_val, max_val, alpha=0.2, color='lightgreen', 
                               label='Normal Range', zorder=2)
                    
                    # Add text annotation for the normal range
                    y_position = min_val + (max_val - min_val) * 0.5
                    plt.text(df['test_date'].iloc[-1], y_position, 
                            f'Normal: {min_val}-{max_val}', 
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                            fontsize=8, ha='right', va='center')
                    
                elif len(numbers) == 1 and ('<' in ref_range or '>' in ref_range):
                    # Single boundary format (e.g., "<200" or ">40")
                    value = float(numbers[0])
                    if '<' in ref_range:
                        plt.axhline(y=value, color='orange', linestyle='--', alpha=0.8, 
                                   label=f'Upper limit: {value}', zorder=2)
                    elif '>' in ref_range:
                        plt.axhline(y=value, color='orange', linestyle='--', alpha=0.8, 
                                   label=f'Lower limit: {value}', zorder=2)
                    
                    # Add text annotation
                    plt.text(df['test_date'].iloc[-1], value, 
                            f'Limit: {ref_range}', 
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.7),
                            fontsize=8, ha='right', va='bottom')
                            
        except Exception as e:
            # If parsing fails, skip adding reference range
            print(f"Could not add reference range for {test_type}: {e}")
            pass
    
    def _create_alert_summary(self, patient_name: str, user_id: int) -> List:
        """Create alert summary section."""
        elements = []
        
        # Section header
        elements.append(Paragraph("Alert Summary", self.heading_style))
        
        try:
            from alert_system import AlertSystem
            alert_system = AlertSystem(self.database)
            
            # Get patient alerts 
            alerts = alert_system.get_patient_alerts(patient_name)
            
            if not alerts:
                elements.append(Paragraph("No active alerts for this patient.", self.styles['Normal']))
                return elements
            
            # Create alerts table
            alert_data = [['Date', 'Test Type', 'Value', 'Level', 'Message']]
            
            for alert in alerts[:10]:  # Limit to 10 most recent alerts
                alert_data.append([
                    str(alert.get('test_date', 'N/A')),
                    str(alert.get('test_type', 'N/A')),
                    str(alert.get('value', 'N/A')),
                    str(alert.get('level', 'N/A')),
                    str(alert.get('message', 'N/A'))
                ])
            
            alerts_table = Table(alert_data, colWidths=[1.2*inch, 1.8*inch, 1*inch, 1*inch, 1.3*inch])
            alerts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            
            elements.append(alerts_table)
            
        except Exception as e:
            elements.append(Paragraph(f"Error loading alerts: {str(e)}", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer = Paragraph(
            f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            "Blood Test Results Management System",
            ParagraphStyle('Footer', parent=self.styles['Normal'], fontSize=8, alignment=TA_CENTER)
        )
        elements.append(footer)
        
        return elements