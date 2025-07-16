# Blood Test Results Management System

## Overview

A Streamlit-based web application for managing, visualizing, and analyzing patient blood test results. The system allows healthcare professionals to upload test results from various file formats, store them in a structured database, and create meaningful visualizations to track patient health trends over time.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application framework
- **Design Pattern**: Multi-page application with sidebar navigation
- **UI Components**: Forms, data tables, charts, file uploaders
- **Caching**: Streamlit resource caching for database connections and components

### Backend Architecture
- **Language**: Python
- **Architecture Pattern**: Modular component-based design
- **Core Components**:
  - Database layer for data persistence
  - File parser for extracting test results from documents
  - Data processor for validation and business logic
  - Visualization engine for charts and graphs
  - Utility functions for data validation and formatting

### Data Storage Solution
- **Database**: SQLite for local data storage
- **Schema Design**: 
  - Patients table with unique patient identification
  - Test results table with foreign key relationships
  - Indexed fields for performance optimization
- **Data Integrity**: Foreign key constraints and unique constraints

## Key Components

### Database Module (`database.py`)
- **Purpose**: Handles all data persistence operations
- **Features**: 
  - Automatic table creation and schema management
  - CRUD operations for patients and test results
  - Performance optimization through indexing
  - Data export capabilities

### File Parser Module (`file_parser.py`)
- **Purpose**: Extracts test results from uploaded documents
- **Supported Formats**: PDF files (extensible to other formats)
- **Pattern Recognition**: Regex-based extraction for common blood test parameters
- **Test Categories Supported**:
  - Glucose and diabetes markers
  - Cholesterol and lipid panels
  - Complete blood count (CBC)
  - Liver function tests
  - Kidney function tests
  - Thyroid function tests
  - Electrolyte panels

### Data Processor Module (`data_processor.py`)
- **Purpose**: Validates and processes test data before storage
- **Validation Logic**: 
  - Patient name format validation
  - Test date validation
  - Test result value validation
- **Business Logic**: Patient management and result aggregation

### Visualization Module (`visualization.py`)
- **Purpose**: Creates interactive charts and graphs
- **Chart Library**: Plotly for interactive visualizations
- **Chart Types**: Trend charts, comparison charts, dashboard views
- **Color Coding**: Consistent color scheme for different test types

### Utility Module (`utils.py`)
- **Purpose**: Common helper functions
- **Functions**: Date validation, value formatting, reference range parsing

## Data Flow

1. **File Upload**: Users upload blood test documents through Streamlit interface
2. **Data Extraction**: File parser extracts test results using pattern matching
3. **Data Validation**: Data processor validates extracted information
4. **Data Storage**: Validated results are stored in SQLite database
5. **Data Retrieval**: Database queries retrieve patient and test data
6. **Data Visualization**: Visualization module creates charts and dashboards
7. **Data Export**: Results can be exported for external use

## External Dependencies

### Core Libraries
- **Streamlit**: Web application framework for the user interface
- **Pandas**: Data manipulation and analysis
- **SQLite3**: Database operations (built into Python)
- **Plotly**: Interactive visualization library
- **PDFPlumber**: PDF text extraction for file parsing

### File Processing
- **Regex**: Pattern matching for test result extraction
- **DateTime**: Date handling and validation
- **IO**: File stream handling

## Deployment Strategy

### Local Deployment
- **Environment**: Python virtual environment recommended
- **Database**: SQLite file-based database (no external database server required)
- **Storage**: Local file system for uploaded documents and database
- **Configuration**: Minimal setup required, self-contained application

### Scalability Considerations
- **Database**: SQLite suitable for single-user or small team usage
- **File Storage**: Local file system adequate for moderate file volumes
- **Performance**: Streamlit caching implemented for database connections
- **Future Enhancements**: Architecture supports migration to PostgreSQL and cloud storage

### Security Considerations
- **Data Privacy**: Local storage keeps patient data secure
- **Access Control**: Application-level access (no built-in authentication)
- **File Validation**: Input validation for uploaded files
- **Data Integrity**: Database constraints prevent invalid data entry

