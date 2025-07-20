import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from database import Database
from file_parser import FileParser
from data_processor import DataProcessor
from visualization import Visualization
from alert_system import AlertSystem
from auth_system import AuthSystem
from auth_ui import AuthUI
from anomaly_detection import AnomalyDetector
from utils import validate_date, format_test_value
from image_snippet_extractor import ImageSnippetExtractor
from investigation_standards import InvestigationStandards
from pdf2image import convert_from_bytes
from PIL import Image
import tempfile
import io

# Initialize database and components
@st.cache_resource
def init_database():
    return Database()

@st.cache_resource
def init_components():
    db = init_database()
    file_parser = FileParser()
    data_processor = DataProcessor(db)
    visualization = Visualization(db)
    alert_system = AlertSystem(db)
    auth_system = AuthSystem()
    auth_ui = AuthUI(auth_system)
    anomaly_detector = AnomalyDetector(db)
    investigation_standards = InvestigationStandards()
    return db, file_parser, data_processor, visualization, alert_system, auth_system, auth_ui, anomaly_detector, investigation_standards

def main():
    st.set_page_config(
        page_title="Blood Test Results Management",
        page_icon="🩸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🩸 Blood Test Results Management")
    st.markdown("Upload, manage, and visualize patient blood test results")
    
    # Initialize components
    db, file_parser, data_processor, visualization, alert_system, auth_system, auth_ui, anomaly_detector, investigation_standards = init_components()
    
    # Store investigation_standards in session state for access in upload page
    st.session_state['investigation_standards'] = investigation_standards
    
    # Check authentication
    if not auth_ui.check_authentication():
        auth_ui.login_page()
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Display user info in sidebar
    auth_ui.sidebar_user_info()
    
    # Page selection
    pages = ["Upload Results", "View Patients", "Patient Dashboard", "Search & Filter", "Export Data", "Manage Data", "Alert Dashboard", "AI Anomaly Detection", "Investigation Standards"]
    
    # Add profile page for logged-in users
    if st.session_state.get('user_id'):
        pages.append("Profile")
    
    page = st.sidebar.selectbox("Select Page", pages)
    
    # Get current user ID
    current_user_id = st.session_state.get('user_id')
    
    if page == "Upload Results":
        upload_results_page(file_parser, data_processor, current_user_id)
    elif page == "View Patients":
        view_patients_page(db, alert_system, current_user_id)
    elif page == "Patient Dashboard":
        patient_dashboard_page(db, visualization, alert_system, current_user_id)
    elif page == "Search & Filter":
        search_filter_page(db, visualization, current_user_id)
    elif page == "Export Data":
        export_data_page(db, current_user_id)
    elif page == "Manage Data":
        manage_data_page(db, current_user_id)
    elif page == "Alert Dashboard":
        alert_dashboard_page(alert_system, current_user_id)
    elif page == "AI Anomaly Detection":
        ai_anomaly_detection_page(anomaly_detector, current_user_id)
    elif page == "Investigation Standards":
        investigation_standards_page(investigation_standards)
    elif page == "Profile":
        auth_ui.user_profile_page()

