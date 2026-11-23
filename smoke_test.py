from config_models import CMSConfig
from geometry.crossbeam_builder import build_crossbeam
from geometry.cms_builder import build_cms

# All four crossbeam families.
for bt, name in [(1,'Monoleg'),(2,'Power-B'),(3,'Standard-B'),(4,'D-section')]:
    r = build_crossbeam(CMSConfig().beam.__class__(beam_type=bt))
    print(f'{name:12s}: valid={r.solid.isValid()} volume={r.solid.Volume():.1f}')

# Default beam-plate/back-plate architecture.
c = CMSConfig()
c.beam.beam_type = 3
r = build_cms(c, lambda *args: True)
print('Default CMS:', all(s.isValid() for s in r.components.values()), r.derived)

# v0.4 through-bolt / zero-straight tapered-Z stress case.
c = CMSConfig.load_json('presets/03_rail_bolted_zero_straights_tapered_z.json')
r = build_cms(c, lambda *args: True)
print('Rail zero-straight:', all(s.isValid() for s in r.components.values()))
print('Bolt axes:', r.derived['rail_bolt_axes_lh'])

# Same rail-bolted case with the intentionally allowed top/bottom split.
c.crush_can.split = 'top_bottom'
c.crush_can.larger_half = 'top'
r = build_cms(c, lambda *args: True)
print('Rail top/bottom split:', all(s.isValid() for s in r.components.values()))


# Crossbeam placement datum: beam and both plate pairs move together in Z.
c = CMSConfig()
c.beam.beam_type = 3
c.beam.front_face_center_z = 125.0
c.crush_can.rear_z = 125.0
c.crush_can.front_z = 125.0
r = build_cms(c, lambda *args: True)
for name in ('Beam', 'Beam_Plate_LH', 'Beam_Plate_RH', 'Back_Plate_LH', 'Back_Plate_RH'):
    shape = r.components[name]
    assert shape.isValid(), name
    bb = shape.BoundingBox()
    center_z = (bb.zmin + bb.zmax) / 2
    assert abs(center_z - c.beam.front_face_center_z) < 1e-6, (name, center_z)
print('Shifted Z placement: beam, beam plates and back plates all centred at Z=125 mm')


# v0.4 deterministic attachment-plane test against a synthetic slanted limiter.
import cadquery as cq
from config_models import CrushCanSpec, FrontInterfaceSpec
from geometry.crush_can_builder import generate_can
ys=(-100,100)
xr=[20-0.20*y for y in ys]
xf=[x-4 for x in xr]
lim=cq.Workplane('XY').workplane(offset=-100).polyline([
    (xr[0],ys[0]),(xr[1],ys[1]),(xf[1],ys[1]),(xf[0],ys[0])
]).close().extrude(200).val()
cs=CrushCanSpec(rear_width=80,rear_depth=80,rear_z=0,
                front_width=80,front_depth=60,front_z=5,
                thickness=2,overlap=4,split='top_bottom',larger_half='top',
                rear_straight=20,front_straight=15,transition_radius=20,
                rear_datum_offset=180,lh_center_y=0)
fh=FrontInterfaceSpec(mode='stop_at_contact')
h,info=generate_can(cs,fh,lim,rear_x=200,center_y=0,direction=-1,
                    interactive_radius_cb=lambda *args: True)
print('v0.8 slanted limiter:',all(x.isValid() for x in h.values()),
      'dx/dy=',info.attachment_plane.dx_dy,
      'angle=',info.attachment_plane.angle_deg)
assert abs(info.attachment_plane.dx_dy + 0.20) < 1e-6

# v0.5 beam-plate exact-fit check: a sidewall front edge must lie on the actual
# rear plate plane rather than on the old finite-probe approximation.
c = CMSConfig(); c.beam.beam_type=3
r = build_cms(c, lambda *args: True)
pl = r.derived['front_attachment_plane']; cy=r.derived['lh_center_y']
y = pl['y_outer'] + c.crush_can.thickness
x_expected = pl['x_center'] + pl['dx_dy']*(y-cy)
import cadquery as cq
sh = r.components['Crush_Can_LH_Top']
bb=sh.BoundingBox(); z=c.crush_can.front_z
probe=cq.Solid.makeBox(bb.xmax-bb.xmin+20,0.06,0.06,cq.Vector(bb.xmin-10,y-0.03,z-0.03))
q=sh.intersect(probe); x_actual=q.BoundingBox().xmin
print('v0.8 exact beam-plate fit: delta=',x_actual-x_expected)
assert abs(x_actual-x_expected) < 1e-4

# v0.5 B-section principle check: top/bottom rear lands at X=20 and a recessed
# centre valley at X=5.  The can must stop at X=20 even at the valley Z level.
land_top=cq.Solid.makeBox(20,200,40,cq.Vector(0,-100,20))
land_bot=cq.Solid.makeBox(20,200,40,cq.Vector(0,-100,-60))
valley=cq.Solid.makeBox(20,200,40,cq.Vector(-15,-100,-20))  # rear face X=5
beam_like=land_top.fuse(land_bot).fuse(valley).clean()
cs=CrushCanSpec(rear_width=80,rear_depth=100,rear_z=0,
                front_width=80,front_depth=100,front_z=0,
                thickness=2,overlap=4,split='top_bottom',larger_half='top',
                rear_straight=0,front_straight=0,transition_radius=0,
                rear_datum_offset=180,lh_center_y=0)
