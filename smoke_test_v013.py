"""v0.13 upper/lower flow continuity and B-valley regression."""
import cadquery as cq
from config_models import CrushCanSpec,FrontInterfaceSpec,CMSConfig
from geometry.crush_can_builder import generate_can
from geometry.validator import validate_config

def needle(shape,x0,x1,y,z,eps=0.15):
    pr=cq.Solid.makeBox(x1-x0,eps,eps,cq.Vector(x0,y-eps/2,z-eps/2))
    q=shape.intersect(pr)
    return q.BoundingBox().xmin if q.Volume()>1e-8 else None

# Beam plate is a thin flat back wall. A tall can overhangs it at top and bottom.
plate=cq.Solid.makeBox(10,120,40,cq.Vector(0,-60,-20))
s=CrushCanSpec(rear_width=80,rear_depth=80,front_width=80,front_depth=80,
               rear_z=0,front_z=0,thickness=2,overlap=4,
               rear_straight=0,front_straight=0,transition_radius=0,lh_center_y=0)
f=FrontInterfaceSpec(mode='flow_over',extra_after_contact=15,flow_top=True,flow_bottom=False,flow_inner=False,flow_outer=False)
h,info=generate_can(s,f,plate,rear_x=200,center_y=0,interactive_radius_cb=lambda *args:True,limiter_kind='beam_plate')
sh=h['top'].fuse(h['bottom']).clean()
assert sh.isValid() and all(v.isValid() for v in h.values())
# The upper sidewall at Z+25 is not part of the top flat face and MUST flow.
x_upper=needle(sh,-10,30,-39,25)
assert x_upper is not None and x_upper < 9, ('upper sidewall missing extension',x_upper)
x_lower=needle(sh,-10,30,-37,-25)
assert x_lower is not None and x_lower >= 9.9, ('lower sidewall incorrectly extended',x_lower)
x_mid=needle(sh,-10,30,-39,0)
assert x_mid is not None and x_mid >= 9.9, ('middle sidewall passed through beam plate',x_mid)
print('beam-plate top-only: upper sidewall flows, bottom stopped; middle plate face protected',x_upper,x_lower,x_mid)

# A B-section-like limiter has upper and lower lands (rear X=20) and a
# recessed central valley (rear X=5). The valley bridge must enforce X>=20
# through the beam height, including when extra flow length exceeds beam depth.
land_top=cq.Solid.makeBox(20,200,40,cq.Vector(0,-100,20))
land_bottom=cq.Solid.makeBox(20,200,40,cq.Vector(0,-100,-60))
valley=cq.Solid.makeBox(20,200,40,cq.Vector(-15,-100,-20))
beam=land_top.fuse(land_bottom).fuse(valley).clean()
s=CrushCanSpec(rear_width=80,rear_depth=160,front_width=80,front_depth=160,
               rear_z=0,front_z=0,thickness=2,overlap=4,
               rear_straight=0,front_straight=0,transition_radius=0,lh_center_y=0)
f=FrontInterfaceSpec(mode='flow_over',extra_after_contact=90,flow_top=True,flow_bottom=True,flow_inner=True,flow_outer=True)
h,info=generate_can(s,f,beam,rear_x=200,center_y=0,interactive_radius_cb=lambda *args:True,limiter_kind='beam')
assert all(v.isValid() for v in h.values())
sh=h['top'].fuse(h['bottom']).clean()
mid=needle(sh,-120,35,-39,0)
upper=needle(sh,-120,35,-39,68)
lower=needle(sh,-120,35,-37,-68)
assert mid is not None and mid >= 19.99, ('B valley leaked',mid)
assert upper is not None and upper < 19, ('beam top sidewall did not flow',upper)
assert lower is not None and lower < 19, ('beam bottom sidewall did not flow',lower)
print('bare-beam: central sidewall does not enter valley; upper/lower portions flow',mid,upper,lower)

# Independent side-only flow is invalid without a plate.
c=CMSConfig();c.beam_plate.enabled=False
c.front_interface=FrontInterfaceSpec(mode='flow_over',flow_top=False,flow_bottom=False,flow_inner=True)
assert validate_config(c).errors
print('v0.13 flow regression PASSED')