def upload_results_page(file_parser, data_processor, user_id):
    st.header("📁 Upload Blood Test Results")
    
    def _get_test_context(full_text, result):
        """Get surrounding context for a specific test result from the document."""
        test_name = result['test_type'].lower()
        test_value = str(result['value'])
        text_lower = full_text.lower()
        
        # Try to find the test name in the text
        name_pos = text_lower.find(test_name)
        if name_pos == -1:
            # Try partial matches or common variations
            name_parts = test_name.split()
            for part in name_parts:
                if len(part) > 3:  # Only search for meaningful parts
                    name_pos = text_lower.find(part)
                    if name_pos != -1:
                        break
        
        # If we found the test name, get surrounding context
        if name_pos != -1:
            # Get 100 characters before and after the test name
            start = max(0, name_pos - 100)
            end = min(len(full_text), name_pos + len(test_name) + 100)
            context = full_text[start:end].strip()
            
            # Clean up the context
            context = ' '.join(context.split())  # Remove extra whitespace
            
            # Highlight the test name and value if found
            if test_value in context:
                context = context.replace(test_value, f"➤ {test_value} ⬅")
            
            return context[:300] + "..." if len(context) > 300 else context
        
        # If test name not found, try to find the value
        value_pos = full_text.find(test_value)
        if value_pos != -1:
            start = max(0, value_pos - 50)
            end = min(len(full_text), value_pos + len(test_value) + 50)
            context = full_text[start:end].strip()
            context = ' '.join(context.split())
            context = context.replace(test_value, f"➤ {test_value} ⬅")
            return context[:200] + "..." if len(context) > 200 else context
        
        return f"Could not locate '{test_name}' in document text"
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose blood test result files",
        type=['pdf', 'txt', 'docx', 'xlsx', 'xls', 'csv', 'xml', 'jpg', 'jpeg', 'png', 'bmp', 'tiff'],
        accept_multiple_files=True,
        help="Upload PDF, Word (.docx), Excel (.xlsx, .xls), CSV, XML, text files, or images (JPG, PNG, BMP, TIFF) containing blood test results"
    )
    
    # Option to force OCR for difficult PDFs
    force_ocr = st.checkbox(
        "Force OCR extraction",
        help="Use OCR (Optical Character Recognition) for image files and scanned documents. This automatically processes images and can help extract text from problematic PDFs."
    )
    
    # Clear cache button for reprocessing
    if st.button("🔄 Clear Cache & Reprocess Files", help="Clear cached extraction results and reprocess all files"):
        # Clear all extraction cache
        keys_to_remove = [key for key in st.session_state.keys() if key.startswith('extraction_')]
        for key in keys_to_remove:
            del st.session_state[key]
        st.rerun()
    
    if uploaded_files:
        st.subheader("Processing Files")
        
        for uploaded_file in uploaded_files:
            with st.expander(f"Processing: {uploaded_file.name}", expanded=True):
                try:
                    # Cache extraction results to prevent reprocessing on form changes
                    cache_key = f"extraction_{uploaded_file.name}_{uploaded_file.size}_{force_ocr}"
                    
                    # Always initialize these for consistent access
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    if cache_key not in st.session_state:
                        # Show processing status during initial extraction
                        status_text.text("Reading file...")
                        progress_bar.progress(25)
                        
                        # Parse file
                        extracted_text = file_parser.parse_file(uploaded_file, force_ocr)
                        
                        status_text.text("Extracting test data...")
                        progress_bar.progress(50)
                        
                        # Extract test data
                        test_data = file_parser.extract_test_data(extracted_text)
                        
                        # Initialize image snippet extractor for OCR documents
                        snippet_extractor = None
                        if uploaded_file.type == "application/pdf" and ("OCR" in extracted_text or force_ocr):
                            snippet_extractor = ImageSnippetExtractor()
                            uploaded_file.seek(0)
                            pdf_bytes = uploaded_file.read()
                            snippet_extractor.process_pdf_for_snippets(pdf_bytes)
                        
                        # Cache the results
                        st.session_state[cache_key] = {
                            'extracted_text': extracted_text,
                            'test_data': test_data,
                            'snippet_extractor': snippet_extractor
                        }
                        
                        status_text.text("Extraction complete!")
                        progress_bar.progress(100)
                    else:
                        # Use cached results
                        status_text.text("ℹ️ Using cached extraction results (no reprocessing needed)")
                        progress_bar.progress(100)
                        cached_data = st.session_state[cache_key]
                        extracted_text = cached_data['extracted_text']
                        test_data = cached_data['test_data']
                        snippet_extractor = cached_data['snippet_extractor']
                    
                    # Check if we have any results - continue processing even if none found
                    has_extracted_results = test_data and test_data.get('results')
                    
                    # Initialize num_additional early to avoid scope issues
                    num_additional = 0
                    
                    if not has_extracted_results:
                        st.warning("No blood test data automatically detected in the file")
                        st.info("💡 Now trying standards-based extraction...")
                        
                        # Try standards-based extraction even when no original results
                        investigation_standards = st.session_state.get('investigation_standards')
                        if investigation_standards and extracted_text:
                            standards_results = file_parser.scan_text_against_standards(extracted_text, investigation_standards)
                            
                            if standards_results:
                                # Create two-column layout for Excel table and document preview
                                col1, col2 = st.columns([1.2, 0.8])
                                
                                with col1:
                                    st.success(f"Found {len(standards_results)} tests using standards-based extraction!")
                                    st.subheader("📊 Standards-Based Extraction Results")
                                    
                                    # Create DataFrame for Excel-like display
                                    df_data = []
                                    seen_investigations = set()
                                    for i, result in enumerate(standards_results):
                                        investigation_name = result['test_type']
                                        # Only enable Include for first occurrence of each investigation
                                        is_first_occurrence = investigation_name not in seen_investigations
                                        seen_investigations.add(investigation_name)
                                        
                                        df_data.append({
                                            'Include': is_first_occurrence,
                                            'Investigation': result['test_type'],
                                            'Value': result['value'],
                                            'Unit': result['unit'],
                                            'Reference Range': result['reference_range'],
                                            'Category': result.get('category', ''),
                                            'Matched Term': result.get('matched_term', ''),
                                        })
                                    
                                    # Display editable dataframe
                                    if df_data:
                                        df = pd.DataFrame(df_data)
                                        
                                        # Configure column editor
                                        column_config = {
                                            'Include': st.column_config.CheckboxColumn(
                                                'Include',
                                                help='Check to include this test in results',
                                                default=True
                                            ),
                                            'Investigation': st.column_config.TextColumn(
                                                'Investigation Type',
                                                help='Standardized investigation name',
                                                width='medium'
                                            ),
                                            'Value': st.column_config.NumberColumn(
                                                'Value',
                                                help='Test result value',
                                                format='%.2f',
                                                width='small'
                                            ),
                                            'Unit': st.column_config.TextColumn(
                                                'Unit',
                                                help='Measurement unit',
                                                width='small'
                                            ),
                                            'Reference Range': st.column_config.TextColumn(
                                                'Reference Range',
                                                help='Normal range for this test',
                                                width='medium'
                                            ),
                                            'Category': st.column_config.TextColumn(
                                                'Category',
                                                help='Test category',
                                                width='small'
                                            ),
                                            'Matched Term': st.column_config.TextColumn(
                                                'Matched Term',
                                                help='Document term that matched',
                                                width='small'
                                            )
                                        }
                                        
                                        # Store the editable results
                                        edited_df = st.data_editor(
                                            df,
                                            column_config=column_config,
                                            use_container_width=True,
                                            num_rows="dynamic",
                                            key=f"standards_results_no_original_{uploaded_file.name}",
                                            height=400
                                        )
                                        
                                        # Store edited results in session state for saving
                                        st.session_state[f'standards_extracted_{uploaded_file.name}'] = edited_df
                                        
                                        # Show summary and save button
                                        included_count = len(edited_df[edited_df['Include'] == True])
                                        st.caption(f"Ready to save: {included_count} tests selected")
                                        
                                        # Save button for standards-based results (no original results case)
                                        if st.button("💾 Save Standards-Based Results", key=f"save_standards_no_orig_{uploaded_file.name}", type="primary"):
                                            if patient_name:
                                                with st.spinner("Saving standards-based results..."):
                                                    # Convert edited dataframe to test results
                                                    standards_final_results = []
                                                    for _, row in edited_df.iterrows():
                                                        if row['Include']:
                                                            standards_final_results.append({
                                                                'test_type': row['Investigation'],
                                                                'value': row['Value'],
                                                                'unit': row['Unit'],
                                                                'reference_range': row['Reference Range']
                                                            })
                                                    
                                                    # Save using data processor
                                                    success = data_processor.save_test_results(
                                                        patient_name=patient_name,
                                                        test_date=test_date,
                                                        test_results=standards_final_results,
                                                        user_id=user_id
                                                    )
                                                    
                                                    if success:
                                                        st.success(f"Successfully saved {len(standards_final_results)} standards-based test results for {patient_name}")
                                                    else:
                                                        st.error("Failed to save standards-based test results to database")
                                            else:
                                                st.warning("Please enter a patient name to save results")
                                
                                with col2:
                                    st.subheader("📄 Document Preview")
                                    with st.expander("📖 View Original Document Content", expanded=True):
                                        # Display file type and size
                                        file_size = len(uploaded_file.getvalue())
                                        st.caption(f"File: {uploaded_file.name} | Size: {file_size:,} bytes | Type: {uploaded_file.type}")
                                        
                                        # Show extracted text in a scrollable container
                                        if extracted_text:
                                            # Limit text length for display
                                            display_text = extracted_text[:3000] + "\n\n... (text truncated for display)" if len(extracted_text) > 3000 else extracted_text
                                            
                                            st.text_area(
                                                "Extracted Document Text",
                                                value=display_text,
                                                height=400,
                                                help="This is the text extracted from your document. Compare with the parsed results below to verify accuracy.",
                                                label_visibility="collapsed"
                                            )
                                        else:
                                            st.warning("No text could be extracted from this document.")
                                
                                # Set flag to show save button
                                has_extracted_results = True
                                
                            else:
                                st.warning("No tests found even with standards-based extraction")
                                st.info("💡 You can manually add test results using the section below")
                                # Show extracted text for debugging
                                with st.expander("Debug: Show extracted text"):
                                    st.text_area("Extracted text", extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text, height=200)
                        else:
                            st.warning("Investigation standards not available")
                            # Show extracted text for debugging
                            with st.expander("Debug: Show extracted text"):
                                st.text_area("Extracted text", extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text, height=200)
                    
                    status_text.text("Processing patient information...")
                    progress_bar.progress(75)
                    
                    # Preview and edit extracted data before saving
                    st.subheader("Preview Extracted Data")
                    
                    # Patient information section
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        patient_name = st.text_input(
                            f"Patient Name for {uploaded_file.name}",
                            value=test_data.get('patient_name', ''),
                            key=f"name_{uploaded_file.name}",
                            help="Edit the patient name if needed"
                        )
                    
                    with col2:
                        test_date = st.date_input(
                            f"Test Date for {uploaded_file.name}",
                            value=test_data.get('test_date', date.today()),
                            key=f"date_{uploaded_file.name}",
                            help="Edit the test date if needed"
                        )
                    

                    
                    # Test results preview and editing
                    if has_extracted_results:
                        # Create two-column layout for Excel table and document preview
                        col1, col2 = st.columns([1.2, 0.8])
                        
                        with col1:
                            st.subheader("📊 Standards-Based Extraction Results")
                            
                            # Scan document text against investigation standards
                            investigation_standards = st.session_state.get('investigation_standards')
                            if investigation_standards and extracted_text:
                                standards_results = file_parser.scan_text_against_standards(extracted_text, investigation_standards)
                                
                                if standards_results:
                                    st.success(f"Found {len(standards_results)} tests matching investigation standards")
                                    
                                    # Create DataFrame for Excel-like display
                                    df_data = []
                                    seen_investigations = set()
                                    for i, result in enumerate(standards_results):
                                        investigation_name = result['test_type']
                                        # Only enable Include for first occurrence of each investigation
                                        is_first_occurrence = investigation_name not in seen_investigations
                                        seen_investigations.add(investigation_name)
                                        
                                        df_data.append({
                                            'Include': is_first_occurrence,
                                            'Investigation': result['test_type'],
                                            'Value': result['value'],
                                            'Unit': result['unit'],
                                            'Reference Range': result['reference_range'],
                                            'Category': result.get('category', ''),
                                            'Matched Term': result.get('matched_term', ''),
                                        })
                                    
                                    # Display editable dataframe
                                    if df_data:
                                        df = pd.DataFrame(df_data)
                                        
                                        # Configure column editor
                                        column_config = {
                                            'Include': st.column_config.CheckboxColumn(
                                                'Include',
                                                help='Check to include this test in results',
                                                default=True
                                            ),
                                            'Investigation': st.column_config.TextColumn(
                                                'Investigation Type',
                                                help='Standardized investigation name',
                                                width='medium'
                                            ),
                                            'Value': st.column_config.NumberColumn(
                                                'Value',
                                                help='Test result value',
                                                format='%.2f',
                                                width='small'
                                            ),
                                            'Unit': st.column_config.TextColumn(
                                                'Unit',
                                                help='Measurement unit',
                                                width='small'
                                            ),
                                            'Reference Range': st.column_config.TextColumn(
                                                'Reference Range',
                                                help='Normal range for this test',
                                                width='medium'
                                            ),
                                            'Category': st.column_config.TextColumn(
                                                'Category',
                                                help='Test category',
                                                width='small'
                                            ),
                                            'Matched Term': st.column_config.TextColumn(
                                                'Matched Term',
                                                help='Document term that matched',
                                                width='small'
                                            )
                                        }
                                        
                                        # Store the editable results
                                        edited_df = st.data_editor(
                                            df,
                                            column_config=column_config,
                                            use_container_width=True,
                                            num_rows="dynamic",
                                            key=f"standards_results_{uploaded_file.name}",
                                            height=400
                                        )
                                        
                                        # Store edited results in session state for saving
                                        st.session_state[f'standards_extracted_{uploaded_file.name}'] = edited_df
                                        
                                        # Show summary and save button
                                        included_count = len(edited_df[edited_df['Include'] == True])
                                        st.caption(f"Ready to save: {included_count} tests selected")
                                        
                                        # Don't show original extraction when standards-based works
                                        st.session_state[f'show_original_extraction_{uploaded_file.name}'] = False
                                        
                                        # Save button for standards-based results
                                        if st.button("💾 Save Standards-Based Results", key=f"save_standards_{uploaded_file.name}", type="primary"):
                                            if patient_name:
                                                with st.spinner("Saving standards-based results..."):
                                                    # Convert edited dataframe to test results
                                                    standards_final_results = []
                                                    for _, row in edited_df.iterrows():
                                                        if row['Include']:
                                                            standards_final_results.append({
                                                                'test_type': row['Investigation'],
                                                                'value': row['Value'],
                                                                'unit': row['Unit'],
                                                                'reference_range': row['Reference Range']
                                                            })
                                                    
                                                    # Save using data processor
                                                    success = data_processor.save_test_results(
                                                        patient_name=patient_name,
                                                        test_date=test_date,
                                                        test_results=standards_final_results,
                                                        user_id=user_id
                                                    )
                                                    
                                                    if success:
                                                        st.success(f"Successfully saved {len(standards_final_results)} standards-based test results for {patient_name}")
                                                    else:
                                                        st.error("Failed to save standards-based test results to database")
                                            else:
                                                st.warning("Please enter a patient name to save results")
                                        
                                else:
                                    st.warning("No tests found matching investigation standards")
                                    st.info("💡 Try using the original extraction results below or add tests manually")
                                    # Set flag to show original extraction when standards-based fails
                                    st.session_state[f'show_original_extraction_{uploaded_file.name}'] = True
                            else:
                                st.warning("Investigation standards not available or no text extracted")
                                # Set flag to show original extraction when standards not available
                                st.session_state[f'show_original_extraction_{uploaded_file.name}'] = True
                            
                            # Only show original extraction results when standards-based extraction fails or finds no results
                            if test_data.get('results') and st.session_state.get(f'show_original_extraction_{uploaded_file.name}', False):
                                with st.expander(f"📋 Original Extraction Results ({len(test_data['results'])} tests found)", expanded=False):
                                    st.write("Review and edit the originally extracted test results:")
                        
                        with col2:
                            st.subheader("📄 Document Preview")
                            with st.expander("📖 View Original Document Content", expanded=True):
                                # Display file type and size
                                file_size = len(uploaded_file.getvalue())
                                st.caption(f"File: {uploaded_file.name} | Size: {file_size:,} bytes | Type: {uploaded_file.type}")
                                
                                # Show extracted text in a scrollable container
                                if extracted_text:
                                    # Limit text length for display
                                    display_text = extracted_text[:3000] + "\n\n... (text truncated for display)" if len(extracted_text) > 3000 else extracted_text
                                    
                                    st.text_area(
                                        "Extracted Document Text",
                                        value=display_text,
                                        height=400,
                                        help="This is the text extracted from your document. Compare with the parsed results below to verify accuracy.",
                                        label_visibility="collapsed"
                                    )
                                    
                                    # Add search functionality for better comparison
                                    search_term = st.text_input(
                                        "🔍 Search in document",
                                        placeholder="Enter test name or value to highlight in document",
                                        key=f"search_{uploaded_file.name}"
                                    )
                                    
                                    if search_term:
                                        # Count occurrences of search term
                                        occurrences = extracted_text.lower().count(search_term.lower())
                                        if occurrences > 0:
                                            st.success(f"Found '{search_term}' {occurrences} time(s) in the document")
                                        else:
                                            st.warning(f"'{search_term}' not found in the document")
                                    
                                    # Show extraction method used
                                    if hasattr(test_data, 'extraction_method'):
                                        st.caption(f"Extraction method: {test_data.get('extraction_method', 'Standard')}")
                                    
                                    # Show full text length info
                                    st.caption(f"Total extracted text: {len(extracted_text):,} characters")
                                else:
                                    st.warning("No text could be extracted from this document.")
                        
                        # Create form for editing - full width below the preview
                        st.markdown("---")  # Separator line
                        
                        # Initialize save_clicked to avoid UnboundLocalError
                        save_clicked = False
                        
                        # Only show original extraction editing interface when standards-based extraction is not available
                        if test_data.get('results') and st.session_state.get(f'show_original_extraction_{uploaded_file.name}', False):
                            # Quick search buttons for extracted tests (outside form)
                            st.write("**Quick Search in Document:**")
                            search_cols = st.columns(min(len(test_data['results']), 6))  # Max 6 buttons per row
                            for i, result in enumerate(test_data['results'][:6]):  # Show first 6 tests
                                with search_cols[i]:
                                    if st.button(f"🔍 {result['test_type'][:10]}{'...' if len(result['test_type']) > 10 else ''}", 
                                               key=f"quick_search_{uploaded_file.name}_{i}",
                                               help=f"Search for '{result['test_type']}' in document"):
                                        st.session_state[f"search_{uploaded_file.name}"] = result['test_type']
                                        st.rerun()
                            
                            if len(test_data['results']) > 6:
                                st.caption(f"Showing first 6 of {len(test_data['results'])} tests")
                        
                            with st.form(key=f"edit_results_{uploaded_file.name}"):
                                st.write("**Review & Edit Extracted Tests:**")
                                st.caption("💡 Left side shows original extracted data, right side allows editing before saving")
                                
                                for i, result in enumerate(test_data['results']):
                                    # Get context text for this specific test
                                    test_context = _get_test_context(extracted_text, result)
                                    
                                    # Create expandable section for each test
                                    with st.expander(f"Test {i+1}: {result['test_type']} = {result['value']} {result.get('unit', '')}", expanded=True):
                                        left_col, right_col = st.columns([1, 1])
                                        
                                        # Left side - Original extracted data (read-only display)
                                        with left_col:
                                            st.markdown("**📄 Original Extracted Data:**")
                                        
                                        # Show image snippet for OCR documents
                                        if snippet_extractor:
                                            snippet_bytes = snippet_extractor.get_image_snippet_for_test(
                                                result['test_type'], str(result['value'])
                                            )
                                            if snippet_bytes:
                                                st.image(snippet_bytes, caption=f"Document snippet for {result['test_type']}", use_container_width=True)
                                            else:
                                                st.caption("📷 No image snippet available for this test")
                                        
                                        # Show context from document
                                        if test_context and "Could not locate" not in test_context:
                                            st.info(f"**Context from document:**\n{test_context}")
                                        
                                        # Show original values in a clean format
                                        st.code(f"""Investigation: {result['test_type']}
Value: {result['value']}
Unit: {result.get('unit', 'Not specified')}
Reference Range: {result.get('reference_range', 'Not specified')}
Extraction Method: {result.get('source', 'regex')}""")
                                    
                                    # Right side - Editable fields
                                    with right_col:
                                        st.markdown("**✏️ Edit Before Saving:**")
                                        
                                        # Editable investigation type with standardization dropdown
                                        investigation_standards = st.session_state.get('investigation_standards')
                                        if investigation_standards:
                                            # Get all standard names
                                            all_standards = investigation_standards.get_all_standards()
                                            standard_names = [std['standard_name'] for std in all_standards]
                                            
                                            # Try to find fuzzy match for current test type (including unit)
                                            standardized_name, match_info = investigation_standards.standardize_test_name(result['test_type'], result.get('unit', ''))
                                            
                                            # Create the options list with option to use the text input
                                            options = ["(Use custom text below)"] + standard_names
                                            
                                            # Determine default selection - if fuzzy match found, select it
                                            if standardized_name in standard_names:
                                                default_index = standard_names.index(standardized_name) + 1  # +1 because of custom option at index 0
                                                # Show match information if fuzzy match was found
                                                if match_info and standardized_name != result['test_type']:
                                                    match_score = match_info.get('match_score', 0)
                                                    st.info(f"🔍 Fuzzy match found: '{result['test_type']}' → '{standardized_name}' (score: {match_score:.2f})")
                                            else:
                                                default_index = 0  # Select custom text option by default
                                            
                                            selected_option = st.selectbox(
                                                "Investigation Type",
                                                options=options,
                                                index=default_index,
                                                key=f"test_dropdown_{uploaded_file.name}_{i}",
                                                help="Choose a standard investigation type or use custom text below"
                                            )
                                            
                                            # Always show the custom text input with extracted text
                                            # Always populate with original extracted text
                                            final_test_name = st.text_input(
                                                "Custom Investigation Type",
                                                value=result['test_type'],  # Always show extracted text
                                                key=f"test_name_{uploaded_file.name}_{i}",
                                                help="Original extracted text - edit if needed"
                                            )
                                            

                                            
                                        else:
                                            # Fallback to text input if standards not available
                                            final_test_name = st.text_input(
                                                "Investigation Type",
                                                value=result['test_type'],
                                                key=f"test_name_{uploaded_file.name}_{i}",
                                                help="Edit the test name if needed"
                                            )

                                        
                                        # Editable value
                                        st.number_input(
                                            "Value",
                                            value=float(result['value']),
                                            key=f"test_value_{uploaded_file.name}_{i}",
                                            format="%.2f",
                                            help="Edit the test value if needed"
                                        )
                                        
                                        # Editable unit
                                        st.text_input(
                                            "Unit",
                                            value=result.get('unit', ''),
                                            key=f"test_unit_{uploaded_file.name}_{i}",
                                            help="Edit the unit if needed"
                                        )
                                        
                                        # Editable reference range
                                        st.text_input(
                                            "Reference Range",
                                            value=result.get('reference_range', ''),
                                            key=f"test_ref_range_{uploaded_file.name}_{i}",
                                            help="Edit the reference range if needed"
                                        )
                                        
                                        # Include checkbox
                                        st.checkbox(
                                            "Include this test in results",
                                            value=True,
                                            key=f"include_{uploaded_file.name}_{i}",
                                            help="Uncheck to exclude this test from being saved"
                                        )
                            

                            
                            # Show additional tests section if any are requested
                            if num_additional > 0:
                                st.write("**Additional Tests (not scanned):**")
                                st.caption("Fill in the fields below for tests not automatically detected in the document")
                                
                            # Additional test inputs
                            if num_additional > 0:
                                for i in range(num_additional):
                                    col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 1, 1])
                                    
                                    with col1:
                                        # Investigation type dropdown for additional tests
                                        investigation_standards = st.session_state.get('investigation_standards')
                                        if investigation_standards:
                                            # Get all standard names
                                            all_standards = investigation_standards.get_all_standards()
                                            standard_names = [std['standard_name'] for std in all_standards]
                                            
                                            # Add option for custom entry at the top
                                            options = ["(Use custom text below)"] + standard_names
                                            
                                            selected_option = st.selectbox(
                                                f"Standard Type {i+1}",
                                                options=options,
                                                key=f"add_test_dropdown_{uploaded_file.name}_{i}",
                                                label_visibility="collapsed",
                                                help="Choose a standard or use custom text below"
                                            )
                                            
                                            # Always show custom text input
                                            st.text_input(
                                                f"Custom Type {i+1}",
                                                key=f"add_test_name_{uploaded_file.name}_{i}",
                                                label_visibility="collapsed",
                                                placeholder="Enter investigation type"
                                            )
                                            

                                                
                                        else:
                                            # Fallback to text input if standards not available
                                            st.text_input(
                                                f"Additional Test {i+1}",
                                                key=f"add_test_name_{uploaded_file.name}_{i}",
                                                label_visibility="collapsed",
                                                placeholder="Enter investigation type"
                                            )

                                    
                                    with col2:
                                        st.number_input(
                                            f"Additional Value {i+1}",
                                            value=0.0,
                                            key=f"add_test_value_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            format="%.2f"
                                        )
                                    
                                    with col3:
                                        st.text_input(
                                            f"Additional Unit {i+1}",
                                            key=f"add_test_unit_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            placeholder="mg/dl, g/dl, etc."
                                        )
                                    
                                    with col4:
                                        st.text_input(
                                            f"Additional Ref Range {i+1}",
                                            key=f"add_test_ref_range_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            placeholder="5.0-15.0"
                                        )
                                    
                                    with col5:
                                        st.checkbox(
                                            f"Add {i+1}",
                                            value=True,
                                            key=f"add_include_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed"
                                        )
                                    
                                    with col6:
                                        # Empty column to maintain layout
                                        st.write("")
                            
                                # Save button
                                save_clicked = st.form_submit_button("💾 Save Results", type="primary")
                        
                        if save_clicked and patient_name:
                            with st.spinner("Saving results..."):
                                status_text.text("Saving to database...")
                                progress_bar.progress(90)
                                
                                # Get final edited results from extracted tests
                                final_results = []
                                for i, result in enumerate(test_data['results']):
                                    if st.session_state.get(f"include_{uploaded_file.name}_{i}", True):
                                        # Determine which test type to use based on user selection
                                        dropdown_selection = st.session_state.get(f"test_dropdown_{uploaded_file.name}_{i}", "(Use custom text below)")
                                        custom_text_value = st.session_state.get(f"test_name_{uploaded_file.name}_{i}", result['test_type'])
                                        
                                        if dropdown_selection == "(Use custom text below)":
                                            # User chose to use custom text - ignore fuzzy match, use custom input
                                            final_test_type = custom_text_value
                                        else:
                                            # User selected a standard from dropdown - use that standard
                                            final_test_type = dropdown_selection
                                        
                                        final_results.append({
                                            'test_type': final_test_type,
                                            'value': st.session_state.get(f"test_value_{uploaded_file.name}_{i}", result['value']),
                                            'unit': st.session_state.get(f"test_unit_{uploaded_file.name}_{i}", result.get('unit', '')),
                                            'reference_range': st.session_state.get(f"test_ref_range_{uploaded_file.name}_{i}", result.get('reference_range', ''))
                                        })
                                
                                # Add additional manual tests
                                num_additional = st.session_state.get(f"num_additional_{uploaded_file.name}", 0)
                                additional_count = 0
                                
                                if num_additional > 0:
                                    for i in range(num_additional):
                                        if st.session_state.get(f"add_include_{uploaded_file.name}_{i}", True):
                                            # Determine which test type to use for additional tests
                                            add_dropdown_selection = st.session_state.get(f"add_test_dropdown_{uploaded_file.name}_{i}", "(Use custom text below)")
                                            
                                            if add_dropdown_selection == "(Use custom text below)":
                                                # User chose to use custom text - use custom input
                                                test_name = st.session_state.get(f"add_test_name_{uploaded_file.name}_{i}", "").strip()
                                            else:
                                                # User selected a standard from dropdown - use that standard
                                                test_name = add_dropdown_selection
                                            
                                            test_value = st.session_state.get(f"add_test_value_{uploaded_file.name}_{i}", 0.0)
                                            test_unit = st.session_state.get(f"add_test_unit_{uploaded_file.name}_{i}", "").strip()
                                            test_ref_range = st.session_state.get(f"add_test_ref_range_{uploaded_file.name}_{i}", "").strip()
                                            
                                            # Only add if test name is provided and value is not zero
                                            if test_name and test_value != 0.0:
                                                final_results.append({
                                                    'test_type': test_name,
                                                    'value': test_value,
                                                    'unit': test_unit,
                                                    'reference_range': test_ref_range
                                                })
                                                additional_count += 1
                                
                                # Save all results using the form values
                                success = data_processor.save_test_results(
                                    patient_name=patient_name,
                                    test_date=test_date,
                                    test_results=final_results,
                                    user_id=user_id
                                )
                                
                                progress_bar.progress(100)
                                
                                if success:
                                    status_text.text("✅ Successfully processed!")
                                    extracted_count = len([r for i, r in enumerate(test_data['results']) if st.session_state.get(f"include_{uploaded_file.name}_{i}", True)])
                                    st.success(f"Successfully saved {len(final_results)} test results for {patient_name}")
                                    st.info(f"Extracted: {extracted_count} tests, Additional: {additional_count} tests")
                                    
                                    # Show extraction debug info
                                    with st.expander("Debug: Extraction details"):
                                        extraction_methods = {}
                                        for result in test_data['results']:
                                            method = result.get('source', 'regex')
                                            extraction_methods[method] = extraction_methods.get(method, 0) + 1
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.write("**Tests extracted by method:**")
                                            for method, count in extraction_methods.items():
                                                st.write(f"- {method.title()}: {count} tests")
                                        
                                        with col2:
                                            st.write("**All original extracted values:**")
                                            for i, result in enumerate(test_data['results'], 1):
                                                source = result.get('source', 'regex')
                                                unit = result.get('unit', '')
                                                unit_text = f" {unit}" if unit else ""
                                                st.write(f"{i}. {result['test_type']}: {result['value']}{unit_text} ({source})")
                                        
                                        # Add text preview for debugging
                                        with st.expander("Raw extracted text (first 2000 chars)"):
                                            debug_text = file_parser.parse_file(uploaded_file, force_ocr)
                                            st.text(debug_text[:2000] + "..." if len(debug_text) > 2000 else debug_text)
                                else:
                                    status_text.text("❌ Failed to save")
                                    st.error("Failed to save test results to database")
                        elif save_clicked and not patient_name:
                            st.warning("Please enter a patient name to save results")
                    else:
                        # No extracted results - show manual entry form only
                        with st.form(key=f"manual_results_{uploaded_file.name}"):
                            st.write("**Manual Test Entry:**")
                            st.caption("No tests were automatically detected. Add tests manually below.")
                            
                            # Get the current number of additional tests from session state
                            current_num_additional = st.session_state.get(f"num_additional_{uploaded_file.name}", 0)
                            
                            # Show additional tests section if any are requested
                            if current_num_additional > 0:
                                st.write("**Manual Tests:**")
                                st.caption("Fill in the fields below for tests to add to the database")
                                
                            # Additional test inputs
                            if current_num_additional > 0:
                                for i in range(current_num_additional):
                                    col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 1, 1])
                                    
                                    with col1:
                                        # Investigation type dropdown for additional tests
                                        investigation_standards = st.session_state.get('investigation_standards')
                                        if investigation_standards:
                                            # Get all standard names
                                            all_standards = investigation_standards.get_all_standards()
                                            standard_names = [std['standard_name'] for std in all_standards]
                                            
                                            # Add option for custom entry at the top
                                            options = ["(Use custom text below)"] + standard_names
                                            
                                            selected_option = st.selectbox(
                                                f"Standard Type {i+1}",
                                                options=options,
                                                key=f"add_test_dropdown_{uploaded_file.name}_{i}",
                                                label_visibility="collapsed",
                                                help="Choose a standard or use custom text below"
                                            )
                                            
                                            # Always show custom text input
                                            st.text_input(
                                                f"Custom Type {i+1}",
                                                key=f"add_test_name_{uploaded_file.name}_{i}",
                                                label_visibility="collapsed",
                                                placeholder="Enter investigation type"
                                            )
                                        else:
                                            # Fallback to text input if standards not available
                                            st.text_input(
                                                f"Manual Test {i+1}",
                                                key=f"add_test_name_{uploaded_file.name}_{i}",
                                                label_visibility="collapsed",
                                                placeholder="Enter investigation type"
                                            )
                                    
                                    with col2:
                                        st.number_input(
                                            f"Value {i+1}",
                                            value=0.0,
                                            key=f"add_test_value_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            format="%.2f"
                                        )
                                    
                                    with col3:
                                        st.text_input(
                                            f"Unit {i+1}",
                                            key=f"add_test_unit_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            placeholder="mg/dl, g/dl, etc."
                                        )
                                    
                                    with col4:
                                        st.text_input(
                                            f"Ref Range {i+1}",
                                            key=f"add_test_ref_range_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            placeholder="5.0-15.0"
                                        )
                                    
                                    with col5:
                                        st.checkbox(
                                            f"Add {i+1}",
                                            value=True,
                                            key=f"add_include_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed"
                                        )
                                    
                                    with col6:
                                        st.write("")
                            
                            # Save button for manual entry
                            save_manual_clicked = st.form_submit_button("💾 Save Manual Tests", type="primary")
                        
                        if save_manual_clicked and patient_name:
                            with st.spinner("Saving manual tests..."):
                                # Process only additional manual tests
                                final_results = []
                                manual_num_additional = st.session_state.get(f"num_additional_{uploaded_file.name}", 0)
                                additional_count = 0
                                
                                if manual_num_additional > 0:
                                    for i in range(manual_num_additional):
                                        if st.session_state.get(f"add_include_{uploaded_file.name}_{i}", True):
                                            # Determine which test type to use for additional tests
                                            add_dropdown_selection = st.session_state.get(f"add_test_dropdown_{uploaded_file.name}_{i}", "(Use custom text below)")
                                            
                                            if add_dropdown_selection == "(Use custom text below)":
                                                test_name = st.session_state.get(f"add_test_name_{uploaded_file.name}_{i}", "").strip()
                                            else:
                                                test_name = add_dropdown_selection
                                            
                                            test_value = st.session_state.get(f"add_test_value_{uploaded_file.name}_{i}", 0.0)
                                            test_unit = st.session_state.get(f"add_test_unit_{uploaded_file.name}_{i}", "").strip()
                                            test_ref_range = st.session_state.get(f"add_test_ref_range_{uploaded_file.name}_{i}", "").strip()
                                            
                                            # Only add if test name is provided and value is not zero
                                            if test_name and test_value != 0.0:
                                                final_results.append({
                                                    'test_type': test_name,
                                                    'value': test_value,
                                                    'unit': test_unit,
                                                    'reference_range': test_ref_range
                                                })
                                                additional_count += 1
                                
                                if final_results:
                                    # Save manual results
                                    success = data_processor.save_test_results(
                                        patient_name=patient_name,
                                        test_date=test_date,
                                        test_results=final_results,
                                        user_id=user_id
                                    )
                                    
                                    if success:
                                        st.success(f"Successfully saved {len(final_results)} manual test results for {patient_name}")
                                    else:
                                        st.error("Failed to save manual test results to database")
                                else:
                                    st.warning("No valid manual tests to save. Please enter test names and non-zero values.")
                        
                        elif save_manual_clicked and not patient_name:
                            st.warning("Please enter a patient name to save results")
                    
                    # Manual test entry section - always shown at bottom
                    st.divider()
                    
                    # Display full document for reference with highlighting
                    st.markdown("### 📄 Document Reference")
                    st.caption("Full document image with highlighted extracted data - green boxes show already extracted tests")
                    
                    # Get extracted test names for highlighting
                    extracted_test_names = []
                    if has_extracted_results and test_data.get('results'):
                        extracted_test_names = [result.get('test_type', '') for result in test_data['results']]
                    
                    try:
                        # Use ImageSnippetExtractor for highlighting
                        snippet_extractor = ImageSnippetExtractor()
                        
                        if uploaded_file.type.startswith('image'):
                            # For image files, display with highlighting
                            highlighted_image = snippet_extractor.highlight_text_in_image(
                                uploaded_file, extracted_test_names
                            )
                            if highlighted_image:
                                st.image(highlighted_image, caption=f"Full Document: {uploaded_file.name} (Green boxes = extracted tests)", use_container_width=True)
                            else:
                                # Fallback to original image
                                st.image(uploaded_file, caption=f"Full Document: {uploaded_file.name}", use_container_width=True)
                        
                        elif uploaded_file.type == 'application/pdf':
                            # For PDF files, use the snippet extractor directly
                            highlighted_image = snippet_extractor.highlight_text_in_image(
                                uploaded_file, extracted_test_names
                            )
                            
                            if highlighted_image:
                                st.image(highlighted_image, caption=f"Document: {uploaded_file.name} (Green boxes = extracted tests)", use_container_width=True)
                            else:
                                # Fallback to convert and display without highlighting
                                pdf_bytes = uploaded_file.getvalue()
                                images = convert_from_bytes(pdf_bytes, dpi=300, fmt='PNG')
                                if images:
                                    for i, image in enumerate(images):
                                        st.image(image, caption=f"Page {i+1} of {uploaded_file.name}", use_container_width=True)
                        
                        else:
                            # For other file types, show text content with highlighting
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_file.flush()
                                
                                try:
                                    if uploaded_file.name.lower().endswith(('.docx', '.doc')):
                                        st.info(f"Document type: {uploaded_file.type}")
                                        st.markdown("**Full document text extracted for reference:**")
                                        
                                        # Extract text for Word documents
                                        if uploaded_file.name.lower().endswith('.docx'):
                                            from docx import Document
                                            doc = Document(tmp_file.name)
                                            full_text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                                            
                                            # Highlight extracted test names in the text
                                            highlighted_text = full_text
                                            for test_name in extracted_test_names:
                                                if test_name and len(test_name) > 2:
                                                    highlighted_text = highlighted_text.replace(
                                                        test_name, f"🟢 **{test_name}** 🟢"
                                                    )
                                            
                                            st.markdown("**Extracted tests are highlighted with 🟢 markers:**")
                                            st.text_area("Document Content", value=highlighted_text, height=300, disabled=True)
                                        else:
                                            st.info("Word document format detected - text extraction available")
                                    else:
                                        st.info(f"Document format: {uploaded_file.type} - showing available content")
                                
                                finally:
                                    os.unlink(tmp_file.name)
                        
                        # Show summary of extracted vs remaining tests
                        if extracted_test_names:
                            st.success(f"✅ {len(extracted_test_names)} tests already extracted: {', '.join(extracted_test_names[:3])}{'...' if len(extracted_test_names) > 3 else ''}")
                            st.info("💡 Look for test results in the document that are NOT highlighted in green - these need to be added manually")
                        else:
                            st.info("⚠️ No tests were automatically extracted - you'll need to add all test results manually")
                                    
                    except Exception as e:
                        st.warning(f"Could not display document preview with highlighting: {str(e)}")
                        st.info("Document is available for processing, but preview highlighting is not available")
                        
                        # Fallback to basic display
                        try:
                            if uploaded_file.type.startswith('image'):
                                st.image(uploaded_file, caption=f"Full Document: {uploaded_file.name}", use_container_width=True)
                            elif uploaded_file.type == 'application/pdf':
                                pdf_bytes = uploaded_file.getvalue()
                                images = convert_from_bytes(pdf_bytes, dpi=300, fmt='PNG')
                                if images:
                                    for i, image in enumerate(images):
                                        st.image(image, caption=f"Page {i+1} of {uploaded_file.name}", use_container_width=True)
                        except:
                            st.error("Unable to display document preview")
                    
                    st.divider()
                    st.markdown("### 📝 Add Additional Tests (Manual Entry)")
                    st.caption("Add test results that weren't automatically detected or scanned from the document")
                    

                    
                    # Number of additional tests to add
                    num_additional = st.number_input(
                        "Number of additional tests to add",
                        min_value=0,
                        max_value=20,
                        value=0,
                        key=f"num_additional_{uploaded_file.name}",
                        help="Choose how many manual tests to add, then press Enter to see input fields below"
                    )
                    
                    # Show additional test input fields when requested
                    if num_additional > 0:
                        st.write(f"**Enter details for {num_additional} additional test(s):**")
                        
                        # Create a form for the manual tests at the bottom
                        with st.form(key=f"bottom_manual_tests_{uploaded_file.name}"):
                            for i in range(num_additional):
                                st.write(f"**Test {i+1}:**")
                                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                                
                                with col1:
                                    # Investigation type dropdown for additional tests
                                    investigation_standards = st.session_state.get('investigation_standards')
                                    if investigation_standards:
                                        # Get all standard names
                                        all_standards = investigation_standards.get_all_standards()
                                        standard_names = [std['standard_name'] for std in all_standards]
                                        
                                        # Add option for custom entry at the top
                                        options = ["(Use custom text below)"] + standard_names
                                        
                                        selected_option = st.selectbox(
                                            f"Standard Type {i+1}",
                                            options=options,
                                            key=f"bottom_test_dropdown_{uploaded_file.name}_{i}",
                                            help="Choose a standard or use custom text below"
                                        )
                                        
                                        # Always show custom text input
                                        st.text_input(
                                            f"Custom Type {i+1}",
                                            key=f"bottom_test_name_{uploaded_file.name}_{i}",
                                            placeholder="Enter investigation type"
                                        )
                                    else:
                                        # Fallback to text input if standards not available
                                        st.text_input(
                                            f"Manual Test {i+1}",
                                            key=f"bottom_test_name_{uploaded_file.name}_{i}",
                                            placeholder="Enter investigation type"
                                        )
                                
                                with col2:
                                    st.number_input(
                                        f"Value {i+1}",
                                        value=0.0,
                                        key=f"bottom_test_value_{uploaded_file.name}_{i}",
                                        format="%.2f"
                                    )
                                
                                with col3:
                                    st.text_input(
                                        f"Unit {i+1}",
                                        key=f"bottom_test_unit_{uploaded_file.name}_{i}",
                                        placeholder="mg/dl, g/dl, etc."
                                    )
                                
                                with col4:
                                    st.text_input(
                                        f"Ref Range {i+1}",
                                        key=f"bottom_test_ref_range_{uploaded_file.name}_{i}",
                                        placeholder="5.0-15.0"
                                    )
                                
                                with col5:
                                    st.checkbox(
                                        f"Include",
                                        value=True,
                                        key=f"bottom_include_{uploaded_file.name}_{i}",
                                        help="Include this test"
                                    )
                            
                            # Save button for bottom manual tests
                            save_bottom_manual = st.form_submit_button("💾 Save Additional Tests", type="primary")
                        
                        # Handle save for bottom manual tests
                        if save_bottom_manual and patient_name:
                            with st.spinner("Saving additional tests..."):
                                # Process manual tests from bottom section
                                final_results = []
                                additional_count = 0
                                
                                for i in range(num_additional):
                                    if st.session_state.get(f"bottom_include_{uploaded_file.name}_{i}", True):
                                        # Determine which test type to use
                                        dropdown_selection = st.session_state.get(f"bottom_test_dropdown_{uploaded_file.name}_{i}", "(Use custom text below)")
                                        
                                        if dropdown_selection == "(Use custom text below)":
                                            test_name = st.session_state.get(f"bottom_test_name_{uploaded_file.name}_{i}", "").strip()
                                        else:
                                            test_name = dropdown_selection
                                        
                                        test_value = st.session_state.get(f"bottom_test_value_{uploaded_file.name}_{i}", 0.0)
                                        test_unit = st.session_state.get(f"bottom_test_unit_{uploaded_file.name}_{i}", "").strip()
                                        test_ref_range = st.session_state.get(f"bottom_test_ref_range_{uploaded_file.name}_{i}", "").strip()
                                        
                                        # Only add if test name is provided and value is not zero
                                        if test_name and test_value != 0.0:
                                            final_results.append({
                                                'test_type': test_name,
                                                'value': test_value,
                                                'unit': test_unit,
                                                'reference_range': test_ref_range
                                            })
                                            additional_count += 1
                                
                                if final_results:
                                    # Save additional results
                                    success = data_processor.save_test_results(
                                        patient_name=patient_name,
                                        test_date=test_date,
                                        test_results=final_results,
                                        user_id=user_id
                                    )
                                    
                                    if success:
                                        st.success(f"Successfully saved {len(final_results)} additional test results for {patient_name}")
                                    else:
                                        st.error("Failed to save additional test results to database")
                                else:
                                    st.warning("No valid additional tests to save. Please enter test names and non-zero values.")
                        
                        elif save_bottom_manual and not patient_name:
                            st.warning("Please enter a patient name to save results")
                        
                except Exception as e:
                    st.error(f"Error processing file {uploaded_file.name}: {str(e)}")

