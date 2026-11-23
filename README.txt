CMS Generator v0.12
===================


v0.12 changes
-------------
- All main input-form columns are vertically scrollable; the contextual help panel stays fixed.
- Window size adapts to the available screen, with a smaller minimum size for laptop/single-screen use.
- Rear datum offset is now measured in global X from the actual crossbeam frontmost X extreme
  (normally the Y=0 crown) to the rearmost crush-can datum.
- Bead placement corrected: outer vehicle sidewall is the anchor; inner positions follow the
  equal-front-flat / last-YZ / equispaced-intermediate rule. Bead plane angles are outputs, not inputs.

Baseline
--------
This release is developed directly from the user-approved baseline:
    CMS_Generator_v0_9(1).zip

Run
---
    python main.py

Dependencies
------------
- cadquery
- shapely
- Pillow   (now used by the GUI for dynamic help-image fit/zoom)
- tkinter  (standard Python install)

v0.10 foundation retained
------------------------------
1. Larger/resizable GUI
   - v0.12 sizes the window to the available screen (up to 1440 x 900)
   - minimum 960 x 600
   - vertically scrollable input forms keep lower fields accessible on laptop/single-screen setups
   - larger fonts, controls, entry fields and row spacing
   - input/help columns expand with the window

2. Dedicated dynamic help image for every current GUI input/control
   - focusing/clicking an input switches the help image automatically
   - image aspect ratio is preserved
   - automatic Fit plus manual - / + zoom and mouse-wheel zoom
   - the selected image remains visible until another input is selected
   - missing images fail gracefully instead of breaking the GUI
   - every supplied image is currently a neutral placeholder
   - replace placeholders without changing Python

   Exact filenames are listed in:
       HELP_IMAGE_FILENAMES.txt

   Help files live below:
       assets/help/

   The helper script:
       python make_help_placeholders.py
   creates only missing placeholders and NEVER overwrites existing replacement images.

3. User-controlled bend-radius definition
   Beam plate and crush can each provide:
       Radius input basis: Inner radius / Outer radius
       Editable radius multiplier [x t]
       Read-only derived counterpart [x t]

   Relationship:
       Ro = Ri + t

   Default preset remains:
       Ri = 4t
       Ro = 5t

   The default is no longer hard-coded into the geometry engine.

4. Independent beam-plate bend radius
   The old v0.9 coupling:
       beam_plate_outer_radius = beam_outer_radius + beam_plate_thickness
   has been removed.

   Beam-plate radius is now defined independently by the user.
   After generation, the code explicitly checks Beam / Beam Plate intersection.
   If the selected radius/gap combination causes solid interference, generation stops
   with an engineering error rather than silently changing the input.

5. Separate vehicle-outer / vehicle-inner beam-plate slip-plane gaps
   New inputs:
       Outer slip-plane gap
       Inner slip-plane gap

   On the LH side, OUTER means farther from Y=0 and INNER means closer to Y=0.
   RH remains mirrored.

   The beam-plate builder no longer assumes a single constant-offset circular path.
   It interrogates the actual beam guideline at the outer and inner stations.

6. Optional user-supplied crossbeam sweep guideline STEP
   Crossbeam > Sweep source:
       Constant radius
       STEP guideline

   Constant-radius mode remains the default and reproduces the legacy sweep geometry.

   STEP guideline requirements for v0.10:
   - one continuous open edge/wire
   - actual dimensions in mm; scale is preserved
   - lies in a plane parallel to global XY (constant Z)
   - approximately symmetric about vehicle Y=0
   - represents the OUTER / FRONT envelope guideline of the crossbeam
   - no branches and no closed loop

   Body position is NOT required.
   The imported curve is translated automatically so:
   - endpoint Y midpoint -> Y=0
   - endpoint X chord -> X=0
   - source constant Z -> Z=0
   The configured Beam Front-face Centre Z is then applied.

   Shape, curvature distribution and scale are never altered by this normalisation.
   Strongly asymmetric guidelines are intentionally rejected in v0.10 because the
   current CMS architecture still mirrors LH components to RH.

