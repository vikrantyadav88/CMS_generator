from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List
import json


def radii_from_basis(thickness: float, basis: str, multiplier: float) -> tuple[float, float]:
    """Return (inner_radius, outer_radius) for constant-thickness sheet geometry."""
    t = float(thickness)
    k = float(multiplier)
    if t <= 0:
        raise ValueError('Thickness must be positive')
    if basis == 'inner':
        ri = k * t
        ro = ri + t
    elif basis == 'outer':
        ro = k * t
        ri = ro - t
    else:
        raise ValueError("Radius basis must be 'inner' or 'outer'")
    if ri <= 0 or ro <= ri:
        raise ValueError('Selected bend-radius definition produces invalid inner/outer radii')
    return ri, ro


@dataclass
class BeamSpec:
    beam_type: int = 1   # 1 Monoleg, 2 Power-B, 3 Standard-B, 4 D-section
    thickness: float = 2.0
    sweep_radius: float = 2000.0
    length: float = 1200.0
    depth: float = 50.0
    height: float = 100.0
    steel_grade: int = 1300
    # Global Z coordinate of the nominal centre point on the frontmost beam face at Y=0.
    front_face_center_z: float = 0.0
    # constant_radius / step_guideline.  In STEP mode radius and length are derived/ignored.
    sweep_mode: str = 'constant_radius'
    guideline_step_path: str = ''


@dataclass
class BeamPlateSpec:
    enabled: bool = True
    outer_y: float = 485.0
    width: float = 100.0
    thickness: float = 3.0
    beam_overlap: float = 6.0
    # Vehicle-relative plate ends.  On LH, outer is farther from Y=0.
    slip_plane_gap_outer: float = 2.0
    slip_plane_gap_inner: float = 2.0
    # User controls one radius definition; the counterpart is derived by +/- thickness.
    bend_radius_basis: str = 'inner'  # inner / outer
    bend_radius_multiplier: float = 4.0

    def bend_radii(self) -> tuple[float, float]:
        return radii_from_basis(self.thickness, self.bend_radius_basis, self.bend_radius_multiplier)


@dataclass
class CrushCanSpec:
    # Rear/base section. Width is vehicle Y, depth is vehicle Z.
    rear_width: float = 80.0
    rear_depth: float = 80.0
    rear_z: float = 0.0

    # Front/top section.
    front_width: float = 80.0
    front_depth: float = 80.0
    front_z: float = 0.0

    thickness: float = 2.0
    overlap: float = 4.0
    split: str = 'top_bottom'      # top_bottom / inner_outer
    larger_half: str = 'top'       # top/bottom or inner/outer

    rear_straight: float = 20.0
    front_straight: float = 15.0
    transition_radius: float = 60.0

    # Global X distance from the crossbeam frontmost extreme (normally at Y=0)
    # to the rearmost crush-can construction datum.  For the standard CMS
    # orientation, rear_x = beam_frontmost_x + rear_datum_offset.
    rear_datum_offset: float = 200.0

    # Used when beam plate is disabled.
    lh_center_y: float = -435.0

    # User-controlled longitudinal corner bend radius.
    corner_radius_basis: str = 'inner'  # inner / outer
    corner_radius_multiplier: float = 4.0

    # Longitudinal loft interpolation control.
    blend_samples: int = 5
    # Legacy v0.12 preset setting; ignored now that corner edges are analytic.
    corner_samples: int = 8

    def corner_radii(self) -> tuple[float, float]:
        return radii_from_basis(self.thickness, self.corner_radius_basis, self.corner_radius_multiplier)


@dataclass
class RearMountSpec:
    architecture: str = 'back_plate'  # back_plate / rail_bolted

    back_plate_thickness: float = 3.5
    back_plate_height: float = 200.0
    back_plate_width: float = 100.0
    back_plate_corner_radius: float = 10.0

    # Rail-bolted case: every bolt runs through BOTH longitudinal sidewalls.
    bolt_count: int = 2
    bolt_x_from_rear: float = 25.0
    hole_diameter: float = 12.0
    vertical_edge_margin: float = 15.0


@dataclass
class FrontInterfaceSpec:
    mode: str = 'flow_over'            # stop_at_contact / flow_over
    extra_after_contact: float = 15.0
    flow_top: bool = True
    flow_bottom: bool = True
    flow_inner: bool = False
    flow_outer: bool = False


@dataclass
class BeadSetOverride:
    """Optional engineering override for one automatically generated bead set.

    A set with no cut_* flags is a normal bead.  Depth mode may inherit the
    global definition, use one uniform depth, or use vehicle-face-specific
    depths.  Values are magnitudes; embossment sense is controlled separately.
    """
    set_index: int = 1
    depth_mode: str = 'inherit'          # inherit / uniform / face_specific
    uniform_depth: float | None = None
    top_depth: float | None = None
    inner_depth: float | None = None
    bottom_depth: float | None = None
    outer_depth: float | None = None
    cut_top: bool = False
    cut_inner: bool = False
    cut_bottom: bool = False
    cut_outer: bool = False


