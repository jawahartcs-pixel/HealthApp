import re
import io
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import pdfplumber
import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from docx import Document
import pandas as pd
import openpyxl
import xlrd
import xml.etree.ElementTree as ET
import csv
from investigation_standards import InvestigationStandards

class FileParser:
    def __init__(self):
        """Initialize the file parser with common blood test patterns."""
        # Initialize investigation standards for matching
        self.investigation_standards = InvestigationStandards()
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
        
        # Date patterns - prioritize DD-MM-YY format at document top
        self.date_patterns = [
            r'(?:date|test\s+date|report\s+date|collection\s+date)[:\-]?\s*(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{2,4})',
            r'(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{2})',  # DD-MM-YY or DD/MM/YY
            r'(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})',  # DD-MM-YYYY or DD/MM/YYYY
            r'(\d{2,4}[\-\/]\d{1,2}[\-\/]\d{1,2})'
        ]
        
        # Patient name patterns - prioritize Mr/Mrs at document top near "Name"
        self.patient_patterns = [
            r'(?:mr|mrs|ms|dr)\.?\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',  # Mr/Mrs prefix first
            r'Name\s*[:\-]?\s*(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]{2,50})',  # Name: Mr/Mrs
            r'Name\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Name: Capitalized words
            r'name\s*[:\-]?\s*(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]{2,50})',
            r'NAME\s*[:\-]?\s*(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]{2,50})',
            r'(?:patient|patient\s+name)[:\-]?\s*(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]+?)(?:\n|$|,)',
            r'Patient\s*[:\-]?\s*(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]{2,50})',
            r'Name\s*[:\-]?\s*([A-Za-z\s]{2,50})',
            r'name\s*[:\-]?\s*([A-Za-z\s]{2,50})',
            r'NAME\s*[:\-]?\s*([A-Za-z\s]{2,50})',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\n|$)',
        ]
        
        # Medical terminology validation set
        self.medical_terms = {
            'glucose', 'sugar', 'fasting_glucose', 'random_glucose', 'hba1c', 'hemoglobin_a1c',
            'cholesterol', 'hdl', 'ldl', 'triglycerides', 'hemoglobin', 'hematocrit', 
            'rbc', 'wbc', 'platelets', 'alt', 'ast', 'bilirubin', 'albumin', 'creatinine',
            'bun', 'egfr', 'tsh', 't3', 't4', 'sodium', 'potassium', 'chloride', 'calcium',
            'phosphorus', 'magnesium', 'uric_acid', 'protein', 'globulin', 'alkaline_phosphatase',
            'ggt', 'lactate_dehydrogenase', 'cpk', 'vitamin_d', 'vitamin_b12', 'folate',
            'iron', 'ferritin', 'transferrin', 'esr', 'crp', 'psa', 'insulin', 'cortisol'
        }
    
    def parse_file(self, uploaded_file, force_ocr: bool = False) -> str:
        """Parse uploaded file and extract text content."""
        try:
            if uploaded_file.type == "application/pdf":
                return self._parse_pdf(uploaded_file, force_ocr)
            elif uploaded_file.type == "text/plain":
                return self._parse_text(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._parse_docx(uploaded_file)
            elif uploaded_file.type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                return self._parse_excel(uploaded_file)
            elif uploaded_file.type == "text/csv":
                return self._parse_csv(uploaded_file)
            elif uploaded_file.type in ["application/xml", "text/xml"]:
                return self._parse_xml(uploaded_file)
            elif uploaded_file.type in ["image/jpeg", "image/jpg", "image/png", "image/bmp", "image/tiff"]:
                return self._parse_image(uploaded_file)
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
            
            # Store images for snippet extraction
            self.ocr_images = images
            
            ocr_text = ""
            # Store OCR data with positions for snippet extraction
            self.ocr_data = []
            
            for i, image in enumerate(images):
                # Use OCR to extract text with position data
                ocr_data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
                
                # Store OCR data for this page
                page_ocr_data = {
                    'page_num': i,
                    'image': image,
                    'text_data': ocr_data
                }
                self.ocr_data.append(page_ocr_data)
                
                # Extract text for the page
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
    
    def _parse_docx(self, uploaded_file) -> str:
        """Extract text from Word document."""
        try:
            uploaded_file.seek(0)
            doc = Document(uploaded_file)
            
            # Extract text from paragraphs
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_content.append(' | '.join(row_text))
            
            return '\n'.join(text_content)
        except Exception as e:
            raise Exception(f"Error reading Word document: {str(e)}")
    
    def _parse_excel(self, uploaded_file) -> str:
        """Extract text from Excel file."""
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Read Excel file using pandas
            df = pd.read_excel(uploaded_file, sheet_name=None, header=None)
            
            text = ""
            for sheet_name, sheet_data in df.items():
                text += f"\n--- SHEET: {sheet_name} ---\n"
                
                # Try to detect if this looks like a structured test results table
                if self._is_structured_test_data(sheet_data):
                    text += self._parse_structured_excel_data(sheet_data)
                else:
                    # Convert DataFrame to text representation
                    for index, row in sheet_data.iterrows():
                        row_text = " ".join([str(cell) for cell in row if pd.notna(cell)])
                        if row_text.strip():
                            text += row_text + "\n"
            
            return text
        except Exception as e:
            raise Exception(f"Error reading Excel file: {str(e)}")
    
    def _is_structured_test_data(self, df: pd.DataFrame) -> bool:
        """Check if Excel data appears to be structured test results."""
        try:
            # Convert all data to string and check for common patterns
            df_str = df.astype(str).str.lower()
            
            # Look for common medical test column headers
            medical_indicators = ['test', 'result', 'value', 'unit', 'reference', 'range', 'normal', 'patient', 'date']
            
            # Check first few rows for header-like content
            first_rows = df_str.head(3).values.flatten()
            
            matches = sum(1 for cell in first_rows if any(indicator in str(cell) for indicator in medical_indicators))
            
            return matches >= 2  # At least 2 medical indicators found
        except:
            return False
    
    def _parse_structured_excel_data(self, df: pd.DataFrame) -> str:
        """Parse structured Excel data (tables with headers)."""
        try:
            text = ""
            
            # Convert to string and find potential header row
            df_str = df.astype(str)
            
            # Look for header row (containing test, result, value, etc.)
            header_row = None
            for i, row in df_str.iterrows():
                row_lower = row.str.lower()
                if any(indicator in ' '.join(row_lower.values) for indicator in ['test', 'result', 'value']):
                    header_row = i
                    break
            
            if header_row is not None:
                # Extract headers
                headers = df_str.iloc[header_row].values
                text += f"Headers: {' | '.join(headers)}\n"
                
                # Extract data rows
                for i in range(header_row + 1, len(df_str)):
                    row = df_str.iloc[i]
                    if row.notna().any():  # Skip empty rows
                        row_data = []
                        for j, cell in enumerate(row.values):
                            if pd.notna(cell) and str(cell) != 'nan':
                                if j < len(headers):
                                    row_data.append(f"{headers[j]}: {cell}")
                                else:
                                    row_data.append(str(cell))
                        if row_data:
                            text += " | ".join(row_data) + "\n"
            else:
                # No clear header found, use standard parsing
                for index, row in df_str.iterrows():
                    row_text = " ".join([str(cell) for cell in row if pd.notna(cell) and str(cell) != 'nan'])
                    if row_text.strip():
                        text += row_text + "\n"
            
            return text
        except Exception as e:
            return str(e)
    
    def _parse_csv(self, uploaded_file) -> str:
        """Extract text from CSV file."""
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Read CSV file using pandas
            df = pd.read_csv(uploaded_file)
            
            text = ""
            
            # Check if this looks like structured test data
            if self._is_structured_test_data(df):
                # Add headers information
                text += f"Headers: {' | '.join(df.columns)}\n"
                
                # Format each row with column names
                for index, row in df.iterrows():
                    row_data = []
                    for col, value in row.items():
                        if pd.notna(value):
                            row_data.append(f"{col}: {value}")
                    if row_data:
                        text += " | ".join(row_data) + "\n"
            else:
                # Convert DataFrame to text representation
                for index, row in df.iterrows():
                    row_text = " ".join([str(cell) for cell in row if pd.notna(cell)])
                    if row_text.strip():
                        text += row_text + "\n"
            
            return text
        except Exception as e:
            raise Exception(f"Error reading CSV file: {str(e)}")
    
    def _parse_xml(self, uploaded_file) -> str:
        """Extract text from XML file."""
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Read XML content
            xml_content = uploaded_file.read()
            if isinstance(xml_content, bytes):
                xml_content = xml_content.decode('utf-8', errors='ignore')
            
            # Parse XML
            root = ET.fromstring(xml_content)
            
            text = ""
            
            # Look for structured medical data patterns
            medical_elements = ['test', 'result', 'value', 'patient', 'name', 'date', 'unit', 'reference']
            
            # Try to extract structured data first
            structured_data = self._extract_structured_xml_data(root, medical_elements)
            if structured_data:
                text += structured_data
            else:
                # Fallback to generic text extraction
                text += self._extract_generic_xml_text(root)
            
            return text
        except Exception as e:
            raise Exception(f"Error reading XML file: {str(e)}")
    
    def _extract_structured_xml_data(self, root, medical_elements: list) -> str:
        """Extract structured medical data from XML."""
        try:
            text = ""
            
            # Look for elements that contain medical data
            for elem in root.iter():
                if elem.tag.lower() in medical_elements:
                    if elem.text and elem.text.strip():
                        text += f"{elem.tag}: {elem.text.strip()}\n"
                    
                    # Check for attributes
                    for attr, value in elem.attrib.items():
                        if attr.lower() in medical_elements:
                            text += f"{attr}: {value}\n"
            
            # Also look for parent-child relationships that might represent test results
            test_results = []
            for elem in root.iter():
                if any(keyword in elem.tag.lower() for keyword in ['test', 'result', 'lab']):
                    result_data = {}
                    
                    # Extract child elements
                    for child in elem:
                        if child.text and child.text.strip():
                            result_data[child.tag] = child.text.strip()
                    
                    # Extract attributes
                    for attr, value in elem.attrib.items():
                        result_data[attr] = value
                    
                    if result_data:
                        test_results.append(result_data)
            
            # Format test results
            for result in test_results:
                result_text = " | ".join([f"{k}: {v}" for k, v in result.items()])
                if result_text:
                    text += result_text + "\n"
            
            return text if text.strip() else ""
        except:
            return ""
    
    def _extract_generic_xml_text(self, root) -> str:
        """Extract generic text from XML elements."""
        text = ""
        
        # Extract text from all elements
        for elem in root.iter():
            if elem.text and elem.text.strip():
                text += elem.text.strip() + "\n"
            if elem.tail and elem.tail.strip():
                text += elem.tail.strip() + "\n"
        
        return text
    
    def _parse_image(self, uploaded_file) -> str:
        """Extract text from image file using OCR."""
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Open image with PIL
            image = Image.open(uploaded_file)
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Configure tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6'
            
            # Extract text using OCR
            extracted_text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean and enhance OCR text
            enhanced_text = self._enhance_ocr_text(extracted_text)
            
            return enhanced_text
        except Exception as e:
            raise Exception(f"Error processing image with OCR: {str(e)}")
    
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
        """Extract patient name from text, prioritizing top of document."""
        # Focus on first 500 characters for patient name (document top)
        top_text = text[:500]
        
        for pattern in self.patient_patterns:
            match = re.search(pattern, top_text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)
                # Remove common prefixes that might be captured
                name = re.sub(r'^(mr|mrs|ms|dr)\.?\s+', '', name, flags=re.IGNORECASE)
                # Only return if it looks like a real name (2+ words, reasonable length)
                if len(name.split()) >= 2 and len(name) <= 50:
                    return name.title()  # Convert to title case
        
        # If not found in top, check full text
        for pattern in self.patient_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\s+', ' ', name)
                name = re.sub(r'^(mr|mrs|ms|dr)\.?\s+', '', name, flags=re.IGNORECASE)
                if len(name.split()) >= 2 and len(name) <= 50:
                    return name.title()  # Convert to title case
        
        return ""
    
    def _extract_test_date(self, text: str) -> Optional[date]:
        """Extract test date from text, prioritizing DD-MM-YY format at document top."""
        # Focus on first 500 characters for test date (document top)
        top_text = text[:500]
        
        # Try top text first
        for pattern in self.date_patterns:
            match = re.search(pattern, top_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try DD-MM-YY formats first (user preference)
                    date_formats = [
                        '%d-%m-%y', '%d/%m/%y',   # DD-MM-YY, DD/MM/YY
                        '%d-%m-%Y', '%d/%m/%Y',   # DD-MM-YYYY, DD/MM/YYYY
                        '%m-%d-%Y', '%m/%d/%Y',   # MM-DD-YYYY, MM/DD/YYYY
                        '%Y-%m-%d', '%Y/%m/%d'    # YYYY-MM-DD, YYYY/MM/DD
                    ]
                    
                    for date_format in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, date_format).date()
                            # Validate that the date is reasonable
                            if parsed_date <= date.today() and parsed_date.year >= 1900:
                                return parsed_date
                        except ValueError:
                            continue
                except:
                    continue
        
        # If not found in top, check full text
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    date_formats = [
                        '%d-%m-%y', '%d/%m/%y',   # DD-MM-YY, DD/MM/YY
                        '%d-%m-%Y', '%d/%m/%Y',   # DD-MM-YYYY, DD/MM/YYYY  
                        '%m-%d-%Y', '%m/%d/%Y',   # MM-DD-YYYY, MM/DD/YYYY
                        '%Y-%m-%d', '%Y/%m/%d'    # YYYY-MM-DD, YYYY/MM/DD
                    ]
                    
                    for date_format in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, date_format).date()
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
        
        # Add line-by-line analysis for structured extraction
        line_results = self._extract_line_by_line_results(text)
        results.extend(line_results)
        
        # Then use regex patterns for any missed results
        for test_name, pattern in self.test_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    value = float(match.group(1))
                    
                    # Get the display name for the test
                    display_name = self._get_display_name(test_name)
                    
                    # Try to match with investigation standards
                    standardized_name, matched_standard = self._standardize_test_with_unit(display_name, self.common_units.get(test_name, ''))
                    
                    result = {
                        'test_type': standardized_name,
                        'value': value,
                        'unit': matched_standard['male_unit'] if matched_standard else self.common_units.get(test_name, ''),
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
            # Validate against medical terminology first
            if not self._is_medical_terminology(result['test_type']):
                continue  # Skip non-medical terms
                
            test_name = result['test_type'].lower().strip()
            test_value = round(result['value'], 2)
            
            # Create key based on test name similarity
            test_key = re.sub(r'[^a-z0-9]', '', test_name)
            
            # Check for duplicates with similar test names
            is_duplicate = False
            for existing_key, existing_result in list(seen.items()):
                existing_name = re.sub(r'[^a-z0-9]', '', existing_key)
                
                # Enhanced duplicate detection for scanned documents
                # Check if test names are similar
                name_similarity = self._calculate_name_similarity(test_key, existing_name)
                
                if name_similarity > 0.7 and len(test_key) > 2:  # Similar test names
                    value_diff = abs(test_value - round(existing_result['value'], 2))
                    
                    # For scanned documents, be more lenient with value differences
                    # due to OCR errors that might cause slight variations
                    threshold = 0.5 if 'ocr' in result.get('source', '') else 0.1
                    
                    if value_diff < threshold:  # Values are close enough
                        # Choose the result with better source priority
                        current_priority = source_priority.get(result.get('source', 'regex'), 5)
                        existing_priority = source_priority.get(existing_result.get('source', 'regex'), 5)
                        
                        if current_priority < existing_priority:
                            # Current result has better source, replace existing
                            seen[existing_key] = result
                            unique_results = [r for r in unique_results if r != existing_result]
                            unique_results.append(result)
                        
                        is_duplicate = True
                        break
                
                # Also check for exact value matches with different test names (common OCR issue)
                elif abs(test_value - round(existing_result['value'], 2)) < 0.01:
                    # Same value, check if test names could be OCR variations
                    if self._could_be_ocr_variation(test_key, existing_name):
                        # Choose the result with better source or more complete name
                        current_priority = source_priority.get(result.get('source', 'regex'), 5)
                        existing_priority = source_priority.get(existing_result.get('source', 'regex'), 5)
                        
                        if current_priority < existing_priority or len(test_name) > len(existing_key):
                            seen[existing_key] = result
                            unique_results = [r for r in unique_results if r != existing_result]
                            unique_results.append(result)
                        
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                seen[test_name] = result
                unique_results.append(result)
        
        return unique_results
    
    def _is_medical_terminology(self, test_name: str) -> bool:
        """Check if test name is a valid medical terminology."""
        # Normalize test name for comparison
        normalized_name = test_name.lower().strip()
        normalized_name = re.sub(r'[^\w\s]', '', normalized_name)  # Remove special chars
        normalized_name = re.sub(r'\s+', '_', normalized_name)     # Replace spaces with underscore
        
        # Check direct match
        if normalized_name in self.medical_terms:
            return True
        
        # Check partial matches for common medical terms
        medical_keywords = {
            'glucose', 'cholesterol', 'hemoglobin', 'hematocrit', 'platelet', 'creatinine',
            'bilirubin', 'albumin', 'protein', 'sodium', 'potassium', 'calcium', 'iron',
            'vitamin', 'thyroid', 'liver', 'kidney', 'blood', 'serum', 'plasma',
            'urea', 'nitrogen', 'triglyceride', 'lymphocyte', 'neutrophil', 'eosinophil',
            'basophil', 'monocyte', 'erythrocyte', 'leukocyte', 'phosphorus', 'magnesium',
            'chloride', 'carbon', 'dioxide', 'bicarbonate', 'anion', 'osmolality',
            'immunoglobulin', 'antibody', 'antigen', 'enzyme', 'kinase', 'transferase',
            'dehydrogenase', 'phosphatase', 'globulin', 'ferritin', 'transferrin',
            'cortisol', 'insulin', 'hormone', 'testosterone', 'estradiol', 'progesterone',
            'prolactin', 'growth', 'follicle', 'luteinizing', 'alpha', 'beta', 'gamma'
        }
        
        for keyword in medical_keywords:
            if keyword in normalized_name:
                return True
        
        # Check for common medical abbreviations
        medical_abbrevs = {
            'hba1c', 'hdl', 'ldl', 'rbc', 'wbc', 'plt', 'alt', 'ast', 'bun', 'egfr',
            'tsh', 't3', 't4', 'psa', 'esr', 'crp', 'cpk', 'ggt', 'alp', 'ldh',
            'ck', 'ckmb', 'troponin', 'bnp', 'procalcitonin', 'inr', 'pt', 'ptt',
            'aptt', 'd_dimer', 'fibrinogen', 'fsh', 'lh', 'hcg', 'afp', 'cea',
            'ca125', 'ca199', 'pth', 'acth', 'cortisol', 'dhea', 'igf', 'rfp',
            'ana', 'anti_ccp', 'rf', 'complement', 'c3', 'c4', 'iga', 'igg', 'igm',
            'vldl', 'apoa', 'apob', 'lpa', 'homocysteine', 'folate', 'b12',
            'ferritin', 'tibc', 'transferrin', 'haptoglobin', 'reticulocyte',
            'mch', 'mchc', 'mcv', 'rdw', 'mpv', 'pdw', 'pct', 'neutrophils',
            'lymphocytes', 'monocytes', 'eosinophils', 'basophils'
        }
        
        if normalized_name in medical_abbrevs:
            return True
        
        return False
    
    def _looks_like_medical_test(self, test_name: str) -> bool:
        """Check if text looks like a medical test name based on structure."""
        if not test_name or len(test_name) < 2:
            return False
        
        # Convert to lowercase for analysis
        name = test_name.lower().strip()
        
        # Skip if it's just numbers or common non-medical words
        if name.isdigit():
            return False
        
        # Skip obvious non-medical terms
        non_medical_words = {
            'date', 'time', 'page', 'total', 'patient', 'doctor', 'address', 'phone',
            'email', 'signature', 'report', 'lab', 'number', 'id', 'code', 'barcode',
            'collected', 'received', 'printed', 'verified', 'reviewed'
        }
        
        if name in non_medical_words:
            return False
        
        # Look for medical-sounding patterns
        medical_patterns = [
            # Common medical suffixes
            r'(emia|uria|osis|itis|ase|ine|ogen|crit|globin|protein)$',
            # Common medical prefixes
            r'^(hemo|leuko|erythro|thyro|hepato|nephro|cardio|neuro)',
            # Medical measurement terms
            r'(count|level|rate|index|ratio|function|test|panel)',
            # Units or measurement indicators
            r'(total|free|bound|reactive|specific|direct|indirect)',
            # Common medical abbreviations pattern (2-5 uppercase letters)
            r'^[a-z]{2,5}$'
        ]
        
        for pattern in medical_patterns:
            if re.search(pattern, name):
                return True
        
        # Check if it contains multiple words that could be medical
        words = name.split()
        if len(words) >= 2:
            # More likely to be medical if it has descriptive words
            descriptive_words = {
                'blood', 'serum', 'plasma', 'urine', 'total', 'free', 'direct', 'indirect',
                'mean', 'average', 'high', 'low', 'density', 'cell', 'white', 'red',
                'complete', 'comprehensive', 'basic', 'panel', 'profile'
            }
            if any(word in descriptive_words for word in words):
                return True
        
        # Additional check for numeric components that might indicate test names
        if re.search(r'[a-z]+\s*\d+', name) or re.search(r'\d+\s*[a-z]+', name):
            return True
        
        return False
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two test names for duplicate detection."""
        if not name1 or not name2:
            return 0.0
        
        # Convert to lowercase for comparison
        name1, name2 = name1.lower(), name2.lower()
        
        # Exact match
        if name1 == name2:
            return 1.0
        
        # Check if one is contained in the other
        if name1 in name2 or name2 in name1:
            return 0.9
        
        # Calculate character overlap
        set1, set2 = set(name1), set(name2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # Boost similarity for common medical abbreviations
        medical_synonyms = {
            'glucose': ['glu', 'sugar', 'blood_sugar'],
            'cholesterol': ['chol', 'total_cholesterol'],
            'hemoglobin': ['hgb', 'hb'],
            'hematocrit': ['hct', 'pcv'],
            'platelets': ['plt', 'platelet_count'],
            'creatinine': ['creat', 'crea'],
            'triglycerides': ['tg', 'trig'],
            'bilirubin': ['bili', 'total_bilirubin'],
            'albumin': ['alb'],
            'protein': ['prot', 'total_protein']
        }
        
        for main_term, synonyms in medical_synonyms.items():
            if ((name1 == main_term and name2 in synonyms) or 
                (name2 == main_term and name1 in synonyms) or
                (name1 in synonyms and name2 in synonyms)):
                return 0.95
        
        return jaccard_similarity
    
    def _could_be_ocr_variation(self, name1: str, name2: str) -> bool:
        """Check if two test names could be OCR variations of the same test."""
        if not name1 or not name2:
            return False
        
        # Convert to lowercase for comparison
        name1, name2 = name1.lower(), name2.lower()
        
        # Common OCR character substitutions
        ocr_substitutions = {
            'o': ['0', 'c', 'e'],
            '0': ['o', 'c', 'e'],
            'i': ['l', '1', 'j'],
            'l': ['i', '1', 'j'],
            '1': ['i', 'l', 'j'],
            'rn': ['m'],
            'm': ['rn'],
            'cl': ['d'],
            'd': ['cl'],
            'vv': ['w'],
            'w': ['vv'],
            'n': ['h'],
            'h': ['n'],
            'a': ['o', 'e'],
            'e': ['c', 'o'],
            'c': ['e', 'o'],
            'u': ['n'],
            'g': ['q'],
            'q': ['g'],
            'b': ['6'],
            '6': ['b'],
            's': ['5'],
            '5': ['s']
        }
        
        # Check if names are similar with OCR substitutions
        def apply_ocr_substitutions(text):
            variations = [text]
            for original, substitutes in ocr_substitutions.items():
                new_variations = []
                for variation in variations:
                    new_variations.append(variation)
                    for substitute in substitutes:
                        if original in variation:
                            new_variations.append(variation.replace(original, substitute))
                variations = new_variations
            return set(variations)
        
        variations1 = apply_ocr_substitutions(name1)
        variations2 = apply_ocr_substitutions(name2)
        
        # Check if any variation of name1 matches any variation of name2
        return bool(variations1 & variations2) or name1 in variations2 or name2 in variations1
    
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
    
    def _clean_reference_range(self, ref_range: str) -> str:
        """Clean and format reference range text."""
        if not ref_range:
            return ''
        
        # Remove extra whitespace and common unwanted characters
        ref_range = re.sub(r'\s+', ' ', ref_range.strip())
        ref_range = ref_range.strip('.,;:|()[]{}')
        
        # Common reference range patterns to extract
        range_patterns = [
            # Numeric ranges like "5.0-15.0", "5.0 - 15.0", "5.0 to 15.0"
            r'(\d+(?:\.\d+)?)\s*(?:[-–to]|to)\s*(\d+(?:\.\d+)?)',
            # Ranges with units like "5.0-15.0 mg/dL"
            r'(\d+(?:\.\d+)?)\s*(?:[-–]|to)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]+)',
            # Less than patterns like "<10", "< 10"
            r'<\s*(\d+(?:\.\d+)?)',
            # Greater than patterns like ">5", "> 5"
            r'>\s*(\d+(?:\.\d+)?)',
            # Between patterns like "between 5 and 15"
            r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)',
            # Normal/reference patterns
            r'(?:normal|reference|ref)[\s\:]*(\d+(?:\.\d+)?)\s*(?:[-–]|to)\s*(\d+(?:\.\d+)?)',
        ]
        
        # Try to extract structured range information
        for pattern in range_patterns:
            match = re.search(pattern, ref_range, re.IGNORECASE)
            if match:
                if pattern.startswith(r'<'):
                    return f"< {match.group(1)}"
                elif pattern.startswith(r'>'):
                    return f"> {match.group(1)}"
                elif len(match.groups()) >= 2:
                    low_val = match.group(1)
                    high_val = match.group(2)
                    if len(match.groups()) >= 3 and match.group(3):
                        unit = match.group(3)
                        return f"{low_val} - {high_val} {unit}"
                    else:
                        return f"{low_val} - {high_val}"
        
        # If no structured pattern found, clean the text but keep it
        # Remove common noise words while preserving meaningful content
        noise_words = ['normal', 'reference', 'ref', 'range', 'values', 'level', 'levels']
        words = ref_range.split()
        cleaned_words = []
        
        for word in words:
            if word.lower() not in noise_words and len(word) > 1:
                cleaned_words.append(word)
        
        cleaned_range = ' '.join(cleaned_words)
        
        # Return cleaned range if it looks meaningful, otherwise empty
        if len(cleaned_range) > 2 and not cleaned_range.isspace():
            return cleaned_range[:50]  # Limit length
        
        return ''
    
    def _extract_reference_range_from_line(self, line_remainder: str) -> str:
        """Extract reference range from the remainder of a line."""
        if not line_remainder:
            return ''
        
        # Look for common reference range patterns in the remainder
        ref_patterns = [
            # Parentheses: (5.0-15.0)
            r'\(([^)]+)\)',
            # Brackets: [5.0-15.0]
            r'\[([^\]]+)\]',
            # Reference/Normal: Reference: 5.0-15.0, Normal: 5.0-15.0
            r'(?:reference|normal|ref|range)[\s\:]*([^\s]+(?:\s*[-–]\s*[^\s]+)?)',
            # Range patterns: 5.0-15.0, 5.0 - 15.0, 5.0 to 15.0
            r'(\d+(?:\.\d+)?\s*[-–to]\s*\d+(?:\.\d+)?)',
            # Less than/greater than: <10, >5, ≤10, ≥5
            r'([<>≤≥]\s*\d+(?:\.\d+)?)',
            # Range with units: 5.0-15.0 mg/dL
            r'(\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*[a-zA-Z\/\%\^µμmM]+)',
            # Additional patterns for medical ranges
            r'(\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*[a-zA-Z\/]*)',
            # Up to patterns: up to 10
            r'(?:up\s+to|upto)\s+(\d+(?:\.\d+)?)',
            # Below patterns: below 5
            r'(?:below|under)\s+(\d+(?:\.\d+)?)',
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, line_remainder, re.IGNORECASE)
            if match:
                return self._clean_reference_range(match.group(1))
        
        return ''
    
    def _extract_tabular_results(self, text: str) -> List[Dict[str, Any]]:
        """Extract test results from tabular format commonly found in lab reports."""
        results = []
        
        # Enhanced tabular patterns to capture test results with reference ranges
        tabular_patterns = [
            # Tab-separated values with reference range
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^µμmM]*)\s+([^\n\r\t]*)',
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\t+(\d+(?:\.\d+)?)\t*([a-zA-Z\/\%\^µμmM]*)\t*([^\n\r\t]*)',
            # Multiple spaces with reference range
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s{3,}(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Pattern with vertical bars/pipes capturing reference range
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s*[\|]\s*(\d+(?:\.\d+)?)\s*[\|]?\s*([a-zA-Z\/\%\^µμmM]*)\s*[\|]?\s*([^\n\r]*)',
            # Pattern with colons and reference range
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?):\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Pattern specifically for reference ranges in parentheses after value
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*\(([^)]+)\)',
            # Pattern for reference ranges with "Normal" or "Ref" keywords
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*(?:normal|ref|reference)[\s\:]*([^\n\r]*)',
            # Pattern for ranges like "Test Name 10.5 mg/dL (5.0-15.0)"
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*\(([0-9\.\-\s]+)\)',
            # Pattern for scientific notation with reference range
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*([^\n\r]*)',
            # Pattern for ranges following the value on same line
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*[\-\–]\s*(\d+(?:\.\d+)?\s*[\-\–]\s*\d+(?:\.\d+)?.*?)(?:\n|\r|$)',
            # Pattern for reference range with brackets
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*\[([^\]]+)\]',
            # Generic pattern for any additional text after unit (likely reference range)
            r'([a-zA-Z][a-zA-Z\s\(\)\/\-\.]+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s+([^\n\r]+)',
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
                    
                    # Be more lenient - use medical terminology check instead of strict filtering
                    if not self._is_medical_terminology(test_name) and not self._looks_like_medical_test(test_name):
                        continue
                    
                    value = float(value_str)
                    
                    # Validate value range
                    if value < 0 or value > 100000:
                        continue
                    
                    # Clean and enhance reference range
                    ref_range = self._clean_reference_range(ref_range)
                    
                    # Try to match with investigation standards
                    standardized_name, matched_standard = self._standardize_test_with_unit(test_name, unit)
                    
                    result = {
                        'test_type': standardized_name,
                        'value': value,
                        'unit': matched_standard['male_unit'] if matched_standard else unit,
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
                        
                        # Try to extract reference range from the remainder of line
                        remainder = line[match.end():].strip()
                        ref_range = self._extract_reference_range_from_line(remainder)
                        
                        # If no range found in remainder, try looking in the entire line
                        if not ref_range:
                            ref_range = self._extract_reference_range_from_line(line)
                        
                        result = {
                            'test_type': test_name.title(),
                            'value': value,
                            'unit': unit,
                            'reference_range': ref_range,
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
                    
                    # Try to match with investigation standards
                    standardized_name, matched_standard = self._standardize_test_with_unit(test_name, unit)
                    
                    result = {
                        'test_type': standardized_name,
                        'value': value,
                        'unit': matched_standard['male_unit'] if matched_standard else unit,
                        'source': 'ocr_pattern'
                    }
                    
                    # Check for duplicates within OCR results to reduce noise
                    is_duplicate = False
                    for existing_result in results:
                        if (self._calculate_name_similarity(test_name.lower(), existing_result['test_type'].lower()) > 0.8 and 
                            abs(value - existing_result['value']) < 0.5):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        results.append(result)
                    
                except (ValueError, IndexError, AttributeError):
                    continue
        
        return results
    
    def _extract_line_by_line_results(self, text: str) -> List[Dict[str, Any]]:
        """Extract test results by analyzing each line for patterns."""
        results = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:  # Skip short lines
                continue
            
            # Look for patterns like "Test Name 123.45 mg/dL 50-150"
            line_patterns = [
                # Pattern: Test Name Value Unit Reference
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.\,\d]{3,50}?)\s+(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^µμmM]+)\s+([^\s].*?)$',
                # Pattern: Test Name Value Unit
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.\,\d]{3,50}?)\s+(\d+(?:\.\d+)?)\s+([a-zA-Z\/\%\^µμmM]+)\s*$',
                # Pattern: Test Name Value (no unit)
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.\,\d]{3,50}?)\s+(\d+(?:\.\d+)?)\s*$',
                # Pattern with separators: Test Name | Value | Unit | Reference
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.\,\d]{3,50}?)\s*[\|\t]\s*(\d+(?:\.\d+)?)\s*[\|\t]?\s*([a-zA-Z\/\%\^µμmM]*)\s*[\|\t]?\s*([^\s].*?)\s*$',
                # Pattern with colon: Test Name: Value Unit
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.\,\d]{3,50}?):\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*(.*)$',
                # Pattern with multiple spaces as separator
                r'^([a-zA-Z][a-zA-Z\s\(\)\/\-\.\,\d]{3,40}?)\s{3,}(\d+(?:\.\d+)?)\s*([a-zA-Z\/\%\^µμmM]*)\s*(.*)$',
            ]
            
            for pattern in line_patterns:
                match = re.match(pattern, line)
                if match:
                    try:
                        test_name = match.group(1).strip()
                        value_str = match.group(2).strip()
                        unit = match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else ''
                        ref_range = match.group(4).strip() if len(match.groups()) > 3 and match.group(4) else ''
                        
                        # Clean up test name
                        test_name = re.sub(r'\s+', ' ', test_name).strip('.,()[]{}:=-')
                        
                        # Skip if not medical terminology
                        if not self._is_medical_terminology(test_name) and not self._looks_like_medical_test(test_name):
                            continue
                        
                        # Skip if test name is too short
                        if len(test_name) < 3:
                            continue
                        
                        value = float(value_str)
                        
                        # Validate value range
                        if value < 0 or value > 1000000:
                            continue
                        
                        # Try to match with investigation standards
                        standardized_name, matched_standard = self._standardize_test_with_unit(test_name, unit)
                        
                        result = {
                            'test_type': standardized_name,
                            'value': value,
                            'unit': matched_standard['male_unit'] if matched_standard else unit,
                            'source': 'line_analysis'
                        }
                        
                        results.append(result)
                        break  # Found a match for this line, move to next line
                        
                    except (ValueError, IndexError):
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
                    
                    # Be more lenient - check if it's medical terminology but don't require specific keywords
                    if not self._is_medical_terminology(test_name):
                        # Also allow if it looks like a medical test (has certain characteristics)
                        if not self._looks_like_medical_test(test_name):
                            continue
                    
                    # Skip if test name is too short or too long
                    if len(test_name) < 3 or len(test_name) > 40:
                        continue
                    
                    value = float(value_str)
                    
                    # Validate value range
                    if value < 0 or value > 50000:
                        continue
                    
                    # Try to match with investigation standards
                    standardized_name, matched_standard = self._standardize_test_with_unit(test_name, unit)
                    
                    result = {
                        'test_type': standardized_name,
                        'value': value,
                        'unit': matched_standard['male_unit'] if matched_standard else unit,
                        'source': 'generic'
                    }
                    
                    results.append(result)
                    
                except (ValueError, IndexError, AttributeError):
                    continue
        
        return results
    
    def _standardize_test_with_unit(self, test_name: str, extracted_unit: str = '') -> tuple:
        """Standardize test name using investigation standards and get proper unit."""
        # Find best match from investigation standards
        match = self.investigation_standards.find_best_match(test_name, threshold=0.6)
        
        if match:
            # Use the standardized name and unit from the standards
            standardized_name = match['standard_name']
            return standardized_name, match
        else:
            # No match found, use original name but clean it
            cleaned_name = test_name.title().strip()
            return cleaned_name, None
