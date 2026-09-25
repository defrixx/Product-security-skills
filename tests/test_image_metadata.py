"""Synthetic lossless container tests; no real photographs or personal metadata."""
import base64
import json
from pathlib import Path
import struct
import tempfile
import subprocess
import sys
import shutil
import unittest
import zlib
from support import cleanup, ROOT

CANARY = b'SYNTHETIC_PRIVATE_METADATA_ONLY'
def chunk(kind, payload):
    return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)

def png(metadata=True):
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))
    if metadata:
        for kind,value in [(b'tEXt',b'Author\0'+CANARY),(b'eXIf',CANARY),(b'iTXt',CANARY),(b'zTXt',b'Comment\0\0'+zlib.compress(CANARY)),(b'iCCP',b'Profile\0\0'+zlib.compress(CANARY))]:
            data+=chunk(kind,value)
    return data+chunk(b'IDAT',zlib.compress(b'\x00\x01\x02\x03\xff'))+chunk(b'IEND',b'')

def jpeg(name='baseline'):
    return base64.b64decode(json.loads((ROOT/'tests/fixtures/synthetic-jpeg.json').read_text())[name])

def segment(marker, value): return b'\xff'+bytes([marker])+struct.pack('>H',len(value)+2)+value

class ImageMetadataTests(unittest.TestCase):
    def test_png_removes_all_ancillary_except_transparency(self):
        output,count=cleanup.strip_image_metadata(png(),'.png')
        self.assertEqual(count,5);self.assertEqual(output,png(False));self.assertNotIn(CANARY,output)
        self.assertEqual(cleanup.strip_image_metadata(output,'.png'),(output,0))

    def test_palette_transparency_preserved(self):
        data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,3,0,0,0))+chunk(b'PLTE',b'\x01\x02\x03')+chunk(b'tRNS',b'\x80')+chunk(b'IDAT',zlib.compress(b'\0\0'))+chunk(b'IEND',b'')
        self.assertEqual(cleanup.strip_image_metadata(data,'.png'),(data,0))

    def test_jpeg_metadata_including_post_scan_removed(self):
        for name in ['baseline','progressive','cmyk']:
            with self.subTest(name=name):
                original=jpeg(name)
                decorated=original[:2]+segment(0xe1,b'Exif\0\0'+CANARY)+segment(0xe2,CANARY)+segment(0xed,CANARY)+original[2:-2]+segment(0xfe,CANARY)+original[-2:]+CANARY
                result,count=cleanup.strip_image_metadata(decorated,'.jpeg')
                self.assertNotIn(CANARY,result);self.assertGreaterEqual(count,5)
                self.assertEqual(result,cleanup.strip_image_metadata(original,'.jpg')[0])
                self.assertEqual(cleanup.strip_image_metadata(result,'.jpg'),(result,0))

    def test_bad_signature_crc_truncation_and_unsupported_omitted(self):
        cases=[(b'not-image','.jpg'),(png()[:-1],'.png'),(jpeg()[:-2],'.jpg')]
        corrupt=bytearray(png());corrupt[30]^=1;cases.append((bytes(corrupt),'.png'))
        animated=png(False);cases.append((animated[:33]+chunk(b'acTL',struct.pack('>II',2,0))+animated[33:],'.png'))
        cases.append((animated[:33]+chunk(b'ABCD',b'')+animated[33:],'.png'))
        for data,suffix in cases:
            with self.subTest(suffix=suffix):
                with self.assertRaises(cleanup.CleanupError):cleanup.strip_image_metadata(data,suffix)

    def test_scan_only_and_clean_copy_preserve_source_and_other_formats(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'input';src.mkdir()
            originals={'person@synthetic.invalid.png':png(),'photo.jpg':jpeg(),'document.pdf':b'SYNTHETIC_UNTOUCHED','note.txt':b'password=SYNTHETIC_UNTOUCHED'}
            for name,data in originals.items():(src/name).write_bytes(data)
            report=cleanup.run(src,root/'scan',image_metadata_only=True)
            self.assertEqual(report['counts']['emitted_files'],0)
            self.assertEqual(report['counts']['metadata_containers_removed'],0)
            self.assertGreater(report['counts']['metadata_containers_proposed'],0)
            report=cleanup.run(src,root/'clean','clean-copy',image_metadata_only=True)
            self.assertEqual(report['counts']['emitted_files'],2);self.assertEqual(report['counts']['skipped'],2)
            self.assertNotIn(CANARY.decode(),json.dumps(report));self.assertNotIn('person@',json.dumps(report))
            for name,data in originals.items():self.assertEqual((src/name).read_bytes(),data)
            for entry in report['files']:
                if 'output' in entry:self.assertNotIn(CANARY,(root/'clean'/entry['output']).read_bytes())

    def test_default_mode_still_omits_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'in').mkdir();(root/'in/a.png').write_bytes(png())
            report=cleanup.run(root/'in',root/'out','clean-copy')
            self.assertEqual(report['counts']['emitted_files'],0)

    def test_image_limits_and_symlinks_use_existing_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'in';src.mkdir();(src/'a.png').write_bytes(png());(src/'b.png').symlink_to(src/'a.png')
            report=cleanup.run(src,root/'out','clean-copy',limits={'max_file_bytes':20},image_metadata_only=True)
            self.assertEqual(report['counts']['emitted_files'],0)
            self.assertEqual({x['reason'] for x in report['files']},{'file_size_limit','symlink_or_nonregular'})

    def test_copied_skill_cli_image_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'in';source.mkdir();(source/'sample.png').write_bytes(png())
            shutil.copytree(ROOT/'skills/sensitive-data-cleanup',root/'skill',ignore=shutil.ignore_patterns('__pycache__'))
            process=subprocess.run([sys.executable,str(root/'skill/scripts/cleanup.py'),'--source',str(source),'--output',str(root/'out'),'--mode','clean-copy','--image-metadata-only'],capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            report=json.loads((root/'out/report.json').read_text())
            self.assertEqual(report['scope'],'jpeg_png_metadata_only')
            self.assertEqual((root/'out'/report['files'][0]['output']).read_bytes(),png(False))
            self.assertNotIn(CANARY.decode(),process.stdout+process.stderr)
