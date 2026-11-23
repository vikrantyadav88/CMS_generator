from __future__ import annotations
import math
from pathlib import Path
from dataclasses import dataclass
import cadquery as cq
from cadquery.func import sweep
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.GeomAbs import GeomAbs_JoinType
from config_models import BeamSpec

def offset_open_wire(wire: cq.Wire, distance: float, kind: str = "arc") -> cq.Wire:

    if not isinstance(wire, cq.Wire):
        raise TypeError(f"Expected cq.Wire, received {type(wire).__name__}.")

    if wire.IsClosed():
        raise ValueError("offset_open_wire() expects an open wire, but the supplied wire is closed.")

    if not wire.isValid():
        raise ValueError("The input wire is invalid.")

    join_types = {
        "arc": GeomAbs_JoinType.GeomAbs_Arc,
        "intersection": GeomAbs_JoinType.GeomAbs_Intersection,
        "tangent": GeomAbs_JoinType.GeomAbs_Tangent,
    }

    if kind not in join_types:
        raise ValueError(
            f"Unsupported offset kind: {kind!r}. "
            f"Use one of {tuple(join_types)}."
        )

    offset_builder = BRepOffsetAPI_MakeOffset()
    offset_builder.Init(join_types[kind], True)
    offset_builder.AddWire(wire.wrapped)

    try:
        offset_builder.Perform(float(distance))
    except Exception as exc:
        raise RuntimeError(
            f"Open-wire offset failed at distance {distance}."
        ) from exc

    if not offset_builder.IsDone():
        raise RuntimeError(
            f"OpenCascade did not complete the offset operation "
            f"at distance {distance}."
        )

    raw_result = offset_builder.Shape()

    if raw_result.IsNull():
        raise RuntimeError(
            f"OpenCascade returned a null offset shape "
            f"at distance {distance}."
        )

    cq_result = cq.Shape.cast(raw_result)

    if isinstance(cq_result, cq.Wire):
        result_wires = [cq_result]
    else:
        result_wires = cq_result.Wires()

    if len(result_wires) != 1:
        raise RuntimeError(
            "Expected one open offset wire, but the operation "
            f"produced {len(result_wires)} wires. This normally "
            "indicates an offset self-intersection."
        )

    result_wire = result_wires[0]

    if result_wire.IsClosed():
        raise RuntimeError(
            "The offset result was unexpectedly closed."
        )

    if not result_wire.isValid():
        raise RuntimeError(
            "The resulting offset wire is invalid."
        )

    return result_wire

def extract_single_wire(profile) -> cq.Wire:

    if isinstance(profile, cq.Workplane):
        try:
            shape = profile.wire().val()
        except Exception:
            shape = profile.val()
    else:
        shape = profile

    if isinstance(shape, cq.Edge):
        shape = cq.Wire.assembleEdges([shape])

    if not isinstance(shape, cq.Wire):
        raise TypeError(f"Expected cq.Wire, received {type(shape).__name__}.")

    return shape


def point_distance(p1: cq.Vector, p2: cq.Vector) -> float:
    return (p1 - p2).Length


def make_closed_section(wire_a: cq.Wire, wire_b: cq.Wire) -> cq.Wire:

    a0 = wire_a.startPoint()
    a1 = wire_a.endPoint()

    b0 = wire_b.startPoint()
    b1 = wire_b.endPoint()

    direct = (point_distance(a0, b0) + point_distance(a1, b1))

    crossed = (point_distance(a0, b1) + point_distance(a1, b0))

    if direct <= crossed:
        connector_1 = cq.Edge.makeLine(a0, b0)
        connector_2 = cq.Edge.makeLine(a1, b1)
    else:
        connector_1 = cq.Edge.makeLine(a0, b1)
        connector_2 = cq.Edge.makeLine(a1, b0)

    closed_wire = cq.Wire.assembleEdges(list(wire_a.Edges()) + list(wire_b.Edges()) + [connector_1, connector_2])

    if not closed_wire.IsClosed():
        raise RuntimeError("Failed to close the offset section.")

    return closed_wire

