import streamlit as st
import pandas as pd
from datetime import date, datetime
from database import Database
from file_parser import FileParser
from data_processor import DataProcessor
from visualization import Visualization
from utils import *

# Set page config
st.set_page_config(
    page_title="Blood Test Results Manager",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_database():
    """Initialize database connection."""
    db = Database()
    db.init_database()
    return db

@st.cache_resource
def init_components():
    """Initialize all components."""
    db = init_database()
    file_parser = FileParser()
    data_processor = DataProcessor(db)
    visualization = Visualization(db)
    return db, file_parser, data_processor, visualization

def main():
    """Main application function."""
    st.title("🩺 Blood Test Results Management System")
    
    # Initialize components
    db, file_parser, data_processor, visualization = init_components()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Upload Results", "View Patients", "Patient Dashboard", "Search & Filter", "Export Data", "Manage Data", "Learning Statistics"]
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
    elif page == "Learning Statistics":
        learning_stats_page(file_parser.learning_system)

def upload_results_page(file_parser, data_processor):
    """Handle file upload and test results extraction."""
    st.title("📄 Upload Blood Test Results")
    st.write("Upload PDF, Word, or text files containing blood test results to extract and save patient data.")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose blood test files",
        type=['pdf', 'txt', 'docx'],
        accept_multiple_files=True,
        help="Supported formats: PDF, TXT, DOCX files"
    )
    
    # OCR option
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
                    
                    # Check if we found test results
                    if test_data and test_data.get('results'):
                        status_text.text("Processing patient information...")
                        progress_bar.progress(75)
                        
                        # Preview and edit extracted data before saving
                        st.subheader("Review & Edit Test Results")
                        st.write("Review extracted data, edit values, and add additional tests not found by the scanner.")
                        
                        # Create comprehensive form for all data
                        with st.form(key=f"comprehensive_form_{uploaded_file.name}"):
                            # Patient information section (editable in form)
                            st.subheader("Patient Information")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                patient_name = st.text_input(
                                    "Patient Name",
                                    value=test_data.get('patient_name', ''),
                                    help="Edit the patient name if needed"
                                )
                            
                            with col2:
                                test_date = st.date_input(
                                    "Test Report Date", 
                                    value=test_data.get('test_date', date.today()),
                                    help="Edit the test date if needed"
                                )
                            
                            st.divider()
                            
                            # Extracted test results section
                            if test_data.get('results'):
                                st.subheader(f"Extracted Test Results ({len(test_data['results'])} found)")
                                st.write("Review and edit the automatically extracted test results:")
                                
                                # Header row for extracted results
                                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                                with col1:
                                    st.write("**Investigation Type**")
                                with col2:
                                    st.write("**Value**") 
                                with col3:
                                    st.write("**Unit**")
                                with col4:
                                    st.write("**Include**")
                                
                                # Show extracted results
                                for i, result in enumerate(test_data['results']):
                                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                                    
                                    with col1:
                                        st.text_input(
                                            f"Extracted Test {i+1}",
                                            value=result['test_type'],
                                            key=f"extracted_name_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed"
                                        )
                                    
                                    with col2:
                                        st.number_input(
                                            f"Extracted Value {i+1}",
                                            value=float(result['value']),
                                            key=f"extracted_value_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed",
                                            format="%.2f"
                                        )
                                    
                                    with col3:
                                        st.text_input(
                                            f"Extracted Unit {i+1}",
                                            value=result.get('unit', ''),
                                            key=f"extracted_unit_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed"
                                        )
                                    
                                    with col4:
                                        st.checkbox(
                                            f"Include extracted {i+1}",
                                            value=True,
                                            key=f"include_extracted_{uploaded_file.name}_{i}",
                                            label_visibility="collapsed"
                                        )
                            
                            st.divider()
                            
                            # Manual test entry section
                            st.subheader("Add Additional Tests")
                            st.write("Add test results that were not automatically detected:")
                            
                            # Initialize session state for manual tests count
                            manual_count_key = f"manual_count_{uploaded_file.name}"
                            if manual_count_key not in st.session_state:
                                st.session_state[manual_count_key] = 3  # Start with 3 empty rows
                            
                            # Button to add more manual test rows
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if st.form_submit_button("➕ Add Row", type="secondary"):
                                    st.session_state[manual_count_key] += 1
                                    st.rerun()
                            
                            with col2:
                                st.write(f"Manual test rows: {st.session_state[manual_count_key]}")
                            
                            # Header row for manual tests
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                            with col1:
                                st.write("**Investigation Type**")
                            with col2:
                                st.write("**Value**") 
                            with col3:
                                st.write("**Unit**")
                            with col4:
                                st.write("**Include**")
                            
                            # Manual test entry rows
                            for i in range(st.session_state[manual_count_key]):
                                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                                
                                with col1:
                                    st.text_input(
                                        f"Manual Test {i+1}",
                                        key=f"manual_name_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        placeholder="Enter test name..."
                                    )
                                
                                with col2:
                                    st.number_input(
                                        f"Manual Value {i+1}",
                                        key=f"manual_value_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        format="%.2f",
                                        value=0.0
                                    )
                                
                                with col3:
                                    st.text_input(
                                        f"Manual Unit {i+1}",
                                        key=f"manual_unit_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        placeholder="e.g., mg/dl, g/dl"
                                    )
                                
                                with col4:
                                    st.checkbox(
                                        f"Include manual {i+1}",
                                        key=f"include_manual_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed"
                                    )
                            
                            st.divider()
                            
                            # Save button
                            save_clicked = st.form_submit_button("💾 Save All Results", type="primary", use_container_width=True)
                            
                            if save_clicked and patient_name:
                                with st.spinner("Saving results..."):
                                    status_text.text("Saving to database...")
                                    progress_bar.progress(90)
                                    
                                    # Collect final results (extracted + manual)
                                    final_results = []
                                    
                                    # Add selected extracted results
                                    for i, result in enumerate(test_data.get('results', [])):
                                        if st.session_state.get(f"include_extracted_{uploaded_file.name}_{i}", True):
                                            test_name = st.session_state.get(f"extracted_name_{uploaded_file.name}_{i}", result['test_type'])
                                            test_value = st.session_state.get(f"extracted_value_{uploaded_file.name}_{i}", result['value'])
                                            test_unit = st.session_state.get(f"extracted_unit_{uploaded_file.name}_{i}", result.get('unit', ''))
                                            
                                            final_results.append({
                                                'test_type': test_name,
                                                'value': test_value,
                                                'unit': test_unit,
                                                'reference_range': result.get('reference_range', '')
                                            })
                                    
                                    # Add manual test results
                                    manual_count = st.session_state.get(manual_count_key, 3)
                                    for i in range(manual_count):
                                        if st.session_state.get(f"include_manual_{uploaded_file.name}_{i}", False):
                                            test_name = st.session_state.get(f"manual_name_{uploaded_file.name}_{i}", "").strip()
                                            test_value = st.session_state.get(f"manual_value_{uploaded_file.name}_{i}", 0.0)
                                            test_unit = st.session_state.get(f"manual_unit_{uploaded_file.name}_{i}", "").strip()
                                            
                                            # Only add if test name is provided and value is not zero
                                            if test_name and test_value != 0.0:
                                                final_results.append({
                                                    'test_type': test_name,
                                                    'value': test_value,
                                                    'unit': test_unit,
                                                    'reference_range': ''
                                                })
                                    
                                    if final_results:
                                        # Learn from user edits before saving
                                        original_results = test_data.get('test_results', [])
                                        extraction_methods = test_data.get('extraction_methods', {})
                                        
                                        # Track user corrections and performance
                                        corrected_count, added_count = file_parser.learning_system.learn_from_user_edits(
                                            original_results, final_results, extraction_methods
                                        )
                                        
                                        # Track extraction performance
                                        file_parser.learning_system.track_extraction_performance(
                                            document_type=uploaded_file.type,
                                            extraction_methods=extraction_methods,
                                            original_count=len(original_results),
                                            final_count=len(final_results),
                                            corrected_count=corrected_count,
                                            added_count=added_count
                                        )
                                        
                                        success = data_processor.save_test_results(
                                            patient_name=patient_name,
                                            test_date=test_date,
                                            test_results=final_results
                                        )
                                        
                                        progress_bar.progress(100)
                                        
                                        if success:
                                            status_text.text("✅ Successfully processed!")
                                            extracted_count = len([r for i, r in enumerate(test_data.get('results', [])) if st.session_state.get(f"include_extracted_{uploaded_file.name}_{i}", True)])
                                            manual_count_saved = len(final_results) - extracted_count
                                            
                                            st.success(f"Successfully saved {len(final_results)} test results for {patient_name}")
                                            st.info(f"📊 Breakdown: {extracted_count} extracted tests + {manual_count_saved} manual tests")
                                        else:
                                            status_text.text("❌ Failed to save")
                                            st.error("Failed to save test results to database")
                                    else:
                                        st.warning("No test results selected to save")
                                        
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
                            elif save_clicked and not patient_name:
                                st.warning("Please enter a patient name to save results")
                    
                    else:
                        # No extracted results - show manual entry form only
                        st.subheader("Add Test Results Manually")
                        st.write("No test results were automatically extracted. Please enter the test data manually:")
                        
                        with st.form(key=f"manual_only_form_{uploaded_file.name}"):
                            # Patient information section
                            st.subheader("Patient Information")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                patient_name = st.text_input(
                                    "Patient Name",
                                    value=test_data.get('patient_name', '') if test_data else '',
                                    help="Enter the patient name"
                                )
                            
                            with col2:
                                test_date = st.date_input(
                                    "Test Report Date", 
                                    value=test_data.get('test_date', date.today()) if test_data else date.today(),
                                    help="Enter the test date"
                                )
                            
                            st.divider()
                            
                            # Manual test entry section
                            st.subheader("Test Results")
                            
                            # Initialize session state for manual tests count
                            manual_count_key = f"manual_only_count_{uploaded_file.name}"
                            if manual_count_key not in st.session_state:
                                st.session_state[manual_count_key] = 5  # Start with 5 empty rows
                            
                            # Button to add more manual test rows
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if st.form_submit_button("➕ Add Row", type="secondary"):
                                    st.session_state[manual_count_key] += 1
                                    st.rerun()
                            
                            with col2:
                                st.write(f"Test entry rows: {st.session_state[manual_count_key]}")
                            
                            # Header row
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                            with col1:
                                st.write("**Investigation Type**")
                            with col2:
                                st.write("**Value**") 
                            with col3:
                                st.write("**Unit**")
                            with col4:
                                st.write("**Include**")
                            
                            # Manual test entry rows
                            for i in range(st.session_state[manual_count_key]):
                                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                                
                                with col1:
                                    st.text_input(
                                        f"Test {i+1}",
                                        key=f"manual_only_name_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        placeholder="Enter test name..."
                                    )
                                
                                with col2:
                                    st.number_input(
                                        f"Value {i+1}",
                                        key=f"manual_only_value_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        format="%.2f",
                                        value=0.0
                                    )
                                
                                with col3:
                                    st.text_input(
                                        f"Unit {i+1}",
                                        key=f"manual_only_unit_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed",
                                        placeholder="e.g., mg/dl, g/dl"
                                    )
                                
                                with col4:
                                    st.checkbox(
                                        f"Include {i+1}",
                                        key=f"include_manual_only_{uploaded_file.name}_{i}",
                                        label_visibility="collapsed"
                                    )
                            
                            # Save button
                            save_manual_clicked = st.form_submit_button("💾 Save Test Results", type="primary", use_container_width=True)
                            
                            if save_manual_clicked and patient_name:
                                with st.spinner("Saving results..."):
                                    status_text.text("Saving to database...")
                                    progress_bar.progress(90)
                                    
                                    # Collect manual test results
                                    final_results = []
                                    manual_count = st.session_state.get(manual_count_key, 5)
                                    
                                    for i in range(manual_count):
                                        if st.session_state.get(f"include_manual_only_{uploaded_file.name}_{i}", False):
                                            test_name = st.session_state.get(f"manual_only_name_{uploaded_file.name}_{i}", "").strip()
                                            test_value = st.session_state.get(f"manual_only_value_{uploaded_file.name}_{i}", 0.0)
                                            test_unit = st.session_state.get(f"manual_only_unit_{uploaded_file.name}_{i}", "").strip()
                                            
                                            # Only add if test name is provided and value is not zero
                                            if test_name and test_value != 0.0:
                                                final_results.append({
                                                    'test_type': test_name,
                                                    'value': test_value,
                                                    'unit': test_unit,
                                                    'reference_range': ''
                                                })
                                    
                                    if final_results:
                                        # Learn from manual entries
                                        for result in final_results:
                                            file_parser.learning_system._learn_medical_term(result['test_type'])
                                        
                                        # Track manual entry performance
                                        file_parser.learning_system.track_extraction_performance(
                                            document_type="manual_entry",
                                            extraction_methods={"manual": "manual"},
                                            original_count=0,
                                            final_count=len(final_results),
                                            corrected_count=0,
                                            added_count=len(final_results)
                                        )
                                        
                                        success = data_processor.save_test_results(
                                            patient_name=patient_name,
                                            test_date=test_date,
                                            test_results=final_results
                                        )
                                        
                                        progress_bar.progress(100)
                                        
                                        if success:
                                            status_text.text("✅ Successfully processed!")
                                            st.success(f"Successfully saved {len(final_results)} manually entered test results for {patient_name}")
                                        else:
                                            status_text.text("❌ Failed to save")
                                            st.error("Failed to save test results to database")
                                    else:
                                        st.warning("No test results entered to save")
                            elif save_manual_clicked and not patient_name:
                                st.warning("Please enter a patient name to save results")
                        
                        # Show debug information for no results case
                        with st.expander("Debug: Why no results found?"):
                            st.write("**Extracted text preview (first 1000 chars):**")
                            st.text(extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text)
                            
                            if test_data:
                                st.write("**Test data structure:**")
                                st.json(test_data)
                
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
                    st.write("Please try a different file or contact support.")

