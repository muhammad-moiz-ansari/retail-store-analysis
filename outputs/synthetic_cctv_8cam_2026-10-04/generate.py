"""Render eight synchronized CCTV views of one deterministic retail simulation.

Linux/WSL requirements: numpy pillow moderngl glcontext and ffmpeg.
Run: python generate.py --output . --duration 60 --fps 10
This is synthetic integration-test footage, not a real-world accuracy benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 540
BASE_TIME = datetime(2026, 10, 4, 10, 0, 0)
VEST = (1.0, .29, .015)
ZONES = [
    ("01", "Entrance / produce", (0, 0, 5.5, 3), "#ffa1b8", (.35, .25, 4.1), (3.2, 2.1, .4)),
    ("02", "Grocery aisles", (5.5, 0, 12.1, 3), "#e5a673", (8.8, .18, 4.2), (8.6, 3.0, .35)),
    ("03", "Chilled goods", (12.1, 0, 16, 3), "#aaaaaa", (15.75, .25, 4.0), (13.5, 2.4, .35)),
    ("04", "Right aisle", (12.1, 3, 16, 6.1), "#ffe500", (15.75, 4.5, 4.0), (12.8, 4.5, .35)),
    ("05", "Household goods", (12.1, 6.1, 16, 9), "#ef1d23", (15.75, 8.75, 4.1), (13.3, 6.8, .35)),
    ("06", "Checkout", (5.5, 6.1, 12.1, 9), "#0cafd6", (8.8, 8.8, 4.2), (8.6, 6.0, .35)),
    ("07", "Lower entrance", (0, 6.1, 5.5, 9), "#693092", (.25, 8.75, 4.1), (3.0, 6.7, .35)),
    ("08", "Left aisle", (0, 3, 5.5, 6.1), "#f4e6a0", (.25, 4.5, 4.0), (3.2, 4.5, .35)),
]


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / max(float(np.linalg.norm(v)), 1e-8)


def look_at(eye, target):
    eye = np.asarray(eye, dtype=np.float32)
    f = unit(np.asarray(target) - eye)
    s = unit(np.cross(f, [0, 0, 1]))
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[:3, :3] = np.stack([s, u, -f])
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fov, aspect, near=.08, far=50):
    q = 1 / math.tan(math.radians(fov) / 2)
    return np.array([[q/aspect, 0, 0, 0], [0, q, 0, 0],
                     [0, 0, (far+near)/(near-far), 2*far*near/(near-far)],
                     [0, 0, -1, 0]], dtype=np.float32)


def rgb(hex_color):
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (1, 3, 5))


class Geometry:
    def __init__(self):
        self.parts = []

    def add(self, mesh, color, center, scale, rotation=None, person_id=0):
        p, n = mesh
        transform = np.diag(np.asarray(scale, dtype=np.float32))
        if rotation is not None:
            transform = rotation @ transform
        verts = p @ transform.T + np.asarray(center, dtype=np.float32)
        norms = n @ np.linalg.inv(transform)
        norms /= np.maximum(np.linalg.norm(norms, axis=1, keepdims=True), 1e-8)
        self.parts.append(np.concatenate([verts, norms,
                                         np.tile(color, (len(p), 1)),
                                         np.full((len(p), 1), person_id)], axis=1).astype('f4'))

    def box(self, center, size, color, rotation=None, person_id=0):
        self.add(CUBE, color, center, size, rotation, person_id)

    def ball(self, center, size, color, rotation=None, person_id=0):
        self.add(SPHERE, color, center, size, rotation, person_id)

    def limb(self, start, end, radius, color, person_id=0):
        a, b = np.asarray(start), np.asarray(end)
        axis = unit(b-a)
        reference = [0, 0, 1] if abs(axis[2]) < .9 else [0, 1, 0]
        x = unit(np.cross(reference, axis))
        y = np.cross(axis, x)
        self.add(CYLINDER, color, (a+b)/2, (radius, radius, float(np.linalg.norm(b-a))),
                 np.stack([x, y, axis], axis=1), person_id)

    def array(self):
        return np.concatenate(self.parts) if self.parts else np.zeros((0, 10), 'f4')


def meshes():
    cp, cn = [], []
    faces = [([1,0,0], [( .5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5),(.5,-.5,.5)]),
             ([-1,0,0], [(-.5,.5,-.5),(-.5,-.5,-.5),(-.5,-.5,.5),(-.5,.5,.5)]),
             ([0,1,0], [(-.5,.5,-.5),(-.5,.5,.5),(.5,.5,.5),(.5,.5,-.5)]),
             ([0,-1,0], [(.5,-.5,-.5),(.5,-.5,.5),(-.5,-.5,.5),(-.5,-.5,-.5)]),
             ([0,0,1], [(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]),
             ([0,0,-1], [(-.5,.5,-.5),(.5,.5,-.5),(.5,-.5,-.5),(-.5,-.5,-.5)])]
    for normal, pts in faces:
        for i in [0,1,2,0,2,3]:
            cp.append(pts[i]); cn.append(normal)
    sp, sn = [], []
    def point(lat, lon):
        return (math.sin(lat)*math.cos(lon), math.sin(lat)*math.sin(lon), math.cos(lat))
    for a in range(8):
        for b in range(12):
            pts = [point(a*math.pi/8, b*math.tau/12),
                   point((a+1)*math.pi/8, b*math.tau/12),
                   point((a+1)*math.pi/8, (b+1)*math.tau/12),
                   point(a*math.pi/8, (b+1)*math.tau/12)]
            for i in [0,1,2,0,2,3]: sp.append(pts[i]); sn.append(pts[i])
    yp, yn = [], []
    for b in range(12):
        c, s = math.cos(b*math.tau/12), math.sin(b*math.tau/12)
        c2, s2 = math.cos((b+1)*math.tau/12), math.sin((b+1)*math.tau/12)
        pts = [(c,s,-.5), (c2,s2,-.5), (c2,s2,.5), (c,s,.5)]
        norms = [(c,s,0),(c2,s2,0),(c2,s2,0),(c,s,0)]
        for i in [0,1,2,0,2,3]: yp.append(pts[i]); yn.append(norms[i])
    return [(np.asarray(p, 'f4'), np.asarray(n, 'f4')) for p,n in [(cp,cn),(sp,sn),(yp,yn)]]


CUBE, SPHERE, CYLINDER = meshes()


def build_store():
    g = Geometry()
    rng = np.random.default_rng(641)
    # Shared floor plan: colored map areas are zones, not opaque dividing walls.
    g.box((8, 4.5, -.12), (16,9,.20), (.57,.58,.56))
    for _, _, (x0,y0,x1,y1), color, *_ in ZONES:
        base = np.asarray(rgb(color))*.13 + np.asarray([.65,.64,.60])*.87
        g.box(((x0+x1)/2,(y0+y1)/2,-.015), (x1-x0,y1-y0,.025), base)
    for x in np.arange(0,16,.5):
        g.box((x,4.5,.006), (.007,9,.008), (.48,.49,.48))
    for y in np.arange(0,9,.5):
        g.box((8,y,.007), (16,.007,.008), (.48,.49,.48))
    # Three exterior walls; left wall contains two door openings.
    wall = (.82,.83,.80)
    g.box((8,-.10,1.25),(16,.18,2.5),wall)
    g.box((16.10,4.5,1.25),(.18,9,2.5),wall)
    g.box((8,9.10,1.25),(16,.18,2.5),wall)
    for a,b in [(0,.65),(2.35,6.65),(8.35,9)]:
        g.box((-.10,(a+b)/2,1.25),(.18,b-a,2.5),wall)
    for cy in [1.5,7.5]:
        for yy in [cy-.87,cy+.87]:
            g.box((0,yy,1.35),(.12,.10,2.7),(.17,.20,.22))
        g.box((0,cy,2.65),(.12,1.84,.12),(.17,.20,.22))
        g.box((.01,cy,.012),(.6,1.65,.025),(.10,.12,.13))
    # Small wall placards echo the attached map without coloring all footage.
    for _,_,(x0,y0,x1,y1),c,*_ in ZONES:
        if y0==0:
            g.box(((x0+x1)/2,.02,2.0),(1.55,.055,.38),rgb(c))
        elif y1==9:
            g.box(((x0+x1)/2,8.97,2.0),(1.55,.055,.38),rgb(c))
    palette = [(.72,.09,.10),(.04,.39,.12),(.08,.22,.60),(.91,.71,.13),
               (.70,.57,.40),(.84,.84,.80),(.33,.08,.35)]
    def shelf(x,y,sx,sy,height=1.35):
        g.box((x,y,height/2),(sx,sy,height),(.20,.22,.23))
        for z in [.16,.49,.82,1.15]:
            g.box((x,y,z),(sx+.025,sy+.025,.05),(.66,.66,.62))
            n = max(3,int(sx/.17))
            for k in range(n):
                for edge in [-1,1]:
                    xx=x-sx/2+(k+.5)*sx/n
                    yy=y+edge*sy*.32
                    col=palette[int(rng.integers(len(palette)))]
                    h=float(rng.uniform(.15,.23))
                    g.box((xx,yy,z+.05+h/2),(sx/n*.79,sy*.22,h),col)
                    g.box((xx,yy-edge*sy*.115,z+.05+h*.45),(sx/n*.63,.012,h*.35),(.86,.84,.76))
    # Narrow wall fixtures leave a continuous circulation path through every zone.
    shelf(2.9,.42,3.4,.48)
    shelf(7.25,.42,2.0,.48); shelf(10.15,.42,2.0,.48)
    shelf(14.20,.42,2.5,.48,1.55)
    shelf(14.15,8.55,2.4,.48)
    shelf(3.15,8.55,2.7,.48)
    # Left/right aisle fixtures are rotated wall shelves.
    before=len(g.parts)
    shelf(0,0,1.5,.45)
    base_parts=g.parts[before:]; g.parts=g.parts[:before]
    for cx,cy in [(.45,4.5),(15.55,4.5)]:
        for arr in base_parts:
            a=arr.copy(); old=a[:,0].copy(); a[:,0]=cx-a[:,1]; a[:,1]=cy+old
            oldn=a[:,3].copy(); a[:,3]=-a[:,4]; a[:,4]=oldn
            g.parts.append(a)
    # Gondolas, refrigerated cases, produce bins, and checkout terminals.
    shelf(7.0,2.05,.80,.55); shelf(10.8,2.05,.80,.55)
    for x in [12.9,14.05,15.15]:
        g.box((x,.53,1.0),(.92,.58,2.0),(.16,.20,.22))
        g.box((x,.835,1.08),(.80,.025,1.58),(.21,.39,.42))
        for z in [.5,.95,1.4]:
            g.box((x,.85,z),(.78,.035,.045),(.70,.73,.73))
        g.box((x+.30,.87,1.02),(.025,.035,.43),(.79,.80,.78))
    for xx in [1.4,3.0,4.6]:
        g.box((xx,.90,.48),(1.1,.62,.96),(.45,.31,.18))
        for k in range(12):
            g.ball((xx+float(rng.uniform(-.42,.42)),.90+float(rng.uniform(-.2,.2)),1.02),
                   (.07,.07,.06),[(.47,.65,.10),(.64,.14,.10),(.73,.65,.18)][k%3])
    for xx in [6.7,9.1,11.25]:
        g.box((xx,8.18,.52),(1.45,.85,1.04),(.36,.38,.36))
        g.box((xx,8.18,1.07),(1.52,.9,.08),(.14,.16,.16))
        g.box((xx+.34,8.30,1.23),(.08,.09,.30),(.16,.17,.18))
        g.box((xx+.34,8.28,1.46),(.37,.08,.28),(.10,.12,.13))
        g.box((xx+.34,8.225,1.46),(.31,.012,.22),(.12,.47,.52))
        g.box((xx-.34,8.14,1.13),(.31,.25,.05),(.50,.50,.46))
    return g.array()


def waypoint(t,x,y): return (float(t),float(x),float(y))


def build_people():
    anchors=[(3.95,1.65),(8.75,1.42),(13.85,1.7),(13.85,4.55),
             (13.7,7.30),(8.6,7.35),(2.0,7.10),(2.0,4.55)]
    people=[]
    skins=[(.72,.48,.32),(.43,.27,.18),(.86,.65,.47),(.61,.39,.25)]
    # Every staff member patrols, serves one customer, and resumes their patrol.
    for i,(x,y) in enumerate(anchors):
        points=[waypoint(0,x,y),waypoint(6,x+.28,y+.20),waypoint(12,x,y),
                waypoint(19,x,y),waypoint(30,x,y),waypoint(37,x+.28,y+.20),
                waypoint(47,x-.22,y+.16),waypoint(59.9,x,y)]
        people.append(dict(id=i+1,name=f"E{i+1:02d}",role="employee",shirt=VEST,
                           pants=(.10,.14,.20),skin=skins[i%4],path=points,
                           engagement=(19,30),facing_override=0.0))
    colors=[(.06,.32,.66),(.14,.48,.26),(.60,.09,.17),(.47,.20,.57),
            (.80,.80,.76),(.07,.52,.58),(.27,.28,.30),(.62,.32,.47)]
    # One customer per zone moves into a staff-facing position, then leaves for a shared aisle.
    for i,(x,y) in enumerate(anchors):
        target=(x+.72,y)
        hub=(6.3+(i%3)*1.75,3.6+(i%2)*1.6)
        start=(x+.78,min(8.0,y+.70))
        points=[waypoint(0,*start),waypoint(9,x+.80,y+.50),waypoint(19,*target),
                waypoint(30,*target),waypoint(42,*hub),waypoint(53,*hub),
                waypoint(59.9,x+.85,y+.4)]
        people.append(dict(id=9+i,name=f"C{i+1:02d}",role="customer",shirt=colors[i],
                           pants=(.12,.17,.24),skin=skins[(i+2)%4],path=points,
                           engagement=(19,30),facing_override=math.pi))
    extra_routes=[
        [(-.8,1.5),(2.5,1.5),(5.9,3.5),(8.1,4.5),(12.8,4.4),(14.1,6.8),(8.0,7.3)],
        [(-.8,7.5),(3.5,7.5),(5.9,5.5),(8.2,4.8),(11.3,3.6),(13.4,2.6),(14.2,1.6)],
        [(14.5,6.8),(12.8,6.7),(11.2,5.6),(8.1,4.5),(5.8,3.5),(3.0,1.8),(-.8,1.5)],
        [(13.5,1.5),(12.8,2.6),(11.4,3.5),(8.2,4.8),(6.1,5.5),(3.0,7.5),(-.8,7.5)],
    ]
    for i,route in enumerate(extra_routes):
        people.append(dict(id=17+i,name=f"C{i+9:02d}",role="customer",shirt=colors[(i+3)%8],
                           pants=(.19,.19,.20),skin=skins[(i+1)%4],
                           path=[waypoint(j*59.9/(len(route)-1),*p) for j,p in enumerate(route)],
                           engagement=None))
    return people


def person_state(p,t):
    path=p['path']
    i=min(len(path)-2,max(0,int(np.searchsorted([a[0] for a in path],t,side='right')-1)))
    a,b=path[i],path[i+1]
    f=np.clip((t-a[0])/max(b[0]-a[0],1e-8),0,1)
    x=a[1]+f*(b[1]-a[1]); y=a[2]+f*(b[2]-a[2])
    speed=math.hypot(b[1]-a[1],b[2]-a[2])/max(b[0]-a[0],1e-8)
    angle=math.atan2(b[2]-a[2],b[1]-a[1]) if speed>.025 else .35+p['id']*.7
    active=bool(p.get('engagement') and p['engagement'][0]<=t<=p['engagement'][1])
    if active: angle=p['facing_override']
    return float(x),float(y),angle,speed,active


def draw_person(g,p,t):
    x,y,a,speed,active=person_state(p,t)
    if not (-.25<x<16.25 and -.25<y<9.25): return
    c,s=math.cos(a),math.sin(a)
    rot=np.array([[c,-s,0],[s,c,0],[0,0,1]],dtype=np.float32)
    pid=p['id']; skin=p['skin']; shirt=p['shirt']; pants=p['pants']
    swing=math.sin(t*7.5+pid*.8)*min(.27,speed*.65)
    bob=abs(math.sin(t*7.5+pid*.8))*.016 if speed>.04 else .003*math.sin(t*2+pid)
    def at(v): return np.asarray([x,y,bob])+rot@np.asarray(v)
    def ball(v,sc,col):g.ball(at(v),sc,col,rot,pid)
    def box(v,sc,col):g.box(at(v),sc,col,rot,pid)
    def limb(a,b,r,col):g.limb(at(a),at(b),r,col,pid)
    # Soft contact shadow, separate from the person's segmentation mask.
    g.ball((x,y,.008),(.31,.26,.003),(.39,.39,.36),person_id=0)
    ball((0,0,1.18),(.20,.265,.32),shirt)
    ball((0,0,.89),(.16,.23,.17),pants)
    limb((0,0,1.43),(0,0,1.52),.067,skin)
    ball((0,0,1.65),(.12,.115,.155),skin)
    ball((-.025,0,1.75),(.118,.12,.084),(.10,.075,.06))
    ball((.118,0,1.66),(.028,.037,.027),skin)
    for side in [-1,1]:
        leg=side*swing
        hip=(-.01,side*.125,.91)
        knee=(leg*.53,side*.14,.51)
        foot=(leg,side*.14,.09)
        limb(hip,knee,.093,pants);ball(knee,(.083,.081,.082),pants)
        limb(knee,foot,.075,pants)
        ball((leg+.05,side*.14,.066),(.145,.075,.065),(.09,.085,.08))
        shoulder=(0,side*.245,1.39)
        elbow=(-side*swing*.60,side*.30,1.13)
        hand=(-side*swing*.85,side*.30,.88)
        if active and side==1:
            elbow=(.21,.27,1.14);hand=(.41,.13,1.11)
        limb(shoulder,elbow,.076,shirt)
        limb(elbow,hand,.059,skin)
        ball(hand,(.062,.052,.077),skin)
    if p['role']=='employee':
        # Full orange vest; contrasting reflective bands wrap all four sides.
        for z in [1.08,1.29]:
            box((.189,0,z),(.022,.43,.041),(.88,.91,.85))
            box((-.189,0,z),(.022,.43,.041),(.88,.91,.85))
            box((0,.242,z),(.32,.018,.041),(.88,.91,.85))
            box((0,-.242,z),(.32,.018,.041),(.88,.91,.85))
        box((.202,0,1.20),(.012,.017,.49),(.15,.15,.15))
        box((.205,-.11,1.35),(.015,.072,.052),(.89,.91,.89))
    elif pid%3==0:
        limb((-.08,-.22,1.40),(-.07,.22,.91),.022,(.04,.04,.04))
        ball((-.07,.29,.89),(.10,.12,.15),(.25,.20,.15))


VERTEX = '''#version 330
uniform mat4 vp;
in vec3 in_position;
in vec3 in_normal;
in vec3 in_color;
in float in_id;
out vec3 world;
out vec3 normal;
out vec3 color;
flat out float ident;
void main(){ world=in_position; normal=in_normal; color=in_color; ident=in_id;
gl_Position=vp*vec4(in_position,1.0); }
'''
FRAGMENT = '''#version 330
in vec3 world; in vec3 normal; in vec3 color; flat in float ident;
layout(location=0) out vec4 pixel;
layout(location=1) out float object_id;
void main(){
vec3 n=normalize(normal);
float light=.60+.27*max(dot(n,normalize(vec3(-.2,-.3,1.0))),0.0)
                 +.10*max(dot(n,normalize(vec3(.7,.2,.7))),0.0);
float grain=fract(sin(dot(world.xy,vec2(127.1,311.7)))*43758.5453);
vec3 c=color*light*(.986+.028*grain);
pixel=vec4(pow(c,vec3(.88)),1.0); object_id=ident;
}
'''


def font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
              '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()


class Renderer:
    def __init__(self):
        self.ctx=moderngl.create_standalone_context(backend='egl')
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.program=self.ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.color=self.ctx.texture((W,H),4)
        self.ids=self.ctx.texture((W,H),1,dtype='f4')
        self.fbo=self.ctx.framebuffer([self.color,self.ids],self.ctx.depth_renderbuffer((W,H)))
        self.static=self.ctx.buffer(build_store().tobytes())
        self.static_vao=self.ctx.vertex_array(self.program,[(self.static,'3f 3f 3f 1f',
              'in_position','in_normal','in_color','in_id')])
        self.dynamic=self.ctx.buffer(reserve=24_000_000)
        self.dynamic_vao=self.ctx.vertex_array(self.program,[(self.dynamic,'3f 3f 3f 1f',
              'in_position','in_normal','in_color','in_id')])
        self.views=[look_at(z[4],z[5]) for z in ZONES]
        self.proj=perspective(78,W/H)
        self.vps=[self.proj @ view for view in self.views]
        self.small=font(16); self.title=font(22)

    def frame(self,cam,t,geometry,people,frame_index):
        self.fbo.use(); self.ctx.viewport=(0,0,W,H)
        self.fbo.clear(.50,.53,.53,1)
        self.program['vp'].write(self.vps[cam].T.astype('f4').tobytes())
        self.static_vao.render()
        self.dynamic_vao.render(vertices=len(geometry))
        raw=self.fbo.read(components=3,alignment=1)
        im=Image.frombytes('RGB',(W,H),raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        mask=np.frombuffer(self.fbo.read(attachment=1,components=1,dtype='f4'),dtype='f4').reshape(H,W)[::-1]
        records=[]
        for p in people:
            yy,xx=np.where(mask==p['id'])
            if len(xx)<12:continue
            x,y,angle,speed,active=person_state(p,t)
            records.append(dict(person_id=p['name'],role=p['role'],
                bbox_xyxy=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],
                visible_pixels=len(xx),world_position_m=[round(x,4),round(y,4)],
                facing_world_xy=[round(math.cos(angle),4),round(math.sin(angle),4)],
                scripted_engagement=active))
        d=ImageDraw.Draw(im)
        d.rectangle((0,0,W,35),fill=(17,24,29))
        d.text((12,7),f"CAM {cam+1:02d}  |  {ZONES[cam][1].upper()}",font=self.small,fill=(224,234,237))
        d.ellipse((W-68,12,W-59,21),fill=(231,53,55));d.text((W-51,7),'REC',font=self.small,fill=(238,238,238))
        timestamp=(BASE_TIME+timedelta(seconds=t)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-5]+' PKT'
        d.rectangle((0,H-29,W,H),fill=(17,24,29))
        d.text((12,H-24),timestamp,font=self.small,fill=(219,229,232))
        d.text((W-304,H-24),f'SYNTHETIC  |  FRAME {frame_index:05d}',font=self.small,fill=(170,186,190))
        return im,records


def encoder(path,w,h,fps):
    return subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',
        '-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','-',
        '-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20',
        '-pix_fmt','yuv420p','-video_track_timescale','90000','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)


def map_panel(people,t):
    im=Image.new('RGB',(640,336),(22,30,37));d=ImageDraw.Draw(im)
    d.text((16,12),'STORE PLAN  /  LIVE SHARED POSITIONS',font=font(17),fill=(227,235,240))
    sx,sy,ox,oy=31.5,25.0,66,61
    for cid,name,(x0,y0,x1,y1),c,*_ in ZONES:
        rr=(ox+x0*sx,oy+y0*sy,ox+x1*sx,oy+y1*sy)
        d.rectangle(rr,fill=c,outline=(30,30,30),width=2)
        d.text((rr[0]+5,rr[1]+4),'CAM '+cid,font=font(13),fill=(18,24,30))
    d.rectangle((ox+5.5*sx,oy+3*sy,ox+12.1*sx,oy+6.1*sy),fill=(16,20,24))
    d.text((ox+6.9*sx,oy+4.1*sy),'SHARED AISLE',font=font(12),fill=(194,208,215))
    for cy in [1.5,7.5]:
        d.rectangle((ox-5,oy+(cy-.6)*sy,ox+5,oy+(cy+.6)*sy),fill='#981354',outline='#12171c')
    for p in people:
        x,y,*_=person_state(p,t)
        if 0<x<16 and 0<y<9:
            px,py=ox+x*sx,oy+y*sy
            col=(255,108,10) if p['role']=='employee' else (53,120,246)
            d.ellipse((px-4,py-4,px+4,py+4),fill=col,outline='white',width=1)
    d.text((16,303),'ORANGE = STAFF    BLUE = CUSTOMER',font=font(15),fill=(220,230,235))
    return im


def monitor(frames,people,t):
    canvas=Image.new('RGB',(1920,1080),(12,18,23));d=ImageDraw.Draw(canvas)
    d.text((22,10),'RETAILPULSE  /  SECURITY MONITOR',font=font(24),fill=(226,235,240))
    d.text((1130,14),'8 CAMERAS  |  SYNCHRONIZED  |  SYNTHETIC TEST',font=font(18),fill=(130,176,185))
    for i,im in enumerate(frames):
        # Fit 16:9 feeds without distortion into the 3x3 NVR panel layout.
        tile=Image.new('RGB',(640,336),(6,9,12))
        resized=im.resize((594,334),Image.Resampling.LANCZOS)
        tile.paste(resized,(23,1))
        canvas.paste(tile,((i%3)*640,48+(i//3)*336))
    canvas.paste(map_panel(people,t),(1280,720))
    for x in [640,1280]:d.line((x,48,x,1056),fill=(53,69,77),width=2)
    for y in [48,384,720,1056]:d.line((0,y,1920,y),fill=(53,69,77),width=2)
    d.text((22,1059),'ALL FEEDS SHARE SOURCE TIME  |  STAFF: ORANGE REFLECTIVE VESTS  |  CUSTOMERS: OTHER CLOTHING',font=font(14),fill=(161,178,187))
    return canvas


def write_metadata(out,people,duration,fps):
    cameras=[]
    for i,z in enumerate(ZONES):
        cam=dict(camera_id=f'cam{i+1:02d}',zone_name=z[1],bounds_xy_m=z[2],map_color=z[3],
                 position_xyz_m=z[4],look_at_xyz_m=z[5],vertical_fov_degrees=78,
                 resolution=[W,H],fps=fps,frame_count=round(duration*fps),
                 view_matrix=look_at(z[4],z[5]).tolist(),
                 projection_matrix=perspective(78,W/H).tolist(),
                 source_start='2026-10-04T10:00:00+05:00',offset_seconds=0,
                 video=f'cam{i+1:02d}.mp4')
        cameras.append(cam)
    manifest=dict(schema_version=1,synthetic=True,render_style='procedural 3D CCTV simulation',
       random_seed=641,duration_seconds=duration,fps=fps,frame_count=round(duration*fps),
       store_dimensions_m=[16,9],coordinate_system='x right, y down on map, z up',
       map_interpretation='8 colored perimeter zones; black center is a shared circulation aisle; two magenta left markers are doorways',
       source_map='reference_map.png',start_time='2026-10-04T10:00:00+05:00',
       camera_count=8,cameras=cameras,monitor='security_monitor_8cams.mp4',
       roles={'employee':{'vest_color_rgb':[255,74,4],'vest_color_description':'bright orange with silver reflective bands'},
              'customer':{'shirt_colors':'blue, green, burgundy, purple, off-white, teal, charcoal, mauve; no orange vests'}},
       actor_count=len(people),employee_count=8,customer_count=12,
       annotations='observations.jsonl',annotation_note='Visible bounding boxes from the renderer depth-tested instance mask; no guarantee of pretrained detector performance. HUD may overlap a few mask pixels.',
       synchronization='Frame n in all files represents the same world state at n/fps seconds. No independently generated camera timelines.',
       events='events.json',actors='actors.json',
       limitations=['Synthetic people and simplified store materials.',
          'Only one store, one lighting configuration and one deterministic scenario.',
          'Employee vest color is a controlled fixture convention, not evidence of employee identity in real stores.',
          'Projected ground-plane motion uses the included 3D camera matrices; no automatic real-camera calibration.',
          'Not a replacement for held-out real CCTV for accuracy evaluation.'])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    actor_export=[]
    for p in people:
        actor_export.append(dict(person_id=p['name'],role=p['role'],
              shirt_rgb=[round(v*255) for v in p['shirt']],
              waypoints=[dict(time_seconds=a[0],x_m=a[1],y_m=a[2]) for a in p['path']]))
    (out/'actors.json').write_text(json.dumps(actor_export,indent=2)+'\n')
    events=[dict(event_type='scripted_engagement',employee_id=f'E{i+1:02d}',customer_id=f'C{i+1:02d}',
                 start_seconds=19,end_seconds=min(30,duration),duration_seconds=max(0,min(30,duration)-19),
                 zone=f'cam{i+1:02d}',definition='scripted close proximity, mutual facing and gesturing; ground truth from simulation')
            for i in range(8) if duration>19]
    (out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    (out/'README.md').write_text(f'''# Eight-camera retail CCTV test footage

Open **security_monitor_8cams.mp4** for an NVR-style security-office display.
Eight independent files **cam01.mp4** through **cam08.mp4** are available for
the analysis pipeline. Each feed is {W} x {H}, {fps} FPS, {duration:g} seconds.
They use H.264/yuv420p, frame-aligned timestamps, no audio, no camera time offset.

## Map interpretation

The supplied unlabeled map is interpreted as a 16 x 9 m open-plan store:
eight colored peripheral zones surrounding the black shared aisle. Color
regions indicate camera zones, not solid room partitions. Two small magenta
marks at the left are assumed to be entrances. Camera mounts, shelves and
door meanings are assumptions because the reference has no legend or view
arrows. See reference_map.png and layout_preview.png.

CAM01 pink upper left: entrance/produce; CAM02 tan upper middle: grocery;
CAM03 gray upper right: chilled; CAM04 yellow middle right: right aisle;
CAM05 red lower right: household; CAM06 cyan lower middle: checkout;
CAM07 purple lower left: lower entrance; CAM08 pale yellow middle left: left aisle.

## Shared scenario and employee colors

8 employees wear orange vests with silver reflective strips and dark trousers.
12 customers wear other clothing colors. Every person has one deterministic
world-space trajectory, used by every camera, so identities and movements are
consistent across overlapping views. Employee/customer pairs face one another
and gesture at 19-30 seconds; other customers enter, cross the center and exit.
The monitor's ninth tile shows the same live positions on the supplied layout.

## Testing and labels

Use the individual feeds for inference; the monitor grid is for human review.
A COCO-pretrained YOLO model predicts `person`, not `employee` from uniform
color automatically. Test a person detector plus an orange-region check on
torso crops, or train a custom two-class employee/customer detector. The color
convention applies to this fixture only. Person detection accuracy on these
procedural human models is not guaranteed.

manifest.json contains cameras, shared clock, resolution and assumptions.
actors.json contains persistent synthetic IDs, roles, colors and trajectories.
observations.jsonl contains one record per camera/frame with depth-tested
visible person boxes, visible pixel counts, facing and world positions.
events.json contains eight scripted engagement intervals. preview_*.jpg are
decoded frames from the final monitor file. verification.json records final
file checks. No real-world accuracy or training sufficiency is claimed.

## Regenerate

Requirements: Python 3.12+, numpy, pillow, moderngl, glcontext, and ffmpeg.
On Linux/WSL install the Python packages in a separate virtual environment;
the renderer uses a headless EGL context and works with Mesa software OpenGL.

`python generate.py --output ./rerender --duration 60 --fps 10`

Use a new output directory: the generator intentionally refuses to replace
an existing recording. Source time starts at 2026-10-04 10:00:00 Asia/Karachi.
''')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).parent)
    parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--fps',type=int,default=10)
    parser.add_argument('--preview-only',action='store_true')
    args=parser.parse_args()
    if args.duration<=0 or args.fps<1:parser.error('Positive duration and FPS required')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    people=build_people();r=Renderer()
    print('Renderer:',r.ctx.info['GL_RENDERER'],flush=True)
    if args.preview_only:
        g=Geometry()
        for p in people:draw_person(g,p,22)
        data=g.array();r.dynamic.write(data.tobytes())
        frames=[r.frame(i,22,data,people,220)[0] for i in range(8)]
        for i,im in enumerate(frames):
            im.save(out/f'draft_cam{i+1:02d}.jpg',quality=94)
        monitor(frames,people,22).save(out/'draft_monitor.jpg',quality=94)
        map_panel(people,22).save(out/'layout_preview.png')
        print('Preview complete',flush=True);return
    videos=[out/f'cam{i+1:02d}.mp4' for i in range(8)]+[out/'security_monitor_8cams.mp4']
    if any(p.exists() for p in videos):raise FileExistsError('Use a new output directory to preserve existing videos')
    write_metadata(out,people,args.duration,args.fps)
    writers=[encoder(p,W,H,args.fps) for p in videos[:8]]+[encoder(videos[-1],1920,1080,args.fps)]
    start=time.monotonic();n=round(args.duration*args.fps)
    completed=False
    try:
        with (out/'observations.jsonl').open('w') as labels:
            for frame_index in range(n):
                t=frame_index/args.fps;g=Geometry()
                for p in people:draw_person(g,p,t)
                geometry=g.array();r.dynamic.write(geometry.tobytes())
                frames=[]
                for i in range(8):
                    im,records=r.frame(i,t,geometry,people,frame_index)
                    frames.append(im);writers[i].stdin.write(im.tobytes())
                    labels.write(json.dumps(dict(camera_id=f'cam{i+1:02d}',frame_index=frame_index,
                        source_time_seconds=t,people=records),separators=(',',':'))+'\n')
                grid=monitor(frames,people,t);writers[-1].stdin.write(grid.tobytes())
                if frame_index in [0,round(22*args.fps),round(45*args.fps)]:
                    grid.save(out/f'render_preview_{frame_index:05d}.jpg',quality=94)
                if frame_index%10==0:
                    elapsed=time.monotonic()-start
                    print(f'{frame_index+1}/{n} shared frames | elapsed {elapsed:.1f}s | ETA {elapsed/max(frame_index+1,1)*(n-frame_index-1):.1f}s',flush=True)
        completed=True
    finally:
        for writer in writers:
            if writer.stdin:writer.stdin.close()
        codes=[writer.wait() for writer in writers]
        if any(codes):raise RuntimeError(f'Video encoding failed: {codes}')
    if completed:
        map_panel(people,22).save(out/'layout_preview.png')
        print(f'Finished {len(videos)} videos in {time.monotonic()-start:.1f}s',flush=True)


if __name__=='__main__':main()