def monoleg_upper_lower_rib():

    section_monoleg_mid_upper_lower_rib = (
        cq.Workplane(section_plane)
        .moveTo((2.5*beam_thickness+3+beam_midplane_radius), -beam_thickness)
        .lineTo(beam_midplane_radius+beam_thickness/2, -beam_thickness)
        .radiusArc((beam_thickness/2, -(beam_thickness+beam_midplane_radius)), -beam_midplane_radius)
        .lineTo(beam_thickness/2, -(beam_thickness+beam_midplane_radius+frontal_flat))
        .radiusArc((tp1x+beam_thickness/2, -(beam_thickness+beam_midplane_radius+frontal_flat+tp1z)), -beam_midplane_radius)
        .radiusArc((rib_depth+beam_thickness/2, -(beam_thickness+beam_midplane_radius+frontal_flat+tp2z)), beam_midplane_radius)
        .radiusArc((tp1x+beam_thickness/2, -(beam_thickness+beam_midplane_radius+frontal_flat+2*tp2z-tp1z)), beam_midplane_radius)
        .radiusArc((beam_thickness/2, -(beam_thickness+beam_midplane_radius+frontal_flat+2*tp2z)), -beam_midplane_radius)
        .lineTo(beam_thickness/2, -(beam_thickness+beam_midplane_radius+frontal_flat+2*tp2z+frontal_flat))
        .radiusArc((beam_midplane_radius+beam_thickness/2, -(beam_height-beam_thickness)/2), -beam_midplane_radius)
        .lineTo((beam_midplane_radius+horizontal_flat+beam_thickness/2), -(beam_height-beam_thickness)/2)
        .radiusArc(((beam_depth-beam_thickness/2), -(beam_height-beam_thickness)/2+beam_midplane_radius), -beam_midplane_radius)
        .lineTo((beam_depth-beam_thickness/2), -(beam_height-beam_thickness)/2+beam_midplane_radius+rear_flat_bottom)
        .radiusArc(((beam_depth-beam_thickness/2-beam_midplane_radius), 0), -beam_midplane_radius)
        .lineTo(beam_midplane_radius+beam_thickness/2, 0)
        .radiusArc((beam_thickness/2, beam_midplane_radius), beam_midplane_radius)
        .lineTo(beam_thickness/2, beam_midplane_radius+frontal_flat)
        .radiusArc((tp1x+beam_thickness/2, beam_midplane_radius+frontal_flat+tp1z), beam_midplane_radius)
        .radiusArc((rib_depth+beam_thickness/2, beam_midplane_radius+frontal_flat+tp2z), -beam_midplane_radius)
        .radiusArc((tp1x+beam_thickness/2, beam_midplane_radius+frontal_flat+2*tp2z-tp1z), -beam_midplane_radius)
        .radiusArc((beam_thickness/2, beam_midplane_radius+frontal_flat+2*tp2z), beam_midplane_radius)
        .lineTo(beam_thickness/2, beam_midplane_radius+frontal_flat+2*tp2z+frontal_flat)
        .radiusArc((beam_midplane_radius+beam_thickness/2, (beam_height-beam_thickness)/2), beam_midplane_radius)
        .lineTo((beam_midplane_radius+horizontal_flat+beam_thickness/2), (beam_height-beam_thickness)/2)
        .radiusArc(((beam_depth-beam_thickness/2), (beam_height-beam_thickness)/2-beam_midplane_radius), beam_midplane_radius)
        .lineTo((beam_depth-beam_thickness/2), (beam_height-beam_thickness)/2-beam_midplane_radius-rear_flat_top)
        .radiusArc(((beam_depth-beam_thickness/2-beam_midplane_radius), (beam_height-beam_thickness)/2-2*beam_midplane_radius-rear_flat_top), beam_midplane_radius)
        .lineTo((beam_depth-beam_midplane_radius-2.5*beam_thickness-3), (beam_height-beam_thickness)/2-2*beam_midplane_radius-rear_flat_top)
        .wire()
        .val()
    )

    section_wire = extract_single_wire(section_monoleg_mid_upper_lower_rib)
    offset_distance = beam_thickness/2 - topology_tol/2
    positive_offset_wire = offset_open_wire(section_wire, offset_distance, kind="arc")
    negative_offset_wire = offset_open_wire(section_wire, -offset_distance, kind="arc")
    closed_section_wire = make_closed_section(positive_offset_wire, negative_offset_wire)
    section_face = cq.Face.makeFromWires(closed_section_wire)
    beam_shape = sweep(section_face, guideline)
    beam_solids = beam_shape.Solids()

    if len(beam_solids) != 1:
        raise RuntimeError(f"Expected one swept solid, but found {len(beam_solids)}.")

    beam = beam_solids[0]

    return beam