def view_patients_page(db):
    """Display all patients and their summary information."""
    st.title("👥 View Patients")
    
    patients = db.get_all_patients()
    
    if patients:
        st.write(f"Total patients: {len(patients)}")
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(patients, columns=[
            'Patient Name', 'First Test Date', 'Latest Test Date', 'Total Tests'
        ])
        
        # Format dates
        df['First Test Date'] = pd.to_datetime(df['First Test Date']).dt.strftime('%Y-%m-%d')
        df['Latest Test Date'] = pd.to_datetime(df['Latest Test Date']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(df, use_container_width=True)
        
        # Patient selection for details
        st.subheader("Patient Details")
        selected_patient = st.selectbox(
            "Select a patient to view details",
            options=[patient[0] for patient in patients]
        )
        
        if selected_patient:
            tests = db.get_patient_tests(selected_patient)
            if tests:
                st.write(f"Test results for **{selected_patient}**:")
                
                test_df = pd.DataFrame(tests, columns=[
                    'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
                ])
                test_df['Date'] = pd.to_datetime(test_df['Date']).dt.strftime('%Y-%m-%d')
                
                st.dataframe(test_df, use_container_width=True)
            else:
                st.info("No test results found for this patient.")
    else:
        st.info("No patients found. Upload some test results first.")

def patient_dashboard_page(db, visualization):
    """Display patient dashboard with charts and trends."""
    st.title("📊 Patient Dashboard")
    
    patients = db.get_all_patients()
    
    if not patients:
        st.info("No patients found. Upload some test results first.")
        return
    
    # Patient selection
    patient_names = [patient[0] for patient in patients]
    selected_patient = st.selectbox("Select Patient", patient_names)
    
    if selected_patient:
        # Get patient tests
        tests = db.get_patient_tests(selected_patient)
        
        if tests:
            # Convert to DataFrame
            df = pd.DataFrame(tests, columns=[
                'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
            ])
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Create dashboard
            dashboard_charts = visualization.create_patient_overview_dashboard(selected_patient)
            
            if dashboard_charts:
                # Display charts
                for chart_name, fig in dashboard_charts.items():
                    st.subheader(chart_name)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not create charts for this patient.")
        else:
            st.info(f"No test results found for {selected_patient}")

def search_filter_page(db, visualization):
    """Search and filter test results with visualizations."""
    st.title("🔍 Search & Filter")
    
    # Get available options
    patients = db.get_all_patients()
    test_types = db.get_all_test_types()
    
    if not patients:
        st.info("No data available. Upload some test results first.")
        return
    
    # Search filters
    st.subheader("Search Filters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_patients = st.multiselect(
            "Select Patients",
            options=[patient[0] for patient in patients],
            default=None
        )
        
        start_date = st.date_input("Start Date", value=None)
    
    with col2:
        selected_test_types = st.multiselect(
            "Select Test Types",
            options=test_types,
            default=None
        )
        
        end_date = st.date_input("End Date", value=None)
    
    # Search button
    if st.button("🔍 Search"):
        results = db.search_test_results(
            patient_names=selected_patients if selected_patients else None,
            test_types=selected_test_types if selected_test_types else None,
            start_date=start_date,
            end_date=end_date
        )
        
        if results:
            st.subheader(f"Search Results ({len(results)} records)")
            
            # Display results
            df = pd.DataFrame(results, columns=[
                'Patient', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
            ])
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(df, use_container_width=True)
            
            # Create visualizations if specific test type selected
            if len(selected_test_types) == 1:
                test_type = selected_test_types[0]
                
                if len(selected_patients) == 1:
                    # Single patient trend
                    patient_name = selected_patients[0]
                    trend_fig = visualization.create_trend_chart(df, test_type, patient_name)
                    st.plotly_chart(trend_fig, use_container_width=True)
                else:
                    # Multi-patient comparison
                    comparison_fig = visualization.create_multi_patient_chart(df, test_type)
                    st.plotly_chart(comparison_fig, use_container_width=True)
        else:
            st.info("No results found matching your criteria.")

def export_data_page(db):
    """Export data in various formats."""
    st.title("📁 Export Data")
    
    export_type = st.selectbox(
        "Select export type",
        ["All Data", "Specific Patient", "Date Range", "Test Type"]
    )
    
    if export_type == "Specific Patient":
        patients = db.get_all_patients()
        patient_names = [patient[0] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names)
        
        if selected_patient and st.button("Export Patient Data"):
            patient_tests = db.get_patient_tests(selected_patient)
            if patient_tests:
                df = pd.DataFrame(patient_tests, columns=[
                    'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
                ])
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download {selected_patient} data as CSV",
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
                df = pd.DataFrame(results, columns=[
                    'Patient', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
                ])
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download data from {start_date} to {end_date} as CSV",
                    data=csv,
                    file_name=f"test_results_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
    
    elif export_type == "Test Type":
        test_types = db.get_all_test_types()
        selected_test_type = st.selectbox("Select Test Type", test_types)
        
        if selected_test_type and st.button("Export Test Type Data"):
            results = db.search_test_results(test_types=[selected_test_type])
            if results:
                df = pd.DataFrame(results, columns=[
                    'Patient', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
                ])
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download {selected_test_type} data as CSV",
                    data=csv,
                    file_name=f"{selected_test_type}_results.csv",
                    mime="text/csv"
                )
    
    elif export_type == "All Data":
        if st.button("Export All Data"):
            all_results = db.get_all_test_results()
            if all_results:
                df = pd.DataFrame(all_results, columns=[
                    'Patient', 'Date', 'Test Type', 'Value', 'Unit', 'Reference Range'
                ])
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download all data as CSV",
                    data=csv,
                    file_name="all_test_results.csv",
                    mime="text/csv"
                )

