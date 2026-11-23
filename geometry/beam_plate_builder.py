from __future__ import annotations
from dataclasses import dataclass, field
import math
import cadquery as cq
from config_models import BeamSpec, BeamPlateSpec
from geometry.crossbeam_builder import BeamResult


@dataclass
class BeamPlateResult:
    lh: cq.Shape
    rh: cq.Shape
    mid_x: float
    mid_y: float
    outer_x: float
    outer_y: float
    inner_x: float
    inner_y: float
    derived: dict = field(default_factory=dict)


def _rear_normal(t: cq.Vector) -> cq.Vector:
    # Guideline tangent is in XY. Rotate clockwise so the normal points toward
    # the beam rear (+X for the normal CMS orientation).
    n=cq.Vector(t.y,-t.x,0)
    if n.x < 0:
        n=cq.Vector(-n.x,-n.y,0)
    L=math.hypot(n.x,n.y)
    if L <= 1e-12:
        raise RuntimeError('Could not determine local beam rear normal')
    return cq.Vector(n.x/L,n.y/L,0)


def _offset_point(guideline, u: float, distance: float):
    p=guideline.positionAt(u,mode='length')
    t=guideline.tangentAt(u,mode='length')
    n=_rear_normal(t)
    return cq.Vector(p.x+distance*n.x,p.y+distance*n.y,p.z), t, n


def _bracket_root(fn, lo, hi, samples=120):
    x0=lo; f0=fn(x0)
    if abs(f0)<1e-10:return x0,x0
    for i in range(1,samples+1):
        x1=lo+(hi-lo)*i/samples; f1=fn(x1)
        if abs(f1)<1e-10:return x1,x1
        if f0*f1 < 0:return x0,x1
        x0,f0=x1,f1
    return None


def _bisect(fn, a, b, iterations=70):
    if a==b:return a
    fa=fn(a); fb=fn(b)
    if fa*fb>0:raise ValueError('Internal beam-plate root was not bracketed')
    for _ in range(iterations):
        m=(a+b)/2; fm=fn(m)
        if abs(fm)<1e-10:return m
        if fa*fm<=0:b=m;fb=fm
        else:a=m;fa=fm
    return (a+b)/2