def power_b_upper_lower_rib():

    section_power_b_outer_upper_lower_rib = (
        cq.Workplane(section_plane)
        .moveTo(0,0)
        .lineTo(0, frontal_flat_major/2)
        .radiusArc((tp1x, frontal_flat_major/2+tp1z), beam_bending_radius)
        .radiusArc((rib_depth, frontal_flat_major/2+tp2z), -beam_inner_radius)
        .radiusArc((tp1x, frontal_flat_major/2+2*tp2z-tp1z), -beam_inner_radius)
        .radiusArc((0, frontal_flat_major/2+2*tp2z), beam_bending_radius))
    if frontal_flat_minor > 1e-5:
        section_power_b_outer_upper_lower_rib = (
            section_power_b_outer_upper_lower_rib
            .lineTo(0, frontal_flat_major/2+2*tp2z+frontal_flat_minor))
    section_power_b_outer_upper_lower_rib = (
        section_power_b_outer_upper_lower_rib
        .radiusArc((beam_bending_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor+beam_bending_radius), beam_bending_radius)
        .lineTo(beam_bending_radius+horizontal_flat_major, frontal_flat_major/2+2*tp2z+frontal_flat_minor+beam_bending_radius)
        .radiusArc((beam_depth, frontal_flat_major/2+2*tp2z+frontal_flat_minor), beam_bending_radius)
        .lineTo(beam_depth, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat)
        .radiusArc((beam_depth-beam_bending_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-beam_bending_radius), beam_bending_radius)
        .lineTo(beam_depth-beam_bending_radius-horizontal_flat_minor, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-beam_bending_radius)
        .radiusArc((beam_depth-beam_bending_radius-horizontal_flat_minor-beam_inner_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-beam_bending_radius-beam_inner_radius), -beam_inner_radius)
        .lineTo(beam_depth-beam_bending_radius-horizontal_flat_minor-beam_inner_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-beam_bending_radius-beam_inner_radius-valley_flat)
        .radiusArc((beam_depth-beam_bending_radius-horizontal_flat_minor, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-beam_bending_radius-2*beam_inner_radius-valley_flat), -beam_inner_radius)
        .lineTo(beam_depth-beam_bending_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-beam_bending_radius-2*beam_inner_radius-valley_flat)
        .radiusArc((beam_depth, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat), beam_bending_radius)
        .lineTo(beam_depth, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat)
        .radiusArc((beam_depth-beam_bending_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-3*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat), beam_bending_radius)
        .lineTo(beam_bending_radius, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-3*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat)
        .radiusArc((0, frontal_flat_major/2+2*tp2z+frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat), beam_bending_radius))
    if frontal_flat_minor > 1e-5:
        section_power_b_outer_upper_lower_rib = (
            section_power_b_outer_upper_lower_rib
            .lineTo(0, frontal_flat_major/2+2*tp2z+2*frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat))
    section_power_b_outer_upper_lower_rib = (
        section_power_b_outer_upper_lower_rib
        .radiusArc((tp1x, frontal_flat_major/2+2*tp2z+2*frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat+tp1z), beam_bending_radius)
        .radiusArc((rib_depth, frontal_flat_major/2+2*tp2z+2*frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat+tp2z), -beam_inner_radius)
        .radiusArc((tp1x, frontal_flat_major/2+2*tp2z+2*frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat+2*tp2z-tp1z), -beam_inner_radius)
        .radiusArc((0, frontal_flat_major/2+2*tp2z+2*frontal_flat_minor-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat+2*tp2z), beam_bending_radius)
        .close()
    )

    outer_solid = section_power_b_outer_upper_lower_rib.sweep(guideline, isFrenet=True)

    section_power_b_inner_upper_lower_rib = (
        section_power_b_outer_upper_lower_rib
        .toPending()
        .offset2D(-beam_thickness+topology_tol)
    )

    inner_solid = section_power_b_inner_upper_lower_rib.sweep(guideline, isFrenet=True)
    beam_cut_list = outer_solid.cut(inner_solid).solids().vals()
    beam = min(beam_cut_list, key=lambda s: s.Volume())

    return beam

