from __future__ import annotations
import cadquery as cq
from config_models import CrushCanSpec, RearMountSpec
from geometry.crush_can_builder import blends, wall_value, limiter_local_bbox


def probe_surface_x(component, can:CrushCanSpec, center_y, prefer='max'):
    """Find the limiter X extent inside the complete can Y-Z footprint.

    v0.2 used a 0.25 mm point-like Y/Z probe.  That can miss thin or irregular
    beam material (especially B sections) and then fall back to a global X
    extremum.  The footprint probe is both local and robust.
    """
    bb=limiter_local_bbox(component,can,center_y)
    if bb is None:
        raise ValueError(
            'The selected limiting component has no material inside the proposed '
            'crush-can Y-Z footprint. Check LH can centre Y and section dimensions.'
        )
    return bb.xmax if prefer=='max' else bb.xmin


def make_rear_plane(rear_x, center_y, *, center_z=0.0):
    """Construction datum retained even when no physical back plate exists."""
    return cq.Plane(origin=(rear_x, center_y, center_z), xDir=(0, 1, 0), normal=(1, 0, 0))


def build_back_plate(rear_x, center_y, spec: RearMountSpec, *, center_z=0.0):
    plane = make_rear_plane(rear_x, center_y, center_z=center_z)
    wp = (
        cq.Workplane(plane)
        .center(0, 0)
        .placeSketch(
            cq.Sketch()
            .rect(spec.back_plate_width, spec.back_plate_height)
            .vertices()
            .fillet(spec.back_plate_corner_radius)
        )
        .extrude(spec.back_plate_thickness)
    )
    lh = wp.val()
    rh = lh.mirror('XZ')
    return lh, rh


def _local_section(can: CrushCanSpec, can_length, transition_radius, u, center_y):
    """Return the solved outer-envelope Y/Z limits at distance u from rear."""
    if u < -1e-9 or u > can_length + 1e-9:
        raise ValueError(
            f'Rail bolt X position ({u:.2f} mm from rear) lies outside the '
            f'solved crush-can length ({can_length:.2f} mm)'
        )
    u = min(max(u, 0.0), can_length)
    bl, _, _ = blends(can, can_length, transition_radius)
    v = {k: wall_value(u, can_length, can, transition_radius, item) for k, item in bl.items()}
    return {
        'y_min': center_y + v['Y-'],
        'y_max': center_y + v['Y+'],
        'z_min': v['Z-'],
        'z_max': v['Z+'],
        'u': u,
    }


def rail_bolt_axes(can: CrushCanSpec, mount: RearMountSpec, can_info, rear_x, center_y, direction=-1):
    """Create equispaced through-bolt axes using the LOCAL section at bolt X.

    Every bolt runs along vehicle Y through BOTH longitudinal sidewalls.  The
    can may start tapering immediately in Z (rear_straight == 0); that is not a
    restriction because the sidewall planes remain valid at the requested X.
    """
    if mount.bolt_count < 1:
        raise ValueError('bolt_count must be >= 1')
    if mount.hole_diameter <= 0:
        raise ValueError('hole_diameter must be positive')
    if mount.bolt_x_from_rear < 0:
        raise ValueError('bolt_x_from_rear cannot be negative')
    if mount.vertical_edge_margin < 0:
        raise ValueError('vertical_edge_margin cannot be negative')

    sec = _local_section(
        can, can_info.length, can_info.transition_radius,
        mount.bolt_x_from_rear, center_y
    )

    # Holes need to sit on the straight part of each longitudinal sidewall,
    # outside the rounded top/bottom corners.  Ri=4t, Ro=5t; the outside corner
    # controls the usable sidewall height.  For an inner/outer split, one C-half
    # is inset by t vertically, so use the common height available on BOTH walls.
    ro = can.corner_radii()[1]
    split_inset = can.thickness if can.split == 'inner_outer' else 0.0
    rad = mount.hole_diameter / 2.0
    zlo = sec['z_min'] + ro + split_inset + mount.vertical_edge_margin + rad
    zhi = sec['z_max'] - ro - split_inset - mount.vertical_edge_margin - rad
    if zhi < zlo:
        local_h = sec['z_max'] - sec['z_min']
        raise ValueError(
            'Insufficient local sidewall height for the requested rail-bolt '
            f'pattern at X={mount.bolt_x_from_rear:.2f} mm from rear '
            f'(local height {local_h:.2f} mm)'
        )

    if mount.bolt_count == 1:
        zs = [(zlo + zhi) / 2.0]
    else:
        zs = [zlo + (zhi-zlo)*i/(mount.bolt_count-1) for i in range(mount.bolt_count)]

    x = rear_x + direction * mount.bolt_x_from_rear
    ymid = (sec['y_min'] + sec['y_max']) / 2.0
    return [
        {
            'x': x,
            'y': ymid,
            'z': z,
            'y_outer': sec['y_min'],
            'y_inner': sec['y_max'],
            'local_z_min': sec['z_min'],
            'local_z_max': sec['z_max'],
        }
        for z in zs
    ]


