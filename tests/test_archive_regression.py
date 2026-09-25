from pathlib import Path
import tempfile,unittest
from archive_fixture import unsafe,fixed,fixture

class ArchiveRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.storage=self.root/'storage';self.storage.mkdir()
        self.outside=self.root/'outside.txt';self.outside.write_text('SYNTHETIC_KEEP')
    def test_manifest_path_bypasses_member_validation(self):
        unsafe(self.storage,fixture('../outside.txt'));self.assertEqual(self.outside.read_text(),'SYNTHETIC_PAYLOAD')
    def test_absolute_path_reproduces_write(self):
        unsafe(self.storage,fixture(str(self.outside)));self.assertEqual(self.outside.read_text(),'SYNTHETIC_PAYLOAD')
    def test_database_rollback_does_not_reverse_filesystem_write(self):
        with self.assertRaises(ValueError):unsafe(self.storage,fixture('../outside.txt'),True)
        self.assertEqual(self.outside.read_text(),'SYNTHETIC_PAYLOAD')
    def test_fixed_rejects_invalid_names_before_writing(self):
        for name in ['../outside.txt',str(self.outside),'..\\outside.txt','C:outside.txt','nested/name.txt','','.','..','a\0b',42]:
            with self.subTest(name=name),self.assertRaises(ValueError):fixed(self.storage,fixture(name))
        self.assertEqual(self.outside.read_text(),'SYNTHETIC_KEEP');self.assertEqual(list(self.storage.iterdir()),[])
    def test_fixed_preserves_valid_import(self):
        p=fixed(self.storage,fixture('two words.txt'));self.assertEqual(p.read_text(),'SYNTHETIC_PAYLOAD')
    def test_fixed_refuses_existing_symlink(self):
        (self.storage/'alias.txt').symlink_to(self.outside)
        with self.assertRaises(FileExistsError):fixed(self.storage,fixture('alias.txt'))
        self.assertEqual(self.outside.read_text(),'SYNTHETIC_KEEP')

if __name__=='__main__':unittest.main()
