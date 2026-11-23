"""v0.13 regression: analytic C-section corners and continuous longitudinal faces.

Does not depend on any optional STEP viewer. Uses CadQuery/OpenCascade topology checks
and a STEP export/import round-trip to guard against new faceting.
"""
from pathlib import Path
import tempfile
import cadquery as cq
from config_models import CrushCanSpec, CMSConfig
from geometry.crush_can_builder import analytic_c_wire, build_raw, AttachmentPlane
from geometry.cms_builder import build_cms

# Any split and either larger half must have exactly four analytic corner arcs
# (two outside/two inside) with no discretized straight facets.
for split,names in [('top_bottom',('top','bottom')),('inner_outer',('inner','outer'))]:
    for larger in names:
        cs=CrushCanSpec(split=split,larger_half=larger)
        for name in names:
            section=analytic_c_wire(80,80,0,cs,name,0,0)
            types=[e.geomType() for e in section.Edges()]
            assert len(types)==12,types
            assert types.count('CIRCLE')==4,types
            assert types.count('LINE')==8,types
            assert section.isValid() and section.IsClosed()
print('All four C-section half/split variants have 4 real circular arc edges')

# Angle-aware slanted plane sections use true ELLIPSE arcs (shear of circle)
# rather than trying to approximate their curvature by linear edges.
cs=CrushCanSpec()
p=AttachmentPlane(-40,40,18,-2,0,8,-0.25,-14.036)
section=analytic_c_wire(80,80,0,cs,'top',0,0,p,1.0)
types=[e.geomType() for e in section.Edges()]
assert types.count('ELLIPSE')==4 and types.count('LINE')==8,types
print('Inclined section has four exact continuous elliptical arcs')

# Smooth axial loft: all stations are absorbed into ONE face per input edge,
# rather than creating a band per station for each formerly faceted corner.
for cs in [
    CrushCanSpec(),
    CrushCanSpec(front_depth=65,front_z=5,front_width=75,transition_radius=35),
    CrushCanSpec(split='inner_outer',larger_half='outer',rear_depth=90,front_depth=70,front_z=8,
                 rear_straight=0,front_straight=0,transition_radius=0),
]:
    halves=build_raw(cs,180,cs.transition_radius,200,0,attachment_plane=p,attach_length=160,orientation_spec=cs)
    for name,solid in halves.items():
        assert solid.isValid() and solid.Volume()>0,(cs.split,name)
        assert len(solid.Faces())==14,(cs.split,name,len(solid.Faces()))
        assert len(solid.Solids())==1
print('Straight, tapered and eccentric C-halves: valid smooth loft; 14 faces each')

# User-selected corner radius is propagated; do not bake in 5*t.
cs=CrushCanSpec(corner_radius_basis='inner',corner_radius_multiplier=3.0, thickness=2.5)
assert cs.corner_radii()==(7.5,10.0)
section=analytic_c_wire(90,90,0,cs,'top',0,0)
radii=sorted(round(e.radius(),6) for e in section.Edges() if e.geomType()=='CIRCLE')
assert radii==[7.5,7.5,10.0,10.0],radii
print('Corner radii follow user-selected Ri/Ro, not a hardcoded 4t/5t')

# STEP export must retain only the intended analytic/smooth faces, without
# the old corner_samples*number_of_stations sliver face explosion.
cs=CrushCanSpec(front_depth=68,front_z=4)
solid=build_raw(cs,180,60,200,0)['top']
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'analytic_can.step'
    cq.exporters.export(solid,str(path))
    imported=cq.importers.importStep(str(path)).val()
    assert imported.isValid()
    assert len(imported.Faces())==14,len(imported.Faces())
print('STEP export/import retains the 14-face continuous-corner topology')

# Full CMS uses v0.8 inherited beam-plate conformal shadow and must remain
# a valid connected assembly after the new loft and sequential shadow Boolean.
r=build_cms(CMSConfig(),lambda *args:True)
assert len(r.components)>=7
assert all(sh.isValid() for sh in r.components.values())
assert all(len(sh.Solids())==1 for name,sh in r.components.items() if name.startswith('Crush_Can_'))
print('Full default CMS remains valid with conformal beam-plate contact')
print('v0.13 analytic corner regressions PASSED')
