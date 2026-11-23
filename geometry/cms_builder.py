from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import time, json
import cadquery as cq
from config_models import CMSConfig
from geometry.crossbeam_builder import build_crossbeam
from geometry.beam_plate_builder import build_beam_plate
from geometry.crush_can_builder import generate_can
from geometry.rear_interface import build_back_plate, cut_rail_holes
from geometry.validator import validate_config
from geometry.bead_layout import calculate_bead_layout

@dataclass
class CMSResult:
    components:dict
    can_info:object
    warnings:list[str]=field(default_factory=list)
    derived:dict=field(default_factory=dict)


def build_cms(config:CMSConfig, radius_approval_cb=None):
    vr=validate_config(config)
    if vr.errors: raise ValueError('\n'.join(vr.errors))
    warnings=list(vr.warnings)

    br=build_crossbeam(config.beam)
    components={'Beam':br.solid}
    bpr=None
    if config.beam_plate.enabled:
        bpr=build_beam_plate(config.beam,config.beam_plate,br)
        components['Beam_Plate_LH']=bpr.lh;components['Beam_Plate_RH']=bpr.rh
        limiter=bpr.lh
        center_y=bpr.mid_y
    else:
        limiter=br.solid
        center_y=config.crush_can.lh_center_y

    # v0.12 rear datum: user offset is a GLOBAL X distance from the actual
    # frontmost extreme of the crossbeam (normally the Y=0 crown) to the
    # rearmost crush-can construction datum.  It is intentionally independent
    # of beam plate / local limiter position.
    beam_frontmost_x=float(br.solid.BoundingBox().xmin)
    rear_x=beam_frontmost_x+config.crush_can.rear_datum_offset

    limiter_kind='beam_plate' if bpr else 'beam'
    halves,ci=generate_can(config.crush_can,config.front_interface,limiter,rear_x,center_y,
                           direction=-1,interactive_radius_cb=radius_approval_cb,
                           limiter_kind=limiter_kind)

    if config.rear_mount.architecture=='rail_bolted':
        halves,axes,w=cut_rail_holes(halves,config.crush_can,config.rear_mount,ci,rear_x,center_y,direction=-1)
        warnings.extend(w)
    else:
        axes=[]
        bp_lh,bp_rh=build_back_plate(
            rear_x, center_y, config.rear_mount, center_z=br.derived['z_translation']
        )
        components['Back_Plate_LH']=bp_lh;components['Back_Plate_RH']=bp_rh

    for name,sh in halves.items():
        components[f'Crush_Can_LH_{name.title()}']=sh
        components[f'Crush_Can_RH_{name.title()}']=sh.mirror('XZ')

    warnings.extend(ci.warnings)

    bead_layout = calculate_bead_layout(config.beads, config.crush_can, ci, direction=-1)
    if config.beads.enabled:
        warnings.append(
            f'Bead layout solved for {bead_layout["count"]} set(s); embossment CAD is not yet applied in v0.12.'
        )

    derived={'rear_x':rear_x,'rear_datum_offset':config.crush_can.rear_datum_offset,'rear_datum_reference':'crossbeam_frontmost_x','crossbeam_frontmost_x':beam_frontmost_x,'lh_center_y':center_y,'limiting_component':limiter_kind,'front_interface_rule':('beam_plate_directional_shadow' if bpr else 'beam_rear_land_envelope'),
             'can_length':ci.length,'contact_x':ci.contact_x,'transition_radius':ci.transition_radius,
             'front_attachment_plane':{
                 'angle_deg':ci.attachment_plane.angle_deg,
                 'x_outer':ci.attachment_plane.x_outer,
                 'x_inner':ci.attachment_plane.x_inner,
                 'x_center':ci.attachment_plane.x_center,
                 'y_outer':ci.attachment_plane.y_outer,
                 'y_inner':ci.attachment_plane.y_inner,
                 'dx_dy':ci.attachment_plane.dx_dy,
             },
             'beam_front_face_center_z':config.beam.front_face_center_z,
             'crush_can_corner_radii':{'inner':config.crush_can.corner_radii()[0],'outer':config.crush_can.corner_radii()[1]},
             'beam_plate':(bpr.derived if bpr else None),
             'rail_bolt_axes_lh':axes,'bead_layout_lh':bead_layout,'beam':br.derived}
    return CMSResult(components,ci,warnings,derived)


def export_result(result:CMSResult,config:CMSConfig,out_dir):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    (out/'Component_CAD').mkdir(exist_ok=True)
    ts=time.strftime('%Y%m%d_%H%M%S')
    suffix='_'+ts if config.export.timestamp_names else ''
    paths=[]
    if config.export.individual_steps:
        for name,sh in result.components.items():
            p=out/'Component_CAD'/f'{name}{suffix}.step';cq.exporters.export(sh,str(p));paths.append(p)
    if config.export.assembly_step:
        assy=cq.Assembly(name='CMS')
        for name,sh in result.components.items():assy.add(sh,name=name)
        p=out/f'CMS{suffix}.step';assy.save(str(p));paths.append(p)
    if config.export.config_json:
        p=out/f'CMS_config{suffix}.json';config.save_json(p);paths.append(p)
    if config.export.validation_text:
        p=out/f'CMS_build_summary{suffix}.txt'
        lines=['CMS Generator v0.12 build summary','',json.dumps(result.derived,indent=2,default=str),'','Warnings:']
        lines.extend(['- '+x for x in result.warnings] or ['- None'])
        p.write_text('\n'.join(lines),encoding='utf-8');paths.append(p)
    return paths