def standard_b_no_rib():

    standard_b_outer_no_rib = (
        cq.Workplane(section_plane)
        .moveTo(0,0)
        .lineTo(0, beam_height/2-beam_bending_radius)
        .radiusArc((beam_bending_radius, beam_height/2), beam_bending_radius)
        .lineTo(beam_bending_radius+horizontal_flat_major, beam_height/2)
        .radiusArc((beam_depth, beam_height/2-beam_bending_radius), beam_bending_radius)
        .lineTo(beam_depth, beam_height/2-beam_bending_radius-rear_flat)
        .radiusArc((beam_depth-beam_bending_radius, beam_height/2-beam_bending_radius-rear_flat-beam_bending_radius), beam_bending_radius)
        .lineTo(beam_depth-beam_bending_radius-horizontal_flat_minor, beam_height/2-beam_bending_radius-rear_flat-beam_bending_radius)
        .radiusArc((beam_depth-beam_bending_radius-horizontal_flat_minor-beam_inner_radius, beam_height/2-beam_bending_radius-rear_flat-beam_bending_radius-beam_inner_radius), -beam_inner_radius)
        .lineTo(beam_depth-beam_bending_radius-horizontal_flat_minor-beam_inner_radius, beam_height/2-beam_bending_radius-rear_flat-beam_bending_radius-beam_inner_radius-valley_flat)
        .radiusArc((beam_depth-beam_bending_radius-horizontal_flat_minor, beam_height/2-beam_bending_radius-rear_flat-beam_bending_radius-2*beam_inner_radius-valley_flat), -beam_inner_radius)
        .lineTo(beam_depth-beam_bending_radius, beam_height/2-beam_bending_radius-rear_flat-beam_bending_radius-2*beam_inner_radius-valley_flat)
        .radiusArc((beam_depth, beam_height/2-beam_bending_radius-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat), beam_bending_radius)
        .lineTo(beam_depth, beam_height/2-beam_bending_radius-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat)
        .radiusArc((beam_depth-beam_bending_radius, beam_height/2-beam_bending_radius-rear_flat-3*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat), beam_bending_radius)
        .lineTo(beam_bending_radius, beam_height/2-beam_bending_radius-rear_flat-3*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat)
        .radiusArc((0, beam_height/2-beam_bending_radius-rear_flat-2*beam_bending_radius-2*beam_inner_radius-valley_flat-rear_flat), beam_bending_radius)
        .close()
    )

    outer_solid = standard_b_outer_no_rib.sweep(guideline, isFrenet=True)

    standard_b_inner_no_rib = (
        standard_b_outer_no_rib
        .toPending()
        .offset2D(-beam_thickness+topology_tol)
    )

    inner_solid = standard_b_inner_no_rib.sweep(guideline, isFrenet=True)
    beam_cut_list = outer_solid.cut(inner_solid).solids().vals()
    beam = min(beam_cut_list, key=lambda s: s.Volume())

    return beam

def D_section():

    section_D_outer = (
        cq.Workplane(section_plane)
        .moveTo(beam_depth, vertical_flat/2)
        .radiusArc((horizontal_flat/2+beam_depth/2, beam_height/2), -beam_bending_radius)
        .lineTo((beam_depth-horizontal_flat)/2, beam_height/2)
        .radiusArc((0, vertical_flat/2), -beam_bending_radius)
        .lineTo(0, -vertical_flat/2)
        .radiusArc(((beam_depth-horizontal_flat)/2, -beam_height/2), -beam_bending_radius)
        .lineTo(horizontal_flat/2+beam_depth/2, -beam_height/2)
        .radiusArc((beam_depth, -beam_height/2+beam_bending_radius), -beam_bending_radius)
        .close()
    )

    outer_solid = section_D_outer.sweep(guideline, isFrenet=True)

    section_D_inner = (
        section_D_outer
        .toPending()
        .offset2D(-beam_thickness+topology_tol)
    )

    inner_solid = section_D_inner.sweep(guideline, isFrenet=True)
    beam_cut_list = outer_solid.cut(inner_solid).solids().vals()
    beam = min(beam_cut_list, key=lambda s: s.Volume())

    return beam


@dataclass
class BeamResult:
    solid: cq.Shape
    guideline: cq.Shape
    section_plane: cq.Plane
    x_origin_change: float
    ord: float
    bending_radius: float
    inner_radius: float
    derived: dict


def _bending_coeff(steel_grade):
    if steel_grade in (420, 440, 550): return 3.0
    if steel_grade in (780, 980): return 3.5
    if steel_grade == 1180: return 4.0
    if steel_grade in (1300, 1500, 1700): return 5.0
    return 5.0


