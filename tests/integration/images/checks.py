"""Independent pixel decode checks; Pillow is test-only, not a helper dependency."""
import io
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from support import cleanup
from test_image_metadata import jpeg, png, segment, CANARY
from PIL import Image, __version__

results=[]
for name in ['baseline','progressive','cmyk']:
    original=jpeg(name)
    exif=Image.Exif();exif[315]=CANARY.decode();exif[274]=6
    decorated=original[:2]+segment(0xe1,exif.tobytes())+segment(0xfe,CANARY)+original[2:]
    cleaned,_=cleanup.strip_image_metadata(decorated,'.jpg')
    with Image.open(io.BytesIO(decorated)) as before, Image.open(io.BytesIO(cleaned)) as after:
        before.load();after.load()
        assert before.size==after.size and before.mode==after.mode
        assert before.tobytes()==after.tobytes()
        assert before.getexif()[315]==CANARY.decode()
        assert not after.getexif()
    results.append(name+': identical decoded samples; EXIF absent')
for mode in ['RGBA','P','L','RGB']:
    image=Image.new(mode,(3,2))
    if mode=='P':image.putpalette([255,0,0]+[0]*765);image.info['transparency']=128
    from PIL.PngImagePlugin import PngInfo
    meta=PngInfo();meta.add_text('Author',CANARY.decode());meta.add_text('Comment',CANARY.decode(),zip=True)
    buffer=io.BytesIO();image.save(buffer,format='PNG',pnginfo=meta)
    cleaned,_=cleanup.strip_image_metadata(buffer.getvalue(),'.png')
    with Image.open(io.BytesIO(buffer.getvalue())) as before, Image.open(io.BytesIO(cleaned)) as after:
        before.load();after.load()
        assert before.convert('RGBA').tobytes()==after.convert('RGBA').tobytes()
        assert 'Author' not in after.info and 'Comment' not in after.info
    results.append(mode+': identical RGBA samples; text metadata absent')
print(json.dumps({'status':'passed','pillow':__version__,'checks':results,'limits':['raw samples compared; color-managed display/orientation may change','synthetic fixtures only']},indent=2))
