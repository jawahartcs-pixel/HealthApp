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
    return db, file_parser, data_processor, visualization

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
    db, file_parser, data_processor, visualization = init_components()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Upload Results", "View Patients", "Patient Dashboard", "Search & Filter", "Export Data", "Manage Data"]
    )
    
    if page == "Upload Results":
        upload_results_page(file_parser, data_processor)
    elif page == "View Patients":
        view_patients_page(db)
    elif page == "Patient Dashboard":
        patient_dashboard_page(db, visualization)
    elif page == "Search & Filter":
        search_filter_page(db, visualization)
    elif page == "Export Data":
        export_data_page(db)
    elif page == "Manage Data":
        manage_data_page(db)

def upload_results_page(file_parser, data_processor):
    st.header("📁 Upload Blood Test Results")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose blood test result files",
        type=['pdf', 'txt'],
        accept_multiple_files=True,
        help="Upload PDF or text files containing blood test results"
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
                        st.subheader(f"Review Test Results ({len(test_data['results'])} tests found)")
                        st.write("Review and edit the extracted test results before saving:")
                        
                        # Create editable interface
                        edited_results = []
                        
                        # Header row
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            st.write("**Test Name**")
                        with col2:
                            st.write("**Value**") 
                        with col3:
                            st.write("**Unit**")
                        with col4:
                            st.write("**Include**")
                        
                        # Create form for editing
                        with st.form(key=f"edit_results_{uploaded_file.name}"):
                            for i, result in enumerate(test_data['results']):
                                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                                
                                with col1:
                                    test_name = st.text_input(
                                        f"Test {i+1}",
                                        value=result['test_type'],
                                        key=f"test_name_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed"
                                    )
                                
                                with col2:
                                    test_value = st.number_input(
                                        f"Value {i+1}",
                                        value=float(result['value']),
                                        key=f"test_value_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        format="%.2f"
                                    )
                                
                                with col3:
                                    test_unit = st.text_input(
                                        f"Unit {i+1}",
                                        value=result.get('unit', ''),
                                        key=f"test_unit_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed"
                                    )
                                
                                with col4:
                                    include_test = st.checkbox(
                                        f"Include {i+1}",
                                        value=True,
                                        key=f"include_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed"
                                    )
                                
                                # Collect edited results
                                if include_test:
                                    edited_results.append({
                                        'test_type': test_name,
                                        'value': test_value,
                                        'unit': test_unit,
                                        'reference_range': result.get('reference_range', '')
                                    })
                            
                            # Save button
                            save_clicked = st.form_submit_button("💾 Save Results", type="primary")
                        
                        if save_clicked and patient_name:
                            with st.spinner("Saving results..."):
                                status_text.text("Saving to database...")
                                progress_bar.progress(90)
                                
                                # Get final edited results (need to rebuild since form values reset)
                                final_results = []
                                for i, result in enumerate(test_data['results']):
                                    if st.session_state.get(f"include_{uploaded_file.name}_{i}", True):
                                        final_results.append({
                                            'test_type': st.session_state.get(f"test_name_{uploaded_file.name}_{i}", result['test_type']),
                                            'value': st.session_state.get(f"test_value_{uploaded_file.name}_{i}", result['value']),
                                            'unit': st.session_state.get(f"test_unit_{uploaded_file.name}_{i}", result.get('unit', '')),
                                            'reference_range': result.get('reference_range', '')
                                        })
                                
                                success = data_processor.save_test_results(
                                    patient_name=patient_name,
                                    test_date=test_date,
                                    test_results=final_results
                                )
                                
                                progress_bar.progress(100)
                                
                                if success:
                                    status_text.text("✅ Successfully processed!")
                                    st.success(f"Successfully saved {len(final_results)} test results for {patient_name}")
                                    
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

def view_patients_page(db):
    st.header("👥 View Patients")
    
    patients = db.get_all_patients()
    
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
            patient_tests = db.get_patient_tests(selected_patient)
            if patient_tests:
                st.subheader(f"Recent Tests for {selected_patient}")
                recent_df = pd.DataFrame(patient_tests[-5:], columns=['Date', 'Test Type', 'Value', 'Unit', 'Reference Range'])
                st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.info("No patients found matching your search.")

def patient_dashboard_page(db, visualization):
    st.header("📊 Patient Dashboard")
    
    patients = db.get_all_patients()
    
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
        patient_tests = db.get_patient_tests(selected_patient)
        
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
        
        # Test type selection for visualization
        test_types = df['Test Type'].unique().tolist()
        selected_tests = st.multiselect(
            "Select test types to visualize",
            options=test_types,
            default=test_types[:3] if len(test_types) >= 3 else test_types
        )
        
        if selected_tests:
            # Create visualizations
            for test_type in selected_tests:
                test_data = df[df['Test Type'] == test_type].copy()
                
                if not test_data.empty:
                    fig = visualization.create_trend_chart(test_data, test_type, selected_patient)
                    st.plotly_chart(fig, use_container_width=True)
        
        # Recent test results table
        st.subheader("📋 Recent Test Results")
        recent_tests = df.sort_values('Date', ascending=False).head(10)
        st.dataframe(recent_tests, use_container_width=True, hide_index=True)

def search_filter_page(db, visualization):
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

def export_data_page(db):
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

def manage_data_page(db):
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
    
    # Deletion options
    deletion_type = st.selectbox(
        "Choose deletion type",
        ["Select an option", "Delete Individual Test Results", "Delete Report by Date", "Delete by Test Type", "Delete Patient Data", "Delete All Data"],
        index=0
    )
    
    if deletion_type == "Delete Individual Test Results":
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
    
    elif deletion_type == "Delete Report by Date":
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
    
    elif deletion_type == "Delete by Test Type":
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
    
    elif deletion_type == "Delete Patient Data":
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
    
    elif deletion_type == "Delete All Data":
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

if __name__ == "__main__":
    main()