def _extract_single_guideline(path: str) -> cq.Shape:
    p = Path(path).expanduser()
    if not p.is_file() and not p.is_absolute():
        project_relative = Path(__file__).resolve().parents[1] / p
        if project_relative.is_file():
            p = project_relative
    if not p.is_file():
        raise ValueError(f'Guideline STEP file does not exist: {p}')
    try:
        imported = cq.importers.importStep(str(p)).val()
    except Exception as exc:
        raise ValueError(f'Could not import sweep-guideline STEP: {exc}') from exc

    wires = list(imported.Wires())
    if len(wires) == 1:
        curve = wires[0]
    else:
        edges = list(imported.Edges())
        if len(edges) == 1:
            curve = edges[0]
        elif edges:
            combined = cq.Wire.combine(edges)
            if len(combined) != 1:
                raise ValueError('Guideline STEP must contain exactly one continuous open wire')
            curve = combined[0]
        else:
            raise ValueError('Guideline STEP contains no usable curve/edge geometry')

    if curve.IsClosed():
        raise ValueError('Guideline STEP must contain an open curve, not a closed loop')
    if not curve.isValid():
        raise ValueError('Imported sweep guideline is invalid')
    return curve


def _normalise_guideline(curve: cq.Shape) -> tuple[cq.Shape, dict]:
    """Normalise an outer-envelope guideline without changing its shape or scale.

    The supplied curve may be translated arbitrarily.  It must already lie in an
    XY-parallel plane and be approximately Y-symmetric.  We centre the endpoint
    Y midpoint on Y=0, put the endpoint X chord at X=0, and move its plane to Z=0.
    """
    p0 = curve.positionAt(0.0, mode='length')
    p1 = curve.positionAt(1.0, mode='length')
    if p0.y > p1.y:
        curve = curve.reverse()
        p0 = curve.positionAt(0.0, mode='length')
        p1 = curve.positionAt(1.0, mode='length')

    samples = [curve.positionAt(i/40.0, mode='length') for i in range(41)]
    zmin=min(p.z for p in samples); zmax=max(p.z for p in samples)
    yspan=max(p.y for p in samples)-min(p.y for p in samples)
    if yspan <= 1e-6:
        raise ValueError('Guideline STEP must span vehicle Y')
    ztol=max(0.05, 1e-4*yspan)
    if zmax-zmin > ztol:
        raise ValueError('Guideline STEP must lie in a plane parallel to XY (constant Z)')

    y_mid=(p0.y+p1.y)/2.0
    x_chord=(p0.x+p1.x)/2.0
    z_mid=sum(p.z for p in samples)/len(samples)
    curve=curve.translate((-x_chord,-y_mid,-z_mid))

    # Initial implementation intentionally keeps the existing symmetric CMS architecture.
    samples=[curve.positionAt(i/40.0, mode='length') for i in range(41)]
    sym_tol=max(0.5, 0.001*yspan)
    max_sym=0.0
    for i in range(21):
        a=samples[i]; b=samples[-1-i]
        max_sym=max(max_sym,abs(a.x-b.x),abs(a.y+b.y),abs(a.z-b.z))
    if max_sym > sym_tol:
        raise ValueError(
            f'Guideline STEP is not sufficiently Y-symmetric for the current mirrored CMS architecture '
            f'(max symmetry mismatch {max_sym:.3f} mm; tolerance {sym_tol:.3f} mm)'
        )

    p0=curve.positionAt(0.0,mode='length'); p1=curve.positionAt(1.0,mode='length')
    derived={
        'source_endpoints_before_normalisation': [[float(p0.x+x_chord),float(p0.y+y_mid),float(p0.z+z_mid)],
                                                  [float(p1.x+x_chord),float(p1.y+y_mid),float(p1.z+z_mid)]],
        'normalised_y_span': float(p1.y-p0.y),
        'normalised_curve_length': float(curve.Length()),
        'symmetry_max_mismatch': float(max_sym),
    }
    return curve,derived


