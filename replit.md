# Blood Test Results Management System

## Overview

A Streamlit-based web application designed for healthcare professionals to manage, visualize, and analyze patient blood test results. This system facilitates uploading various file formats, storing data in a structured database, and generating meaningful visualizations to track health trends over time. The project aims to provide an intuitive tool for patient health monitoring, offering comprehensive data analysis and reporting capabilities.

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
- **Schema Design**: Tables for patients and test results with foreign key relationships and indexed fields for performance.
- **Data Integrity**: Enforced through foreign key and unique constraints.

### Key Features & Technical Implementations
- **Data Management**: CRUD operations for patients and test results, automatic table creation, and schema management.
- **File Parsing**: Supports PDF, Word, Excel, CSV, XML, and various image formats (JPEG, PNG, BMP, TIFF) with OCR. Features include regex-based extraction, tabular data handling, and intelligent reference range parsing.
- **Data Processing**: Validates patient information, test dates, and result values; includes business logic for patient management and result aggregation.
- **Visualization**: Utilizes Plotly for interactive 2D charts (trend, comparison, grouped) with consistent color schemes, compact layouts, and annotations. Supports category grouping based on investigation standards.
- **Investigation Standards Management**: Manages predefined and user-defined test standards, including reference ranges, units, and aliases. Features auto-synchronization of test results with standard changes and Excel-style editing.
- **AI-Powered Anomaly Detection**: Integrates multiple machine learning algorithms (Isolation Forest, Statistical Outlier, DBSCAN, Temporal, Correlation-based) for comprehensive anomaly detection across patients, providing medical insights and actionable recommendations.
- **Alert System**: Implements a four-level severity system (Critical, High, Medium, Low) for abnormal values based on deviation from normal ranges, with a dedicated alert dashboard and integrated display.
- **Medication Management**: Tracks medications, schedules, adherence, and effectiveness, integrated with test results for analysis. Includes a multi-tab UI for comprehensive management.
- **Document Preview & Comparison**: Provides side-by-side document preview with extracted results, highlighting, search functionality, and tools for verification.
- **Data Filtering & Sorting**: Advanced filtering and sorting capabilities for database records, including multi-column sorting, date/value range filtering, and text search.
- **PDF Report Generation**: Generates comprehensive, shareable PDF reports with patient summaries, tables, and 2D charts.

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