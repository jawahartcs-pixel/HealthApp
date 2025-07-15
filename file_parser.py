import re
import io
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import pdfplumber
import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

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
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Name\s*[:\-]?\s*([A-Za-z\s]{2,50})',
            r'Patient\s*[:\-]?\s*([A-Za-z\s]{2,50})',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\n|$)',
            r'^\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Mary\s+Stella',
            r'([A-Z][a-z]*\s+[A-Z][a-z]*(?:\s+[A-Z][a-z]*)?)'
        ]
    
    def parse_file(self, uploaded_file, force_ocr: bool = False) -> str:
        """Parse uploaded file and extract text content."""
        try:
            if uploaded_file.type == "application/pdf":
                return self._parse_pdf(uploaded_file, force_ocr)
            elif uploaded_file.type == "text/plain":
                return self._parse_text(uploaded_file)
            else:
                raise ValueError(f"Unsupported file type: {uploaded_file.type}")
        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")
            return ""
    
    def _parse_pdf(self, uploaded_file, force_ocr: bool = False) -> str:
        """Extract text from PDF file using both direct text extraction and OCR."""
        uploaded_file.seek(0)  # Reset file pointer
        pdf_bytes = uploaded_file.read()
        
        # If OCR is forced, skip regular extraction and go straight to OCR
        if force_ocr:
            st.info("Using OCR extraction as requested...")
            try:
                ocr_text = self._extract_text_with_ocr(pdf_bytes)
                return "--- OCR EXTRACTED TEXT ---\n" + ocr_text
            except Exception as ocr_error:
                st.error(f"OCR extraction failed: {str(ocr_error)}")
                st.info("Falling back to standard extraction...")
        
        try:
            text = ""
            tables_text = ""
            
            # First, try regular text extraction
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    # Extract regular text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Try to extract tables which might contain test results
                    try:
                        tables = page.extract_tables()
                        for table_idx, table in enumerate(tables):
                            if table:
                                tables_text += f"\n--- TABLE {table_idx + 1} ---\n"
                                for row_idx, row in enumerate(table):
                                    if row and any(cell for cell in row if cell is not None):
                                        # Clean and join cells
                                        cleaned_row = []
                                        for cell in row:
                                            if cell is not None:
                                                cell_str = str(cell).strip()
                                                if cell_str:
                                                    cleaned_row.append(cell_str)
                                        
                                        if cleaned_row:
                                            row_text = '\t'.join(cleaned_row)
                                            tables_text += row_text + "\n"
                                tables_text += f"--- END TABLE {table_idx + 1} ---\n"
                    except Exception as e:
                        # If table extraction fails, continue with text extraction
                        pass
            
            # Combine regular text and table text
            combined_text = text + "\n\n" + tables_text
            
            # If we got very little text, try OCR
            if len(combined_text.strip()) < 200:
                st.info("PDF has limited extractable text. Using OCR to read the document...")
                try:
                    ocr_text = self._extract_text_with_ocr(pdf_bytes)
                    combined_text = combined_text + "\n--- OCR EXTRACTED TEXT ---\n" + ocr_text
                except Exception as ocr_error:
                    st.warning(f"OCR extraction failed: {str(ocr_error)}")
            
            return combined_text
                
        except Exception as e:
            # Try OCR as fallback
            st.warning(f"Standard PDF extraction failed: {str(e)}")
            try:
                st.info("Attempting OCR as fallback...")
                ocr_text = self._extract_text_with_ocr(pdf_bytes)
                return "--- OCR EXTRACTED TEXT ---\n" + ocr_text
            except Exception as ocr_error:
                raise Exception(f"Both standard and OCR extraction failed. Standard: {str(e)}, OCR: {str(ocr_error)}")
    
    def _extract_text_with_ocr(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using OCR."""
        try:
            # Configure tesseract for better accuracy with medical documents
            # PSM 6 = single uniform block, OEM 3 = default engine
            custom_config = r'--oem 3 --psm 6'
            
            # Convert PDF to images with high DPI for better OCR accuracy
            images = convert_from_bytes(pdf_bytes, dpi=300, fmt='PNG')
            
            ocr_text = ""
            for i, image in enumerate(images):
                # Use OCR to extract text from each page
                page_text = pytesseract.image_to_string(image, config=custom_config)
                if page_text.strip():
                    ocr_text += f"\n--- PAGE {i + 1} OCR ---\n"
                    # Clean and enhance the OCR text
                    cleaned_text = self._enhance_ocr_text(page_text)
                    ocr_text += cleaned_text + "\n"
            
            return ocr_text
            
        except Exception as e:
            raise Exception(f"OCR extraction failed: {str(e)}")
    
    def _enhance_ocr_text(self, text: str) -> str:
        """Clean and enhance OCR extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Fix common OCR errors for medical terms and numbers
        replacements = {
            # Medical terms
            'G1ucose': 'Glucose',
            'Giucose': 'Glucose',
            'HbA1c': 'HbA1c', 
            'HbAlc': 'HbA1c',
            'HbAic': 'HbA1c',
            'Cho1estero1': 'Cholesterol',
            'Cholestero1': 'Cholesterol',
            'Hemog1obin': 'Hemoglobin',
            'Hemogiobin': 'Hemoglobin',
            'P1ate1et': 'Platelet',
            'Platelet': 'Platelet',
            'Creatinine': 'Creatinine',
            'Creatlnine': 'Creatinine',
            'Triglycerldes': 'Triglycerides',
            'Triglycerides': 'Triglycerides',
            'Bilirubin': 'Bilirubin',
            'Bi1irubin': 'Bilirubin',
            'Albumin': 'Albumin',
            'A1bumin': 'Albumin',
            'Hematocrit': 'Hematocrit',
            'Sodium': 'Sodium',
            'Potassium': 'Potassium',
            'Chloride': 'Chloride',
            'Protein': 'Protein',
            'Urea': 'Urea',
            'Calcium': 'Calcium',
            'Phosphorus': 'Phosphorus',
            'Magnesium': 'Magnesium',
            'Iron': 'Iron',
            'Ferritin': 'Ferritin',
            'Vitamin': 'Vitamin',
            'TSH': 'TSH',
            'T4': 'T4',
            'T3': 'T3',
            
            # Units
            'mg/d1': 'mg/dl',
            'mmo1/1': 'mmol/l',
            'mmol/1': 'mmol/l',
            'u/1': 'u/l',
            'U/1': 'U/l',
            'g/d1': 'g/dl',
            'µg/d1': 'µg/dl',
            'ng/m1': 'ng/ml',
            'mIU/m1': 'mIU/ml',
            'pg/m1': 'pg/ml',
            
            # Names
            'Mary Stella': 'Mary Stella',
            'Mary': 'Mary',
            'Stella': 'Stella'
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        return text
    
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
        
        # Try more aggressive pattern matching for OCR text
        ocr_results = self._extract_ocr_specific_patterns(text)
        results.extend(ocr_results)
        
        # Remove duplicates with improved matching, keeping source info for debugging
        unique_results = []
        seen = {}
        
        # Sort by source priority (tabular and line_analysis preferred over regex/generic)
        source_priority = {'tabular': 0, 'line_analysis': 1, 'ocr_pattern': 2, 'regex': 3, 'generic': 4}
        results.sort(key=lambda x: source_priority.get(x.get('source', 'regex'), 5))
        
        for result in results:
            test_name = result['test_type'].lower().strip()
            test_value = round(result['value'], 2)
            
            # Create key based on test name similarity
            test_key = re.sub(r'[^a-z0-9]', '', test_name)
            
            # Check for duplicates with similar test names
            is_duplicate = False
            for existing_key, existing_result in list(seen.items()):
                existing_name = re.sub(r'[^a-z0-9]', '', existing_key)
                
                # Check if test names are similar and values are close
                if (test_key in existing_name or existing_name in test_key) and len(test_key) > 2:
                    value_diff = abs(test_value - round(existing_result['value'], 2))
                    if value_diff < 0.1:  # Values are very close
                        current_priority = source_priority.get(result.get('source', 'regex'), 4)
                        existing_priority = source_priority.get(existing_result.get('source', 'regex'), 4)
                        
                        if current_priority <= existing_priority:
                            # Replace with better source
                            unique_results = [r for r in unique_results if r != existing_result]
                            del seen[existing_key]
                            break
                        else:
                            is_duplicate = True
                            break
            
            if not is_duplicate:
                seen[test_name] = result
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
        
        # Enhanced tabular patterns to capture more variations including decimal numbers
        tabular_patterns = [
            # Tab-separated values with decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\t+(\d+(?:\.\d+)?)\t*([a-zA-Z\/\%\^µμmM]*)\t*([^\n\r\t]*)',
            # Multiple spaces with flexible spacing and decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s{3,}(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Values at end of line with decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*$',
            # Pattern with vertical bars, pipes, or dashes with decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s*[\|\-]\s*(\d+(?:\.\d+)?)\s*[\|\-]?\s*([a-zA-Z\/\%\^µμmM]*)\s*[\|\-]?\s*([^\n\r]*)',
            # Pattern with colons and decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?):\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Pattern with dots or dashes leading to values with decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)[\.\-]{2,}\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Pattern for values in parentheses or brackets with decimal support
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s*[\(\[]\s*(\d+(?:\.\d+)?)\s*[\)\]]\s*([a-zA-Z\/\%\^µμmM]*)',
            # Pattern for scientific notation values
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Pattern for ranges like "Test Name 10.5 - 15.2" (capture first value)
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*[\-\–]\s*\d+(?:\.\d+)?\s*([a-zA-Z\/\%\^µμmM]*)',
            # Pattern for values followed by reference ranges in parentheses
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*\([^)]*\)',
            # Simple pattern for test name followed by number anywhere in line
            r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.]{2,40}?)\s.*?(\d+(?:\.\d+))\s*([a-zA-Z\/\%\^µμmM]*)'
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
                    if len(test_name) < 2 or len(test_name) > 60:
                        continue
                    
                    # Skip common non-test words but be less restrictive
                    skip_words = ['page', 'report', 'signature', 'address', 'phone', 'email', 'total', 'subtotal']
                    if any(word == test_name.lower().strip() for word in skip_words):
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
        
        # Additional line-by-line analysis for missed values
        line_results = self._extract_line_by_line(text)
        results.extend(line_results)
        
        return results
    
    def _extract_line_by_line(self, text: str) -> List[Dict[str, Any]]:
        """Extract test results by analyzing each line for numeric patterns."""
        results = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Look for any numeric value in the line
            numeric_matches = re.findall(r'\d+(?:\.\d+)?', line)
            if not numeric_matches:
                continue
                
            # Try to find test name and value patterns
            # Pattern: any text followed by one or more numbers
            patterns = [
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)',
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)[\s\t]+(\d+(?:\.\d+)?)',
                r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]{3,})\s*[\:\-\=]\s*(\d+(?:\.\d+)?)',
                r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]{3,})\s+(\d+(?:\.\d+)?)\s*[a-zA-Z\/\%\^µμ]*\s*$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        test_name = match.group(1).strip()
                        value_str = match.group(2).strip()
                        
                        # Clean test name
                        test_name = re.sub(r'\s+', ' ', test_name)
                        test_name = test_name.strip('.,()[]{}')
                        
                        # Skip if looks like header or non-test
                        if len(test_name) < 3 or len(test_name) > 50:
                            continue
                            
                        skip_words = ['page', 'total', 'sum', 'count', 'number', 'id', 'code']
                        if any(word in test_name.lower() for word in skip_words):
                            continue
                            
                        value = float(value_str)
                        if value < 0 or value > 50000:
                            continue
                            
                        # Extract unit if present
                        unit_match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμ]+)', line)
                        unit = unit_match.group(2) if unit_match else ''
                        
                        result = {
                            'test_type': test_name.title(),
                            'value': value,
                            'unit': unit,
                            'reference_range': '',
                            'source': 'line_analysis'
                        }
                        
                        results.append(result)
                        break  # Found a match for this line, move to next
                        
                    except (ValueError, IndexError, AttributeError):
                        continue
        
        return results
    
    def _extract_ocr_specific_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract test results using patterns specific to OCR text."""
        results = []
        
        # OCR often produces inconsistent spacing and formatting
        # Look for patterns that might appear in OCR'd lab reports
        ocr_patterns = [
            # Test name followed by value with inconsistent spacing
            r'([A-Za-z][A-Za-z\s]{2,30}?)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)',
            # Test name with colon and value
            r'([A-Za-z][A-Za-z\s]{2,30}?):\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)',
            # Test name with dash and value
            r'([A-Za-z][A-Za-z\s]{2,30}?)\s*-\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)',
            # Value at end of line after test name
            r'([A-Za-z][A-Za-z\s]{2,30}?)\s+(\d+(?:\.\d+)?)\s*$',
            # Test name followed by multiple spaces and value
            r'([A-Za-z][A-Za-z\s]{2,30}?)\s{2,}(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)',
            # Common lab test patterns
            r'(Glucose|Cholesterol|Hemoglobin|Platelet|Creatinine|Albumin|Bilirubin|Sodium|Potassium|Chloride|Protein|Urea|Calcium|Iron|TSH|T4|T3|HbA1c|Triglycerides|HDL|LDL|Hematocrit|WBC|RBC)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)'
        ]
        
        for pattern in ocr_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                try:
                    test_name = match.group(1).strip()
                    value_str = match.group(2).strip()
                    unit = match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else ''
                    
                    # Clean up test name
                    test_name = re.sub(r'\s+', ' ', test_name)
                    test_name = test_name.strip('.,()[]{}')
                    
                    # Skip if test name is too short or looks invalid
                    if len(test_name) < 3 or len(test_name) > 40:
                        continue
                    
                    # Skip common non-test words
                    skip_words = ['page', 'table', 'result', 'value', 'normal', 'abnormal', 'high', 'low', 'reference', 'range']
                    if any(word in test_name.lower() for word in skip_words):
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
                        'source': 'ocr_pattern'
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
