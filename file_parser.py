import re
import io
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import pdfplumber
import streamlit as st

class FileParser:
    def __init__(self):
        """Initialize the file parser with common blood test patterns."""
        # Common blood test parameters and their patterns
        self.test_patterns = {
            # Glucose tests
            'glucose': r'(?:glucose|sugar|glu)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'fasting_glucose': r'(?:fasting\s+glucose|fbs|fbg)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'random_glucose': r'(?:random\s+glucose|rbs|rbg)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'hba1c': r'(?:hba1c|hemoglobin\s+a1c|glycated\s+hemoglobin)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?',
            
            # Cholesterol tests
            'total_cholesterol': r'(?:total\s+cholesterol|cholesterol)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'hdl_cholesterol': r'(?:hdl|hdl\s+cholesterol|high\s+density\s+lipoprotein)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'ldl_cholesterol': r'(?:ldl|ldl\s+cholesterol|low\s+density\s+lipoprotein)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'triglycerides': r'(?:triglycerides|tg|trig)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            
            # Blood count tests
            'hemoglobin': r'(?:hemoglobin|hgb|hb)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:g/dl|g/l)?',
            'hematocrit': r'(?:hematocrit|hct|pcv)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?',
            'rbc_count': r'(?:rbc|red\s+blood\s+cell\s+count|erythrocytes)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:million/ul|×10\^6/ul)?',
            'wbc_count': r'(?:wbc|white\s+blood\s+cell\s+count|leukocytes)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:thousand/ul|×10\^3/ul)?',
            'platelet_count': r'(?:platelets?|plt)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:thousand/ul|×10\^3/ul)?',
            
            # Liver function tests
            'alt': r'(?:alt|alanine\s+aminotransferase|sgpt)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:u/l|iu/l)?',
            'ast': r'(?:ast|aspartate\s+aminotransferase|sgot)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:u/l|iu/l)?',
            'bilirubin_total': r'(?:total\s+bilirubin|bilirubin)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|μmol/l)?',
            'albumin': r'(?:albumin|alb)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:g/dl|g/l)?',
            
            # Kidney function tests
            'creatinine': r'(?:creatinine|creat)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|μmol/l)?',
            'bun': r'(?:bun|blood\s+urea\s+nitrogen|urea)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mg/dl|mmol/l)?',
            'egfr': r'(?:egfr|estimated\s+gfr)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:ml/min/1\.73m2)?',
            
            # Thyroid function tests
            'tsh': r'(?:tsh|thyroid\s+stimulating\s+hormone)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:μiu/ml|miu/l)?',
            't4': r'(?:t4|thyroxine|free\s+t4)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:ng/dl|pmol/l)?',
            't3': r'(?:t3|triiodothyronine|free\s+t3)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:pg/ml|pmol/l)?',
            
            # Electrolytes
            'sodium': r'(?:sodium|na)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:meq/l|mmol/l)?',
            'potassium': r'(?:potassium|k)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:meq/l|mmol/l)?',
            'chloride': r'(?:chloride|cl)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:meq/l|mmol/l)?',
            
            # Other common tests
            'vitamin_d': r'(?:vitamin\s+d|25\s*\(\s*oh\s*\)\s*d3?)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:ng/ml|nmol/l)?',
            'vitamin_b12': r'(?:vitamin\s+b12|b12|cobalamin)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:pg/ml|pmol/l)?',
            'iron': r'(?:iron|fe)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:μg/dl|μmol/l)?',
            'ferritin': r'(?:ferritin)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:ng/ml|μg/l)?'
        }
        
        # Common units for each test type
        self.common_units = {
            'glucose': 'mg/dL',
            'fasting_glucose': 'mg/dL',
            'random_glucose': 'mg/dL',
            'hba1c': '%',
            'total_cholesterol': 'mg/dL',
            'hdl_cholesterol': 'mg/dL',
            'ldl_cholesterol': 'mg/dL',
            'triglycerides': 'mg/dL',
            'hemoglobin': 'g/dL',
            'hematocrit': '%',
            'rbc_count': 'million/uL',
            'wbc_count': 'thousand/uL',
            'platelet_count': 'thousand/uL',
            'alt': 'U/L',
            'ast': 'U/L',
            'bilirubin_total': 'mg/dL',
            'albumin': 'g/dL',
            'creatinine': 'mg/dL',
            'bun': 'mg/dL',
            'egfr': 'mL/min/1.73m²',
            'tsh': 'μIU/mL',
            't4': 'ng/dL',
            't3': 'pg/mL',
            'sodium': 'mEq/L',
            'potassium': 'mEq/L',
            'chloride': 'mEq/L',
            'vitamin_d': 'ng/mL',
            'vitamin_b12': 'pg/mL',
            'iron': 'μg/dL',
            'ferritin': 'ng/mL'
        }
        
        # Common reference ranges
        self.reference_ranges = {
            'glucose': '70-100 mg/dL',
            'fasting_glucose': '70-100 mg/dL',
            'random_glucose': '<140 mg/dL',
            'hba1c': '4.0-5.6%',
            'total_cholesterol': '<200 mg/dL',
            'hdl_cholesterol': '>40 mg/dL (M), >50 mg/dL (F)',
            'ldl_cholesterol': '<100 mg/dL',
            'triglycerides': '<150 mg/dL',
            'hemoglobin': '12.0-16.0 g/dL (F), 14.0-18.0 g/dL (M)',
            'hematocrit': '36-46% (F), 41-50% (M)',
            'rbc_count': '4.2-5.4 million/uL (F), 4.7-6.1 million/uL (M)',
            'wbc_count': '4.5-11.0 thousand/uL',
            'platelet_count': '150-450 thousand/uL',
            'alt': '7-56 U/L',
            'ast': '10-40 U/L',
            'bilirubin_total': '0.2-1.2 mg/dL',
            'albumin': '3.5-5.0 g/dL',
            'creatinine': '0.6-1.2 mg/dL (F), 0.7-1.3 mg/dL (M)',
            'bun': '7-20 mg/dL',
            'egfr': '>60 mL/min/1.73m²',
            'tsh': '0.4-4.0 μIU/mL',
            't4': '4.5-12.0 ng/dL',
            't3': '2.3-4.2 pg/mL',
            'sodium': '136-145 mEq/L',
            'potassium': '3.5-5.0 mEq/L',
            'chloride': '98-107 mEq/L',
            'vitamin_d': '30-100 ng/mL',
            'vitamin_b12': '200-900 pg/mL',
            'iron': '60-170 μg/dL',
            'ferritin': '12-150 ng/mL (F), 12-300 ng/mL (M)'
        }
        
        # Date patterns
        self.date_patterns = [
            r'(?:date|test\s+date|collection\s+date)[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:date|test\s+date|collection\s+date)[:\-]?\s*(\d{2,4}[\/\-]\d{1,2}[\/\-]\d{1,2})',
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{2,4}[\/\-]\d{1,2}[\/\-]\d{1,2})'
        ]
        
        # Patient name patterns
        self.patient_patterns = [
            r'(?:patient|name|patient\s+name)[:\-]?\s*([A-Za-z\s]+?)(?:\n|$|,)',
            r'(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]+?)(?:\n|$|,)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
    
    def parse_file(self, uploaded_file) -> str:
        """Parse uploaded file and extract text content."""
        try:
            if uploaded_file.type == "application/pdf":
                return self._parse_pdf(uploaded_file)
            elif uploaded_file.type == "text/plain":
                return self._parse_text(uploaded_file)
            else:
                raise ValueError(f"Unsupported file type: {uploaded_file.type}")
        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")
            return ""
    
    def _parse_pdf(self, uploaded_file) -> str:
        """Extract text from PDF file."""
        try:
            with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
                text = ""
                tables_text = ""
                
                for page in pdf.pages:
                    # Extract regular text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Try to extract tables which might contain test results
                    try:
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if row:
                                    # Join non-None cells with tabs
                                    row_text = '\t'.join([str(cell) if cell is not None else '' for cell in row])
                                    tables_text += row_text + "\n"
                    except:
                        # If table extraction fails, continue with text extraction
                        pass
                
                # Combine text and table content
                combined_text = text + "\n\n" + tables_text
                return combined_text
                
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def _parse_text(self, uploaded_file) -> str:
        """Extract text from text file."""
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            content = uploaded_file.read()
            
            # Handle both bytes and string content
            if isinstance(content, bytes):
                text = content.decode('utf-8', errors='ignore')
            else:
                text = content
            
            return text
        except Exception as e:
            raise Exception(f"Error reading text file: {str(e)}")
    
    def extract_test_data(self, text: str) -> Dict[str, Any]:
        """Extract test data from text content."""
        if not text.strip():
            return {}
        
        # Normalize text for better pattern matching
        normalized_text = self._normalize_text(text)
        
        # Extract patient information
        patient_name = self._extract_patient_name(normalized_text)
        test_date = self._extract_test_date(normalized_text)
        
        # Extract test results
        test_results = self._extract_test_results(normalized_text)
        
        return {
            'patient_name': patient_name,
            'test_date': test_date,
            'results': test_results
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better pattern matching."""
        # Convert to lowercase for case-insensitive matching
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with parsing
        text = re.sub(r'[^\w\s\.\-\:\(\)/]', ' ', text)
        
        return text.strip()
    
    def _extract_patient_name(self, text: str) -> str:
        """Extract patient name from text."""
        for pattern in self.patient_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)
                # Only return if it looks like a real name (2+ words, reasonable length)
                if len(name.split()) >= 2 and len(name) <= 50:
                    return name.title()  # Convert to title case
        
        return ""
    
    def _extract_test_date(self, text: str) -> Optional[date]:
        """Extract test date from text."""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for date_format in ['%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m-%d-%Y', '%d-%m-%Y', '%Y-%m-%d']:
                        try:
                            parsed_date = datetime.strptime(date_str, date_format).date()
                            # Validate that the date is reasonable (not in the future, not too old)
                            if parsed_date <= date.today() and parsed_date.year >= 1900:
                                return parsed_date
                        except ValueError:
                            continue
                except:
                    continue
        
        return date.today()  # Default to today if no date found
    
    def _extract_test_results(self, text: str) -> List[Dict[str, Any]]:
        """Extract test results from text."""
        results = []
        
        # First, try to find results using tabular pattern (common in PDF reports)
        tabular_results = self._extract_tabular_results(text)
        results.extend(tabular_results)
        
        # Then use regex patterns for any missed results
        for test_name, pattern in self.test_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    value = float(match.group(1))
                    
                    # Get the display name for the test
                    display_name = self._get_display_name(test_name)
                    
                    result = {
                        'test_type': display_name,
                        'value': value,
                        'unit': self.common_units.get(test_name, ''),
                        'reference_range': self.reference_ranges.get(test_name, ''),
                        'source': 'regex'
                    }
                    
                    results.append(result)
                    
                except (ValueError, IndexError):
                    continue
        
        # Try to extract any numeric value pairs that look like test results
        generic_results = self._extract_generic_test_results(text)
        results.extend(generic_results)
        
        # Remove duplicates but be less aggressive - only remove exact matches
        unique_results = []
        seen = set()
        
        for result in results:
            # Create a more specific key to avoid removing different tests with same value
            key = (result['test_type'].lower().strip(), round(result['value'], 2))
            if key not in seen:
                seen.add(key)
                # Remove the source field before returning
                if 'source' in result:
                    del result['source']
                unique_results.append(result)
        
        return unique_results
    
    def _get_display_name(self, test_key: str) -> str:
        """Convert test key to display name."""
        display_names = {
            'glucose': 'Glucose',
            'fasting_glucose': 'Fasting Glucose',
            'random_glucose': 'Random Glucose',
            'hba1c': 'HbA1c',
            'total_cholesterol': 'Total Cholesterol',
            'hdl_cholesterol': 'HDL Cholesterol',
            'ldl_cholesterol': 'LDL Cholesterol',
            'triglycerides': 'Triglycerides',
            'hemoglobin': 'Hemoglobin',
            'hematocrit': 'Hematocrit',
            'rbc_count': 'RBC Count',
            'wbc_count': 'WBC Count',
            'platelet_count': 'Platelet Count',
            'alt': 'ALT',
            'ast': 'AST',
            'bilirubin_total': 'Total Bilirubin',
            'albumin': 'Albumin',
            'creatinine': 'Creatinine',
            'bun': 'BUN',
            'egfr': 'eGFR',
            'tsh': 'TSH',
            't4': 'T4',
            't3': 'T3',
            'sodium': 'Sodium',
            'potassium': 'Potassium',
            'chloride': 'Chloride',
            'vitamin_d': 'Vitamin D',
            'vitamin_b12': 'Vitamin B12',
            'iron': 'Iron',
            'ferritin': 'Ferritin'
        }
        
        return display_names.get(test_key, test_key.replace('_', ' ').title())
    
    def _extract_tabular_results(self, text: str) -> List[Dict[str, Any]]:
        """Extract test results from tabular format commonly found in lab reports."""
        results = []
        
        # Look for common tabular patterns where test name, value, and range are on the same line
        # Pattern: Test Name | Value | Unit | Reference Range
        tabular_patterns = [
            # Tab-separated values (most common in extracted tables)
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]+?)\t+(\d+(?:\.\d+)?)\t*([a-zA-Z\/\%\^]*)\t*([^\n\r]*)',
            # Multiple spaces or tabs
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]+?)\s{2,}(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^]*)\s*([^\n\r]*)',
            # Pattern with vertical bars or pipes
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]+?)\s*[\|\-]\s*(\d+(?:\.\d+)?)\s*[\|\-]\s*([a-zA-Z\/\%\^]*)\s*[\|\-]?\s*([^\n\r]*)',
            # Pattern with colons
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]+?):\s*(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^]*)\s*([^\n\r]*)',
            # Pattern with dots leading to values
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]+?)\.{2,}\s*(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^]*)\s*([^\n\r]*)'
        ]
        
        for pattern in tabular_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                try:
                    test_name = match.group(1).strip()
                    value_str = match.group(2).strip()
                    unit = match.group(3).strip() if match.group(3) else ''
                    ref_range = match.group(4).strip() if match.group(4) else ''
                    
                    # Clean up test name
                    test_name = re.sub(r'\s+', ' ', test_name)
                    test_name = test_name.strip('.,()[]{}')
                    
                    # Skip if test name is too short or looks invalid
                    if len(test_name) < 2 or len(test_name) > 50:
                        continue
                    
                    # Skip common non-test words
                    skip_words = ['page', 'lab', 'report', 'date', 'time', 'patient', 'doctor', 'reference', 'normal', 'abnormal']
                    if any(word in test_name.lower() for word in skip_words):
                        continue
                    
                    value = float(value_str)
                    
                    # Validate value range
                    if value < 0 or value > 100000:
                        continue
                    
                    result = {
                        'test_type': test_name.title(),
                        'value': value,
                        'unit': unit,
                        'reference_range': ref_range,
                        'source': 'tabular'
                    }
                    
                    results.append(result)
                    
                except (ValueError, IndexError, AttributeError):
                    continue
        
        return results
    
    def _extract_generic_test_results(self, text: str) -> List[Dict[str, Any]]:
        """Extract generic test results using broader patterns."""
        results = []
        
        # Look for patterns like "Test Name: 123" or "Test Name = 123"
        generic_patterns = [
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]{2,30})\s*[:\=]\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^]*)',
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]{2,30})\s+(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^]+)',
            # Pattern for results in parentheses
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-]{2,30})\s*\(\s*(\d+(?:\.\d+)?)\s*\)',
        ]
        
        common_test_keywords = [
            'glucose', 'cholesterol', 'hemoglobin', 'hematocrit', 'platelet', 'white', 'red', 'wbc', 'rbc',
            'sodium', 'potassium', 'chloride', 'creatinine', 'bun', 'alt', 'ast', 'bilirubin', 'albumin',
            'tsh', 'thyroid', 'iron', 'ferritin', 'vitamin', 'calcium', 'phosphorus', 'magnesium'
        ]
        
        for pattern in generic_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    test_name = match.group(1).strip()
                    value_str = match.group(2).strip()
                    unit = match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else ''
                    
                    # Clean up test name
                    test_name = re.sub(r'\s+', ' ', test_name)
                    test_name = test_name.strip('.,()[]{}')
                    
                    # Only include if test name contains known test keywords
                    if not any(keyword in test_name.lower() for keyword in common_test_keywords):
                        continue
                    
                    # Skip if test name is too short or too long
                    if len(test_name) < 3 or len(test_name) > 40:
                        continue
                    
                    value = float(value_str)
                    
                    # Validate value range
                    if value < 0 or value > 50000:
                        continue
                    
                    result = {
                        'test_type': test_name.title(),
                        'value': value,
                        'unit': unit,
                        'reference_range': '',
                        'source': 'generic'
                    }
                    
                    results.append(result)
                    
                except (ValueError, IndexError, AttributeError):
                    continue
        
        return results
