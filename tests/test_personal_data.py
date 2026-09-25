"""Synthetic field-context coverage, not population-wide PII recall."""
import json
from pathlib import Path
import tempfile
import unittest
from support import cleanup


class PersonalDataTests(unittest.TestCase):
    def test_additional_fields_and_normalization(self):
        fields = ['middleName', 'dateOfBirth', 'birth_date', 'DOB', 'home-address',
                  'residential_address', 'passportNumber', 'national_id',
                  'socialSecurityNumber', 'ssn', 'taxpayer_id',
                  'driverLicenseNumber', 'bankAccount', 'IBAN',
                  'creditCardNumber', 'medicalRecordNumber']
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source'; source.mkdir()
            values = {key: 'SYNTHETIC_PERSONAL_%02d' % i for i, key in enumerate(fields)}
            original = json.dumps(values).encode()
            (source / 'input.json').write_bytes(original)
            report = cleanup.run(source, root / 'out', 'clean-copy')
            output = json.loads((root / 'out' / report['files'][0]['output']).read_text())
            self.assertEqual(report['counts']['replacement_occurrences'], len(fields))
            for key, value in values.items():
                self.assertNotEqual(output[key], value)
                self.assertNotIn(value, json.dumps(report))
            self.assertEqual((source / 'input.json').read_bytes(), original)

    def test_ambiguous_fields_are_not_assumed_personal(self):
        detector = cleanup.Detector(cleanup.policy_config())
        for key in ['name', 'address', 'id', 'account', 'date', 'version']:
            with self.subTest(key=key):
                self.assertEqual(detector.spans('SYNTHETIC_PRODUCT_VALUE', key), [])

    def test_numeric_identifier_is_not_silently_retained(self):
        detector = cleanup.Detector(cleanup.policy_config())
        with self.assertRaisesRegex(cleanup.CleanupError, 'sensitive_nonstring_field'):
            cleanup.transform('{"nationalId":123456}', '.json', 'input.json', detector)

    def test_csv_field_context(self):
        detector = cleanup.Detector(cleanup.policy_config())
        result = cleanup.transform('passportNumber,version\nSYNTHETIC_DOCUMENT,1.2.3\n', '.csv', 'input.csv', detector)
        self.assertNotIn('SYNTHETIC_DOCUMENT', result)
        self.assertIn('1.2.3', result)

    def test_natural_language_name_remains_explicitly_uncovered(self):
        detector = cleanup.Detector(cleanup.policy_config())
        self.assertEqual(detector.spans('The fictional person is Example Person.'), [])