def manage_data_page(db):
    """Manage and delete data."""
    st.title("🗑️ Manage Data")
    st.warning("⚠️ Data deletion is permanent and cannot be undone!")
    
    # Show database statistics
    stats = db.get_database_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Patients", stats['total_patients'])
    with col2:
        st.metric("Total Test Results", stats['total_results'])
    with col3:
        if stats['earliest_test'] and stats['latest_test']:
            date_range = f"{stats['earliest_test']} to {stats['latest_test']}"
            st.metric("Date Range", date_range)
    
    st.subheader("Delete Options")
    
    deletion_type = st.selectbox(
        "What would you like to delete?",
        ["Delete Individual Test Results", "Delete Patient Reports by Date", 
         "Delete Test Type for Patient", "Delete Entire Patient Record", "Delete All Data"]
    )
    
    if deletion_type == "Delete Individual Test Results":
        patients = db.get_all_patients()
        
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[0] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names)
        
        if selected_patient:
            test_results = db.get_patient_test_results_with_ids(selected_patient)
            
            if not test_results:
                st.info(f"No test results found for {selected_patient}")
                return
            
            st.write(f"Test results for **{selected_patient}**:")
            
            # Create checkboxes for each test result
            results_to_delete = []
            for result in test_results:
                result_id, date, test_type, value, unit = result
                checkbox_key = f"delete_{result_id}"
                
                if st.checkbox(
                    f"{date} - {test_type}: {value} {unit}",
                    key=checkbox_key
                ):
                    results_to_delete.append(result_id)
            
            if results_to_delete and st.button("Delete Selected Results", type="primary"):
                deleted_count = 0
                for result_id in results_to_delete:
                    if db.delete_test_result(result_id):
                        deleted_count += 1
                
                if deleted_count > 0:
                    st.success(f"Successfully deleted {deleted_count} test results")
                    st.rerun()
                else:
                    st.error("Failed to delete test results")
    
    elif deletion_type == "Delete Patient Reports by Date":
        patients = db.get_all_patients()
        
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[0] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names)
        
        if selected_patient:
            test_dates = db.get_test_results_by_date(selected_patient)
            
            if not test_dates:
                st.info(f"No test results found for {selected_patient}")
                return
            
            st.write(f"Test dates for **{selected_patient}**:")
            
            for test_date, results in test_dates.items():
                st.write(f"**{test_date}** ({len(results)} tests)")
                
                if st.button(f"Delete all results from {test_date}", key=f"delete_date_{test_date}"):
                    if db.delete_test_results_by_date(selected_patient, test_date):
                        st.success(f"Successfully deleted all results from {test_date}")
                        st.rerun()
                    else:
                        st.error(f"Failed to delete results from {test_date}")
    
    elif deletion_type == "Delete Test Type for Patient":
        patients = db.get_all_patients()
        
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[0] for patient in patients]
        selected_patient = st.selectbox("Select Patient", patient_names)
        
        if selected_patient:
            patient_tests = db.get_patient_tests(selected_patient)
            test_types = list(set([test[1] for test in patient_tests]))
            
            if not test_types:
                st.info(f"No test types found for {selected_patient}")
                return
            
            selected_test_type = st.selectbox("Select Test Type to Delete", test_types)
            
            if selected_test_type and st.button(f"Delete all {selected_test_type} results for {selected_patient}", type="primary"):
                if db.delete_test_results_by_type(selected_patient, selected_test_type):
                    st.success(f"Successfully deleted all {selected_test_type} results for {selected_patient}")
                    st.rerun()
                else:
                    st.error(f"Failed to delete {selected_test_type} results")
    
    elif deletion_type == "Delete Entire Patient Record":
        patients = db.get_all_patients()
        
        if not patients:
            st.info("No patients found.")
            return
        
        patient_names = [patient[0] for patient in patients]
        selected_patient = st.selectbox("Select Patient to Delete", patient_names)
        
        if selected_patient:
            patient_tests = db.get_patient_tests(selected_patient)
            st.warning(f"This will delete **{selected_patient}** and all {len(patient_tests)} test results!")
            
            confirm_text = st.text_input(f"Type '{selected_patient}' to confirm deletion:")
            
            if confirm_text == selected_patient and st.button("DELETE PATIENT", type="primary"):
                if db.delete_patient(selected_patient):
                    st.success(f"Successfully deleted {selected_patient} and all associated data")
                    st.rerun()
                else:
                    st.error(f"Failed to delete {selected_patient}")
    
    elif deletion_type == "Delete All Data":
        stats = db.get_database_stats()
        
        if stats['total_results'] > 0:
            st.error(f"⚠️ This will permanently delete ALL {stats['total_patients']} patients and {stats['total_results']} test results!")
            
            confirm1 = st.checkbox("I understand this action cannot be undone")
            confirm2 = st.checkbox("I want to delete ALL data from the database")
            confirm_text = st.text_input("Type 'DELETE ALL DATA' to confirm:")
            
            if confirm1 and confirm2 and confirm_text == "DELETE ALL DATA":
                if st.button("🗑️ DELETE ALL DATA", type="primary"):
                    if db.delete_all_data():
                        st.success("All data has been deleted from the database")
                        st.rerun()
                    else:
                        st.error("Failed to delete all data.")
        else:
            st.info("Database is already empty.")