## Recent Changes

### July 16, 2025 - Gender-Specific Reference Ranges
- **Flexible Range Configuration**: Added gender-specific flag to control reference range display
  - Optional gender differentiation for investigation standards with checkbox control
  - When enabled: Shows separate male and female reference ranges with independent min/max/unit values
  - When disabled: Shows single reference range applied to both genders with "(shared)" indicator
  - Existing standards automatically configured based on actual range differences
- **Enhanced Standards Management**: Updated investigation standards interface
  - Gender-specific checkbox in both view/edit and add new standard forms
  - Dynamic UI that shows appropriate range inputs based on gender-specific setting
  - Smart range display in preview showing "(shared)" for unified ranges
  - Database schema updated to include gender_specific boolean column
- **Backward Compatibility**: Seamless integration with existing data
  - Automatic column addition to existing investigation_standards table
  - Default gender_specific=False for existing standards with same ranges
  - True for standards like Hemoglobin, Creatinine where ranges actually differ by gender

### July 16, 2025 - Investigation Type Dropdown with Fuzzy Matching
- **Smart Investigation Selection**: Replaced text inputs with intelligent dropdown selections in extraction details
  - Investigation type selectboxes display all standardized investigation names from the standards table
  - Automatic fuzzy matching pre-selects the best match when extraction finds similar test names
  - If no match found, original extracted name appears first in dropdown with all standards below
  - Match score and standardization information displayed when fuzzy matching occurs
- **Additional Test Enhancement**: Enhanced manual test addition with same dropdown approach
  - Additional tests can be selected from standardized investigation types
  - Custom test name option available when standard types don't match
  - Seamless integration with standardization system for consistent data entry
- **Session State Integration**: Investigation standards available throughout upload workflow
  - Standards component stored in session state for access across upload pages
  - Real-time fuzzy matching during extraction preview and editing
  - Consistent standardization whether tests are extracted or manually added

### July 15, 2025 - Document Preview & Comparison System
- **Side-by-Side Document Verification**: Implemented comprehensive document preview feature for upload validation
  - Real-time document text extraction and display alongside parsed results
  - Search functionality within document content with occurrence counting
  - Quick search buttons for extracted test values to locate them in source document
  - File information display showing name, size, and extraction method used
- **Enhanced Result Verification**: Built-in comparison tools for accuracy checking
  - Tooltip help text showing original extracted values for each editable field
  - Source information display showing extraction method (tabular, OCR, regex, etc.)
  - Extraction method breakdown with test counts per method
  - Raw text preview for debugging extraction issues
- **Improved Form Structure**: Fixed critical form validation and interaction issues
  - Proper form submit button implementation for result saving
  - Separated interactive elements from form structure to prevent errors
  - Quick search functionality positioned outside form for proper operation
  - Maintained all preview and editing capabilities without form conflicts

### July 15, 2025 - AI-Powered Anomaly Detection System
- **Advanced Machine Learning Integration**: Created comprehensive AI anomaly detection system using multiple algorithms
  - Isolation Forest for multivariate anomaly detection
  - Statistical outlier detection using Z-score and IQR methods
  - DBSCAN clustering for pattern-based anomaly identification
  - Temporal anomaly detection for trend analysis
  - Correlation-based anomaly detection using Elliptic Envelope
  - Medical pattern recognition for clinical insights
- **Multi-Algorithm Analysis**: Implemented ensemble approach combining six different detection methods
  - Each algorithm targets specific types of anomalies
  - Results are combined for comprehensive analysis
  - Severity scoring based on multiple factors
  - Confidence levels for each detection method
- **Intelligent Medical Insights**: Built-in medical knowledge for pattern recognition
  - Diabetes risk assessment from glucose patterns
  - Cardiovascular risk evaluation from lipid profiles
  - Kidney function monitoring from creatinine/BUN levels
  - Anemia detection from hemoglobin/hematocrit values
  - Liver function assessment from enzyme levels
