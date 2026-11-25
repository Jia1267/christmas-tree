"""Generate the 3D scene embedded in the standalone Christmas web page.

Run: python build_scene.py [index.html]
Only the marked scene block is replaced. Existing photos and page code are preserved.
"""
from argparse import ArgumentParser
import base64
import json
import math
from pathlib import Path
import random
import struct
import zlib

BEGIN = "/* PYTHON_SCENE_START */"
END = "/* PYTHON_SCENE_END */"
VERTEX = struct.Struct("<6hH4B")
POSITION_SCALE = 15000
SIZE_SCALE = 2048
BODY_COUNT = 1700
CAMERA = {"far_pitch": .69, "near_pitch": .105, "far_zoom": .43,
          "push_at": 3240, "push_duration": 2110, "form_at": 680,
          "form_duration": 2250, "gift_at": 6200}
GOLD = ["#a67649", "#cb995d", "#eac180", "#f9d99a", "#fff2c8"]
PHOTO_POSES = [(-math.tau/6, .32, .124, -.10), (0, .52, .181, .07),
               (math.tau/3, .32, .124, .09), (math.tau/6, .72, .228, .07),
               (math.tau/2, .52, .181, -.09), (-math.tau/3, .72, .228, -.08)]

def radius(y):
    return .386*y*(.82+.18*math.cos((y*7.4+.05)*math.tau))

def spiral_radius(y):
    return .438*y**.86

def polar(angle, y, distance):
    return (math.sin(angle)*distance, y, math.cos(angle)*distance)

def point(position, **properties):
    return dict(zip(("x", "y", "z"), position), **properties)

def vertex(position, size, color, kind=0, drift=(0, 0, 0)):
    coordinates = (round(value*POSITION_SCALE) for value in (*position, *drift))
    return VERTEX.pack(*coordinates, round(size*SIZE_SCALE), *color, kind)

def rgb(color):
    return tuple(bytes.fromhex(color[1:]))

def light_geometry(rng):
    buffer = bytearray()
    for index in range(BODY_COUNT):
        y = .035+.965*(index/BODY_COUNT)**.72
        angle = rng.random()*math.tau
        distance = radius(y)*(.25+.78*rng.random()**.52)
        color = rng.choice(GOLD)
        size = .65+rng.random()**2*1.65
        drift = polar(angle+(rng.random()-.5)*1.2, (rng.random()-.5)*.56, .09+rng.random()*.38)
        buffer.extend(vertex(polar(angle, y, distance), size, rgb(color), drift=drift))
    for _ in range(8700):
        angle = rng.random()*math.tau
        distance = math.sqrt(rng.random())*1.56
        y = 1.014 + .056*rng.random()
        brightness = int(255*(1-distance/1.68)**.65*(.28+.72*rng.random()))
        size = .38+.92*rng.random()**2
        buffer.extend(vertex(polar(angle,y,distance),size,(brightness,0,0),kind=1))
    blush = [(255,229,243),(255,249,245),(249,205,233),(238,214,250),(255,243,229)]
    for index in range(5400):
        y = .04+.96*index/5400
        angle = y*math.tau*5.35+rng.gauss(0,.14)
        distance = max(.004,spiral_radius(y)+rng.gauss(0,.023+.013*y))
        pos = polar(angle,max(.011,min(1.02,y+rng.gauss(0,.023))),distance)
        size = .38+1.38*rng.random()**2
        buffer.extend(vertex(pos,size,rng.choice(blush),kind=2))
    return base64.b64encode(buffer).decode("ascii")

def compact_snow(rng):
    size = 256
    pixels = bytearray(size*size*2)
    for _ in range(221):
        x, y = rng.randrange(size), rng.randrange(size)
        draw = rng.randrange(32, 141)
        index=(y*size+x)*2
        pixels[index:index+2] = bytes((241,draw))
        if draw>118:
            for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                neighbor=(((y+dy)%size)*size+(x+dx)%size)*2
                pixels[neighbor:neighbor+2] = bytes((234,draw//4))
    def chunk(name, data):
        return struct.pack(">I",len(data))+name+data+struct.pack(">I",zlib.crc32(name+data))
    rows=b"".join(b"\x00"+pixels[y*size*2:(y+1)*size*2] for y in range(size))
    raw=(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",size,size,8,4,0,0,0))+
         chunk(b"IDAT",zlib.compress(rows,9))+chunk(b"IEND",b""))
    return "data:image/png;base64,"+base64.b64encode(raw).decode("ascii")

def build_scene():
    rng=random.Random(5221267)
    balls=[]
    for i in range(46):
        y=.19+.77*((i+.3)/46)**.8
        balls.append(point(polar(i*2.4,y,radius(y)*1.08),type="ball",color=i%5,
                           size=.009+rng.random()*.008,phase=rng.random()*math.tau,
                           drift=point(polar(i*2.4,.09*math.sin(i),.17+rng.random()*.26))))
    lights=[]
    for i in range(74):
        y=.10+.88*i/74
        lights.append(point(polar(y*math.tau*7.1,y,radius(y)*1.06),type="light",
                            phase=rng.random()*math.tau,size=.002+rng.random()*.0023))
    cards=[point(polar(angle,y,max(r,radius(y)*1.09)),angle=angle,tilt=tilt,
                 index=i,type="photo") for i,(angle,y,r,tilt) in enumerate(PHOTO_POSES)]
    spiral=[point(polar(y*math.tau*5.35,y,spiral_radius(y))) for y in (i/170 for i in range(171))]
    metadata=dict(camera=CAMERA, body_count=BODY_COUNT, gold=GOLD, balls=balls, lights=lights, cards=cards, spiral=spiral)
    return dict(metadata=metadata, vertices=light_geometry(rng), snow=compact_snow(rng))

def inject_scene(html):
    if html.count(BEGIN)!=1 or html.count(END)!=1:
        raise ValueError("Expected one pair of Python scene markers")
    before, rest=html.split(BEGIN,1)
    _, after=rest.split(END,1)
    scene=json.dumps(build_scene(),ensure_ascii=False,separators=(",",":"))
    return f"{before}{BEGIN}\nconst builtScene = {scene};\n{END}{after}"

def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("page",nargs="?",type=Path,default=Path(__file__).with_name("index.html"))
    args=parser.parse_args()
    page=args.page
    page.write_text(inject_scene(page.read_text(encoding="utf-8")),encoding="utf-8")

if __name__=="__main__":
    main()
