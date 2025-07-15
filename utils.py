from datetime import datetime, date
from typing import Any, Optional, Union
import re
import streamlit as st

def validate_date(date_value: Any) -> bool:
    """Validate if the given value is a valid date."""
    try:
        if isinstance(date_value, date):
            return True
        elif isinstance(date_value, str):
            # Try to parse string date
            datetime.strptime(date_value, '%Y-%m-%d')
            return True
        return False
    except:
        return False

def format_test_value(value: float, test_type: str) -> str:
    """Format test value based on test type for display."""
    try:
        # Define precision for different test types
        precision_map = {
            'HbA1c': 1,
            'Glucose': 0,
            'Fasting Glucose': 0,
            'Random Glucose': 0,
            'Total Cholesterol': 0,
            'HDL Cholesterol': 0,
            'LDL Cholesterol': 0,
            'Triglycerides': 0,
            'Hemoglobin': 1,
            'Hematocrit': 1,
            'Creatinine': 2,
            'BUN': 0,
            'TSH': 2,
            'T4': 1,
            'T3': 1,
            'Sodium': 0,
            'Potassium': 1,
            'Chloride': 0
        }
        
        precision = precision_map.get(test_type, 1)
        return f"{value:.{precision}f}"
    except:
        return str(value)

def parse_reference_range(ref_range: str) -> dict:
    """Parse reference range string into min/max values."""
    try:
        if not ref_range or ref_range.strip() == '':
            return {}
        
        # Remove units and extra text
        range_text = re.sub(r'\s*\([MF]\)', '', ref_range)  # Remove (M) or (F) indicators
        range_text = re.sub(r'[a-zA-Z/%\s]+$', '', range_text)  # Remove units at the end
        
        # Extract numbers
        numbers = re.findall(r'\d+(?:\.\d+)?', range_text)
        
        if len(numbers) >= 2:
            return {
                'min': float(numbers[0]),
                'max': float(numbers[1]),
                'type': 'range'
            }
        elif len(numbers) == 1:
            value = float(numbers[0])
            if '<' in ref_range:
                return {
                    'max': value,
                    'type': 'upper_limit'
                }
            elif '>' in ref_range:
                return {
                    'min': value,
                    'type': 'lower_limit'
                }
        
        return {}
    except:
        return {}

def is_value_normal(value: float, ref_range: str) -> tuple:
    """Check if a value is within normal range and return status."""
    try:
        parsed_range = parse_reference_range(ref_range)
        
        if not parsed_range:
            return True, "Unknown"
        
        if parsed_range['type'] == 'range':
            min_val = parsed_range['min']
            max_val = parsed_range['max']
            
            if value < min_val:
                return False, "Low"
            elif value > max_val:
                return False, "High"
            else:
                return True, "Normal"
        
        elif parsed_range['type'] == 'upper_limit':
            max_val = parsed_range['max']
            if value > max_val:
                return False, "High"
            else:
                return True, "Normal"
        
        elif parsed_range['type'] == 'lower_limit':
            min_val = parsed_range['min']
            if value < min_val:
                return False, "Low"
            else:
                return True, "Normal"
        
        return True, "Unknown"
    except:
        return True, "Unknown"

def format_date_for_display(date_value: Union[str, date, datetime]) -> str:
    """Format date for display in UI."""
    try:
        if isinstance(date_value, str):
            date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
        elif isinstance(date_value, datetime):
            date_obj = date_value.date()
        elif isinstance(date_value, date):
            date_obj = date_value
        else:
            return str(date_value)
        
        return date_obj.strftime('%B %d, %Y')
    except:
        return str(date_value)

def sanitize_patient_name(name: str) -> str:
    """Sanitize patient name for safe storage and display."""
    try:
        if not name or not isinstance(name, str):
            return ""
        
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Remove special characters except spaces, hyphens, and apostrophes
        name = re.sub(r'[^a-zA-Z\s\-\']', '', name)
        
        # Capitalize properly
        name = ' '.join(word.capitalize() for word in name.split())
        
        return name
    except:
        return str(name)

