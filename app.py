import streamlit as st
import pandas as pd
import os
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
    return db, file_parser, data_processor, visualization, alert_system, auth_system, auth_ui, anomaly_detector

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
    db, file_parser, data_processor, visualization, alert_system, auth_system, auth_ui, anomaly_detector = init_components()
    
    # Check authentication
    if not auth_ui.check_authentication():
        auth_ui.login_page()
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Display user info in sidebar
    auth_ui.sidebar_user_info()
    
    # Page selection
    pages = ["Upload Results", "View Patients", "Patient Dashboard", "Search & Filter", "Export Data", "Manage Data", "Alert Dashboard", "AI Anomaly Detection"]
    
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
        type=['pdf', 'txt', 'docx', 'xlsx', 'xls', 'csv', 'xml'],
        accept_multiple_files=True,
        help="Upload PDF, Word (.docx), Excel (.xlsx, .xls), CSV, XML, or text files containing blood test results"
    )
    
    # Option to force OCR for difficult PDFs
    force_ocr = st.checkbox(
        "Force OCR extraction",
        help="Use OCR (Optical Character Recognition) for image-based or problematic PDFs. This can help extract text from scanned documents."
    )
    
    if uploaded_files:
        st.subheader("Processing Files")
        
        for uploaded_file in uploaded_files:
            with st.expander(f"Processing: {uploaded_file.name}"):
                try:
                    # Show processing status
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("Reading file...")
                    progress_bar.progress(25)
                    
                    # Parse file
                    extracted_text = file_parser.parse_file(uploaded_file, force_ocr)
                    
                    status_text.text("Extracting test data...")
                    progress_bar.progress(50)
                    
                    # Extract test data
                    test_data = file_parser.extract_test_data(extracted_text)
                    
                    if not test_data or not test_data.get('results'):
                        st.error("No valid blood test data found in the file")
                        # Show extracted text for debugging
                        with st.expander("Debug: Show extracted text"):
                            st.text_area("Extracted text", extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text, height=200)
                        continue
                    
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
                            key=f"date_{uploaded_file.name}"
                        )
                    
                    # Test results preview and editing
                    if test_data.get('results'):
                        # Document preview and results comparison
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader(f"📋 Review Test Results ({len(test_data['results'])} tests found)")
                            st.write("Review and edit the extracted test results, then add any missing tests:")
                        
                        with col2:
                            st.subheader("📄 Document Preview")
                            with st.expander("📖 View Original Document Content", expanded=False):
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
                        
                        # Quick search buttons for extracted tests (outside form)
                        if test_data.get('results'):
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
                                        
                                        # Editable investigation type
                                        st.text_input(
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
                                        
                                        # Include checkbox
                                        st.checkbox(
                                            "Include this test in results",
                                            value=True,
                                            key=f"include_{uploaded_file.name}_{i}",
                                            help="Uncheck to exclude this test from being saved"
                                        )
                            
                            # Additional manual tests section
                            st.write("**Add Additional Tests (not scanned):**")
                            
                            # Number of additional tests to add
                            num_additional = st.number_input(
                                "Number of additional tests to add",
                                min_value=0,
                                max_value=20,
                                value=0,
                                key=f"num_additional_{uploaded_file.name}"
                            )
                            
                            # Additional test inputs
                            if num_additional > 0:
                                for i in range(num_additional):
                                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                                    
                                    with col1:
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
                                        st.checkbox(
                                            f"Add {i+1}",
                                            value=True,
                                            key=f"add_include_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed"
                                        )
                                    
                                    with col5:
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
                                        final_results.append({
                                            'test_type': st.session_state.get(f"test_name_{uploaded_file.name}_{i}", result['test_type']),
                                            'value': st.session_state.get(f"test_value_{uploaded_file.name}_{i}", result['value']),
                                            'unit': st.session_state.get(f"test_unit_{uploaded_file.name}_{i}", result.get('unit', '')),
                                            'reference_range': result.get('reference_range', '')
                                        })
                                
                                # Add additional manual tests
                                num_additional = st.session_state.get(f"num_additional_{uploaded_file.name}", 0)
                                additional_count = 0
                                
                                if num_additional > 0:
                                    for i in range(num_additional):
                                        if st.session_state.get(f"add_include_{uploaded_file.name}_{i}", True):
                                            test_name = st.session_state.get(f"add_test_name_{uploaded_file.name}_{i}", "").strip()
                                            test_value = st.session_state.get(f"add_test_value_{uploaded_file.name}_{i}", 0.0)
                                            test_unit = st.session_state.get(f"add_test_unit_{uploaded_file.name}_{i}", "").strip()
                                            
                                            # Only add if test name is provided and value is not zero
                                            if test_name and test_value != 0.0:
                                                final_results.append({
                                                    'test_type': test_name,
                                                    'value': test_value,
                                                    'unit': test_unit,
                                                    'reference_range': ''
                                                })
                                                additional_count += 1
                                
                                # Save all results
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
                        st.warning("No test results found to preview")
                        
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
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tests", len(df))
        
        with col2:
            st.metric("Test Types", df['Test Type'].nunique())
        
        with col3:
            first_test = df['Date'].min().strftime('%Y-%m-%d')
            st.metric("First Test", first_test)
        
        with col4:
            last_test = df['Date'].max().strftime('%Y-%m-%d')
            st.metric("Last Test", last_test)
        
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

if __name__ == "__main__":
    main()