def learning_stats_page(learning_system):
    """Display learning system statistics and insights."""
    st.title("🧠 Learning Statistics")
    st.write("Monitor how the system improves through user feedback and corrections")
    
    # Get learning statistics
    stats = learning_system.get_learning_stats()
    
    # Display overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Learned Medical Terms", stats.get('learned_terms', 0))
    
    with col2:
        st.metric("User Corrections", stats.get('user_corrections', 0))
    
    with col3:
        st.metric("Duplicate Patterns", stats.get('duplicate_patterns', 0))
    
    with col4:
        improvement_rate = 0
        if stats.get('user_corrections', 0) > 0:
            improvement_rate = round((stats.get('learned_terms', 0) / stats.get('user_corrections', 1)) * 100, 1)
        st.metric("Learning Efficiency", f"{improvement_rate}%")
    
    # Correction types breakdown
    if stats.get('correction_types'):
        st.subheader("📊 Types of User Corrections")
        correction_data = stats['correction_types']
        
        col1, col2 = st.columns(2)
        
        with col1:
            correction_labels = {
                'name': 'Test Name Corrections',
                'value': 'Value Corrections', 
                'unit': 'Unit Corrections',
                'added': 'Manual Additions',
                'removed': 'Removals'
            }
            
            for correction_type, count in correction_data.items():
                label = correction_labels.get(correction_type, correction_type.title())
                st.write(f"**{label}**: {count}")
        
        with col2:
            if correction_data:
                import plotly.express as px
                import pandas as pd
                
                df = pd.DataFrame(list(correction_data.items()), columns=['Type', 'Count'])
                df['Label'] = df['Type'].map(correction_labels).fillna(df['Type'].str.title())
                
                fig = px.pie(df, values='Count', names='Label', title="Correction Types Distribution")
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
    
    # Learning insights
    st.subheader("💡 Learning Insights")
    
    if stats.get('learned_terms', 0) > 0:
        st.success(f"✅ System has learned {stats['learned_terms']} medical terms from user interactions")
    
    if stats.get('user_corrections', 0) > 0:
        st.info(f"📈 {stats['user_corrections']} corrections have been processed to improve future extractions")
    
    if stats.get('duplicate_patterns', 0) > 0:
        st.info(f"🔍 {stats['duplicate_patterns']} duplicate patterns identified for better deduplication")
    
    if stats.get('learned_terms', 0) == 0:
        st.warning("📚 No learning data yet. Upload some documents and make corrections to train the system!")
    
    # Performance tips
    with st.expander("💡 How to improve system accuracy"):
        st.write("""
        **Tips for training the system:**
        
        1. **Review extracted results** - Always check what the system found before saving
        2. **Correct test names** - Edit any incorrectly identified test names  
        3. **Add missing tests** - Use manual entry for tests the scanner missed
        4. **Remove duplicates** - Uncheck duplicate or incorrect test results
        5. **Be consistent** - Use standard medical terminology for better learning
        
        **The more you use and correct the system, the better it becomes at:**
        - Recognizing medical terminology
        - Avoiding duplicate extractions
        - Improving extraction accuracy
        - Learning your preferred formats
        """)

if __name__ == "__main__":
    main()