- **Interactive Analysis Interface**: Dedicated AI anomaly detection page with multiple analysis modes
  - All patients analysis with comprehensive overview
  - Individual patient analysis with personalized insights
  - Trend analysis showing anomaly patterns over time
  - Visual charts and severity distribution displays
  - Actionable recommendations based on detected patterns
- **Real-Time Processing**: AI analysis runs on-demand with progress indicators
  - Spinner animations during analysis processing
  - Error handling for insufficient data scenarios
  - Caching for improved performance
  - User-friendly result presentation with color coding

### July 15, 2025 - Alert System for Abnormal Values
- **Comprehensive Alert System**: Created intelligent alert system for abnormal test results
  - Critical value thresholds for immediate medical attention
  - Four-level alert severity system (Critical, High, Medium, Low)
  - Automatic severity determination based on deviation from normal ranges
  - Test-specific recommendations and clinical guidance
- **Alert Dashboard**: Dedicated page for monitoring all alerts across patients
  - Real-time alert summary with metrics and counters
  - Advanced filtering by alert level and patient
  - Visual alert indicators with color coding and icons
  - Recent alerts tracking (last 7 days)
- **Integrated Alert Display**: Enhanced existing pages with alert information
  - Patient dashboard shows active alerts with expandable details
  - View patients page displays alert counts and recent alerts
  - Color-coded visual indicators for different alert levels
  - Actionable recommendations for each alert type
- **Smart Alert Logic**: Intelligent alert generation system
  - Reference range-based normal value checking
  - Critical threshold monitoring for emergency situations
  - Test-specific medical recommendations
  - Trend analysis capabilities for pattern detection

### July 15, 2025 - Multiple File Format Support
- **Enhanced File Parser**: Added support for multiple file formats beyond PDF and Word
  - Excel files (.xlsx, .xls) with multi-sheet support
  - CSV files with structured data parsing
  - XML files with hierarchical data extraction
  - Improved text extraction from tabular data in Excel
- **Updated File Upload Interface**: Enhanced file uploader to accept new formats
  - Added Excel, CSV, and XML to supported file types
  - Updated help text to reflect all supported formats
  - Maintained backward compatibility with existing PDF and Word support
- **Robust Error Handling**: Added comprehensive error handling for new file formats
  - Graceful handling of malformed files
  - Clear error messages for unsupported content
  - Automatic fallback mechanisms for parsing issues
- **Dependencies Management**: Added required packages for new file format support
  - openpyxl for Excel file processing
  - xlrd for legacy Excel format support
  - lxml for XML parsing capabilities
  - pandas integration for structured data handling

### July 15, 2025 - Advanced Table Filtering & Sorting System
- **Enhanced Complete Database Records Table**: Added comprehensive filtering and sorting capabilities
  - Multi-column sorting (Date, Test Type, Value, Unit) with ascending/descending options
  - Test type filter dropdown with all available test types
  - Date range filtering with start and end date pickers
  - Value range filtering with slider control for numeric values
  - Text search functionality across test type, unit, and reference range
  - Reset filters button to clear all applied filters
- **Improved Table Display**: Enhanced visual presentation and interaction
  - Column configuration with proper formatting (dates, numbers, text)
  - Export functionality with CSV download for filtered results
  - Result count display showing filtered vs total records
  - Empty state handling with appropriate messages
  - Timestamped export filenames for easy file management
- **Better User Experience**: Streamlined interface with organized controls
  - Two-row layout for filter controls (sorting/test type, then date/value ranges)
  - Clear visual separation between filter controls and data display
  - Real-time filtering updates as users adjust controls
  - Professional table styling with consistent column widths

### July 15, 2025 - Separated Data Management & Streamlined Dashboard
- **Dedicated Data Management Page**: Moved comprehensive editing features to separate "Manage Data" page
  - "View & Edit Patient Data" section with complete editable interface
  - Individual result editing with form-based interface
  - Multiple result deletion with checkbox selection
  - Date-grouped editing for batch operations
  - Complete database records table with all test results
