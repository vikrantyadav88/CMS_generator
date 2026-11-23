from pathlib import Path
import math
from config_models import CMSConfig
from geometry.crossbeam_builder import build_crossbeam
from geometry.beam_plate_builder import build_beam_plate
from geometry.cms_builder import build_cms
from gui_main import HELP, PAGE_DEFAULT, HELP_ROOT, ScrollableForm

print('v0.12 smoke test')

# Four beam families remain valid.
for bt,name in [(1,'Monoleg'),(2,'Power-B'),(3,'Standard-B'),(4,'D-section')]:
    c=CMSConfig(); c.beam.beam_type=bt
    br=build_crossbeam(c.beam); assert br.solid.isValid(); print(name,'OK')


# Foundation regressions retained without multiplying full CMS builds.
for fn in ('presets/05_asymmetric_slip_gaps.json','presets/06_custom_STEP_guideline.json'):
    c=CMSConfig.load_json(fn); br=build_crossbeam(c.beam); assert br.solid.isValid()
    if c.beam_plate.enabled:
        bp=build_beam_plate(c.beam,c.beam_plate,br); assert bp.lh.isValid() and bp.rh.isValid()
assert CMSConfig.load_json('presets/06_custom_STEP_guideline.json').beam.sweep_mode=='step_guideline'
print('v0.10 sweep / beam-plate foundation regressions OK')

# Rear datum is referenced from actual crossbeam xmin/frontmost extreme.
c=CMSConfig(); r=build_cms(c,lambda *a:True)
expected=r.derived['crossbeam_frontmost_x']+c.crush_can.rear_datum_offset
assert abs(r.derived['rear_x']-expected)<1e-9
assert r.derived['rear_datum_reference']=='crossbeam_frontmost_x'
print('crossbeam-referenced rear datum OK')

# Corrected bead placement.
c=CMSConfig.load_json('presets/07_bead_layout_demo.json'); r=build_cms(c,lambda *a:True)
lay=r.derived['bead_layout_lh']; sets=lay['sets']; assert lay['count']>=2
W=c.beads.width; S=c.beads.clear_spacing_x
# Outer first leading edge has S flat land; successive outer centres have W+S pitch.
assert abs(sets[0]['outer_center_from_front']-(S+W/2))<1e-7
for a,b in zip(sets,sets[1:]): assert abs((b['outer_center_from_front']-a['outer_center_from_front'])-(W+S))<1e-6
# Inner first leading-edge clearance is the same S (within geometric solver tolerance).
assert abs(sets[0]['inner_center_from_front_x']-(S+W/2))<0.05
# Last inner and outer centres share one YZ plane.
assert abs(sets[-1]['inner_center_x']-sets[-1]['outer_center_x'])<1e-6
assert abs(sets[-1]['plane_angle_deg'])<1e-6
# Intermediate inner X centres are equispaced.
if len(sets)>2:
    dx=[sets[i+1]['inner_center_x']-sets[i]['inner_center_x'] for i in range(len(sets)-1)]
    assert max(dx)-min(dx)<1e-6
# First derived angle should naturally track the front interface because both walls keep equal front X land.
assert abs(sets[0]['plane_angle_deg']-r.derived['front_attachment_plane']['angle_deg'])<0.2
assert sets[1]['cut_radii']['top'] and sets[1]['cut_radii']['outer']
assert abs(sets[2]['depths']['inner']-1.6)<1e-12
print('corrected outer-anchor / inner-boundary bead layout + overrides OK:',lay['count'],'sets')

# Adaptive-height geometry was regression-tested separately on preset 03 during v0.12 development.

# Old v0.11 first_offset field is accepted and ignored/migrated without crashing.
d={'beads':{'enabled':True,'first_offset_from_front':35.0,'width':11.0,'clear_spacing_x':18.0}}
c=CMSConfig.from_dict(d); assert c.beads.clear_spacing_x==18.0
print('v0.11 bead preset migration OK')

paths=[HELP_ROOT/spec[0] for spec in HELP.values()]+[HELP_ROOT/rel for rel in PAGE_DEFAULT.values()]
assert not [str(p) for p in paths if not p.is_file()]
print('context-help placeholders OK:',len(paths))
print('v0.12 smoke test PASSED')
