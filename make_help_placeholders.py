"""Create only missing contextual-help placeholder PNGs.

Safe to rerun after the user replaces images: existing files are never overwritten.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from gui_main import HELP, PAGE_DEFAULT, ROOT, HELP_ROOT


def font(size,bold=False):
    candidates=[
        'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for p in candidates:
        try:return ImageFont.truetype(p,size)
        except:pass
    return ImageFont.load_default()


def placeholder(path:Path,title:str,filename:str):
    if path.exists():return
    path.parent.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(900,600),'white'); d=ImageDraw.Draw(im)
    d.rectangle((18,18,882,582),outline='#999999',width=3)
    d.text((55,60),'CMS GENERATOR — HELP IMAGE PLACEHOLDER',fill='#444444',font=font(28,True))
    d.text((55,145),title,fill='#111111',font=font(38,True))
    d.line((55,215,845,215),fill='#bbbbbb',width=2)
    d.text((55,260),'Replace this PNG with your engineering illustration.',fill='#333333',font=font(24))
    d.text((55,315),'Keep the exact same filename and path.',fill='#333333',font=font(24))
    d.text((55,405),filename,fill='#111111',font=font(23,True))
    d.text((55,485),'The GUI will auto-fit the replacement image and preserve aspect ratio.',fill='#555555',font=font(19))
    im.save(path)


entries=[]
for key,(rel,title,_) in HELP.items():
    path=HELP_ROOT/rel; placeholder(path,title,rel); entries.append((key,rel,title))
for page,rel in PAGE_DEFAULT.items():
    placeholder(HELP_ROOT/rel,f'{page} overview',rel); entries.append((f'PAGE: {page}',rel,f'{page} overview'))

manifest=ROOT/'HELP_IMAGE_FILENAMES.txt'
manifest.write_text('\n'.join([
    'CMS Generator contextual help image manifest',
    '===========================================',
    '',
    'Replace any placeholder PNG below using exactly the same relative path/filename.',
    'The GUI dynamically loads the image when the associated input is focused.',
    '',
]+[f'{key:24s}  assets/help/{rel}' for key,rel,_ in entries])+'\n',encoding='utf-8')
print(f'Help images present: {len(entries)}')
print(manifest)