- **Streamlined Patient Dashboard**: Focused on visualization and quick insights
  - Individual investigation graphs for each test type
  - Dates from database only on x-axis with proper date formatting
  - Value ranges on y-axis with appropriate units
  - Link to data management page for editing
  - Quick summary statistics for total records, test dates, and test types
- **Enhanced Data Visualization**: Improved chart layout and functionality
  - Proper date handling without random dates
  - Auto-adjusted date ranges based on actual test dates
  - Clean graph styling with grid lines and hover information
  - Individual color coding for different investigation types
- **Direct Database Integration**: Real-time database updates in management page
  - Update test type, value, unit, date, and reference range
  - Immediate deletion of individual or multiple results
  - Bulk operations for date-specific result management
- **Enhanced Safety Features**: Built-in safeguards for data integrity
  - Confirmation warnings for destructive operations
  - Transaction-based updates with rollback capability
  - Real-time UI updates after database changes

### July 15, 2025 - Manual Test Addition & Enhanced Duplicate Removal
- **Manual Test Addition**: Added ability to add tests not captured by scanning
  - Dynamic input fields for investigation type, value, and unit
  - Configurable number of additional tests (up to 20)
  - Separate section for manual tests with include/exclude checkboxes
  - Combined saving of extracted and manual tests
- **Enhanced Duplicate Removal**: Improved duplicate detection for scanned documents
  - Smart name similarity calculation using Jaccard similarity
  - OCR variation detection for common character substitutions (o/0, l/1, rn/m)
  - Medical synonym recognition (glucose/sugar, cholesterol/chol)
  - Source-priority based duplicate resolution
  - Lenient value thresholds for OCR-extracted content
- **Improved Editing Interface**: Enhanced the preview and edit system
  - Clear separation between extracted and manual tests
  - Investigation type, value, and unit columns for consistency
  - Patient name and date remain editable before saving
  - Real-time count of extracted vs additional tests

### July 15, 2025 - OCR Implementation & Preview/Edit Interface
- **OCR Integration**: Added Tesseract OCR support for image-based and scanned PDFs
  - Automatic OCR fallback when standard extraction yields limited text
  - Force OCR option with checkbox for problematic documents
  - Enhanced medical term correction for common OCR errors
  - High-quality 300 DPI processing for better accuracy
- **Preview & Edit Interface**: Added comprehensive review system before saving results
  - Interactive table for editing test names, values, and units
  - Checkbox system to include/exclude individual tests
  - Patient name editing with improved extraction patterns
  - Form-based editing with real-time preview
- **Enhanced Patient Name Recognition**: Prioritized patterns looking for text near "Name"
- **Multi-Layer Extraction Strategy**: 5-tier approach with priority system
  - Tabular extraction > Line analysis > OCR patterns > Regex > Generic
- **Improved Debug Information**: Enhanced extraction method tracking and raw text preview

### July 15, 2025 - Enhanced PDF Parsing & Data Management
- **Improved PDF Text Extraction**: Added table extraction capability to handle structured lab reports
- **Multiple Pattern Matching**: Implemented tabular, regex, and generic pattern matching for comprehensive test result extraction
- **Enhanced Debug Information**: Added extraction method breakdown and text preview for troubleshooting
- **Better Duplicate Handling**: Refined duplicate removal to be less aggressive while maintaining accuracy
- **Comprehensive Data Management**: Added new "Manage Data" page with multiple deletion options:
  - Delete individual test results with multi-select capability
  - Delete entire reports by date
  - Delete all results of a specific test type for a patient
  - Delete complete patient records with confirmation
  - Delete all database data with multiple safety confirmations

## Development Notes

- **Code Organization**: Clear separation of concerns with modular design
- **Error Handling**: Comprehensive validation and user-friendly error messages
- **Extensibility**: Multi-method file parser can handle various PDF layouts and formats
- **Maintainability**: Well-structured codebase with clear component boundaries
- **PDF Processing**: Enhanced extraction handles both text and tabular data from lab reports