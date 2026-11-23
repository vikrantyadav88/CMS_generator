from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
A=Path(__file__).resolve().parent/'assets';A.mkdir(exist_ok=True)
W,H=520,300
try: font=ImageFont.truetype('arial.ttf',16); small=ImageFont.truetype('arial.ttf',13); title=ImageFont.truetype('arialbd.ttf',19)
except: font=small=title=ImageFont.load_default()

def base(t):
 im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im);d.text((18,14),t,fill='black',font=title);return im,d

def save(im,n): im.save(A/n)

im,d=base('Crossbeam families')
labels=['Monoleg','Power-B','Standard-B','D-section']
for i,l in enumerate(labels):
 x=25+i*122;y=105
 d.rounded_rectangle((x,y,x+90,y+75),12,outline='black',width=3)
 if 'B' in l:
  d.line((x+45,y+10,x+65,y+28,x+45,y+38,x+65,y+50,x+45,y+65),fill='black',width=3)
 if l=='Monoleg': d.line((x+20,y+15,x+50,y+25,x+30,y+40,x+55,y+55),fill='black',width=3)
 d.text((x,y+90),l,fill='black',font=small)
# Global placement datum used by the GUI.
d.line((235,245,235,285),fill='black',width=2);d.polygon([(235,245),(229,257),(241,257)],fill='black')
d.text((245,254),'Z',fill='black',font=small);d.ellipse((226,268,234,276),fill='black')
d.text((245,268),'front-face centre Z datum (Y=0)',fill='black',font=small)
save(im,'beam_types.png')

im,d=base('Crush-can transition definition')
d.rectangle((70,95,150,205),outline='black',width=3);d.rectangle((365,115,425,190),outline='black',width=3)
d.line((150,95,365,115),fill='black',width=3);d.line((150,205,365,190),fill='black',width=3)
d.text((55,220),'Rear / base',fill='black',font=font);d.text((350,205),'Front / top',fill='black',font=font)
d.line((70,78,150,78),fill='black',width=2);d.text((90,56),'Wr',fill='black',font=font);d.text((370,92),'Wf',fill='black',font=font)
d.text((185,140),'straight -> taper -> straight',fill='black',font=small)
save(im,'can_geometry.png')

im,d=base('Crush-can split options')
# top/bottom
x0,y0=35,90;d.rounded_rectangle((x0,y0,x0+180,y0+130),20,outline='black',width=3);d.line((x0,y0+65,x0+180,y0+65),fill='black',width=3)
d.text((73,230),'Top / Bottom',fill='black',font=font)
# inner outer
x0=300;d.rounded_rectangle((x0,y0,x0+180,y0+130),20,outline='black',width=3);d.line((x0+90,y0,x0+90,y0+130),fill='black',width=3)
d.text((335,230),'Inner / Outer',fill='black',font=font)
save(im,'can_split.png')

im,d=base('Rear attachment architecture')
d.rectangle((25,90,180,210),outline='black',width=4);d.text((55,225),'Back plate',fill='black',font=font)
# Rail-bolted: side view (equispaced Z) + small top-view inset showing through-bolt
d.rounded_rectangle((285,80,465,215),18,outline='black',width=3)
for z in (120,175): d.ellipse((350,z-9,368,z+9),outline='black',width=3)
d.line((359,105,359,193),fill='black',width=1);d.text((375,140),'equispaced Z',fill='black',font=small)
d.text((290,225),'Rail through-bolted',fill='black',font=font)
# top-view inset: two constant-Y sidewalls and one Y-axis bolt through both
d.line((300,260,455,260),fill='black',width=3);d.line((300,285,455,285),fill='black',width=3)
d.line((365,252,365,293),fill='black',width=4);d.text((372,263),'bolt axis Y',fill='black',font=small)
save(im,'rear_interface.png')

im,d=base('Front interaction / limiter-specific attachment')
# Upper: beam plate exact-fit concept.
d.text((35,48),'BEAM PLATE: exact rear-face fit',fill='black',font=font)
d.line((55,88,255,88),fill='black',width=4); d.line((55,128,255,128),fill='black',width=4)
d.line((255,88,292,97),fill='black',width=4); d.line((255,128,292,137),fill='black',width=4)
d.line((292,70,322,150),fill='black',width=4)
d.line((327,67,357,147),fill='gray',width=6)
d.text((365,92),'plate rear face',fill='black',font=small)
d.text((70,145),'overshoot -> exact Boolean fit',fill='black',font=small)
# Lower: bare beam rear-land envelope; recessed valley is deliberately bridged.
d.text((35,178),'BARE BEAM: bridge recessed valleys',fill='black',font=font)
d.line((55,215,255,215),fill='black',width=4); d.line((55,255,255,255),fill='black',width=4)
d.line((255,215,292,224),fill='black',width=4); d.line((255,255,292,246),fill='black',width=4)
# envelope line and stylized B-profile behind it
d.line((315,195,315,275),fill='gray',width=2)
d.line((315,195,350,195),fill='black',width=5); d.line((350,195,350,212),fill='black',width=5)
d.line((350,212,332,212),fill='black',width=5); d.line((332,212,332,258),fill='black',width=5)
d.line((332,258,350,258),fill='black',width=5); d.line((350,258,350,275),fill='black',width=5)
d.line((350,275,315,275),fill='black',width=5)
d.text((360,220),'valley',fill='black',font=small)
d.text((65,270),'front edge stays on land envelope',fill='black',font=small)
save(im,'front_interface.png')

im,d=base('Continuous bead sense / positioning')
d.line((60,150,460,150),fill='black',width=3);d.arc((160,110,240,190),180,360,fill='black',width=4);d.arc((280,110,360,190),0,180,fill='black',width=4)
d.text((55,205),'Sidewall sense reverses smoothly through the bend radius into the connecting face',fill='black',font=small)
d.text((55,235),'Bead centres are spaced rearward from the FRONT end of the solved crush can',fill='black',font=small)
d.line((455,260,330,260),fill='black',width=2);d.polygon([(330,260),(342,254),(342,266)],fill='black');d.text((400,270),'FRONT',fill='black',font=small)
save(im,'beads.png')

im,d=base('Review / validation')
for i,(s,t) in enumerate([('OK','Beam geometry'),('OK','Can envelope'),('WARN','Bolt/split clearance'),('OK','Front contact')]):
 y=75+i*45;d.text((45,y),s,fill='black',font=font);d.text((130,y),t,fill='black',font=font)
save(im,'review.png')

im,d=base('Export')
d.rectangle((75,80,445,230),outline='black',width=3)
for i,t in enumerate(['CMS assembly STEP','Individual component STEP','Configuration JSON','Build summary']):
 y=100+i*30;d.rectangle((95,y,110,y+15),outline='black',width=2);d.text((125,y-2),t,fill='black',font=font)
save(im,'export.png')
