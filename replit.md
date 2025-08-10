# Blood Test Results Management System

## Overview

A Streamlit-based web application designed for healthcare professionals to manage, visualize, and analyze patient blood test results. This system facilitates uploading various file formats, storing data in a structured database, and generating meaningful visualizations to track health trends over time. The project aims to provide an intuitive tool for patient health monitoring, offering comprehensive data analysis and reporting capabilities.

## Recent Changes (August 2025)

### Enhanced Patient Profile Management
- Added date of birth field to patient profiles with automatic age calculation
- Database schema updated with date_of_birth column
- Profile forms now derive age from birth date for better accuracy

### Improved Alert System Terminology
- Updated alert levels from "Low/Medium/High/Critical" to "Minor Alert/Medium Alert/High Alert/Critical Alert"
- Enhanced alert headers now display complete status with values and dates: "CHOL/HDL is high: 5.74(2025-07-17)"
- Alert display uses descriptive labels for better user understanding

### Enhanced OCR Accuracy
- Improved patient name extraction with "patient" tag priority for intelligent identification
- Enhanced date extraction patterns to correctly identify recent years (2022-2025) over older dates
- Updated regex patterns for better medical document parsing

## User Preferences

Preferred communication style: Simple, everyday language.
User prefers beautiful 2D graph designs over 3D for better performance and readability.
User wants proper category grouping for visualizations using the investigation standards table.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application framework.
- **Design Pattern**: Multi-page application with sidebar navigation.
- **UI Components**: Forms, data tables, interactive charts, file uploaders.
- **Caching**: Streamlit's built-in caching for database connections and components.

### Backend Architecture
- **Language**: Python.
- **Architecture Pattern**: Modular, component-based design.
- **Core Components**:
    - Database layer for data persistence.
    - File parser for extracting test results from diverse document formats.
    - Data processor for validation and business logic.
    - Visualization engine for dynamic charts and graphs.
    - Utility functions for data validation and formatting.

### Data Storage Solution
- **Database**: SQLite for local data storage.
- **Schema Design**: Tables for patients, test results, and patient documents with foreign key relationships and indexed fields for performance. Extended patient table includes comprehensive profile fields (age, gender, contact information, medical history, medications, allergies, emergency contacts, notes).
- **Data Integrity**: Enforced through foreign key and unique constraints.
- **Document Storage**: Physical file storage with database metadata tracking, supporting original filename preservation and multiple file formats.

### Key Features & Technical Implementations
- **Data Management**: CRUD operations for patients and test results, automatic table creation, and schema management.
- **File Parsing**: Supports PDF, Word, Excel, CSV, XML, and various image formats (JPEG, PNG, BMP, TIFF) with OCR. Features include regex-based extraction, tabular data handling, and intelligent reference range parsing.
- **Data Processing**: Validates patient information, test dates, and result values; includes business logic for patient management and result aggregation.
- **Visualization**: Utilizes Plotly for interactive 2D charts (trend, comparison, grouped) with consistent color schemes, compact layouts, and annotations. Supports category grouping based on investigation standards and gender-specific reference ranges with visual indicators.
- **Investigation Standards Management**: Manages predefined and user-defined test standards, including reference ranges, units, and aliases. Features auto-synchronization of test results with standard changes and Excel-style editing.
- **AI-Powered Anomaly Detection**: Integrates multiple machine learning algorithms (Isolation Forest, Statistical Outlier, DBSCAN, Temporal, Correlation-based) for comprehensive anomaly detection across patients, providing medical insights and actionable recommendations.
- **Alert System**: Implements a four-level severity system (Critical Alert, High Alert, Medium Alert, Minor Alert) for abnormal values based on deviation from normal ranges, with enhanced headers showing complete status and values, and a dedicated alert dashboard with integrated display.
- **Medication Management**: Tracks medications, schedules, adherence, and effectiveness, integrated with test results for analysis. Includes a multi-tab UI for comprehensive management.
- **Document Preview & Comparison**: Provides side-by-side document preview with extracted results, highlighting, search functionality, and tools for verification.
- **Data Filtering & Sorting**: Advanced filtering and sorting capabilities for database records, including multi-column sorting, date/value range filtering, and text search.
- **PDF Report Generation**: Generates comprehensive, shareable PDF reports with patient summaries, tables, and 2D charts.
- **Comprehensive Patient Profile Management**: Three-tab system including patient directory with search, detailed profile management with age/gender/contact/medical information, and document upload/management with original filename preservation and file type support.
- **Gender-Specific Reference Ranges**: Visualization system automatically applies appropriate reference ranges based on patient gender, with color-coded indicators and fallback logic for missing data.

## External Dependencies

### Core Libraries
- **Streamlit**: Web application framework.
- **Pandas**: Data manipulation and analysis.
- **SQLite3**: Database operations (built-in).
- **Plotly**: Interactive visualization library.
- **PDFPlumber**: PDF text extraction.
- **ReportLab**: PDF report generation.
- **Tesseract**: OCR processing (for image and scanned PDF support).
- **Scikit-learn**: For anomaly detection algorithms (e.g., Isolation Forest, DBSCAN).

### File Processing
- **Regex**: Pattern matching.
- **DateTime**: Date handling.
- **IO**: File stream handling.
- **openpyxl**: Excel file processing (.xlsx).
- **xlrd**: Legacy Excel format support (.xls).
- **lxml**: XML parsing.