def build_beam_plate(beam_spec: BeamSpec, plate: BeamPlateSpec, beam_result: BeamResult) -> BeamPlateResult:
    if not plate.enabled:
        raise ValueError('Beam plate is disabled')
    if min(plate.width, plate.thickness) <= 0:
        raise ValueError('Beam-plate width/thickness must be positive')
    if min(plate.slip_plane_gap_outer,plate.slip_plane_gap_inner) < 0:
        raise ValueError('Beam-plate slip-plane gaps cannot be negative')

    ri,ro=plate.bend_radii()
    if min(beam_spec.height,beam_spec.depth) <= 2*ro:
        raise ValueError('Beam-plate bend radius is too large for the selected beam section envelope')

    g=beam_result.guideline
    outer_y_target=-abs(float(plate.outer_y))
    d_outer=float(beam_spec.depth)+float(plate.thickness)+float(plate.slip_plane_gap_outer)
    d_inner=float(beam_spec.depth)+float(plate.thickness)+float(plate.slip_plane_gap_inner)

    # Outer station is specified on the actual beam-plate rear-face path, not on
    # the beam guideline. Search only the LH half; RH remains a mirror.
    f_outer=lambda u:_offset_point(g,u,d_outer)[0].y-outer_y_target
    bracket=_bracket_root(f_outer,0.0,0.5)
    if bracket is None:
        y0=_offset_point(g,0.0,d_outer)[0].y; yc=_offset_point(g,0.5,d_outer)[0].y
        raise ValueError(
            f'Beam-plate Outer Y={outer_y_target:.3f} mm is outside the available LH offset path '
            f'({y0:.3f} to {yc:.3f} mm)'
        )
    u_outer=_bisect(f_outer,*bracket)
    p_outer,t_outer,n_outer=_offset_point(g,u_outer,d_outer)

    # Width retains the legacy meaning: straight chord distance between the
    # outer and inner section origins. Inner gap is allowed to differ.
    def width_residual(u):
        p,_,_=_offset_point(g,u,d_inner)
        return math.hypot(p.x-p_outer.x,p.y-p_outer.y)-float(plate.width)
    bracket=_bracket_root(width_residual,u_outer,0.5)
    if bracket is None:
        maxp,_,_=_offset_point(g,0.5,d_inner)
        maxw=math.hypot(maxp.x-p_outer.x,maxp.y-p_outer.y)
        raise ValueError(f'Beam-plate width {plate.width:.3f} mm does not fit before Y=0 (available chord {maxw:.3f} mm)')
    u_inner=_bisect(width_residual,*bracket)
    p_inner,t_inner,n_inner=_offset_point(g,u_inner,d_inner)

    p1=cq.Plane(origin=(p_outer.x,p_outer.y,p_outer.z),xDir=(1,0,0),
                normal=(t_outer.x,t_outer.y,t_outer.z))
    p2=cq.Plane(origin=(p_inner.x,p_inner.y,p_inner.z),xDir=(1,0,0),
                normal=(t_inner.x,t_inner.y,t_inner.z))

    def section(plane, gap):
        # ro is the outside sheet radius, ri the inside sheet radius.
        return (cq.Workplane(plane)
            .moveTo(0,0)
            .lineTo(0,beam_spec.height/2+plate.thickness-ro)
            .radiusArc((-ro,beam_spec.height/2+plate.thickness),-ro)
            .lineTo(-ro-plate.beam_overlap-gap,beam_spec.height/2+plate.thickness)
            .lineTo(-ro-plate.beam_overlap-gap,beam_spec.height/2)
            .lineTo(-ro-gap+plate.thickness,beam_spec.height/2)
            .radiusArc((-plate.thickness,beam_spec.height/2-ro+plate.thickness),ri)
            .lineTo(-plate.thickness,0)
            .lineTo(-plate.thickness,-beam_spec.height/2+ro-plate.thickness)
            .radiusArc((-ro,-beam_spec.height/2),ri)
            .lineTo(-ro-plate.beam_overlap-gap,-beam_spec.height/2)
            .lineTo(-ro-plate.beam_overlap-gap,-beam_spec.height/2-plate.thickness)
            .lineTo(-ro,-beam_spec.height/2-plate.thickness)
            .radiusArc((0,-beam_spec.height/2-plate.thickness+ro),-ro)
            .close().val())

    lh=cq.Solid.makeLoft([
        section(p1,float(plate.slip_plane_gap_outer)),
        section(p2,float(plate.slip_plane_gap_inner))
    ],ruled=True)
    if not lh.isValid():
        raise RuntimeError('Generated LH beam plate is invalid')
    rh=lh.mirror('XZ')

    # Explicitly guard the reason the old radius was coupled to the beam.
    iv=beam_result.solid.intersect(lh).Volume()
    if iv > 1e-5:
        raise ValueError(
            f'Independent beam-plate bend radius/gap causes beam interference '
            f'(intersection volume {iv:.6f} mm^3). Increase the relevant slip-plane gap or bend radius.'
        )

    derived={
        'inner_bend_radius':ri,'outer_bend_radius':ro,
        'outer_slip_gap':float(plate.slip_plane_gap_outer),
        'inner_slip_gap':float(plate.slip_plane_gap_inner),
        'outer_guideline_fraction':float(u_outer),'inner_guideline_fraction':float(u_inner),
        'beam_plate_chord_width':math.hypot(p_inner.x-p_outer.x,p_inner.y-p_outer.y),
        'beam_intersection_volume':iv,
    }
    return BeamPlateResult(lh=lh,rh=rh,
                           mid_x=(p_inner.x+p_outer.x)/2,mid_y=(p_inner.y+p_outer.y)/2,
                           outer_x=p_outer.x,outer_y=p_outer.y,inner_x=p_inner.x,inner_y=p_inner.y,
                           derived=derived)
