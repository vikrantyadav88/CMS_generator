from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from config_models import CMSConfig

@dataclass
class ValidationResult:
    errors:list[str]=field(default_factory=list)
    warnings:list[str]=field(default_factory=list)
    notes:list[str]=field(default_factory=list)
    @property
    def ok(self): return not self.errors


def validate_config(c:CMSConfig):
    r=ValidationResult()
    b=c.beam; p=c.beam_plate; cc=c.crush_can; rm=c.rear_mount; fi=c.front_interface
    if b.beam_type not in (1,2,3,4):
        r.errors.append('Beam family must be Monoleg, Power-B, Standard-B or D-section')
    if min(b.thickness,b.depth,b.height)<=0:
        r.errors.append('Beam thickness/depth/height must be positive')
    if b.sweep_mode not in ('constant_radius','step_guideline'):
        r.errors.append('Beam sweep mode must be constant-radius or STEP guideline')
    elif b.sweep_mode=='constant_radius':
        if min(b.sweep_radius,b.length)<=0:r.errors.append('Beam sweep radius/length must be positive')
        elif b.length>=2*b.sweep_radius:r.errors.append('Beam length must be smaller than the sweep-circle diameter')
    else:
        if not str(b.guideline_step_path).strip():r.errors.append('STEP-guideline mode requires a guideline STEP file')
        else:
            gp=Path(b.guideline_step_path).expanduser()
            if not gp.is_file() and not gp.is_absolute():
                gp=Path(__file__).resolve().parents[1]/gp
            if not gp.is_file():r.errors.append('Selected sweep-guideline STEP file does not exist')

    if p.enabled:
        if min(p.width,p.thickness)<=0:r.errors.append('Beam-plate width/thickness must be positive')
        if min(p.slip_plane_gap_outer,p.slip_plane_gap_inner)<0:r.errors.append('Beam-plate slip-plane gaps cannot be negative')
        try:
            pri,pro=p.bend_radii()
            if min(b.height,b.depth)<=2*pro:r.errors.append('Beam-plate bend radius is too large for the beam envelope')
        except Exception as exc:r.errors.append(f'Beam-plate bend radius: {exc}')

    if cc.split not in ('top_bottom','inner_outer'):r.errors.append('Invalid crush-can split')
    valid_large=('top','bottom') if cc.split=='top_bottom' else ('inner','outer')
    if cc.larger_half not in valid_large:r.errors.append(f'Larger half must be one of {valid_large}')
    if min(cc.rear_width,cc.rear_depth,cc.front_width,cc.front_depth,cc.thickness,cc.overlap)<=0:
        r.errors.append('Crush-can dimensions/thickness/overlap must be positive')
    try:
        cri,cro=cc.corner_radii()
        if min(cc.rear_width,cc.rear_depth,cc.front_width,cc.front_depth)<=2*cro:
            r.errors.append('A crush-can section is too small for the selected outer corner radius')
    except Exception as exc:r.errors.append(f'Crush-can corner radius: {exc}')
    if cc.rear_straight<0 or cc.front_straight<0:r.errors.append('Straight lengths cannot be negative')

    if rm.architecture not in ('back_plate','rail_bolted'):r.errors.append('Invalid rear architecture')
    if rm.architecture=='rail_bolted':
        if rm.bolt_count<1:r.errors.append('Rail bolt count must be at least 1')
        if rm.bolt_x_from_rear < 0:r.errors.append('Rail bolt X-from-rear cannot be negative')
        if rm.hole_diameter <= 0:r.errors.append('Rail bolt-hole diameter must be positive')
        if rm.vertical_edge_margin < 0:r.errors.append('Rail-bolt vertical edge margin cannot be negative')
        if cc.split=='top_bottom':r.warnings.append('Top/bottom split with rail sidewall bolting is allowed, but bolt/split interaction will be checked after geometry build')

    if fi.mode not in ('stop_at_contact','flow_over'):r.errors.append('Invalid front-interface mode')
    if fi.mode=='flow_over' and not any((fi.flow_top,fi.flow_bottom,fi.flow_inner,fi.flow_outer)):
        r.errors.append('Flow-over mode requires at least one allowed flow face')

    r.notes.append('Rear datum X offset is measured from the crossbeam frontmost X extreme to the rearmost crush-can datum')
    r.notes.append('Crush-can front attachment plane is derived automatically from the limiting component at the outer/inner sidewall Y locations')
    if b.sweep_mode=='step_guideline':
        r.notes.append('STEP guideline is treated as the crossbeam outer/front envelope; translation is normalised automatically while shape and scale are preserved')
    if p.enabled:
        r.notes.append('Beam-plate bend radius is independent of the beam; inner/outer counterpart is derived from sheet thickness')
    else:
        r.notes.append('Beam plate disabled: crossbeam becomes the limiting front component')
        if fi.mode=='flow_over' and (fi.flow_inner or fi.flow_outer):
            r.warnings.append('Beam-limited designs usually flow only on top/bottom; inner/outer flow is nevertheless permitted')

    if c.beads.enabled:
        bs=c.beads
        if bs.width <= 0:r.errors.append('Bead width must be positive')
        if bs.clear_spacing_x < 0:r.errors.append('Flat X land / clear bead spacing cannot be negative')
        if bs.minimum_rear_remainder < 0:r.errors.append('Minimum rear bead remainder cannot be negative')
        if bs.flat_land_z < 0:r.errors.append('Bead flat Z land cannot be negative')
        if bs.sidewall_sense not in ('inward','outward'):
            r.errors.append("Initial sidewall bead sense must be 'inward' or 'outward'")
        if bs.depth_mode not in ('uniform','face_specific'):
            r.errors.append("Bead depth mode must be 'uniform' or 'face_specific'")
        if bs.default_depth <= 0:r.errors.append('Default bead depth must be positive')
        if bs.depth_mode=='face_specific':
            vals=(bs.top_depth,bs.inner_depth,bs.bottom_depth,bs.outer_depth)
            if min(vals)<=0:r.errors.append('All face-specific bead depths must be positive')
        seen=set()
        for ov in bs.set_overrides:
            if ov.set_index < 1:r.errors.append('Bead-set override index must be at least 1')
            if ov.set_index in seen:r.errors.append(f'Duplicate bead-set override for set {ov.set_index}')
            seen.add(ov.set_index)
            if ov.depth_mode not in ('inherit','uniform','face_specific'):
                r.errors.append(f'Bead-set {ov.set_index} has invalid depth override mode')
            if ov.depth_mode=='uniform' and (ov.uniform_depth is None or ov.uniform_depth<=0):
                r.errors.append(f'Bead-set {ov.set_index} uniform depth override must be positive')
            if ov.depth_mode=='face_specific':
                vals=(ov.top_depth,ov.inner_depth,ov.bottom_depth,ov.outer_depth)
                if any(v is None or v<=0 for v in vals):
                    r.errors.append(f'Bead-set {ov.set_index} requires positive Top/Inner/Bottom/Outer depth overrides')
        # CAD embossment itself follows in the next milestone; v0.12 already
        # calculates/exports the automatic layout and stores all engineering inputs.
        r.warnings.append('Bead layout/configuration is active, but bead embossment CAD is not yet applied to the crush-can solids')
    return r