@dataclass
class BeadSpec:
    enabled: bool = False

    # Automatic front-to-rear layout.  The vehicle-OUTER sidewall is the
    # longitudinal anchor.  The same clear flat X land is used from the front
    # edge to bead 1 and between adjacent bead edges.
    width: float = 11.0                    # longitudinal X width at outer wall
    clear_spacing_x: float = 18.0          # front flat land + inter-bead clear X land
    minimum_rear_remainder: float = 10.0   # stop adding further sets below this

    # Adaptive bead height.  Flat land is measured from bead end to the local
    # outside-corner tangency on both Z sides of a sidewall bead.
    flat_land_z: float = 8.0

    # Depth magnitudes are measured normal to the local parent sheet surface.
    depth_mode: str = 'uniform'            # uniform / face_specific
    default_depth: float = 1.2
    top_depth: float = 1.2
    inner_depth: float = 1.2
    bottom_depth: float = 1.2
    outer_depth: float = 1.2

    # First-set sidewall embossment sense.  Top/bottom use the opposite sense.
    sidewall_sense: str = 'outward'        # inward / outward

    # Individual sets may override depth and/or select bend radii to cut.
    set_overrides: List[BeadSetOverride] = field(default_factory=list)

    # Reference-style bead-shape controls retained as advanced geometry
    # parameters; these are not hidden engineering dimensions.
    end_fade: float = 5.0
    shoulder_u: float = 0.55
    shoulder_height: float = 0.68
    corner_switch_start: float = 0.18
    corner_switch_end: float = 0.82


@dataclass
class ExportSpec:
    assembly_step: bool = True
    individual_steps: bool = True
    config_json: bool = True
    validation_text: bool = True
    timestamp_names: bool = True


@dataclass
class CMSConfig:
    beam: BeamSpec = field(default_factory=BeamSpec)
    beam_plate: BeamPlateSpec = field(default_factory=BeamPlateSpec)
    crush_can: CrushCanSpec = field(default_factory=CrushCanSpec)
    rear_mount: RearMountSpec = field(default_factory=RearMountSpec)
    front_interface: FrontInterfaceSpec = field(default_factory=FrontInterfaceSpec)
    beads: BeadSpec = field(default_factory=BeadSpec)
    export: ExportSpec = field(default_factory=ExportSpec)

    def to_dict(self):
        return asdict(self)

    def save_json(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding='utf-8')

    @classmethod
    def from_dict(cls, d):
        beads_d = dict(d.get('beads', {}))
        # v0.9/v0.10 migration: the legacy page stored a common width plus one
        # manually positioned row with leg/face depths.  Convert that into the
        # new automatic layout without inventing additional bead sets.
        legacy_rows = beads_d.pop('beads', None)
        legacy_width = beads_d.pop('common_width', None)
        beads_d.pop('leg1_to_edge', None); beads_d.pop('leg2_to_edge', None)
        beads_d.pop('leg1_stop', None); beads_d.pop('leg2_stop', None)
        if legacy_width is not None:
            beads_d.setdefault('width', legacy_width)
        if legacy_rows:
            row = dict(legacy_rows[0])
            centre = row.get('centre_from_front', row.get('centre_from_rear', 35.0))
            # Legacy versions stored the first bead centre explicitly.  v0.12
            # uses one flat-X-land value at the front and between beads.  Only
            # infer it when the old preset does not already contain clear spacing.
            if 'clear_spacing_x' not in beads_d:
                w_for_migration = float(beads_d.get('width', legacy_width if legacy_width is not None else 11.0))
                beads_d['clear_spacing_x'] = max(0.0, float(centre) - w_for_migration/2.0)
            # Legacy CAD was deferred, so use the first leg depth as the uniform
            # migrated magnitude rather than pretending topology-specific depths
            # map unambiguously to vehicle faces.
            beads_d.setdefault('default_depth', row.get('leg1_depth', 1.2))
            beads_d.setdefault('top_depth', row.get('face_depth', row.get('leg1_depth', 1.2)))
            beads_d.setdefault('bottom_depth', row.get('face_depth', row.get('leg1_depth', 1.2)))
            beads_d.setdefault('inner_depth', row.get('leg1_depth', 1.2))
            beads_d.setdefault('outer_depth', row.get('leg2_depth', row.get('leg1_depth', 1.2)))
        legacy_first = beads_d.pop('first_offset_from_front', None)
        if legacy_first is not None and 'clear_spacing_x' not in beads_d:
            beads_d['clear_spacing_x'] = max(0.0, float(legacy_first) - float(beads_d.get('width',11.0))/2.0)
        override_rows = [BeadSetOverride(**dict(x)) for x in beads_d.pop('set_overrides', [])]
        bead_spec = BeadSpec(**beads_d, set_overrides=override_rows)

        rear_d = dict(d.get('rear_mount', {}))
        rear_d.pop('mounting_face', None)

        beam_d = dict(d.get('beam', {}))
        beam_d.setdefault('sweep_mode', 'constant_radius')
        beam_d.setdefault('guideline_step_path', '')

        plate_d = dict(d.get('beam_plate', {}))
        # v0.9 compatibility: migrate one common gap to both vehicle-relative ends.
        legacy_gap = plate_d.pop('slip_plane_gap', None)
        if legacy_gap is not None:
            plate_d.setdefault('slip_plane_gap_outer', legacy_gap)
            plate_d.setdefault('slip_plane_gap_inner', legacy_gap)
        plate_d.setdefault('slip_plane_gap_outer', 2.0)
        plate_d.setdefault('slip_plane_gap_inner', 2.0)
        plate_d.setdefault('bend_radius_basis', 'inner')
        plate_d.setdefault('bend_radius_multiplier', 4.0)

        cc_d = dict(d.get('crush_can', {}))
        cc_d.setdefault('corner_radius_basis', 'inner')
        cc_d.setdefault('corner_radius_multiplier', 4.0)

        return cls(
            beam=BeamSpec(**beam_d),
            beam_plate=BeamPlateSpec(**plate_d),
            crush_can=CrushCanSpec(**cc_d),
            rear_mount=RearMountSpec(**rear_d),
            front_interface=FrontInterfaceSpec(**d.get('front_interface', {})),
            beads=bead_spec,
            export=ExportSpec(**d.get('export', {})),
        )

    @classmethod
    def load_json(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))