def generate_filename_safe_string(text: str) -> str:
    """Convert text to filename-safe string."""
    try:
        # Replace spaces with underscores
        text = text.replace(' ', '_')
        
        # Remove characters that are not alphanumeric, underscore, or hyphen
        text = re.sub(r'[^a-zA-Z0-9_\-]', '', text)
        
        # Limit length
        if len(text) > 50:
            text = text[:50]
        
        return text.lower()
    except:
        return "file"

def calculate_age_from_dob(dob: date) -> int:
    """Calculate age from date of birth."""
    try:
        today = date.today()
        age = today.year - dob.year
        
        # Adjust if birthday hasn't occurred this year
        if today.month < dob.month or (today.month == dob.month and today.day < dob.day):
            age -= 1
        
        return age
    except:
        return 0

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    try:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        
        return f"{s} {size_names[i]}"
    except:
        return f"{size_bytes} B"

def get_status_color(status: str) -> str:
    """Get color code for different status values."""
    status_colors = {
        'Normal': '#28a745',    # Green
        'High': '#dc3545',      # Red
        'Low': '#fd7e14',       # Orange
        'Critical': '#721c24',  # Dark red
        'Unknown': '#6c757d'    # Gray
    }
    
    return status_colors.get(status, '#6c757d')

def create_download_link(data: str, filename: str, link_text: str) -> str:
    """Create a download link for data."""
    import base64
    
    try:
        b64 = base64.b64encode(data.encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
        return href
    except:
        return link_text

def validate_file_type(file_type: str) -> bool:
    """Validate if file type is supported."""
    supported_types = [
        'application/pdf',
        'text/plain',
        'text/csv',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/xml',
        'text/xml'
    ]
    
    return file_type in supported_types

def extract_numeric_value(text: str) -> Optional[float]:
    """Extract numeric value from text string."""
    try:
        # Remove common non-numeric characters but keep decimal points
        cleaned = re.sub(r'[^\d\.]', '', text)
        
        if cleaned:
            return float(cleaned)
        
        return None
    except:
        return None

def format_test_name_for_display(test_name: str) -> str:
    """Format test name for better display."""
    try:
        # Convert underscores to spaces
        formatted = test_name.replace('_', ' ')
        
        # Capitalize each word
        formatted = ' '.join(word.capitalize() for word in formatted.split())
        
        # Handle special cases
        special_cases = {
            'Hba1c': 'HbA1c',
            'Hdl': 'HDL',
            'Ldl': 'LDL',
            'Tsh': 'TSH',
            'T4': 'T4',
            'T3': 'T3',
            'Alt': 'ALT',
            'Ast': 'AST',
            'Bun': 'BUN',
            'Egfr': 'eGFR',
            'Rbc': 'RBC',
            'Wbc': 'WBC'
        }
        
        for old, new in special_cases.items():
            formatted = formatted.replace(old, new)
        
        return formatted
    except:
        return test_name

def get_test_interpretation(test_type: str, value: float, ref_range: str) -> dict:
    """Get interpretation and recommendations for a test result."""
    try:
        is_normal, status = is_value_normal(value, ref_range)
        
        # Basic interpretations (for educational purposes only)
        interpretations = {
            'Glucose': {
                'High': 'Elevated glucose levels may indicate diabetes or prediabetes.',
                'Low': 'Low glucose levels may indicate hypoglycemia.',
                'Normal': 'Glucose levels are within normal range.'
            },
            'HbA1c': {
                'High': 'Elevated HbA1c indicates poor glucose control over the past 2-3 months.',
                'Low': 'HbA1c levels are optimal.',
                'Normal': 'HbA1c levels indicate good glucose control.'
            },
            'Total Cholesterol': {
                'High': 'High cholesterol may increase cardiovascular risk.',
                'Low': 'Low cholesterol levels are generally favorable.',
                'Normal': 'Cholesterol levels are within recommended range.'
            }
        }
        
        interpretation = interpretations.get(test_type, {}).get(status, 'Consult your healthcare provider for interpretation.')
        
        return {
            'status': status,
            'is_normal': is_normal,
            'interpretation': interpretation,
            'recommendation': 'Please consult with your healthcare provider for proper medical interpretation and advice.'
        }
    except:
        return {
            'status': 'Unknown',
            'is_normal': True,
            'interpretation': 'Unable to interpret result.',
            'recommendation': 'Consult your healthcare provider.'
        }