7. Generalised beam-plate placement
   Beam-plate outer/inner stations are now solved from the actual guideline and local
   tangent/rear normal. When both slip gaps are equal and the guideline is circular,
   the new solver reproduces the legacy circular beam-plate endpoint locations to
   numerical precision.

Retained v0.9 / validated behaviour
-----------------------------------
- Monoleg, Power-B, Standard-B and D-section crossbeams
- crossbeam Front-face Centre Z placement
- optional beam plate
- exact v0.9 beam-plate / crush-can front-interface conformity
- beam-plate radius-region contact / directional-shadow trim
- bare-beam rear-land envelope and B-section valley bridging
- back-plate or rail-bolted rear architecture
- rail through-bolts across BOTH longitudinal sidewalls
- zero rear/front crush-can straight lengths
- general rear/front crush-can taper and Z eccentricity
- top/bottom or inner/outer C-section split
- stop-at-contact or selected-face flow-over
- JSON presets and STEP exports

Crush-can radius implementation note
------------------------------------
The user-selected Ri/Ro values now drive the existing sampled rounded-section
construction. The previously discussed upgrade from sampled/discretised corner radii
to fully analytic CAD radii remains a later geometry-cleanup task.

Beads
-----
v0.12 corrects the v0.10 omission: the Beads page and configuration model now
use the complete rule-based specification agreed with the user instead of the
legacy v0.9 Leg1 / connecting-face / Leg2 row.

Current bead engineering inputs:
- Enable beads
- Bead width in X
- One Flat X land value used both from the front edge to bead 1 and between adjacent bead edges
- User-defined minimum rear flat remainder (default preset 10 mm; not hard-coded)
- Flat Z land retained to the local outside-corner tangency
- Initial sidewall bead sense: inward / outward; Top and Bottom use the opposite sense
- Depth mode: one uniform local-normal depth OR vehicle-face-specific depths
- User-defined Top / Inner / Bottom / Outer depth magnitudes
- Per-set override editor with set number, inherit/uniform/face-specific depth override,
  and independent Top / Inner / Bottom / Outer bend-radius-cut selections

Automatic layout calculation is active in v0.12:
- vehicle-outer sidewall is the longitudinal anchor
- its bead centres run front-to-rear using bead width + the shared flat X land
- bead count follows the actual outer-sidewall X length
- no further set is added after the remaining rear flat falls below the user input
- inner bead 1 keeps the same front flat X land as the outer bead 1
- rearmost inner bead centre shares the same YZ plane / global X as the rearmost outer bead
- intermediate inner bead centres are equispaced in global X
- bead-plane angles are derived afterwards from the matching outer/inner centre pairs
- for a single-set layout the equal-front-flat condition takes priority
- local sidewall bead height follows changing crush-can height and Z centre
- the requested flat Z land is retained to the local corner tangencies
- set-specific depth/radius-cut selections are resolved and exported in the build summary

The bead embossment / B-spline CAD deformation itself is intentionally NOT applied yet.
v0.12 calculates and validates the placement/configuration so those rules can be inspected
before the reference-style bead geometry is connected to the crush-can surfaces.

Every bead input, including every field in the per-set override editor, has its own
dynamic help-image placeholder. Exact filenames are in HELP_IMAGE_FILENAMES.txt.

Examples / presets
------------------
01_beamplate_backplate.json
02_standardB_rail_bolted_no_beamplate.json
03_rail_bolted_zero_straights_tapered_z.json
04_standardB_shifted_Z.json
05_asymmetric_slip_gaps.json
06_custom_STEP_guideline.json
07_bead_layout_demo.json

The custom-guideline preset uses:
    examples/example_custom_sweep_guideline.step

Testing
-------
Run:
    python smoke_test_v012.py

The v0.12 smoke test checks:
- all v0.10 sweep / beam-plate foundation regressions
- the complete rule-based bead configuration model and per-set overrides
- corrected outer-wall bead count plus inner first/last boundary conditions and equispacing
- per-set depth and bend-radius-cut override resolution
- existence of every contextual help-image placeholder
- rear datum referenced from the actual crossbeam frontmost X extreme

Additional targeted development regression: adaptive bead height on a tapered / Z-varying crush can.