def _make_guideline(spec: BeamSpec) -> tuple[cq.Shape, float, float, float, dict]:
    if spec.sweep_mode == 'constant_radius':
        if spec.sweep_radius <= 0 or spec.length <= 0:
            raise ValueError('Beam sweep radius and length must be positive')
        if spec.length >= 2*spec.sweep_radius:
            raise ValueError('Beam length must be smaller than the sweep-circle diameter')
        xo=((spec.sweep_radius**2)-((spec.length**2)/4))**0.5
        sag=spec.sweep_radius-xo
        g=cq.Edge.makeThreePointArc((0,-spec.length/2,0),(-sag,0,0),(0,spec.length/2,0))
        return g,float(spec.length),float(xo),float(sag),{
            'sweep_mode':'constant_radius','sweep_radius':float(spec.sweep_radius),
            'guideline_curve_length':float(g.Length()),'guideline_y_span':float(spec.length)
        }
    if spec.sweep_mode == 'step_guideline':
        if not str(spec.guideline_step_path).strip():
            raise ValueError('STEP-guideline mode requires a guideline STEP file')
        raw=_extract_single_guideline(spec.guideline_step_path)
        g,info=_normalise_guideline(raw)
        p0=g.positionAt(0.0,mode='length'); p1=g.positionAt(1.0,mode='length')
        info.update(sweep_mode='step_guideline',guideline_step_path=str(spec.guideline_step_path),
                    guideline_y_span=float(p1.y-p0.y),guideline_curve_length=float(g.Length()))
        return g,float(p1.y-p0.y),0.0,0.0,info
    raise ValueError("Beam sweep_mode must be 'constant_radius' or 'step_guideline'")


