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

### July 15, 2025 - Enhanced Manual Entry & Comprehensive Form Interface
- **Manual Test Entry**: Added ability to manually enter additional test results not detected by scanner
  - Dynamic row addition for unlimited manual test entries
  - Three-column format: Investigation Type, Value, Unit with Include checkboxes
  - Automatic filtering of empty entries (requires test name and non-zero value)
  - Separate tracking for extracted vs manually entered tests
- **Unified Form Interface**: Comprehensive single-form workflow for all data entry
  - Editable patient name and test date within the form
  - Combined extracted and manual test results in one submission
  - Clear separation between auto-extracted and manually added tests
  - Smart validation for manual entries
- **Word Document Support**: Added Microsoft Word (.docx) file upload capability
  - Extracts text from both paragraphs and tables in Word documents
  - Seamless integration with existing PDF and text file processing
- **Enhanced Medical Terminology Validation**: Improved filtering of test results
  - Comprehensive medical terms database with 40+ test types
  - Smart keyword matching for medical terminology
  - Abbreviation recognition (HbA1c, HDL, LDL, TSH, etc.)
  - Only medical test values are saved to database

### July 15, 2025 - OCR Implementation & Preview/Edit Interface  
- **OCR Integration**: Added Tesseract OCR support for image-based and scanned PDFs
  - Automatic OCR fallback when standard extraction yields limited text
  - Force OCR option with checkbox for problematic documents
  - Enhanced medical term correction for common OCR errors
  - High-quality 300 DPI processing for better accuracy
- **Enhanced Patient Name Recognition**: Prioritized patterns looking for text near "Name" with Mr/Mrs prefixes
- **DD-MM-YY Date Format**: Prioritized DD-MM-YY format recognition at document top
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