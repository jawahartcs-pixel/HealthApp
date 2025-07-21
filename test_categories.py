"""
Test Categories for Blood Test Results
Maps individual test types to medical categories for organized visualization.
"""

def get_test_categories():
    """Return dictionary mapping test types to their medical categories."""
    return {
        # Metabolic Panel
        'Glucose': 'Metabolic Panel',
        'Fasting Glucose': 'Metabolic Panel',
        'Random Glucose': 'Metabolic Panel',
        'HbA1c': 'Metabolic Panel',
        'Sodium': 'Metabolic Panel',
        'Potassium': 'Metabolic Panel',
        'Chloride': 'Metabolic Panel',
        'CO2': 'Metabolic Panel',
        'BUN': 'Metabolic Panel',
        'Creatinine': 'Metabolic Panel',
        'eGFR': 'Metabolic Panel',
        'Total Protein': 'Metabolic Panel',
        'Albumin': 'Metabolic Panel',
        'Globulin': 'Metabolic Panel',
        'A/G Ratio': 'Metabolic Panel',
        'Bilirubin Total': 'Metabolic Panel',
        'Bilirubin Direct': 'Metabolic Panel',
        'Bilirubin Indirect': 'Metabolic Panel',
        'ALP': 'Metabolic Panel',
        'ALT': 'Metabolic Panel',
        'AST': 'Metabolic Panel',
        'GGT': 'Metabolic Panel',
        
        # Complete Blood Count
        'Hemoglobin': 'Complete Blood Count',
        'Hematocrit': 'Complete Blood Count',
        'RBC Count': 'Complete Blood Count',
        'WBC Count': 'Complete Blood Count',
        'Platelet Count': 'Complete Blood Count',
        'MCV': 'Complete Blood Count',
        'MCH': 'Complete Blood Count',
        'MCHC': 'Complete Blood Count',
        'RDW': 'Complete Blood Count',
        'MPV': 'Complete Blood Count',
        'Neutrophils': 'Complete Blood Count',
        'Lymphocytes': 'Complete Blood Count',
        'Monocytes': 'Complete Blood Count',
        'Eosinophils': 'Complete Blood Count',
        'Basophils': 'Complete Blood Count',
        
        # Lipid Panel
        'Total Cholesterol': 'Lipid Panel',
        'HDL Cholesterol': 'Lipid Panel',
        'LDL Cholesterol': 'Lipid Panel',
        'Triglycerides': 'Lipid Panel',
        'VLDL Cholesterol': 'Lipid Panel',
        'Non-HDL Cholesterol': 'Lipid Panel',
        'Cholesterol/HDL Ratio': 'Lipid Panel',
        
        # Thyroid Function
        'TSH': 'Thyroid Function',
        'T3': 'Thyroid Function',
        'T4': 'Thyroid Function',
        'Free T3': 'Thyroid Function',
        'Free T4': 'Thyroid Function',
        'Reverse T3': 'Thyroid Function',
        'TPO Antibodies': 'Thyroid Function',
        'Thyroglobulin': 'Thyroid Function',
        
        # Cardiac Markers
        'Troponin I': 'Cardiac Markers',
        'Troponin T': 'Cardiac Markers',
        'CK-MB': 'Cardiac Markers',
        'CK Total': 'Cardiac Markers',
        'LDH': 'Cardiac Markers',
        'Myoglobin': 'Cardiac Markers',
        'BNP': 'Cardiac Markers',
        'NT-proBNP': 'Cardiac Markers',
        
        # Inflammatory Markers
        'ESR': 'Inflammatory Markers',
        'CRP': 'Inflammatory Markers',
        'High Sensitivity CRP': 'Inflammatory Markers',
        'Procalcitonin': 'Inflammatory Markers',
        'Ferritin': 'Inflammatory Markers',
        
        # Vitamins & Minerals
        'Vitamin D': 'Vitamins & Minerals',
        'Vitamin B12': 'Vitamins & Minerals',
        'Folate': 'Vitamins & Minerals',
        'Iron': 'Vitamins & Minerals',
        'TIBC': 'Vitamins & Minerals',
        'Transferrin': 'Vitamins & Minerals',
        'Transferrin Saturation': 'Vitamins & Minerals',
        'Calcium': 'Vitamins & Minerals',
        'Phosphorus': 'Vitamins & Minerals',
        'Magnesium': 'Vitamins & Minerals',
        'Zinc': 'Vitamins & Minerals',
        
        # Hormones
        'Testosterone': 'Hormones',
        'Estradiol': 'Hormones',
        'Progesterone': 'Hormones',
        'LH': 'Hormones',
        'FSH': 'Hormones',
        'Prolactin': 'Hormones',
        'Cortisol': 'Hormones',
        'DHEA-S': 'Hormones',
        'IGF-1': 'Hormones',
        'Growth Hormone': 'Hormones',
        'Insulin': 'Hormones',
        'C-Peptide': 'Hormones',
        
        # Coagulation Studies
        'PT': 'Coagulation Studies',
        'PTT': 'Coagulation Studies',
        'INR': 'Coagulation Studies',
        'Fibrinogen': 'Coagulation Studies',
        'D-Dimer': 'Coagulation Studies',
        'Factor V Leiden': 'Coagulation Studies',
        'Protein C': 'Coagulation Studies',
        'Protein S': 'Coagulation Studies',
        
        # Tumor Markers
        'PSA': 'Tumor Markers',
        'CEA': 'Tumor Markers',
        'CA 19-9': 'Tumor Markers',
        'CA 125': 'Tumor Markers',
        'CA 15-3': 'Tumor Markers',
        'AFP': 'Tumor Markers',
        'HCG': 'Tumor Markers',
        
        # Immunology
        'IgA': 'Immunology',
        'IgG': 'Immunology',
        'IgM': 'Immunology',
        'IgE': 'Immunology',
        'Complement C3': 'Immunology',
        'Complement C4': 'Immunology',
        'ANA': 'Immunology',
        'Anti-dsDNA': 'Immunology',
        'RF': 'Immunology',
        'Anti-CCP': 'Immunology'
    }

def categorize_test_types(test_types):
    """Categorize a list of test types and return grouped dictionary."""
    categories = get_test_categories()
    grouped = {}
    
    for test_type in test_types:
        category = categories.get(test_type, 'Other Tests')
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(test_type)
    
    return grouped

def get_category_colors():
    """Return color scheme for different test categories."""
    return {
        'Metabolic Panel': '#FF6B6B',
        'Complete Blood Count': '#4ECDC4', 
        'Lipid Panel': '#45B7D1',
        'Thyroid Function': '#96CEB4',
        'Cardiac Markers': '#FFEAA7',
        'Inflammatory Markers': '#DDA0DD',
        'Vitamins & Minerals': '#98D8C8',
        'Hormones': '#F7DC6F',
        'Coagulation Studies': '#BB8FCE',
        'Tumor Markers': '#85C1E9',
        'Immunology': '#F8C471',
        'Other Tests': '#D7DBDD'
    }