fh=FrontInterfaceSpec(mode='stop_at_contact')
h,info=generate_can(cs,fh,beam_like,rear_x=200,center_y=0,direction=-1,
                    interactive_radius_cb=lambda *args: True,limiter_kind='beam')
# probe outer sidewall at valley Z=0
sh=h['top']; bb=sh.BoundingBox(); y=-cs.front_width/2+cs.thickness
probe=cq.Solid.makeBox(bb.xmax-bb.xmin+20,0.06,0.06,cq.Vector(bb.xmin-10,y-0.03,-0.03))
q=sh.intersect(probe); xv=q.BoundingBox().xmin
print('v0.8 beam valley bridge: front X at valley=',xv,'expected 20')
assert abs(xv-20.0) < 1e-4


# v0.8 projected beam-plate envelope check.  A plate covers only the middle
# Z band.  Can material inside that band must stop at rear plane X=10, while
# requested top/bottom flow outside the plate envelope remains continuous.
plate=cq.Solid.makeBox(10,120,40,cq.Vector(0,-60,-20))  # rear face X=10
cs=CrushCanSpec(rear_width=80,rear_depth=80,rear_z=0,
                front_width=80,front_depth=80,front_z=0,
                thickness=2,overlap=4,split='top_bottom',larger_half='top',
                rear_straight=0,front_straight=0,transition_radius=0,
                rear_datum_offset=190,lh_center_y=0)
fh=FrontInterfaceSpec(mode='flow_over',extra_after_contact=15,
                      flow_top=True,flow_bottom=True,flow_inner=False,flow_outer=False)
h,info=generate_can(cs,fh,plate,rear_x=200,center_y=0,direction=-1,
                    interactive_radius_cb=lambda *args: True,limiter_kind='beam_plate')
# Middle-Z sidewall must have no material ahead of X=10.
allsh=h['top'].fuse(h['bottom']).clean()
probe_mid=cq.Solid.makeBox(60,0.08,0.08,cq.Vector(-20,-39.0,-0.04))
qm=allsh.intersect(probe_mid)
assert qm.Volume()>1e-10
assert qm.BoundingBox().xmin >= 10-1e-4
# Top wall outside plate Z envelope must still flow past X=10.
probe_top=cq.Solid.makeBox(60,0.08,0.08,cq.Vector(-20,-0.04,38.9))
qt=allsh.intersect(probe_top)
assert qt.Volume()>1e-10
assert qt.BoundingBox().xmin < 9.0
print('v0.8 beam-plate projected envelope: mid Xmin=',qm.BoundingBox().xmin,
      'top-flow Xmin=',qt.BoundingBox().xmin)


# v0.8 actual beam-plate radius conformity check.
# Make the can taller than the plate so its longitudinal sidewall crosses the
# complete top/bottom plate bend regions. Compare the first can X and the first
# plate X through those radii; the difference should be numerical only.
c = CMSConfig(); c.beam.beam_type=3
c.crush_can.rear_depth=120.0
c.crush_can.front_depth=120.0
r = build_cms(c, lambda *args: True)
plate = r.components['Beam_Plate_LH']
allcan = r.components['Crush_Can_LH_Top'].fuse(r.components['Crush_Can_LH_Bottom']).clean()
cy = r.derived['lh_center_y']
y = cy - c.crush_can.front_width/2 + c.crush_can.thickness
pbb=plate.BoundingBox()

def xr_at(shape,y,z,eps=0.005):
    bb=shape.BoundingBox()
    pr=cq.Solid.makeBox(bb.xmax-bb.xmin+30,2*eps,2*eps,
                        cq.Vector(bb.xmin-15,y-eps,z-eps))
    q=shape.intersect(pr)
    if q.Volume()<=1e-10:
        return None
    qb=q.BoundingBox()
    return qb.xmin,qb.xmax

checked=0
max_gap=0.0
for z in [pbb.zmin+3.0, pbb.zmin+4.0, pbb.zmin+5.0, pbb.zmin+6.0,
          pbb.zmin+7.0, pbb.zmin+8.0, pbb.zmin+9.0,
          pbb.zmax-9.0, pbb.zmax-8.0, pbb.zmax-7.0, pbb.zmax-6.0,
          pbb.zmax-5.0, pbb.zmax-4.0, pbb.zmax-3.0]:
    px=xr_at(plate,y,z)
    cx=xr_at(allcan,y,z)
    if px and cx:
        gap=cx[0]-px[1]
        max_gap=max(max_gap,abs(gap))
        checked+=1
assert checked>=8
assert max_gap < 0.05, f'Beam-plate radius gap too large: {max_gap}'
print('v0.8 beam-plate radius conformity: samples=',checked,'max |gap|=',max_gap)
