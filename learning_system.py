import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple
import re
from difflib import SequenceMatcher

class LearningSystem:
    def __init__(self, db_path: str = "learning_data.db"):
        """Initialize the learning system with persistent storage."""
        self.db_path = db_path
        self.init_learning_database()
        
    def init_learning_database(self):
        """Create learning database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Medical terminology learning table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_medical_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_term TEXT,
                corrected_term TEXT,
                frequency INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.5,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(original_term, corrected_term)
            )
        ''')
        
        # User corrections learning table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extraction_method TEXT,
                original_value TEXT,
                corrected_value TEXT,
                test_type TEXT,
                correction_type TEXT, -- 'name', 'value', 'unit', 'added', 'removed'
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Duplicate patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS duplicate_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern_data TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern_type, pattern_data)
            )
        ''')
        
        # Extraction performance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extraction_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT,
                extraction_method TEXT,
                tests_found INTEGER,
                tests_kept INTEGER,
                tests_corrected INTEGER,
                tests_added INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def learn_from_user_edits(self, original_results: List[Dict], final_results: List[Dict], 
                             extraction_methods: Dict[str, str]):
        """Learn from user corrections and edits."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Track what was corrected
        corrected_count = 0
        added_count = 0
        
        # Learn from corrections to extracted results
        original_map = {f"{r['test_type']}_{r['value']}": r for r in original_results}
        final_map = {f"{r['test_type']}_{r['value']}": r for r in final_results}
        
        # Find corrections
        for key, original in original_map.items():
            if key in final_map:
                final = final_map[key]
                if original['test_type'] != final['test_type']:
                    # Test name was corrected
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_corrections 
                        (extraction_method, original_value, corrected_value, test_type, correction_type)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        extraction_methods.get(original['test_type'], 'unknown'),
                        original['test_type'],
                        final['test_type'], 
                        final['test_type'],
                        'name'
                    ))
                    corrected_count += 1
                
                if abs(original['value'] - final['value']) > 0.01:
                    # Value was corrected
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_corrections 
                        (extraction_method, original_value, corrected_value, test_type, correction_type)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        extraction_methods.get(original['test_type'], 'unknown'),
                        str(original['value']),
                        str(final['value']),
                        final['test_type'],
                        'value'
                    ))
                    corrected_count += 1
        
        # Find added tests (not in original)
        for final in final_results:
            key = f"{final['test_type']}_{final['value']}"
            if key not in original_map:
                cursor.execute('''
                    INSERT INTO user_corrections 
                    (extraction_method, original_value, corrected_value, test_type, correction_type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    'manual',
                    '',
                    final['test_type'],
                    final['test_type'],
                    'added'
                ))
                added_count += 1
        
        # Update medical terminology learning
        for result in final_results:
            self._learn_medical_term(result['test_type'])
        
        conn.commit()
        conn.close()
        
        return corrected_count, added_count
    
    def _learn_medical_term(self, term: str):
        """Learn and validate medical terminology."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        normalized_term = self._normalize_term(term)
        
        cursor.execute('''
            INSERT OR REPLACE INTO learned_medical_terms 
            (original_term, corrected_term, frequency, confidence_score)
            VALUES (?, ?, COALESCE((SELECT frequency FROM learned_medical_terms WHERE original_term = ?), 0) + 1, ?)
        ''', (term, normalized_term, term, self._calculate_confidence(term)))
        
        conn.commit()
        conn.close()
    
    def _normalize_term(self, term: str) -> str:
        """Normalize medical term for consistency."""
        # Common medical term standardizations
        term = term.lower().strip()
        
        # Apply learned corrections
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT corrected_term FROM user_corrections 
            WHERE LOWER(original_value) = ? AND correction_type = 'name'
            ORDER BY timestamp DESC LIMIT 1
        ''', (term,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # Standard normalizations
        normalizations = {
            'hba1c': 'HbA1c',
            'hemoglobin a1c': 'HbA1c',
            'total cholesterol': 'Total Cholesterol',
            'hdl cholesterol': 'HDL Cholesterol',
            'ldl cholesterol': 'LDL Cholesterol',
            'white blood cell count': 'WBC Count',
            'red blood cell count': 'RBC Count',
            'platelet count': 'Platelet Count'
        }
        
        return normalizations.get(term, term.title())
    
    def _calculate_confidence(self, term: str) -> float:
        """Calculate confidence score for medical term."""
        # Base confidence based on term characteristics
        confidence = 0.5
        
        # Higher confidence for known medical abbreviations
        medical_abbrevs = {'hba1c', 'hdl', 'ldl', 'rbc', 'wbc', 'tsh', 't3', 't4', 'alt', 'ast'}
        if term.lower() in medical_abbrevs:
            confidence += 0.3
        
        # Higher confidence for terms with medical keywords
        medical_keywords = ['glucose', 'cholesterol', 'hemoglobin', 'protein', 'vitamin']
        for keyword in medical_keywords:
            if keyword in term.lower():
                confidence += 0.2
                break
        
        return min(confidence, 1.0)
    
    def get_learned_medical_terms(self) -> Set[str]:
        """Get all learned medical terms."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT corrected_term FROM learned_medical_terms')
        terms = {row[0].lower() for row in cursor.fetchall()}
        
        conn.close()
        return terms
    
    def smart_duplicate_removal(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Advanced duplicate removal using learned patterns."""
        if not results:
            return results
        
        # Group similar results
        groups = []
        for result in results:
            added_to_group = False
            for group in groups:
                if self._are_similar_results(result, group[0]):
                    group.append(result)
                    added_to_group = True
                    break
            if not added_to_group:
                groups.append([result])
        
        # Select best result from each group
        final_results = []
        for group in groups:
            if len(group) == 1:
                final_results.append(group[0])
            else:
                best_result = self._select_best_from_group(group)
                final_results.append(best_result)
                
                # Learn duplicate pattern
                self._learn_duplicate_pattern(group)
        
        return final_results
    
    def _are_similar_results(self, result1: Dict, result2: Dict) -> bool:
        """Check if two results are similar (potential duplicates)."""
        # Check test name similarity
        name1 = self._normalize_term(result1['test_type'])
        name2 = self._normalize_term(result2['test_type'])
        
        name_similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        
        # Check value similarity
        try:
            val1 = float(result1['value'])
            val2 = float(result2['value'])
            value_diff = abs(val1 - val2) / max(val1, val2, 1)
        except:
            value_diff = 1.0
        
        # Consider similar if names are very similar and values are close
        return (name_similarity > 0.8 and value_diff < 0.1) or (name_similarity > 0.95)
    
    def _select_best_from_group(self, group: List[Dict]) -> Dict:
        """Select the best result from a group of similar results."""
        # Scoring system based on source priority and learned preferences
        source_priority = {'tabular': 5, 'line_analysis': 4, 'ocr_pattern': 3, 'regex': 2, 'generic': 1}
        
        best_result = group[0]
        best_score = 0
        
        for result in group:
            score = source_priority.get(result.get('source', 'generic'), 1)
            
            # Bonus for learned terms
            if self._is_learned_term(result['test_type']):
                score += 2
            
            # Bonus for reasonable values
            try:
                value = float(result['value'])
                if 0.1 <= value <= 10000:  # Reasonable medical value range
                    score += 1
            except:
                score -= 1
            
            if score > best_score:
                best_score = score
                best_result = result
        
        return best_result
    
    def _is_learned_term(self, term: str) -> bool:
        """Check if term is in learned medical terminology."""
        learned_terms = self.get_learned_medical_terms()
        return term.lower() in learned_terms
    
    def _learn_duplicate_pattern(self, group: List[Dict]):
        """Learn from duplicate patterns for future prevention."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        pattern_data = json.dumps({
            'terms': [r['test_type'] for r in group],
            'values': [r['value'] for r in group],
            'sources': [r.get('source', 'unknown') for r in group]
        })
        
        cursor.execute('''
            INSERT OR REPLACE INTO duplicate_patterns 
            (pattern_type, pattern_data, frequency)
            VALUES (?, ?, COALESCE((SELECT frequency FROM duplicate_patterns WHERE pattern_data = ?), 0) + 1)
        ''', ('similar_results', pattern_data, pattern_data))
        
        conn.commit()
        conn.close()
    
    def get_correction_suggestions(self, test_name: str) -> List[str]:
        """Get correction suggestions based on learned data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get similar corrections from history
        cursor.execute('''
            SELECT corrected_value, COUNT(*) as frequency
            FROM user_corrections 
            WHERE correction_type = 'name' 
            AND (LOWER(original_value) LIKE ? OR LOWER(corrected_value) LIKE ?)
            GROUP BY corrected_value
            ORDER BY frequency DESC, timestamp DESC
            LIMIT 5
        ''', (f'%{test_name.lower()}%', f'%{test_name.lower()}%'))
        
        suggestions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return suggestions
    
    def track_extraction_performance(self, document_type: str, extraction_methods: Dict, 
                                   original_count: int, final_count: int, 
                                   corrected_count: int, added_count: int):
        """Track extraction performance for learning."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        primary_method = max(extraction_methods.values()) if extraction_methods else 'unknown'
        
        cursor.execute('''
            INSERT INTO extraction_performance 
            (document_type, extraction_method, tests_found, tests_kept, tests_corrected, tests_added)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (document_type, primary_method, original_count, final_count, corrected_count, added_count))
        
        conn.commit()
        conn.close()
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Learned terms count
        cursor.execute('SELECT COUNT(*) FROM learned_medical_terms')
        stats['learned_terms'] = cursor.fetchone()[0]
        
        # User corrections count
        cursor.execute('SELECT COUNT(*) FROM user_corrections')
        stats['user_corrections'] = cursor.fetchone()[0]
        
        # Duplicate patterns identified
        cursor.execute('SELECT COUNT(*) FROM duplicate_patterns')
        stats['duplicate_patterns'] = cursor.fetchone()[0]
        
        # Most frequent corrections
        cursor.execute('''
            SELECT correction_type, COUNT(*) 
            FROM user_corrections 
            GROUP BY correction_type
        ''')
        stats['correction_types'] = dict(cursor.fetchall())
        
        conn.close()
        return stats