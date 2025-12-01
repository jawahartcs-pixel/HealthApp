# Blood Test Results Management System

## Overview
A Streamlit-based web application for healthcare professionals to manage, visualize, and analyze patient blood test results. The system supports uploading various file formats, storing data in a structured database, and generating visualizations to track health trends. It aims to be an intuitive tool for patient health monitoring, offering comprehensive data analysis, reporting, and AI-powered anomaly detection capabilities.

## User Preferences
Preferred communication style: Simple, everyday language.
User prefers beautiful 2D graph designs over 3D for better performance and readability.
User wants proper category grouping for visualizations using the investigation standards table.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application.
- **Design Pattern**: Multi-page application with sidebar navigation, forms, data tables, interactive charts, and file uploaders.
- **Caching**: Streamlit's built-in caching for database connections and components.

### Backend Architecture
- **Language**: Python.
- **Architecture Pattern**: Modular, component-based design.
- **Core Components**: Database layer, file parser, data processor, visualization engine, and utility functions.

### Data Storage Solution
- **Database**: SQLite for local data storage.
- **Schema Design**: Tables for patients, test results, patient documents, and patient events, with foreign key relationships and indexed fields. Comprehensive patient profile fields include age, gender, contact information, medical history, medications, allergies, emergency contacts, and notes.
- **Data Integrity**: Enforced through foreign key and unique constraints.
- **Document Storage**: Physical file storage with database metadata tracking, supporting original filename preservation and multiple file formats.

### Key Features & Technical Implementations
- **Data Management**: CRUD operations for patients and test results, automatic table creation, and schema management.
- **File Parsing**: Supports PDF, Word, Excel, CSV, XML, and various image formats (JPEG, PNG, BMP, TIFF) with OCR, including regex-based extraction and intelligent reference range parsing.
- **Data Processing**: Validates patient information, test dates, and result values, incorporating business logic for patient management and result aggregation.
- **Visualization**: Utilizes Plotly for interactive 2D charts (trend, comparison, grouped) with consistent color schemes, compact layouts, and annotations. Supports category grouping based on investigation standards and gender-specific reference ranges with visual indicators and event markers.
- **Investigation Standards Management**: Manages predefined and user-defined test standards, including reference ranges, units, and aliases, with auto-synchronization and Excel-style editing.
- **AI-Powered Anomaly Detection**: Integrates multiple machine learning algorithms (Isolation Forest, Statistical Outlier, DBSCAN, Temporal, Correlation-based) for comprehensive anomaly detection and medical insights.
- **Alert System**: Implements a four-level severity system ("Minor Alert" to "Critical Alert") for abnormal values based on deviation from normal ranges, with enhanced headers and a dedicated alert dashboard.
- **Enhanced Medication Management**: Advanced medication tracking with flexible scheduling, an automated email reminder system, adherence monitoring, and effectiveness analysis. Features a multi-tab UI with email notification management and intelligent interval-based reminder scheduling.
- **Patient Event Tracking**: Comprehensive system for tracking medical events (surgeries, treatments, diagnoses) with full CRUD operations, integrated into visualizations as event markers, and supporting correlation analysis.
- **Document Preview & Comparison**: Side-by-side document preview with extracted results, highlighting, search, and verification tools.
- **Data Filtering & Sorting**: Advanced filtering and sorting for database records, including multi-column sorting, date/value range filtering, and text search.
- **Threshold Comparison Filter**: Optional filter comparing two selected reports to show only tests with values that changed above a specified percentage threshold (1-100%, default 20%). When enabled, filters reports, events, alerts, visualizations, and downloads to focus on significant changes.
- **PDF Report Generation**: Generates comprehensive, shareable PDF reports with patient summaries, tables, and 2D charts, respecting applied filters.
- **Comprehensive Patient Profile Management**: Three-tab system for patient directory, detailed profile management (age/gender/contact/medical information), and document upload/management.
- **Gender-Specific Reference Ranges**: Visualization system automatically applies appropriate reference ranges based on patient gender, with color-coded indicators.

## External Dependencies

### Core Libraries
- **Streamlit**: Web application framework.
- **Pandas**: Data manipulation and analysis.
- **SQLite3**: Database operations.
- **Plotly**: Interactive visualization library.
- **PDFPlumber**: PDF text extraction.
- **ReportLab**: PDF report generation.
- **Pillow (PIL)**: Image processing.
- **pytesseract**: OCR processing (interface to Tesseract).
- **Scikit-learn**: Machine learning algorithms (Isolation Forest, DBSCAN).

### File Processing
- **Regex**: Pattern matching.
- **DateTime**: Date handling.
- **IO**: File stream handling.
- **openpyxl**: Excel file processing (.xlsx).
- **xlrd**: Legacy Excel format support (.xls).
- **lxml**: XML parsing.