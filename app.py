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
        ["Upload Results", "View Patients", "Patient Dashboard", "Search & Filter", "Export Data"]
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

def upload_results_page(file_parser, data_processor):
    st.header("📁 Upload Blood Test Results")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose blood test result files",
        type=['pdf', 'txt'],
        accept_multiple_files=True,
        help="Upload PDF or text files containing blood test results"
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
                    extracted_text = file_parser.parse_file(uploaded_file)
                    
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
                    
                    # Manual patient info input if not found
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        patient_name = st.text_input(
                            f"Patient Name for {uploaded_file.name}",
                            value=test_data.get('patient_name', ''),
                            key=f"name_{uploaded_file.name}"
                        )
                    
                    with col2:
                        test_date = st.date_input(
                            f"Test Date for {uploaded_file.name}",
                            value=test_data.get('test_date', date.today()),
                            key=f"date_{uploaded_file.name}"
                        )
                    
                    if patient_name:
                        status_text.text("Saving to database...")
                        progress_bar.progress(90)
                        
                        # Save to database
                        success = data_processor.save_test_results(
                            patient_name=patient_name,
                            test_date=test_date,
                            test_results=test_data['results']
                        )
                        
                        progress_bar.progress(100)
                        
                        if success:
                            status_text.text("✅ Successfully processed!")
                            st.success(f"Successfully saved {len(test_data['results'])} test results for {patient_name}")
                            
                            # Display extracted data
                            if test_data['results']:
                                st.subheader(f"Extracted Test Results ({len(test_data['results'])} tests found)")
                                df = pd.DataFrame(test_data['results'])
                                st.dataframe(df, use_container_width=True)
                                
                                # Show extraction method breakdown
                                with st.expander("Debug: Extraction details"):
                                    extraction_methods = {}
                                    for result in test_data['results']:
                                        method = result.get('source', 'regex')
                                        extraction_methods[method] = extraction_methods.get(method, 0) + 1
                                    
                                    st.write("Tests extracted by method:")
                                    for method, count in extraction_methods.items():
                                        st.write(f"- {method.title()}: {count} tests")
                        else:
                            status_text.text("❌ Failed to save")
                            st.error("Failed to save test results to database")
                    else:
                        st.warning("Please enter patient name to save the results")
                        
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

if __name__ == "__main__":
    main()