def build_crossbeam(spec: BeamSpec) -> BeamResult:
    """Build one of the four legacy crossbeam families on a circular or imported guideline."""
    global beam_thickness, beam_sweep_radius, beam_length, beam_depth, beam_height
    global steel_grade, beam_bending_radius, beam_inner_radius, topology_tol
    global x_origin_change, ord, guideline, t, section_plane
    global beam_midplane_radius, max_rib_depth, rib_depth, theta, tp1x, tp1z, tp2x, tp2z, rib_height
    global frontal_flat, rear_flat_top, rear_flat_bottom, horizontal_flat
    global valley_flat, frontal_flat_minor, frontal_flat_major, rear_flat
    global horizontal_flat_major, horizontal_flat_minor, vertical_flat

    if spec.beam_type not in (1,2,3,4):
        raise ValueError('beam_type must be 1 Monoleg, 2 Power-B, 3 Standard-B or 4 D-section')
    if min(spec.thickness, spec.depth, spec.height) <= 0:
        raise ValueError('Beam thickness/depth/height must be positive')

    beam_thickness=float(spec.thickness)
    beam_sweep_radius=float(spec.sweep_radius)
    beam_depth=float(spec.depth)
    beam_height=float(spec.height)
    steel_grade=spec.steel_grade
    topology_tol=1e-5

    coeff=_bending_coeff(steel_grade)
    beam_bending_radius=coeff*beam_thickness
    beam_inner_radius=(coeff-1)*beam_thickness

    guideline,beam_length,x_origin_change,ord,ginfo=_make_guideline(spec)
    t=guideline.tangentAt(0.0,mode='length')
    start=guideline.positionAt(0.0,mode='length')
    section_plane=cq.Plane(origin=(start.x,start.y,start.z),xDir=(1,0,0),normal=(t.x,t.y,t.z))

    derived={'bending_radius':beam_bending_radius,'inner_radius':beam_inner_radius,**ginfo}

    if spec.beam_type == 1:
        beam_midplane_radius=(beam_bending_radius+beam_inner_radius)/2
        max_rib_depth=beam_depth-2*beam_thickness-25
        rib_depth=min(max_rib_depth,2*beam_midplane_radius)
        if rib_depth <= 0: raise ValueError('Monoleg rib depth is non-positive; increase beam depth')
        theta=math.acos(1-rib_depth/(2*beam_midplane_radius))
        tp1x=beam_midplane_radius*(1-math.cos(theta)); tp1z=beam_midplane_radius*math.sin(theta)
        tp2x=(2*beam_midplane_radius)*(1-math.cos(theta)); tp2z=(2*beam_midplane_radius)*math.sin(theta)
        rib_height=2*tp2z
        frontal_flat=(beam_height-beam_thickness)/4-rib_height/2-beam_midplane_radius
        rear_flat_top=(beam_height-3*beam_thickness)/2-2*beam_midplane_radius
        rear_flat_bottom=(beam_height-beam_thickness)/2-2*beam_midplane_radius
        horizontal_flat=beam_depth-beam_thickness-2*beam_midplane_radius
        requested_rib_depth=rib_depth
        while True:
            try:
                solid=monoleg_upper_lower_rib()
                break
            except RuntimeError:
                rib_depth -= 0.5
                if rib_depth <= max(0.5, beam_thickness):
                    raise
                theta=math.acos(1-rib_depth/(2*beam_midplane_radius))
                tp1x=beam_midplane_radius*(1-math.cos(theta)); tp1z=beam_midplane_radius*math.sin(theta)
                tp2x=(2*beam_midplane_radius)*(1-math.cos(theta)); tp2z=(2*beam_midplane_radius)*math.sin(theta)
                rib_height=2*tp2z
                frontal_flat=(beam_height-beam_thickness)/4-rib_height/2-beam_midplane_radius
                rear_flat_top=(beam_height-3*beam_thickness)/2-2*beam_midplane_radius
                rear_flat_bottom=(beam_height-beam_thickness)/2-2*beam_midplane_radius
                horizontal_flat=beam_depth-beam_thickness-2*beam_midplane_radius
        derived.update(rib_depth=rib_depth, rib_height=rib_height)
        if rib_depth < requested_rib_depth-1e-9:
            derived['rib_depth_requested']=requested_rib_depth
            derived['rib_depth_auto_reduced']=True
    elif spec.beam_type == 2:
        max_rib_depth=beam_depth-2*beam_thickness-25
        rib_depth=min(max_rib_depth,beam_bending_radius+beam_inner_radius)
        if rib_depth <= 0: raise ValueError('Power-B rib depth is non-positive; increase beam depth')
        theta=math.acos(1-rib_depth/(beam_bending_radius+beam_inner_radius))
        tp1x=beam_bending_radius*(1-math.cos(theta)); tp1z=beam_bending_radius*math.sin(theta)
        tp2x=(beam_bending_radius+beam_inner_radius)*(1-math.cos(theta)); tp2z=(beam_bending_radius+beam_inner_radius)*math.sin(theta)
        rib_height=2*tp2z
        valley_flat=16/beam_thickness
        frontal_flat_minor=(beam_height-valley_flat)/4-rib_height/2-beam_bending_radius
        frontal_flat_major=(beam_height+valley_flat)/2-rib_height
        rear_flat=(beam_height-4*beam_bending_radius-2*beam_inner_radius-valley_flat)/2
        horizontal_flat_major=beam_depth-2*beam_bending_radius
        horizontal_flat_minor=beam_depth-2*beam_thickness-beam_bending_radius-beam_inner_radius
        solid=power_b_upper_lower_rib()
        derived.update(rib_depth=rib_depth, rib_height=rib_height, valley_flat=valley_flat)
    elif spec.beam_type == 3:
        valley_flat=16/beam_thickness
        rear_flat=(beam_height-4*beam_bending_radius-2*beam_inner_radius-valley_flat)/2
        horizontal_flat_major=beam_depth-2*beam_bending_radius
        horizontal_flat_minor=beam_depth-2*beam_thickness-beam_bending_radius-beam_inner_radius
        solid=standard_b_no_rib()
        derived.update(valley_flat=valley_flat)
    else:
        vertical_flat=beam_height-2*beam_bending_radius
        horizontal_flat=beam_depth-2*beam_bending_radius
        if min(vertical_flat,horizontal_flat) <= 0:
            raise ValueError('D-section flats are non-positive; section is too small for bend radius')
        solid=D_section()
        derived.update(vertical_flat=vertical_flat,horizontal_flat=horizontal_flat)

    if not solid.isValid():
        raise RuntimeError('Generated crossbeam solid is invalid')

    z_shift=float(spec.front_face_center_z)
    if abs(z_shift)>1e-12:
        solid=solid.translate((0,0,z_shift))
        guideline=guideline.translate((0,0,z_shift))
        start=guideline.positionAt(0.0,mode='length')
        t=guideline.tangentAt(0.0,mode='length')
        section_plane=cq.Plane(origin=(start.x,start.y,start.z),xDir=(1,0,0),normal=(t.x,t.y,t.z))
    derived.update(front_face_center_z=float(spec.front_face_center_z),
                   z_translation=z_shift, effective_beam_y_span=float(beam_length))

    return BeamResult(solid=solid,guideline=guideline,section_plane=section_plane,
                      x_origin_change=x_origin_change,ord=ord,
                      bending_radius=beam_bending_radius,inner_radius=beam_inner_radius,
                      derived=derived)

