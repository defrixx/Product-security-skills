"""Synthetic archive regression: unsafe is an intentional anti-example.
fixed demonstrates basename validation; both are evaluated only in temp dirs.
This is test material, not a recommended complete archive extraction library.
"""
import io,json,zipfile
from pathlib import Path,PurePosixPath

def inspect(data):
    archive=zipfile.ZipFile(io.BytesIO(data))
    for info in archive.infolist():
        p=PurePosixPath(info.filename)
        if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe member')
    return archive,json.loads(archive.read('manifest.json'))

def unsafe(root,data,fail_after_write=False):
    archive,manifest=inspect(data)
    with archive:
        path=Path(root)/manifest['filename']
        path.write_bytes(archive.read('payload.txt'))
        if fail_after_write:raise ValueError('simulated database rollback')
        return path

def fixed(root,data):
    archive,manifest=inspect(data)
    with archive:
        name=manifest['filename']
        if not isinstance(name,str) or not name or name in {'.','..'} or any(x in name for x in ('/','\\','\0',':')):
            raise ValueError('unsafe filename')
        # Exclusive creation also refuses an existing symlink/destination.
        path=Path(root)/name
        with path.open('xb') as output:output.write(archive.read('payload.txt'))
        return path

def fixture(name):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('manifest.json',json.dumps({'filename':name}));z.writestr('payload.txt','SYNTHETIC_PAYLOAD')
    return stream.getvalue()
