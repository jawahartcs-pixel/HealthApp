import tempfile
import unittest
from datetime import date
from pathlib import Path

from data_processor import DataProcessor
from database import Database
from file_parser import FileParser
from investigation_standards import InvestigationStandards
from result_values import classify_test_result, normalize_test_value


class QualitativeResultTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "results.sqlite")
        self.db = Database(self.db_path)
        self.standards = InvestigationStandards(self.db)
        self.standards.add_standard({
            "standard_name": "HBsAg",
            "aliases": "Hepatitis B surface antigen",
            "category": "Serology",
            "qualitative_good_result": "Negative",
        })

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_normalizes_common_binary_labels_and_numeric_strings(self):
        self.assertEqual(normalize_test_value(" non-reactive "), "Negative")
        self.assertEqual(normalize_test_value("Detected"), "Positive")
        self.assertEqual(normalize_test_value("0"), 0.0)

    def test_classifies_numeric_and_binary_results_without_assuming_polarity(self):
        self.assertEqual(classify_test_result(75, min_value=70, max_value=100), "good")
        self.assertEqual(classify_test_result(120, min_value=70, max_value=100), "bad")
        self.assertEqual(classify_test_result("Negative", good_result="Negative"), "good")
        self.assertEqual(classify_test_result("Positive", good_result="Negative"), "bad")
        self.assertEqual(classify_test_result("Positive"), "unknown")
        self.assertEqual(classify_test_result("Negative", good_result="Positive"), "bad")
        self.assertEqual(classify_test_result("Positive", good_result="Positive"), "good")

    def test_standard_polarity_round_trips_and_parser_extracts_binary_value(self):
        standard = next(
            item for item in self.standards.get_all_standards()
            if item["standard_name"] == "HBsAg"
        )
        self.assertEqual(standard["qualitative_good_result"], "Negative")
        self.assertEqual(
            self.standards.get_reference_range("HBsAg"),
            "Expected: Negative",
        )

        parsed = FileParser().scan_text_against_standards(
            "HBsAg: Positive", self.standards
        )
        hbsag = next(item for item in parsed if item["test_type"] == "HBsAg")
        self.assertEqual(hbsag["value"], "Positive")
        self.assertEqual(hbsag["reference_range"], "Expected: Negative")

    def test_bulk_and_update_preserve_positive_good_direction(self):
        result = self.standards.add_standards([{
            "standard_name": "Anti-HBs",
            "category": "Serology",
            "qualitative_good_result": "Positive",
        }])
        self.assertEqual(len(result["added"]), 1)
        anti_hbs = next(
            item for item in self.standards.get_all_standards()
            if item["standard_name"] == "Anti-HBs"
        )
        self.assertEqual(anti_hbs["qualitative_good_result"], "Positive")
        self.assertTrue(self.standards.update_standard(
            anti_hbs["id"],
            {**anti_hbs, "qualitative_good_result": "Negative"},
        ))
        updated = self.standards.get_standard_by_id(anti_hbs["id"])
        self.assertEqual(updated["qualitative_good_result"], "Negative")

    def test_saves_binary_results_and_numeric_zero(self):
        processor = DataProcessor(self.db)
        saved = processor.save_test_results(
            patient_name="Test Patient",
            test_date=date.today(),
            test_results=[
                {"test_type": "HBsAg", "value": "Negative"},
                {"test_type": "Glucose", "value": "0"},
            ],
            user_id=77,
            show_feedback=False,
        )
        self.assertTrue(saved)

        records = self.db.get_patient_tests("Test Patient", user_id=77)
        values_by_type = {record[1]: record[2] for record in records}
        self.assertEqual(values_by_type["HBsAg"], "Negative")
        self.assertEqual(float(values_by_type["Glucose"]), 0.0)

        ids = self.db.get_patient_test_results_with_ids("Test Patient")
        hbsag_id = next(row[0] for row in ids if row[2] == "HBsAg")
        self.assertTrue(self.db.update_test_result(
            hbsag_id, "HBsAg", "Positive", "", date.today(), "Expected: Negative"
        ))
        updated = self.db.get_patient_tests("Test Patient", user_id=77)
        self.assertEqual(
            next(record[2] for record in updated if record[1] == "HBsAg"),
            "Positive",
        )


if __name__ == "__main__":
    unittest.main()