def view_patients_page(db, alert_system, user_id):
    st.header("👥 View Patients")
    
    patients = db.get_all_patients(user_id)
    
    if not patients:
        st.info("No patients found. Please upload some blood test results first.")
        return
    
    # Display patients in a table
    patients_df = pd.DataFrame(patients, columns=['Patient ID', 'Patient Name', 'First Test', 'Last Test', 'Total Tests'])
    
    st.subheader(f"Total Patients: {len(patients)}")
    
    # Add search functionality
    search_term = st.text_input("🔍 Search patients by name", placeholder="Enter patient name...")
    
    if search_term:
        patients_df = patients_df[patients_df['Patient Name'].str.contains(search_term, case=False, na=False)]
    
    if not patients_df.empty:
        st.dataframe(patients_df, use_container_width=True, hide_index=True)
        
        # Patient selection for quick actions
        selected_patient = st.selectbox(
            "Select patient for quick view",
            options=patients_df['Patient Name'].tolist(),
            index=None,
            placeholder="Choose a patient..."
        )
        
        if selected_patient:
            patient_tests = db.get_patient_tests(selected_patient, user_id)
            patient_alerts = alert_system.get_patient_alerts(selected_patient)
            
            if patient_tests:
                # Display alerts summary
                if patient_alerts:
                    critical_alerts = [a for a in patient_alerts if a['level'] == 'CRITICAL']
                    high_alerts = [a for a in patient_alerts if a['level'] == 'HIGH']
                    
                    st.subheader(f"🚨 Alerts for {selected_patient}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Critical Alerts", len(critical_alerts))
                    with col2:
                        st.metric("High Priority", len(high_alerts))
                    with col3:
                        st.metric("Total Alerts", len(patient_alerts))
                    
                    # Show top alerts
                    for alert in patient_alerts[:3]:
                        st.markdown(f"""
                        <div style="padding: 10px; margin: 5px 0; border-left: 4px solid {alert['color']}; background-color: {alert['color']}15; border-radius: 5px;">
                            <strong>{alert['icon']} {alert['level']}</strong>: {alert['message']} 
                            <br><small>Date: {alert['test_date']} | {alert['test_type']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.subheader(f"Recent Tests for {selected_patient}")
                recent_df = pd.DataFrame(patient_tests[-5:], columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.info("No patients found matching your search.")

def patient_dashboard_page(db, visualization, alert_system, user_id):
    st.header("📊 Patient Dashboard")
    
    patients = db.get_all_patients(user_id)
    
    if not patients:
        st.info("No patients found. Please upload some blood test results first.")
        return
    
    # Patient selection
    patient_names = [patient[1] for patient in patients]
    selected_patient = st.selectbox(
        "Select Patient",
        options=patient_names,
        index=None,
        placeholder="Choose a patient to view dashboard..."
    )
    
    if selected_patient:
        # Get patient data
        patient_tests = db.get_patient_tests(selected_patient, user_id)
        
        if not patient_tests:
            st.warning(f"No test results found for {selected_patient}")
            return
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(patient_tests, columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
        df['Date'] = pd.to_datetime(df['Date'])
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        # Patient summary
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Tests", len(df))
        
        with col2:
            unique_reports = df['Date'].dt.date.nunique()
            st.metric("Reports", unique_reports)
        
        with col3:
            st.metric("Test Types", df['Test Type'].nunique())
        
        with col4:
            first_test = df['Date'].min().strftime('%Y-%m-%d')
            st.metric("First Test", first_test)
        
        with col5:
            last_test = df['Date'].max().strftime('%Y-%m-%d')
            st.metric("Last Test", last_test)
        
        # Show detailed report breakdown
        st.subheader("📋 Report Summary")
        
        # Create a detailed summary by date
        date_groups = df.groupby(df['Date'].dt.date).agg({
            'Test Type': ['count', lambda x: ', '.join(sorted(x.unique()))]
        }).reset_index()
        date_groups.columns = ['Report Date', 'Test Count', 'Test Types']
        
        # Display in a nice format
        for _, row in date_groups.iterrows():
            with st.expander(f"📊 Report from {row['Report Date']} - {row['Test Count']} tests"):
                test_types_list = row['Test Types'].split(', ')
                cols = st.columns(min(3, len(test_types_list)))
                for i, test_type in enumerate(test_types_list):
                    with cols[i % 3]:
                        test_values = df[(df['Date'].dt.date == row['Report Date']) & (df['Test Type'] == test_type)]
                        if len(test_values) > 0:
                            value = test_values.iloc[0]['Value']
                            unit = test_values.iloc[0]['Unit'] or ''
                            st.metric(test_type, f"{value} {unit}")
        
        st.divider()
        
        # Get and display patient alerts
        patient_alerts = alert_system.get_patient_alerts(selected_patient)
        if patient_alerts:
            st.subheader("🚨 Active Alerts")
            critical_alerts = [a for a in patient_alerts if a['level'] == 'CRITICAL']
            high_alerts = [a for a in patient_alerts if a['level'] == 'HIGH']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Critical Alerts", len(critical_alerts))
            with col2:
                st.metric("High Priority", len(high_alerts))
            with col3:
                st.metric("Total Alerts", len(patient_alerts))
            
            # Show alerts with expandable details
            for alert in patient_alerts:
                with st.expander(f"{alert['icon']} {alert['level']} - {alert['test_type']} ({alert['test_date']})", expanded=alert['level'] == 'CRITICAL'):
                    st.markdown(f"**Message:** {alert['message']}")
                    st.markdown(f"**Value:** {alert['value']} {alert['unit']}")
                    st.markdown(f"**Reference Range:** {alert['reference_range']}")
                    
                    if alert['recommendations']:
                        st.markdown("**Recommendations:**")
                        for rec in alert['recommendations']:
                            st.markdown(f"• {rec}")
            
            st.divider()
        
        # Create individual graphs for each investigation type
        st.subheader("📈 Investigation Trends")
        
        # Get unique test types from database
        test_types = df['Test Type'].unique().tolist()
        
        if test_types:
            # Create a graph for each investigation type
            for test_type in test_types:
                test_data = df[df['Test Type'] == test_type].copy()
                
                if not test_data.empty:
                    # Sort by date for proper trend visualization
                    test_data = test_data.sort_values('Date')
                    
                    # Create trend chart for this investigation type
                    fig = visualization.create_trend_chart(test_data, test_type, selected_patient)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No test results available for visualization.")
        
        # Link to data management page
        st.subheader("📊 Data Management")
        st.info(f"View and edit all test results for {selected_patient} in the 'Manage Data' page")
        
        # Quick summary of patient data
        all_test_data = db.get_patient_test_results_with_ids(selected_patient)
        if all_test_data:
            edit_df = pd.DataFrame(all_test_data, columns=['ID', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
            
            # Add quick stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(edit_df))
            with col2:
                unique_dates = edit_df['Date'].nunique()
                st.metric("Test Dates", unique_dates)
            with col3:
                unique_types = edit_df['Test Type'].nunique()
                st.metric("Test Types", unique_types)
        else:
            st.info("No test results found for this patient.")

def search_filter_page(db, visualization, user_id):
    st.header("🔍 Search & Filter Results")
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Patient filter
        patients = db.get_all_patients()
        patient_names = [patient[1] for patient in patients]
        selected_patients = st.multiselect(
            "Filter by Patient",
            options=patient_names,
            placeholder="Select patients..."
        )
    
    with col2:
        # Date range filter
        start_date = st.date_input(
            "Start Date",
            value=date.today().replace(year=date.today().year-1)
        )
    
    with col3:
        end_date = st.date_input(
            "End Date",
            value=date.today()
        )
    
    # Test type filter
    all_test_types = db.get_all_test_types()
    selected_test_types = st.multiselect(
        "Filter by Test Type",
        options=all_test_types,
        placeholder="Select test types..."
    )
    
    # Apply filters and get results
    if st.button("🔍 Apply Filters", type="primary"):
        results = db.search_test_results(
            patient_names=selected_patients if selected_patients else None,
            test_types=selected_test_types if selected_test_types else None,
            start_date=start_date,
            end_date=end_date
        )
        
        if results:
            st.subheader(f"📊 Search Results ({len(results)} records)")
            
            # Convert to DataFrame
            df = pd.DataFrame(results, columns=['Patient Name', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
            df['Date'] = pd.to_datetime(df['Date'])
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            
            # Display results table
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Create summary visualization if data exists
            if not df.empty and selected_test_types:
                st.subheader("📈 Trend Visualization")
                
                for test_type in selected_test_types:
                    test_data = df[df['Test Type'] == test_type]
                    if not test_data.empty:
                        fig = visualization.create_multi_patient_chart(test_data, test_type)
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No results found matching your criteria.")

def export_data_page(db, user_id):
    st.header("📤 Export Data")
    
    # Export options
    export_type = st.radio(
        "Select export type",
        ["All Data", "Specific Patient", "Date Range", "Test Type"]
    )
    
    if export_type == "Specific Patient":
        patients = db.get_all_patients()
        patient_names = [patient[1] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names)
        
        if selected_patient and st.button("Export Patient Data"):
            patient_tests = db.get_patient_tests(selected_patient)
            if patient_tests:
                df = pd.DataFrame(patient_tests, columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download {selected_patient}_test_results.csv",
                    data=csv,
                    file_name=f"{selected_patient}_test_results.csv",
                    mime="text/csv"
                )
    
    elif export_type == "Date Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")
        
        if st.button("Export Date Range"):
            results = db.search_test_results(start_date=start_date, end_date=end_date)
            if results:
                df = pd.DataFrame(results, columns=['Patient Name', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download results_{start_date}_to_{end_date}.csv",
                    data=csv,
                    file_name=f"results_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
    
    elif export_type == "Test Type":
        test_types = db.get_all_test_types()
        selected_test_type = st.selectbox("Select Test Type", test_types)
        
        if selected_test_type and st.button("Export Test Type Data"):
            results = db.search_test_results(test_types=[selected_test_type])
            if results:
                df = pd.DataFrame(results, columns=['Patient Name', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download {selected_test_type}_results.csv",
                    data=csv,
                    file_name=f"{selected_test_type}_results.csv",
                    mime="text/csv"
                )
    
    elif export_type == "All Data":
        if st.button("Export All Data"):
            all_results = db.get_all_test_results()
            if all_results:
                df = pd.DataFrame(all_results, columns=['Patient Name', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download all_test_results.csv",
                    data=csv,
                    file_name="all_test_results.csv",
                    mime="text/csv"
                )

def manage_data_page(db, user_id):
    st.header("🗂️ Manage Data")
    
    # Database statistics
    stats = db.get_database_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Patients", stats['total_patients'])
    with col2:
        st.metric("Total Tests", stats['total_tests'])
    with col3:
        st.metric("Test Types", stats['unique_test_types'])
    with col4:
        if stats['earliest_test'] and stats['latest_test']:
            st.metric("Date Range", f"{stats['earliest_test']} to {stats['latest_test']}")
    
    st.divider()
    
    # Management options
    management_type = st.selectbox(
        "Choose management type",
        ["Select an option", "View & Edit Patient Data", "Delete Individual Test Results", "Delete Report by Date", "Delete by Test Type", "Delete Patient Data", "Delete All Data"],
        index=0
    )
    
    if management_type == "View & Edit Patient Data":
        st.subheader("📊 View & Edit Patient Data")
        
        # Patient selection
        patients = db.get_all_patients()
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[1] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names, index=None, placeholder="Choose a patient...")
        
        if selected_patient:
            st.subheader(f"📊 All Collected Data for {selected_patient} - Editable")
            st.write(f"Complete database records for {selected_patient} - Click to edit any value")
            
            # Get all test results with IDs for editing
            all_test_data = db.get_patient_test_results_with_ids(selected_patient)
            
            if all_test_data:
                # Convert to DataFrame with IDs
                edit_df = pd.DataFrame(all_test_data, columns=['ID', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                edit_df['Date'] = pd.to_datetime(edit_df['Date']).dt.strftime('%Y-%m-%d')
                edit_df['Value'] = pd.to_numeric(edit_df['Value'], errors='coerce')
                
                # Show total count
                st.info(f"Total records: {len(edit_df)} test results")
                
                # Create editable interface
                with st.expander("🔧 Edit Test Results", expanded=True):
                    st.warning("⚠️ Caution: Changes will be saved directly to the database")
                    
                    # Selection for editing
                    edit_mode = st.radio(
                        "Choose editing mode:",
                        ["Edit individual results", "Delete multiple results", "Edit by date groups"],
                        key="edit_mode"
                    )
                    
                    if edit_mode == "Edit individual results":
                        # Individual result editing
                        st.write("**Edit Individual Test Results:**")
                        
                        # Select result to edit
                        result_options = []
                        for _, row in edit_df.iterrows():
                            result_options.append(f"ID {row['ID']}: {row['Date']} - {row['Test Type']} = {row['Value']} {row['Unit']}")
                        
                        selected_result = st.selectbox(
                            "Select a test result to edit:",
                            options=result_options,
                            index=None,
                            placeholder="Choose a result to edit..."
                        )
                        
                        if selected_result:
                            # Extract ID from selection
                            result_id = int(selected_result.split(':')[0].replace('ID ', ''))
                            result_row = edit_df[edit_df['ID'] == result_id].iloc[0]
                            
                            # Edit form
                            with st.form(key=f"edit_result_{result_id}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    new_test_type = st.text_input("Test Type", value=result_row['Test Type'])
                                    new_value = st.number_input("Value", value=float(result_row['Value']), format="%.2f")
                                    new_unit = st.text_input("Unit", value=result_row['Unit'])
                                
                                with col2:
                                    new_date = st.date_input("Date", value=pd.to_datetime(result_row['Date']).date())
                                    new_ref_range = st.text_input("Reference Range", value=result_row['Reference Range'])
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    update_clicked = st.form_submit_button("✅ Update Result", type="primary")
                                with col2:
                                    delete_clicked = st.form_submit_button("🗑️ Delete Result", type="secondary")
                            
                            # Handle update
                            if update_clicked:
                                try:
                                    # Update in database
                                    success = db.update_test_result(
                                        result_id=result_id,
                                        test_type=new_test_type,
                                        value=new_value,
                                        unit=new_unit,
                                        test_date=new_date,
                                        reference_range=new_ref_range
                                    )
                                    
                                    if success:
                                        st.success("✅ Test result updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to update test result")
                                except Exception as e:
                                    st.error(f"❌ Error updating result: {str(e)}")
                            
                            # Handle delete
                            if delete_clicked:
                                try:
                                    success = db.delete_test_result(result_id)
                                    if success:
                                        st.success("✅ Test result deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete test result")
                                except Exception as e:
                                    st.error(f"❌ Error deleting result: {str(e)}")
                    
                    elif edit_mode == "Delete multiple results":
                        # Multiple deletion interface
                        st.write("**Select Multiple Results to Delete:**")
                        
                        # Create checkboxes for each result
                        results_to_delete = []
                        for _, row in edit_df.iterrows():
                            result_label = f"{row['Date']} - {row['Test Type']} = {row['Value']} {row['Unit']}"
                            if st.checkbox(result_label, key=f"delete_check_{row['ID']}"):
                                results_to_delete.append(row['ID'])
                        
                        if results_to_delete:
                            st.warning(f"⚠️ {len(results_to_delete)} results selected for deletion")
                            
                            if st.button("🗑️ Delete Selected Results", type="secondary"):
                                deleted_count = 0
                                for result_id in results_to_delete:
                                    if db.delete_test_result(result_id):
                                        deleted_count += 1
                                
                                if deleted_count == len(results_to_delete):
                                    st.success(f"✅ Successfully deleted {deleted_count} test results!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Only {deleted_count} of {len(results_to_delete)} results were deleted")
                    
                    elif edit_mode == "Edit by date groups":
                        # Group by date editing
                        st.write("**Edit All Results by Date:**")
                        
                        # Group results by date
                        date_groups = edit_df.groupby('Date')
                        
                        for test_date, group in date_groups:
                            with st.expander(f"📅 {test_date} ({len(group)} tests)"):
                                st.write(f"**Tests on {test_date}:**")
                                
                                # Show tests for this date
                                for _, row in group.iterrows():
                                    col1, col2, col3 = st.columns([2, 1, 1])
                                    with col1:
                                        st.write(f"• {row['Test Type']}: {row['Value']} {row['Unit']}")
                                    with col2:
                                        if st.button(f"Edit", key=f"edit_date_{row['ID']}"):
                                            st.session_state[f"editing_result_{row['ID']}"] = True
                                    with col3:
                                        if st.button(f"Delete", key=f"delete_date_{row['ID']}"):
                                            if db.delete_test_result(row['ID']):
                                                st.success("Deleted!")
                                                st.rerun()
                                
                                # Option to delete all results for this date
                                if st.button(f"🗑️ Delete All Results for {test_date}", key=f"delete_all_{test_date}"):
                                    if db.delete_test_results_by_date(selected_patient, pd.to_datetime(test_date).date()):
                                        st.success(f"✅ All results for {test_date} deleted!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete results")
                
                # Always show the complete data table at the bottom
                st.subheader("📋 Complete Database Records")
                
                # Add sorting and filtering controls
                st.write("**Table Controls:**")
                
                # Convert date strings to datetime for filtering
                edit_df['Date_dt'] = pd.to_datetime(edit_df['Date'])
                min_date = edit_df['Date_dt'].min().date()
                max_date = edit_df['Date_dt'].max().date()
                min_value = edit_df['Value'].min()
                max_value = edit_df['Value'].max()
                
                # Reset filters button
                if st.button("🔄 Reset All Filters"):
                    # Clear all filter-related session state keys
                    keys_to_clear = ['sort_column', 'sort_order', 'filter_test_type', 'start_date', 'end_date', 'value_range', 'search_term']
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                
                # Row 1: Sort and Test Type Filter
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    sort_column = st.selectbox(
                        "Sort by:",
                        options=['Date', 'Test Type', 'Value', 'Unit'],
                        index=0,
                        key='sort_column'
                    )
                
                with col2:
                    sort_order = st.selectbox(
                        "Sort order:",
                        options=['Ascending', 'Descending'],
                        index=1,
                        key='sort_order'
                    )
                
                with col3:
                    filter_test_type = st.selectbox(
                        "Filter by Test Type:",
                        options=['All'] + sorted(edit_df['Test Type'].unique().tolist()),
                        index=0,
                        key='filter_test_type'
                    )
                
                # Row 2: Date Range Filter
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    start_date = st.date_input(
                        "Start Date:",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key='start_date'
                    )
                
                with col2:
                    end_date = st.date_input(
                        "End Date:",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key='end_date'
                    )
                
                with col3:
                    # Value range filter
                    value_range = st.slider(
                        "Value Range:",
                        min_value=float(min_value),
                        max_value=float(max_value),
                        value=(float(min_value), float(max_value)),
                        step=0.1,
                        key='value_range'
                    )
                
                # Search functionality
                search_term = st.text_input(
                    "🔍 Search in table:", 
                    placeholder="Search test type, unit, or reference range...",
                    key='search_term'
                )
                
                # Apply filters and sorting
                filtered_df = edit_df.copy()
                
                # Apply test type filter
                if filter_test_type != 'All':
                    filtered_df = filtered_df[filtered_df['Test Type'] == filter_test_type]
                
                # Apply date range filter
                filtered_df = filtered_df[
                    (filtered_df['Date_dt'].dt.date >= start_date) & 
                    (filtered_df['Date_dt'].dt.date <= end_date)
                ]
                
                # Apply value range filter
                filtered_df = filtered_df[
                    (filtered_df['Value'] >= value_range[0]) & 
                    (filtered_df['Value'] <= value_range[1])
                ]
                
                # Apply search filter
                if search_term:
                    search_mask = (
                        filtered_df['Test Type'].str.contains(search_term, case=False, na=False) |
                        filtered_df['Unit'].str.contains(search_term, case=False, na=False) |
                        filtered_df['Reference Range'].str.contains(search_term, case=False, na=False)
                    )
                    filtered_df = filtered_df[search_mask]
                
                # Apply sorting
                ascending = sort_order == 'Ascending'
                if sort_column == 'Date':
                    filtered_df = filtered_df.sort_values('Date', ascending=ascending)
                elif sort_column == 'Value':
                    filtered_df = filtered_df.sort_values('Value', ascending=ascending)
                else:
                    filtered_df = filtered_df.sort_values(sort_column, ascending=ascending)
                
                # Display filtered and sorted data (remove helper columns)
                display_df = filtered_df.drop(['ID', 'Date_dt'], axis=1)
                
                # Show result count and export option
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.info(f"Showing {len(display_df)} of {len(edit_df)} records")
                
                with col2:
                    if not display_df.empty:
                        csv = display_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"filtered_test_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                # Display the table with column configuration
                if not display_df.empty:
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Date": st.column_config.DateColumn(
                                "Date",
                                format="DD/MM/YYYY",
                                width="medium"
                            ),
                            "Test Type": st.column_config.TextColumn(
                                "Test Type",
                                width="medium"
                            ),
                            "Value": st.column_config.NumberColumn(
                                "Value",
                                format="%.2f",
                                width="small"
                            ),
                            "Unit": st.column_config.TextColumn(
                                "Unit",
                                width="small"
                            ),
                            "Reference Range": st.column_config.TextColumn(
                                "Reference Range",
                                width="medium"
                            )
                        }
                    )
                else:
                    st.warning("No records match the current filters.")
                
                # Add quick stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Records", len(edit_df))
                with col2:
                    unique_dates = edit_df['Date'].nunique()
                    st.metric("Test Dates", unique_dates)
                with col3:
                    unique_types = edit_df['Test Type'].nunique()
                    st.metric("Test Types", unique_types)
            else:
                st.info("No test results found for this patient.")
    
    elif management_type == "Delete Individual Test Results":
        st.subheader("🎯 Delete Individual Test Results")
        
        # Patient selection
        patients = db.get_all_patients()
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[1] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names, index=None, placeholder="Choose a patient...")
        
        if selected_patient:
            # Get test results with IDs
            test_results = db.get_patient_test_results_with_ids(selected_patient)
            
            if not test_results:
                st.info("No test results found for this patient.")
                return
            
            st.write(f"**Test Results for {selected_patient}**")
            
            # Create DataFrame for display
            df = pd.DataFrame(test_results, columns=['ID', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
            
            # Multi-select for deletion
            selected_indices = st.multiselect(
                "Select test results to delete",
                options=range(len(df)),
                format_func=lambda x: f"{df.iloc[x]['Date']} - {df.iloc[x]['Test Type']}: {df.iloc[x]['Value']} {df.iloc[x]['Unit']}"
            )
            
            if selected_indices:
                st.dataframe(df.iloc[selected_indices], use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🗑️ Delete Selected", type="primary"):
                        deleted_count = 0
                        for idx in selected_indices:
                            result_id = df.iloc[idx]['ID']
                            if db.delete_test_result(result_id):
                                deleted_count += 1
                        
                        if deleted_count > 0:
                            st.success(f"Successfully deleted {deleted_count} test results!")
                            st.rerun()
                        else:
                            st.error("Failed to delete test results.")
            else:
                st.dataframe(df.drop('ID', axis=1), use_container_width=True, hide_index=True)
    
    elif management_type == "Delete Report by Date":
        st.subheader("📅 Delete Report by Date")
        
        # Patient selection
        patients = db.get_all_patients()
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[1] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names, index=None, placeholder="Choose a patient...")
        
        if selected_patient:
            # Get test results grouped by date
            results_by_date = db.get_test_results_by_date(selected_patient)
            
            if not results_by_date:
                st.info("No test results found for this patient.")
                return
            
            st.write(f"**Test Reports for {selected_patient}**")
            
            for test_date, tests in results_by_date.items():
                with st.expander(f"📋 Report from {test_date} ({len(tests)} tests)"):
                    # Show tests for this date
                    date_df = pd.DataFrame(tests, columns=['Test Type', 'Value', 'Unit', 'Reference Range', 'Count'])
                    st.dataframe(date_df, use_container_width=True, hide_index=True)
                    
                    if st.button(f"🗑️ Delete Entire Report ({test_date})", key=f"delete_date_{test_date}"):
                        if db.delete_test_results_by_date(selected_patient, test_date):
                            st.success(f"Successfully deleted all test results from {test_date}!")
                            st.rerun()
                        else:
                            st.error("Failed to delete test results.")
    
    elif management_type == "Delete by Test Type":
        st.subheader("🧪 Delete by Test Type")
        
        # Patient selection
        patients = db.get_all_patients()
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[1] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names, index=None, placeholder="Choose a patient...")
        
        if selected_patient:
            # Get available test types for this patient
            patient_tests = db.get_patient_tests(selected_patient)
            if not patient_tests:
                st.info("No test results found for this patient.")
                return
            
            # Extract unique test types
            test_types = list(set([test[1] for test in patient_tests]))
            test_types.sort()
            
            selected_test_type = st.selectbox("Select Test Type to Delete", test_types, index=None, placeholder="Choose a test type...")
            
            if selected_test_type:
                # Show tests of this type
                filtered_tests = [test for test in patient_tests if test[1] == selected_test_type]
                
                st.warning(f"⚠️ This will delete **{len(filtered_tests)}** {selected_test_type} test results for {selected_patient}!")
                
                with st.expander("Preview of data to be deleted"):
                    test_df = pd.DataFrame(filtered_tests, columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                    st.dataframe(test_df, use_container_width=True, hide_index=True)
                
                # Confirmation
                confirm = st.checkbox(f"I confirm I want to delete all {selected_test_type} results for {selected_patient}")
                
                if confirm:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button(f"🗑️ Delete {selected_test_type} Results", type="primary"):
                            if db.delete_test_results_by_type(selected_patient, selected_test_type):
                                st.success(f"Successfully deleted all {selected_test_type} results for {selected_patient}!")
                                st.rerun()
                            else:
                                st.error("Failed to delete test results.")
    
    elif management_type == "Delete Patient Data":
        st.subheader("👤 Delete Patient Data")
        
        # Patient selection
        patients = db.get_all_patients()
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[1] for patient in patients]
        selected_patient = st.selectbox("Select Patient to Delete", patient_names, index=None, placeholder="Choose a patient...")
        
        if selected_patient:
            # Show patient summary
            patient_tests = db.get_patient_tests(selected_patient)
            if patient_tests:
                st.warning(f"⚠️ This will delete **{selected_patient}** and **{len(patient_tests)}** test results permanently!")
                
                # Show recent tests
                with st.expander("Preview of data to be deleted"):
                    recent_df = pd.DataFrame(patient_tests[:10], columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                    st.dataframe(recent_df, use_container_width=True, hide_index=True)
                    if len(patient_tests) > 10:
                        st.write(f"... and {len(patient_tests) - 10} more test results")
                
                # Confirmation
                confirm = st.checkbox(f"I confirm I want to delete all data for {selected_patient}")
                
                if confirm:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("🗑️ Delete Patient", type="primary"):
                            if db.delete_patient(selected_patient):
                                st.success(f"Successfully deleted {selected_patient} and all associated test results!")
                                st.rerun()
                            else:
                                st.error("Failed to delete patient data.")
    
    elif management_type == "Delete All Data":
        st.subheader("🚨 Delete All Data")
        
        st.error("⚠️ **DANGER ZONE** ⚠️")
        st.warning("This will permanently delete ALL patient data and test results from the database!")
        
        if stats['total_patients'] > 0:
            st.write(f"This action will delete:")
            st.write(f"- **{stats['total_patients']}** patients")
            st.write(f"- **{stats['total_tests']}** test results")
            st.write(f"- **{stats['unique_test_types']}** different test types")
            
            # Multiple confirmations required
            confirm1 = st.checkbox("I understand this action cannot be undone")
            confirm2 = st.checkbox("I want to delete ALL data from the database") if confirm1 else False
            confirm3 = st.text_input("Type 'DELETE ALL DATA' to confirm") if confirm2 else ""
            
            if confirm1 and confirm2 and confirm3 == "DELETE ALL DATA":
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🗑️ DELETE ALL DATA", type="primary"):
                        if db.delete_all_data():
                            st.success("All data has been permanently deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete all data.")
        else:
            st.info("Database is already empty.")

def alert_dashboard_page(alert_system, user_id):
    st.header("🚨 Alert Dashboard")
    
    # Get alert summary
    alert_summary = alert_system.get_alert_summary()
    all_alerts = alert_system.get_all_alerts()
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Alerts", alert_summary['total_alerts'])
    with col2:
        st.metric("Critical Alerts", alert_summary['critical_alerts'])
    with col3:
        st.metric("High Priority", alert_summary['high_alerts'])
    with col4:
        st.metric("Patients Affected", alert_summary['patients_with_alerts'])
    
    if not all_alerts:
        st.info("🎉 No alerts found! All test results are within normal ranges.")
        return
    
    # Alert level filter
    st.subheader("Filter Alerts")
    col1, col2 = st.columns(2)
    
    with col1:
        selected_levels = st.multiselect(
            "Alert Levels",
            options=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
            default=['CRITICAL', 'HIGH']
        )
    
    with col2:
        selected_patients = st.multiselect(
            "Patients",
            options=sorted(set([alert['patient_name'] for alert in all_alerts])),
            default=[]
        )
    
    # Filter alerts based on selection
    filtered_alerts = all_alerts
    if selected_levels:
        filtered_alerts = [a for a in filtered_alerts if a['level'] in selected_levels]
    if selected_patients:
        filtered_alerts = [a for a in filtered_alerts if a['patient_name'] in selected_patients]
    
    # Display filtered alerts
    st.subheader(f"Alerts ({len(filtered_alerts)} of {len(all_alerts)})")
    
    if not filtered_alerts:
        st.info("No alerts match the selected filters.")
        return
    
    # Group alerts by level
    critical_alerts = [a for a in filtered_alerts if a['level'] == 'CRITICAL']
    high_alerts = [a for a in filtered_alerts if a['level'] == 'HIGH']
    medium_alerts = [a for a in filtered_alerts if a['level'] == 'MEDIUM']
    low_alerts = [a for a in filtered_alerts if a['level'] == 'LOW']
    
    # Display Critical Alerts
    if critical_alerts:
        st.subheader("🚨 Critical Alerts")
        for alert in critical_alerts:
            st.markdown(f"""
            <div style="padding: 15px; margin: 10px 0; border-left: 5px solid {alert['color']}; background-color: {alert['color']}20; border-radius: 5px;">
                <h4>{alert['icon']} {alert['patient_name']} - {alert['test_type']}</h4>
                <p><strong>Message:</strong> {alert['message']}</p>
                <p><strong>Date:</strong> {alert['test_date']} | <strong>Value:</strong> {alert['value']} {alert['unit']}</p>
                <p><strong>Reference Range:</strong> {alert['reference_range']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if alert['recommendations']:
                with st.expander("View Recommendations"):
                    for rec in alert['recommendations']:
                        st.markdown(f"• {rec}")
    
    # Display High Priority Alerts
    if high_alerts:
        st.subheader("⚠️ High Priority Alerts")
        for alert in high_alerts:
            with st.expander(f"{alert['icon']} {alert['patient_name']} - {alert['test_type']} ({alert['test_date']})"):
                st.markdown(f"**Message:** {alert['message']}")
                st.markdown(f"**Value:** {alert['value']} {alert['unit']}")
                st.markdown(f"**Reference Range:** {alert['reference_range']}")
                
                if alert['recommendations']:
                    st.markdown("**Recommendations:**")
                    for rec in alert['recommendations']:
                        st.markdown(f"• {rec}")
    
    # Display Medium and Low Priority Alerts
    if medium_alerts or low_alerts:
        st.subheader("⚡ Other Alerts")
        other_alerts = medium_alerts + low_alerts
        
        for alert in other_alerts:
            with st.expander(f"{alert['icon']} {alert['level']} - {alert['patient_name']} - {alert['test_type']} ({alert['test_date']})"):
                st.markdown(f"**Message:** {alert['message']}")
                st.markdown(f"**Value:** {alert['value']} {alert['unit']}")
                st.markdown(f"**Reference Range:** {alert['reference_range']}")
                
                if alert['recommendations']:
                    st.markdown("**Recommendations:**")
                    for rec in alert['recommendations']:
                        st.markdown(f"• {rec}")
    
    # Recent Alerts Section
    st.subheader("📅 Recent Alerts (Last 7 Days)")
    recent_alerts = alert_system.check_recent_alerts(7)
    
    if recent_alerts:
        st.write(f"Found {len(recent_alerts)} alerts in the last 7 days")
        
        # Create a summary table of recent alerts
        recent_data = []
        for alert in recent_alerts:
            recent_data.append({
                'Patient': alert['patient_name'],
                'Test Type': alert['test_type'],
                'Level': alert['level'],
                'Date': alert['test_date'],
                'Value': f"{alert['value']} {alert['unit']}",
                'Message': alert['message']
            })
        
        recent_df = pd.DataFrame(recent_data)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts in the last 7 days.")

def ai_anomaly_detection_page(anomaly_detector, user_id):
    """AI-powered anomaly detection page."""
    st.header("🤖 AI-Powered Anomaly Detection")
    st.markdown("Advanced machine learning algorithms to detect unusual patterns in blood test results")
    
    # Analysis options
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_type = st.selectbox(
            "Analysis Type",
            ["All Patients", "Specific Patient", "Anomaly Trends"]
        )
    
    with col2:
        if analysis_type == "Specific Patient":
            # Get list of patients for the current user
            patients = anomaly_detector.database.get_all_patients(user_id)
            if patients:
                patient_names = [patient[1] for patient in patients]
                selected_patient = st.selectbox("Select Patient", patient_names)
            else:
                st.warning("No patients found.")
                return
        else:
            selected_patient = None
    
    # Analysis controls
    st.subheader("Analysis Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Run Analysis", type="primary"):
            st.session_state['run_anomaly_analysis'] = True
    
    with col2:
        if st.button("📊 View Trends"):
            st.session_state['show_trends'] = True
    
    with col3:
        if st.button("🔄 Refresh Data"):
            st.session_state['refresh_anomaly_data'] = True
            st.rerun()
    
    # Run analysis
    if st.session_state.get('run_anomaly_analysis', False):
        st.session_state['run_anomaly_analysis'] = False
        
        with st.spinner("🧠 AI is analyzing your data..."):
            if analysis_type == "All Patients":
                results = anomaly_detector.detect_anomalies(user_id=user_id)
            elif analysis_type == "Specific Patient":
                results = anomaly_detector.get_patient_anomaly_summary(selected_patient, user_id)
            else:  # Anomaly Trends
                results = anomaly_detector.get_anomaly_trends(user_id=user_id)
        
        if 'error' in results:
            st.error(f"Analysis failed: {results['error']}")
            return
        
        # Display results based on analysis type
        if analysis_type == "All Patients":
            display_all_patients_analysis(results)
        elif analysis_type == "Specific Patient":
            display_patient_analysis(results, selected_patient)
        else:
            display_trends_analysis(results)
    
    # Show trends if requested
    if st.session_state.get('show_trends', False):
        st.session_state['show_trends'] = False
        
        with st.spinner("Analyzing trends..."):
            trends = anomaly_detector.get_anomaly_trends(user_id=user_id)
        
        if 'error' not in trends:
            st.subheader("📈 Anomaly Trends")
            display_trends_analysis(trends)

def display_all_patients_analysis(results):
    """Display analysis results for all patients."""
    st.subheader("🔍 Analysis Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Anomalies", results['total_anomalies'])
    
    with col2:
        st.metric("High Severity", results['severity_distribution']['high'])
    
    with col3:
        st.metric("Medium Severity", results['severity_distribution']['medium'])
    
    with col4:
        st.metric("Patients Analyzed", results['data_summary']['total_patients'])
    
    # Severity distribution chart
    if results['total_anomalies'] > 0:
        severity_data = results['severity_distribution']
        fig = px.pie(
            values=list(severity_data.values()),
            names=list(severity_data.keys()),
            title="Anomaly Severity Distribution",
            color_discrete_map={'high': '#ff4444', 'medium': '#ffaa00', 'low': '#44ff44'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations
    if results['recommendations']:
        st.subheader("🎯 AI Recommendations")
        
        for rec in results['recommendations']:
            severity_color = {
                'high': '#ff4444',
                'medium': '#ffaa00',
                'low': '#44ff44'
            }.get(rec['priority'], '#888888')
            
            st.markdown(f"""
            <div style="border-left: 4px solid {severity_color}; padding-left: 20px; margin: 10px 0;">
                <h4>{rec['title']}</h4>
                <p>{rec['description']}</p>
                <ul>
                    {''.join([f'<li>{item}</li>' for item in rec['action_items']])}
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    # Detailed anomalies table
    if results['anomalies']:
        st.subheader("📋 Detailed Anomalies")
        
        anomaly_data = []
        for anomaly in results['anomalies']:
            anomaly_data.append({
                'Patient': anomaly['patient_name'],
                'Date': anomaly.get('test_date', 'N/A'),
                'Method': anomaly.get('detection_method', 'N/A'),
                'Severity': anomaly.get('severity', 'medium'),
                'Type': anomaly.get('pattern_type', anomaly.get('test_type', 'N/A')),
                'Description': anomaly.get('description', 'Anomaly detected')
            })
        
        df = pd.DataFrame(anomaly_data)
        
        # Add color coding for severity
        def highlight_severity(val):
            if val == 'high':
                return 'background-color: #ffebee'
            elif val == 'medium':
                return 'background-color: #fff3e0'
            else:
                return 'background-color: #e8f5e8'
        
        styled_df = df.style.applymap(highlight_severity, subset=['Severity'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

def display_patient_analysis(results, patient_name):
    """Display analysis results for a specific patient."""
    st.subheader(f"🔍 Analysis Results for {patient_name}")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Anomalies", results['total_anomalies'])
    
    with col2:
        st.metric("High Severity", results['severity_distribution']['high'])
    
    with col3:
        st.metric("Medium Severity", results['severity_distribution']['medium'])
    
    # Patient-specific anomalies
    if results['anomalies']:
        st.subheader("📊 Anomaly Details")
        
        for anomaly in results['anomalies']:
            with st.expander(f"{anomaly.get('detection_method', 'Unknown')} - {anomaly.get('severity', 'medium').title()} Severity"):
                st.markdown(f"**Date:** {anomaly.get('test_date', 'N/A')}")
                st.markdown(f"**Method:** {anomaly.get('detection_method', 'N/A')}")
                
                if 'description' in anomaly:
                    st.markdown(f"**Description:** {anomaly['description']}")
                
                if 'value' in anomaly:
                    st.markdown(f"**Value:** {anomaly['value']}")
                
                if 'tests_involved' in anomaly:
                    st.markdown(f"**Tests Involved:** {', '.join(anomaly['tests_involved'])}")
    
    # Recommendations
    if results['recommendations']:
        st.subheader("🎯 Personalized Recommendations")
        
        for rec in results['recommendations']:
            st.markdown(f"""
            <div style="border-left: 4px solid #4CAF50; padding-left: 20px; margin: 10px 0;">
                <h4>{rec['title']}</h4>
                <p>{rec['description']}</p>
                <ul>
                    {''.join([f'<li>{item}</li>' for item in rec['action_items']])}
                </ul>
            </div>
            """, unsafe_allow_html=True)

def display_trends_analysis(results):
    """Display anomaly trends analysis."""
    st.subheader("📈 Anomaly Trends Analysis")
    
    if 'trend_data' in results and results['trend_data']:
        # Create trend chart
        trend_df = pd.DataFrame(results['trend_data'])
        
        fig = px.line(
            trend_df,
            x='week',
            y='anomaly_count',
            title=f"Anomaly Trends Over Last {results['period_days']} Days",
            labels={'week': 'Week', 'anomaly_count': 'Number of Anomalies'}
        )
        
        fig.update_layout(
            xaxis_title="Week",
            yaxis_title="Anomaly Count",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Tests", results['total_tests'])
        
        with col2:
            avg_anomalies = sum(item['anomaly_count'] for item in results['trend_data']) / len(results['trend_data'])
            st.metric("Avg Anomalies/Week", f"{avg_anomalies:.1f}")
        
        with col3:
            max_anomalies = max(item['anomaly_count'] for item in results['trend_data'])
            st.metric("Peak Anomalies", max_anomalies)
    
    else:
        st.info("No trend data available for the selected period.")

def investigation_standards_page(investigation_standards):
    """Investigation Standards Management Page."""
    st.header("🔬 Investigation Standards Management")
    st.markdown("Manage standardized investigation types with reference ranges for male and female patients")
    
    # Create tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 View Standards", "➕ Add New Standard", "📊 Standardization Preview", "📄 Extract from Reports"])
    
    with tab1:
        st.subheader("Current Investigation Standards")
        
        # Get all standards
        standards = investigation_standards.get_all_standards()
        
        if standards:
            # Convert to DataFrame for better display
            standards_df = pd.DataFrame(standards)
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Standards", len(standards))
            with col2:
                categories = standards_df['category'].nunique()
                st.metric("Categories", categories)
            with col3:
                avg_aliases = standards_df['aliases'].str.split(',').str.len().mean()
                st.metric("Avg Aliases", f"{avg_aliases:.1f}")
            
            st.markdown("---")
            
            # Filter and sort controls
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # Filter by category
                categories = ['All'] + sorted(standards_df['category'].unique().tolist())
                selected_category = st.selectbox("Filter by Category", categories)
            
            with col2:
                # Search functionality
                search_term = st.text_input("Search Standards", placeholder="Search by name, aliases, or category...")
            
            with col3:
                # Export button
                if st.button("📥 Export CSV"):
                    csv_data = standards_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"investigation_standards_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
            
            # Apply filters
            filtered_df = standards_df.copy()
            
            if selected_category != 'All':
                filtered_df = filtered_df[filtered_df['category'] == selected_category]
            
            if search_term:
                search_mask = (
                    filtered_df['standard_name'].str.contains(search_term, case=False, na=False) |
                    filtered_df['aliases'].str.contains(search_term, case=False, na=False) |
                    filtered_df['category'].str.contains(search_term, case=False, na=False) |
                    filtered_df['description'].str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[search_mask]
            
            # Prepare display DataFrame
            display_df = filtered_df.copy()
            
            # Format columns for better display
            display_df['Common Unit'] = display_df.apply(
                lambda row: row.get('common_unit') or row.get('male_unit') or row.get('female_unit') or 'Not specified', 
                axis=1
            )
            
            display_df['Male Range'] = display_df.apply(
                lambda row: f"{row['male_range_min']}-{row['male_range_max']}" if pd.notna(row['male_range_min']) and pd.notna(row['male_range_max']) else 'Not specified',
                axis=1
            )
            
            display_df['Female Range'] = display_df.apply(
                lambda row: f"{row['female_range_min']}-{row['female_range_max']}" if pd.notna(row['female_range_min']) and pd.notna(row['female_range_max']) else 'Not specified',
                axis=1
            )
            
            # Truncate long aliases for display
            display_df['Aliases (truncated)'] = display_df['aliases'].apply(
                lambda x: x[:50] + "..." if pd.notna(x) and len(str(x)) > 50 else (x if pd.notna(x) else "None")
            )
            
            # Select columns for display
            display_columns = [
                'standard_name', 'category', 'Common Unit', 
                'Male Range', 'Female Range', 'Aliases (truncated)', 'description'
            ]
            
            # Rename columns for better display
            column_config = {
                'standard_name': st.column_config.TextColumn('Standard Name', width='medium'),
                'category': st.column_config.TextColumn('Category', width='small'),
                'Common Unit': st.column_config.TextColumn('Unit', width='small'),
                'Male Range': st.column_config.TextColumn('Male Range', width='small'),
                'Female Range': st.column_config.TextColumn('Female Range', width='small'),
                'Aliases (truncated)': st.column_config.TextColumn('Aliases', width='large'),
                'description': st.column_config.TextColumn('Description', width='large')
            }
            
            # Display format selection
            st.subheader(f"Standards Data ({len(display_df)} records)")
            
            view_mode = st.radio(
                "Display Format:",
                ["📊 Excel Table (Sortable)", "📋 Detailed Cards (Editable)"],
                horizontal=True,
                help="Choose between sortable table view or detailed editable cards"
            )
            
            st.markdown(f"**Showing {len(display_df)} of {len(standards_df)} total standards**")
            
            if view_mode == "📊 Excel Table (Sortable)":
                # Prepare editable DataFrame with proper structure
                edit_df = filtered_df.copy()
                
                # Add computed columns for display but keep original data for editing
                edit_df['computed_unit'] = edit_df.apply(
                    lambda row: row.get('common_unit') or row.get('male_unit') or row.get('female_unit') or '', 
                    axis=1
                )
                
                # Define column configuration for editing
                edit_column_config = {
                    'id': st.column_config.NumberColumn('ID', width='small', disabled=True),
                    'standard_name': st.column_config.TextColumn('Standard Name', width='medium', required=True),
                    'category': st.column_config.SelectboxColumn(
                        'Category', 
                        width='small',
                        options=investigation_standards.get_predefined_categories(),
                        required=True
                    ),
                    'computed_unit': st.column_config.TextColumn('Unit', width='small'),
                    'male_range_min': st.column_config.NumberColumn('Male Min', width='small', format="%.2f"),
                    'male_range_max': st.column_config.NumberColumn('Male Max', width='small', format="%.2f"),
                    'female_range_min': st.column_config.NumberColumn('Female Min', width='small', format="%.2f"),
                    'female_range_max': st.column_config.NumberColumn('Female Max', width='small', format="%.2f"),
                    'aliases': st.column_config.TextColumn('Aliases', width='large', help="Comma-separated list"),
                    'description': st.column_config.TextColumn('Description', width='large')
                }
                
                # Select columns for editing (include id for tracking)
                edit_columns = [
                    'id', 'standard_name', 'category', 'computed_unit',
                    'male_range_min', 'male_range_max', 'female_range_min', 'female_range_max',
                    'aliases', 'description'
                ]
                
                # Warning about unique names
                st.info("ℹ️ **Important:** Standard names must be unique. If you change a name to one that already exists, the update will fail.")
                
                # Excel-like editable table
                edited_df = st.data_editor(
                    edit_df[edit_columns],
                    column_config=edit_column_config,
                    use_container_width=True,
                    num_rows="dynamic",
                    hide_index=True,
                    key="standards_data_editor"
                )
                
                # Process changes and additions
                if not edited_df.equals(edit_df[edit_columns]):
                    st.markdown("---")
                    st.subheader("💾 Save Changes")
                    
                    # Check for new rows (rows without ID or with ID=0)
                    new_rows = []
                    for idx, row in edited_df.iterrows():
                        if (pd.isna(row['id']) or row['id'] == 0) and pd.notna(row['standard_name']) and str(row['standard_name']).strip():
                            new_rows.append(row)
                    
                    if new_rows:
                        st.write("**New Standards to Add:**")
                        new_rows_df = pd.DataFrame(new_rows)
                        st.dataframe(new_rows_df, use_container_width=True)
                        
                        if st.button("✅ Add New Standards", type="primary"):
                            success_count = 0
                            for row in new_rows:
                                standard_data = {
                                    'standard_name': str(row['standard_name']).strip(),
                                    'aliases': row['aliases'] if pd.notna(row['aliases']) else '',
                                    'male_range_min': row['male_range_min'] if pd.notna(row['male_range_min']) else 0.0,
                                    'male_range_max': row['male_range_max'] if pd.notna(row['male_range_max']) else 0.0,
                                    'female_range_min': row['female_range_min'] if pd.notna(row['female_range_min']) else 0.0,
                                    'female_range_max': row['female_range_max'] if pd.notna(row['female_range_max']) else 0.0,
                                    'male_unit': row['computed_unit'] if pd.notna(row['computed_unit']) else '',
                                    'female_unit': row['computed_unit'] if pd.notna(row['computed_unit']) else '',
                                    'common_unit': row['computed_unit'] if pd.notna(row['computed_unit']) else '',
                                    'description': row['description'] if pd.notna(row['description']) else '',
                                    'category': row['category'] if pd.notna(row['category']) else 'Other'
                                }
                                
                                if investigation_standards.add_standard(standard_data):
                                    success_count += 1
                            
                            if success_count > 0:
                                st.success(f"Successfully added {success_count} new standards!")
                                st.rerun()
                            else:
                                st.error("Failed to add new standards. Please check the data.")
                    
                    # Check for modifications to existing rows (by ID, not position)
                    existing_changes = []
                    for idx, edited_row in edited_df.iterrows():
                        # Skip rows without ID (new rows) or with empty/null ID
                        if pd.isna(edited_row['id']) or edited_row['id'] == 0:
                            continue
                            
                        record_id = int(edited_row['id'])
                        # Find the original row with matching ID
                        original_rows = edit_df[edit_df['id'] == record_id]
                        if len(original_rows) > 0:
                            original_row = original_rows.iloc[0]
                            
                            # Check if any field changed (excluding id column)
                            edit_cols_without_id = [col for col in edit_columns if col != 'id']
                            if not original_row[edit_cols_without_id].equals(edited_row[edit_cols_without_id]):
                                existing_changes.append((record_id, edited_row, original_row))
                    
                    if existing_changes:
                        st.write("**Modified Standards:**")
                        changes_df = pd.DataFrame([change[1] for change in existing_changes])
                        st.dataframe(changes_df, use_container_width=True)
                        
                        if st.button("💾 Update Modified Standards", type="primary"):
                            success_count = 0
                            failed_updates = []
                            
                            for record_id, edited_row, original_row in existing_changes:
                                update_data = {
                                    'standard_name': edited_row['standard_name'],
                                    'aliases': edited_row['aliases'] if pd.notna(edited_row['aliases']) else '',
                                    'male_range_min': edited_row['male_range_min'] if pd.notna(edited_row['male_range_min']) else 0.0,
                                    'male_range_max': edited_row['male_range_max'] if pd.notna(edited_row['male_range_max']) else 0.0,
                                    'female_range_min': edited_row['female_range_min'] if pd.notna(edited_row['female_range_min']) else 0.0,
                                    'female_range_max': edited_row['female_range_max'] if pd.notna(edited_row['female_range_max']) else 0.0,
                                    'male_unit': edited_row['computed_unit'] if pd.notna(edited_row['computed_unit']) else '',
                                    'female_unit': edited_row['computed_unit'] if pd.notna(edited_row['computed_unit']) else '',
                                    'common_unit': edited_row['computed_unit'] if pd.notna(edited_row['computed_unit']) else '',
                                    'description': edited_row['description'] if pd.notna(edited_row['description']) else '',
                                    'category': edited_row['category'] if pd.notna(edited_row['category']) else 'Other'
                                }
                                
                                if investigation_standards.update_standard(record_id, update_data):
                                    success_count += 1
                                else:
                                    failed_updates.append(edited_row['standard_name'])
                            
                            if success_count > 0:
                                st.success(f"Successfully updated {success_count} standards!")
                                if failed_updates:
                                    st.warning(f"Failed to update {len(failed_updates)} standards: {', '.join(failed_updates)}. Check for duplicate names.")
                                st.rerun()
                            else:
                                if failed_updates:
                                    st.error(f"❌ Failed to update standards: **{', '.join(failed_updates)}**")
                                    st.info("💡 **Tip:** These standard names already exist in the database. Please use unique names or update the existing records instead.")
                                    
                                    # Show suggestions for similar names
                                    for failed_name in failed_updates:
                                        similar_names = investigation_standards.get_similar_standard_names(failed_name)
                                        if similar_names:
                                            st.warning(f"🔍 **'{failed_name}'** conflicts with existing standards: {', '.join(similar_names)}")
                                    
                                    # Show existing standards for reference
                                    with st.expander("📋 View all existing standard names for reference"):
                                        all_standards = investigation_standards.get_all_standards()
                                        existing_names = sorted([s['standard_name'] for s in all_standards])
                                        st.write("**Current standard names in database:**")
                                        for i, name in enumerate(existing_names, 1):
                                            st.write(f"{i}. {name}")
                                else:
                                    st.error("Failed to update standards. Please try again.")
            
            else:
                # Original detailed expandable cards format
                for idx, standard in filtered_df.iterrows():
                    with st.expander(f"🧪 {standard['standard_name']} ({standard['category']})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**📝 Basic Information**")
                            edit_name = st.text_input("Standard Name", value=standard['standard_name'], key=f"name_{standard['id']}")
                            edit_category = st.selectbox("Category", 
                                investigation_standards.get_predefined_categories(),
                                index=investigation_standards.get_predefined_categories().index(standard['category']) 
                                      if standard['category'] in investigation_standards.get_predefined_categories() 
                                      else investigation_standards.get_predefined_categories().index('Other'),
                                key=f"cat_{standard['id']}")
                            edit_description = st.text_area("Description", value=standard['description'] or '', key=f"desc_{standard['id']}")
                            edit_aliases = st.text_area("Aliases (comma-separated)", value=standard['aliases'] or '', key=f"alias_{standard['id']}")
                        
                        with col2:
                            st.markdown("**🚹🚺 Reference Ranges**")
                            
                            # Common unit
                            st.markdown("**Common Unit:**")
                            # Use common_unit if available, otherwise fallback to male_unit or female_unit
                            current_unit = standard.get('common_unit') or standard.get('male_unit') or standard.get('female_unit') or ''
                            common_unit_edit = st.text_input("Unit (for both ranges)", value=current_unit, key=f"common_unit_{standard['id']}")
                            
                            # Male ranges
                            st.markdown("**Male Range:**")
                            col_m1, col_m2 = st.columns(2)
                            with col_m1:
                                male_min = st.number_input("Min", value=float(standard['male_range_min']) if standard['male_range_min'] else 0.0, key=f"m_min_{standard['id']}")
                            with col_m2:
                                male_max = st.number_input("Max", value=float(standard['male_range_max']) if standard['male_range_max'] else 0.0, key=f"m_max_{standard['id']}")
                            
                            # Female ranges
                            st.markdown("**Female Range:**")
                            col_f1, col_f2 = st.columns(2)
                            with col_f1:
                                female_min = st.number_input("Min", value=float(standard['female_range_min']) if standard['female_range_min'] else 0.0, key=f"f_min_{standard['id']}")
                            with col_f2:
                                female_max = st.number_input("Max", value=float(standard['female_range_max']) if standard['female_range_max'] else 0.0, key=f"f_max_{standard['id']}")
                        
                        # Action buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("💾 Update", key=f"update_{standard['id']}"):
                                update_data = {
                                    'standard_name': edit_name,
                                    'aliases': edit_aliases,
                                    'male_range_min': male_min,
                                    'male_range_max': male_max,
                                    'male_unit': common_unit_edit,  # Use common unit for male
                                    'female_range_min': female_min,
                                    'female_range_max': female_max,
                                    'female_unit': common_unit_edit,  # Use common unit for female
                                    'common_unit': common_unit_edit,
                                    'description': edit_description,
                                    'category': edit_category
                                }
                                
                                if investigation_standards.update_standard(standard['id'], update_data):
                                    st.success("Standard updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update standard")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_{standard['id']}"):
                                if investigation_standards.delete_standard(standard['id']):
                                    st.success("Standard deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete standard")
                        
                        with col3:
                            # Show current reference ranges with common unit
                            display_unit = current_unit or "No unit"
                            st.info(f"Unit: {display_unit}\nM: {male_min}-{male_max}\nF: {female_min}-{female_max}")
            
            # Action buttons below the table
            if view_mode == "📊 Excel Table (Sortable)":
                st.markdown("---")
                st.subheader("Quick Actions")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 Refresh Data"):
                        st.rerun()
                
                with col2:
                    st.info("📝 Edit cells directly in the table above")
                
                with col3:
                    st.info("➕ Click the '+' button in table to add new rows")
                
                # Instructions
                st.markdown("""
                **How to use Excel Table mode:**
                - ✏️ **Edit existing records**: Click any cell to modify values
                - ➕ **Add new records**: Click the '+' button at the bottom of the table to add rows
                - 💾 **Save changes**: Use the save buttons that appear when you make changes
                - 📊 **Sort & Filter**: Use the column headers and filter controls above
                """)
            
            else:
                # For detailed cards mode
                st.markdown("---")
                st.markdown("**💡 Tip:** Each card allows direct inline editing with Update/Delete buttons")
        
        else:
            st.info("No investigation standards found. Add some standards to get started.")
    
    with tab2:
        st.subheader("Add New Investigation Standard")
        
        with st.form("add_standard_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Standard Name*", placeholder="e.g., Total Bilirubin")
                new_category = st.selectbox("Category*", investigation_standards.get_predefined_categories())
                new_description = st.text_area("Description", placeholder="Brief description of the test")
                new_aliases = st.text_area("Aliases (comma-separated)", 
                    placeholder="bilirubin, total bil, tbil")
            
            with col2:
                st.markdown("**Reference Ranges**")
                
                # Common unit field
                st.markdown("**Common Unit:**")
                new_common_unit = st.text_input("Unit (for both ranges)", placeholder="mg/dL", key="new_common_unit")
                
                # Male ranges
                st.markdown("**Male Range:**")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    new_male_min = st.number_input("Min Value", value=0.0, key="new_m_min")
                with col_m2:
                    new_male_max = st.number_input("Max Value", value=0.0, key="new_m_max")
                
                # Female ranges
                st.markdown("**Female Range:**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    new_female_min = st.number_input("Min Value", value=0.0, key="new_f_min")
                with col_f2:
                    new_female_max = st.number_input("Max Value", value=0.0, key="new_f_max")
            
            if st.form_submit_button("🔬 Add Standard"):
                if new_name and new_category:
                    new_standard = {
                        'standard_name': new_name,
                        'aliases': new_aliases,
                        'male_range_min': new_male_min,
                        'male_range_max': new_male_max,
                        'male_unit': new_common_unit,  # Use common unit for male
                        'female_range_min': new_female_min,
                        'female_range_max': new_female_max,
                        'female_unit': new_common_unit,  # Use common unit for female
                        'common_unit': new_common_unit,
                        'description': new_description,
                        'category': new_category
                    }
                    
                    if investigation_standards.add_standard(new_standard):
                        st.success(f"✅ Successfully added '{new_name}' to investigation standards!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add standard. Name might already exist.")
                else:
                    st.error("❌ Please fill in at least the Standard Name and Category.")
    
    with tab3:
        st.subheader("Test Standardization Preview")
        st.markdown("Enter test names to see how they would be standardized using fuzzy matching")
        
        # Test input
        test_names_input = st.text_area(
            "Enter test names (one per line)",
            placeholder="glucose\nhaemoglobin\nchol\ncreat",
            height=100
        )
        
        if test_names_input:
            test_names = [name.strip() for name in test_names_input.split('\n') if name.strip()]
            
            if test_names:
                st.subheader("Standardization Results")
                
                results_data = []
                for test_name in test_names:
                    standardized_name, match_info = investigation_standards.standardize_test_name(test_name)
                    
                    if match_info:
                        match_score = match_info.get('match_score', 0)
                        category = match_info.get('category', 'Unknown')
                        male_range = f"{match_info['male_range_min']}-{match_info['male_range_max']} {match_info['male_unit']}"
                        female_range = f"{match_info['female_range_min']}-{match_info['female_range_max']} {match_info['female_unit']}"
                        status = "✅ Matched"
                    else:
                        match_score = 0
                        category = "No match"
                        male_range = "N/A"
                        female_range = "N/A"
                        status = "❌ No match"
                    
                    results_data.append({
                        'Original Name': test_name,
                        'Standardized Name': standardized_name,
                        'Status': status,
                        'Match Score': f"{match_score:.2f}" if match_score else "0.00",
                        'Category': category,
                        'Male Range': male_range,
                        'Female Range': female_range
                    })
                
                # Display results in a table
                results_df = pd.DataFrame(results_data)
                st.dataframe(results_df, use_container_width=True)
                
                # Summary
                matched_count = len([r for r in results_data if "✅" in r['Status']])
                st.metric("Standardization Success Rate", f"{matched_count}/{len(results_data)} ({matched_count/len(results_data)*100:.1f}%)")
    
    with tab4:
        st.subheader("📄 Extract Standards from Medical Reports")
        st.markdown("Upload medical reports to extract test types and automatically create investigation standards")
        
        # File upload section
        st.write("**📁 Upload Medical Reports**")
        uploaded_files = st.file_uploader(
            "Choose files to extract investigation types from",
            type=['pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls', 'csv', 'xml', 'jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            accept_multiple_files=True,
            help="Supported formats: PDF, Word, Text, Excel, CSV, XML, and Images (JPG, PNG, BMP, TIFF)"
        )
        

        
        # Initialize session state for extraction results
        if 'standards_extraction_results' not in st.session_state:
            st.session_state.standards_extraction_results = {}
        
        # Process uploaded files
        if uploaded_files:
            all_files = uploaded_files
            
            if all_files:
                st.subheader("📊 Processing Results")
                
                # Get file parser and data processor from session state
                file_parser = st.session_state.get('file_parser')
                data_processor = st.session_state.get('data_processor')
                
                if not file_parser:
                    from file_parser import FileParser
                    file_parser = FileParser()
                    st.session_state.file_parser = file_parser
                
                # Process each file
                all_extracted_tests = []
                processing_summary = []
                
                for i, uploaded_file in enumerate(all_files):
                    file_name = uploaded_file.name if hasattr(uploaded_file, 'name') else f"camera_photo_{i+1}.jpg"
                    
                    with st.expander(f"📄 {file_name}", expanded=True):
                        try:
                            # Show file info
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**File:** {file_name}")
                                if hasattr(uploaded_file, 'size'):
                                    st.write(f"**Size:** {uploaded_file.size:,} bytes")
                                if hasattr(uploaded_file, 'type'):
                                    st.write(f"**Type:** {uploaded_file.type}")
                            
                            # Force OCR option for images and scanned documents (enabled by default)
                            force_ocr = st.checkbox(f"Force OCR for {file_name}", value=True, key=f"force_ocr_{i}")
                            
                            with st.spinner(f"Processing {file_name}..."):
                                # Process file for image snippets if it's a PDF or image
                                if uploaded_file.type == "application/pdf" or uploaded_file.type.startswith("image/"):
                                    try:
                                        # Get image snippet extractor from session state
                                        if hasattr(st.session_state, 'image_snippet_extractor'):
                                            image_snippet_extractor = st.session_state.image_snippet_extractor
                                        else:
                                            from image_snippet_extractor import ImageSnippetExtractor
                                            image_snippet_extractor = ImageSnippetExtractor()
                                            st.session_state.image_snippet_extractor = image_snippet_extractor
                                        
                                        # Process file for image snippets
                                        uploaded_file.seek(0)  # Reset file pointer
                                        file_bytes = uploaded_file.read()
                                        uploaded_file.seek(0)  # Reset again for text extraction
                                        
                                        if uploaded_file.type == "application/pdf":
                                            image_snippet_extractor.process_pdf_for_snippets(file_bytes)
                                        elif uploaded_file.type.startswith("image/"):
                                            # For image files, process them for OCR and snippets
                                            image_snippet_extractor.process_image_for_snippets(file_bytes)
                                    except Exception as snippet_error:
                                        st.warning(f"Could not process {file_name} for image snippets: {str(snippet_error)}")
                                
                                # Extract text from file
                                extracted_text = file_parser.parse_file(uploaded_file, force_ocr=force_ocr)
                                
                                if extracted_text and "Error" not in extracted_text:
                                    # Extract test data
                                    test_data = file_parser.extract_test_data(extracted_text)
                                    
                                    if test_data.get('results'):
                                        # Display extracted tests
                                        st.success(f"✅ Extracted {len(test_data['results'])} test types from {file_name}")
                                        
                                        # Store full test data with reference ranges in session state
                                        if 'extracted_test_data' not in st.session_state:
                                            st.session_state.extracted_test_data = {}
                                        
                                        # Display extracted test types and store full test data
                                        test_types_found = []
                                        for result in test_data['results']:
                                            test_type = result.get('test_type', '').strip()
                                            if test_type and test_type not in test_types_found:
                                                test_types_found.append(test_type)
                                                # Store the full result data for this test type
                                                st.session_state.extracted_test_data[test_type] = result
                                        
                                        st.write(f"**Found {len(test_types_found)} investigation types:**")
                                        
                                        # Debug: Show all extracted test data
                                        with st.expander("🔍 Debug: View Extracted Test Data", expanded=False):
                                            for test_type in test_types_found:
                                                test_info = st.session_state.extracted_test_data[test_type]
                                                st.write(f"**{test_type}:**")
                                                st.json(test_info)
                                        
                                        for test_type in test_types_found:
                                            ref_range = st.session_state.extracted_test_data[test_type].get('reference_range', '')
                                            ref_info = f" (Range: {ref_range})" if ref_range else " (No range extracted)"
                                            st.write(f"• {test_type}{ref_info}")
                                        
                                        if test_types_found:
                                            st.info("👇 Each investigation below shows the document snippet with highlighted text and extracted reference ranges")
                                        
                                        # Add to all extracted tests
                                        all_extracted_tests.extend(test_types_found)
                                        processing_summary.append({
                                            'file': file_name,
                                            'tests_found': len(test_types_found),
                                            'status': 'Success'
                                        })
                                    else:
                                        st.warning(f"⚠️ No test results found in {file_name}")
                                        processing_summary.append({
                                            'file': file_name,
                                            'tests_found': 0,
                                            'status': 'No tests found'
                                        })
                                else:
                                    st.error(f"❌ Failed to extract text from {file_name}")
                                    processing_summary.append({
                                        'file': file_name,
                                        'tests_found': 0,
                                        'status': 'Extraction failed'
                                    })
                        
                        except Exception as e:
                            st.error(f"❌ Error processing {file_name}: {str(e)}")
                            processing_summary.append({
                                'file': file_name,
                                'tests_found': 0,
                                'status': f'Error: {str(e)}'
                            })
                
                # Show processing summary
                if processing_summary:
                    st.subheader("📋 Processing Summary")
                    summary_df = pd.DataFrame(processing_summary)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
                # Create standards from extracted tests
                if all_extracted_tests:
                    st.subheader("🔬 Create Investigation Standards")
                    
                    # Remove duplicates and sort
                    unique_tests = sorted(list(set(all_extracted_tests)))
                    
                    st.write(f"**Found {len(unique_tests)} unique investigation types across all files:**")
                    
                    # Get all existing aliases from standards
                    existing_standards = investigation_standards.get_all_standards()
                    
                    # Helper function to check if a test name matches any existing aliases using case-insensitive matching
                    def check_case_insensitive_match(test_name):
                        """Check if test name matches any existing aliases using case-insensitive matching."""
                        test_name_clean = test_name.lower().strip()
                        
                        for standard in existing_standards:
                            # Check against standard name (exact match)
                            standard_name = standard['standard_name'].lower()
                            if test_name_clean == standard_name:
                                return True, standard['standard_name']
                            
                            # Check against aliases (exact match)
                            if standard.get('aliases'):
                                aliases = [alias.strip().lower() for alias in standard['aliases'].split(',')]
                                for alias in aliases:
                                    if test_name_clean == alias:
                                        return True, standard['standard_name']
                        
                        return False, None
                    
                    # Process each unique test individually
                    for i, test_name in enumerate(unique_tests):
                        # Check if this test exists in aliases using case-insensitive matching
                        exists_in_aliases, matched_standard = check_case_insensitive_match(test_name)
                        
                        with st.expander(f"{'✅' if exists_in_aliases else '➕'} {test_name}", expanded=not exists_in_aliases):
                            # Create two-column layout: Document snippet on left, Investigation details on right
                            snippet_col, details_col = st.columns([1, 1])
                            
                            with snippet_col:
                                st.subheader("📄 Document Snippet")
                                # Show image snippet for this investigation type
                                if hasattr(st.session_state, 'image_snippet_extractor'):
                                    image_snippet_extractor = st.session_state.image_snippet_extractor
                                else:
                                    from image_snippet_extractor import ImageSnippetExtractor
                                    image_snippet_extractor = ImageSnippetExtractor()
                                    st.session_state.image_snippet_extractor = image_snippet_extractor
                                
                                try:
                                    # Get image snippet for this test with highlighting
                                    snippet_image = image_snippet_extractor.get_context_snippet(test_name)
                                    if snippet_image:
                                        st.image(snippet_image, caption=f"Highlighted: '{test_name}'", use_container_width=True)
                                        st.caption("🔵 Blue boxes highlight the investigation type")
                                    else:
                                        st.info(f"No visual snippet available for '{test_name}'")
                                        
                                        # Debug: Show what text was extracted for troubleshooting
                                        if hasattr(image_snippet_extractor, 'ocr_data') and image_snippet_extractor.ocr_data:
                                            ocr_texts = []
                                            for page_data in image_snippet_extractor.ocr_data:
                                                for text in page_data['text_data']['text']:
                                                    if text.strip() and len(text.strip()) > 2:
                                                        ocr_texts.append(text.strip())
                                            
                                            if ocr_texts:
                                                with st.expander("🔍 Debug: OCR Text Found", expanded=False):
                                                    st.write("OCR extracted the following text from the document:")
                                                    st.text_area("", value="\n".join(ocr_texts[:50]), height=150)  # Show first 50 text items
                                                    st.caption(f"Showing first 50 items out of {len(ocr_texts)} total text elements")
                                            else:
                                                st.warning("No OCR text was extracted from the document")
                                except Exception as e:
                                    st.error(f"Error getting snippet: {str(e)}")
                            
                            with details_col:
                                st.subheader("🔬 Investigation Details")
                                if exists_in_aliases:
                                    st.info("📋 This investigation type already exists in the system")
                                    st.write("**Status:** Found in existing aliases")
                                    if matched_standard:
                                        st.write(f"**Matched Standard:** {matched_standard}")
                                else:
                                    st.warning("🆕 New investigation type - not found in existing aliases")
                                    st.write("**Status:** No exact match found")
                                
                                # Always provide both options regardless of match status
                                st.subheader("🎯 Available Actions")
                                
                                # Option 1: Create as new standard
                                create_new = st.checkbox(
                                    f"Create '{test_name}' as new standard",
                                    key=f"create_new_{i}",
                                    value=not exists_in_aliases,
                                    help="Create this as a completely new investigation standard"
                                )
                                
                                # Option 2: Add to existing standard's aliases
                                add_to_existing = st.checkbox(
                                    f"Add '{test_name}' to existing standard's aliases",
                                    key=f"add_to_existing_{i}",
                                    value=False,
                                    help="Add this test name as an alias to an existing standard"
                                )
                                
                                # If adding to existing, show dropdown to select standard
                                selected_standard = None
                                if add_to_existing:
                                    standard_options = [s['standard_name'] for s in existing_standards]
                                    selected_standard = st.selectbox(
                                        "Select existing standard to add alias to:",
                                        options=standard_options,
                                        key=f"select_standard_{i}",
                                        index=0 if not matched_standard else (
                                            standard_options.index(matched_standard) if matched_standard in standard_options else 0
                                        )
                                    )
                                
                                # Show forms based on selected options
                                if create_new:
                                        # Create unique form key using test name hash to avoid duplicates
                                        form_key = f"create_form_{abs(hash(test_name)) % 1000000}"
                                        
                                        # Get extracted test data for this test if available
                                        extracted_data = st.session_state.get('extracted_test_data', {}).get(test_name, {})
                                        reference_range = extracted_data.get('reference_range', '')
                                        extracted_unit = extracted_data.get('unit', 'mg/dL')
                                        
                                        # Parse reference range to extract min/max values
                                        def parse_reference_range(ref_range_str):
                                            """Parse reference range string to extract min/max values."""
                                            if not ref_range_str:
                                                return 0.0, 100.0, extracted_unit
                                            
                                            # Clean the reference range string
                                            ref_clean = ref_range_str.strip()
                                            
                                            # Try to extract numeric ranges (e.g., "5.0-15.0", "5.0 - 15.0", "5.0 to 15.0")
                                            range_patterns = [
                                                r'(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',  # 5.0-15.0 or 5.0 - 15.0
                                                r'(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',     # 5.0 to 15.0
                                                r'(\d+\.?\d*)\s*–\s*(\d+\.?\d*)',      # em dash
                                                r'(\d+\.?\d*)\s*\-\s*(\d+\.?\d*)',     # regular dash
                                            ]
                                            
                                            for pattern in range_patterns:
                                                match = re.search(pattern, ref_clean, re.IGNORECASE)
                                                if match:
                                                    try:
                                                        min_val = float(match.group(1))
                                                        max_val = float(match.group(2))
                                                        return min_val, max_val, extracted_unit
                                                    except ValueError:
                                                        continue
                                            
                                            # Try to extract single value with operator (e.g., "<10", ">5")
                                            single_patterns = [
                                                r'<\s*(\d+\.?\d*)',  # <10
                                                r'>\s*(\d+\.?\d*)',  # >5
                                                r'≤\s*(\d+\.?\d*)',  # ≤10
                                                r'≥\s*(\d+\.?\d*)',  # ≥5
                                            ]
                                            
                                            for pattern in single_patterns:
                                                match = re.search(pattern, ref_clean)
                                                if match:
                                                    try:
                                                        val = float(match.group(1))
                                                        if '<' in pattern or '≤' in pattern:
                                                            return 0.0, val, extracted_unit
                                                        else:  # > or ≥
                                                            return val, val * 2, extracted_unit
                                                    except ValueError:
                                                        continue
                                            
                                            # Default fallback
                                            return 0.0, 100.0, extracted_unit
                                        
                                        # Parse the reference range
                                        min_val, max_val, unit = parse_reference_range(reference_range)
                                        
                                        with st.form(form_key):
                                            st.write("**Investigation Standard Details:**")
                                            
                                            # Show extracted reference range if available
                                            if reference_range:
                                                st.info(f"📋 **Extracted Reference Range:** {reference_range}")
                                                st.caption("The values below are automatically populated from the document")
                                            
                                            # Standard name (pre-populated with extracted text)
                                            standard_name = st.text_input(
                                                "Standard Investigation Name", 
                                                value=test_name,
                                                key=f"name_{form_key}"
                                            )
                                            
                                            # Category
                                            category = st.selectbox(
                                                "Category", 
                                                investigation_standards.get_predefined_categories(),
                                                key=f"category_{form_key}"
                                            )
                                            
                                            # Common unit first
                                            st.write("**Common Unit:**")
                                            common_unit = st.text_input("Unit (for both ranges)", value=unit, key=f"common_unit_{form_key}")
                                            
                                            # Reference ranges
                                            col_male, col_female = st.columns(2)
                                            
                                            with col_male:
                                                st.write("**Male Range:**")
                                                male_min = st.number_input("Min", value=min_val, key=f"male_min_{form_key}")
                                                male_max = st.number_input("Max", value=max_val, key=f"male_max_{form_key}")
                                            
                                            with col_female:
                                                st.write("**Female Range:**")
                                                female_min = st.number_input("Min", value=min_val, key=f"female_min_{form_key}")
                                                female_max = st.number_input("Max", value=max_val, key=f"female_max_{form_key}")
                                            
                                            # Description
                                            description = st.text_area(
                                                "Description", 
                                                value="Investigation standard created from medical report extraction",
                                                key=f"desc_{form_key}"
                                            )
                                            
                                            # Aliases (automatically include the extracted text)
                                            aliases_input = st.text_input(
                                                "Aliases (comma-separated)", 
                                                value=test_name,
                                                help="The extracted test name will be automatically added to aliases",
                                                key=f"aliases_{form_key}"
                                            )
                                            
                                            # Submit button
                                            submit_individual = st.form_submit_button(
                                                f"✅ Create Standard for {test_name}", 
                                                type="primary"
                                            )
                                            
                                            if submit_individual:
                                                try:
                                                    # Ensure extracted test name is in aliases
                                                    aliases_list = [alias.strip() for alias in aliases_input.split(',') if alias.strip()]
                                                    if test_name not in aliases_list:
                                                        aliases_list.append(test_name)
                                                    
                                                    standard_data = {
                                                        'standard_name': standard_name,
                                                        'category': category,
                                                        'male_range_min': male_min,
                                                        'male_range_max': male_max,
                                                        'male_unit': common_unit,  # Use common unit for male
                                                        'female_range_min': female_min,
                                                        'female_range_max': female_max,
                                                        'female_unit': common_unit,  # Use common unit for female
                                                        'common_unit': common_unit,
                                                        'description': description,
                                                        'aliases': ", ".join(aliases_list)
                                                    }
                                                    
                                                    success = investigation_standards.add_standard(standard_data)
                                                    
                                                    if success:
                                                        st.success(f"✅ Successfully created standard for {test_name}!")
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Failed to create standard for {test_name}")
                                                
                                                except Exception as e:
                                                    st.error(f"Error creating standard: {str(e)}")
                                
                                # Handle adding to existing standard's aliases
                                if add_to_existing and selected_standard:
                                    st.subheader(f"Add to '{selected_standard}' aliases")
                                    
                                    # Find the selected standard
                                    target_standard = None
                                    for std in existing_standards:
                                        if std['standard_name'] == selected_standard:
                                            target_standard = std
                                            break
                                    
                                    if target_standard:
                                        current_aliases = target_standard.get('aliases', '')
                                        st.write(f"**Current aliases:** {current_aliases}")
                                        
                                        # Check if already exists
                                        existing_aliases = [alias.strip().lower() for alias in current_aliases.split(',') if alias.strip()]
                                        if test_name.lower() in existing_aliases:
                                            st.info(f"'{test_name}' already exists in aliases")
                                        else:
                                            if st.button(f"Add '{test_name}' to aliases", key=f"add_alias_{i}"):
                                                try:
                                                    # Add to aliases
                                                    new_aliases = f"{current_aliases}, {test_name}".strip(', ')
                                                    
                                                    # Update the standard
                                                    updated_data = target_standard.copy()
                                                    updated_data['aliases'] = new_aliases
                                                    
                                                    success = investigation_standards.update_standard(target_standard['id'], updated_data)
                                                    
                                                    if success:
                                                        st.success(f"✅ Added '{test_name}' to '{selected_standard}' aliases!")
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Failed to update aliases for '{selected_standard}'")
                                                        
                                                except Exception as e:
                                                    st.error(f"Error updating aliases: {str(e)}")
                                    else:
                                        st.error("Selected standard not found")

if __name__ == "__main__":
    main()
