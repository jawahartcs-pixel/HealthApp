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

### July 15, 2025 - Enhanced PDF Parsing
- **Improved PDF Text Extraction**: Added table extraction capability to handle structured lab reports
- **Multiple Pattern Matching**: Implemented tabular, regex, and generic pattern matching for comprehensive test result extraction
- **Enhanced Debug Information**: Added extraction method breakdown and text preview for troubleshooting
- **Better Duplicate Handling**: Refined duplicate removal to be less aggressive while maintaining accuracy

## Development Notes

- **Code Organization**: Clear separation of concerns with modular design
- **Error Handling**: Comprehensive validation and user-friendly error messages
- **Extensibility**: Multi-method file parser can handle various PDF layouts and formats
- **Maintainability**: Well-structured codebase with clear component boundaries
- **PDF Processing**: Enhanced extraction handles both text and tabular data from lab reports