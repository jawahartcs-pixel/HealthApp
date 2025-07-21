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
        try:
            # Create PDF buffer
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
            
            # Collect report elements
            story = []
            
            # Title page
            story.extend(self._create_title_page(patient_name))
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
            return buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Failed to generate PDF report: {str(e)}")
    
    def _create_title_page(self, patient_name: str) -> List:
        """Create title page for the report."""
        elements = []
        
        # Main title
        title = Paragraph("Blood Test Results Report", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
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
        
        df = pd.DataFrame(test_data, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
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
        
        df = pd.DataFrame(test_data, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
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
        
        df = pd.DataFrame(test_data, columns=['patient_name', 'test_date', 'test_type', 'test_value', 'unit', 'reference_range'])
        df['test_date'] = pd.to_datetime(df['test_date'])
        df['test_value'] = pd.to_numeric(df['test_value'], errors='coerce')
        
        # Create charts for each test type
        test_types = df['test_type'].unique()[:6]  # Limit to 6 charts per page
        
        for test_type in test_types:
            test_df = df[df['test_type'] == test_type].sort_values('test_date')
            
            if len(test_df) > 1:
                chart_image = self._create_trend_chart(test_df, test_type)
                if chart_image:
                    elements.append(Paragraph(f"{test_type} Trend", self.subheading_style))
                    elements.append(chart_image)
                    elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_trend_chart(self, df: pd.DataFrame, test_type: str) -> Optional[Image]:
        """Create trend chart for a specific test type."""
        try:
            # Create matplotlib figure
            plt.figure(figsize=(8, 4))
            plt.plot(df['test_date'], df['test_value'], marker='o', linewidth=2, markersize=6)
            plt.title(f'{test_type} Trend Over Time', fontsize=14, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Value', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            plt.savefig(temp_file.name, dpi=150, bbox_inches='tight')
            plt.close()
            
            # Create ReportLab Image
            image = Image(temp_file.name, width=6*inch, height=3*inch)
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return image
            
        except Exception as e:
            print(f"Error creating chart for {test_type}: {e}")
            return None
    
    def _create_alert_summary(self, patient_name: str, user_id: int) -> List:
        """Create alert summary section."""
        elements = []
        
        # Section header
        elements.append(Paragraph("Alert Summary", self.heading_style))
        
        try:
            from alert_system import AlertSystem
            alert_system = AlertSystem(self.database)
            
            # Get patient alerts
            alerts = alert_system.get_patient_alerts(patient_name, user_id)
            
            if not alerts:
                elements.append(Paragraph("No active alerts for this patient.", self.styles['Normal']))
                return elements
            
            # Create alerts table
            alert_data = [['Date', 'Test Type', 'Value', 'Level', 'Status']]
            
            for alert in alerts[:10]:  # Limit to 10 most recent alerts
                alert_data.append([
                    alert.get('test_date', 'N/A'),
                    alert.get('test_type', 'N/A'),
                    str(alert.get('test_value', 'N/A')),
                    alert.get('alert_level', 'N/A'),
                    alert.get('status', 'N/A')
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