def _side_probe(rad, x, y0, y1, z):
    """Short cylinder along +Y used to verify one physical sidewall exists."""
    if y1 <= y0:
        raise ValueError('Invalid side-probe Y interval')
    return cq.Solid.makeCylinder(rad, y1-y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))


def cut_rail_holes(halves: dict, can: CrushCanSpec, mount: RearMountSpec,
                   can_info, rear_x, center_y, direction=-1):
    """Cut each rail bolt completely through BOTH crush-can sidewalls."""
    axes = rail_bolt_axes(can, mount, can_info, rear_x, center_y, direction)
    out = dict(halves)
    warnings = []
    rad = mount.hole_diameter / 2.0
    side_probe_len = max(4.0*can.thickness, 2.0)
    cutter_margin = max(4.0*can.thickness, 5.0)

    for idx, axis in enumerate(axes, 1):
        x, z = axis['x'], axis['z']
        y0, y1 = axis['y_outer'], axis['y_inner']

        # Verify that the requested axis actually intersects material at BOTH
        # longitudinal sides before cutting.  Which C-half owns a sidewall is
        # intentionally left to the chosen split geometry.
        outer_probe = _side_probe(rad, x, y0-cutter_margin, y0+side_probe_len, z)
        inner_probe = _side_probe(rad, x, y1-side_probe_len, y1+cutter_margin, z)
        outer_hit = any(sh.intersect(outer_probe).Volume() > 1e-8 for sh in out.values())
        inner_hit = any(sh.intersect(inner_probe).Volume() > 1e-8 for sh in out.values())
        if not outer_hit or not inner_hit:
            missing = []
            if not outer_hit:
                missing.append('outer')
            if not inner_hit:
                missing.append('inner')
            raise ValueError(
                f'Rail bolt {idx} does not intersect the {" and ".join(missing)} '
                'sidewall at the requested X/Z location'
            )

        # One cutter spans the complete Y width, so the resulting holes are
        # coaxial and the physical bolt can run through the entire crush can.
        start_y = y0 - cutter_margin
        length_y = (y1-y0) + 2*cutter_margin
        cutter = cq.Solid.makeCylinder(rad, length_y, cq.Vector(x, start_y, z), cq.Vector(0, 1, 0))

        touched = []
        for name, sh in list(out.items()):
            if sh.intersect(cutter).Volume() > 1e-8:
                touched.append(name)
                out[name] = sh.cut(cutter).clean()
        if not touched:
            raise RuntimeError(f'Rail bolt {idx} cutter did not intersect the crush can')
        if len(touched) > 1 and can.split == 'top_bottom':
            warnings.append(
                f'Rail bolt {idx} intersects both top/bottom C-halves '
                f'({", ".join(touched)}); review its proximity to the split/overlap band.'
            )

    return out, axes, warnings
