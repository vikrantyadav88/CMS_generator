from __future__ import annotations
import math
from config_models import BeadSpec, BeadSetOverride, CrushCanSpec
from geometry.crush_can_builder import blends, wall_value, _orientation_factor


def _opposite_sense(sense: str) -> str:
    return 'inward' if sense == 'outward' else 'outward'


def _depths_for_set(spec: BeadSpec, index: int) -> tuple[dict, BeadSetOverride | None]:
    if spec.depth_mode == 'uniform':
        d = float(spec.default_depth)
        depths = {k: d for k in ('top','inner','bottom','outer')}
    else:
        depths = {
            'top': float(spec.top_depth),
            'inner': float(spec.inner_depth),
            'bottom': float(spec.bottom_depth),
            'outer': float(spec.outer_depth),
        }
    ov = next((x for x in spec.set_overrides if x.set_index == index), None)
    if ov is not None:
        if ov.depth_mode == 'uniform':
            d = float(ov.uniform_depth)
            depths = {k: d for k in depths}
        elif ov.depth_mode == 'face_specific':
            depths = {
                'top': float(ov.top_depth),
                'inner': float(ov.inner_depth),
                'bottom': float(ov.bottom_depth),
                'outer': float(ov.outer_depth),
            }
    return depths, ov


def calculate_bead_layout(spec: BeadSpec, can: CrushCanSpec, can_info, direction: int = -1) -> dict:
    """Calculate the v0.12 bead layout without applying bead CAD.

    Corrected placement rule:
    1) vehicle-OUTER sidewall is the anchor and is normally the shorter X wall;
    2) bead width + one user flat-X-land value determine all outer-wall centres;
       that same flat land is also used ahead of bead 1;
    3) inner bead 1 has the same front flat land measured from the actual inner
       front edge;
    4) the rearmost inner bead centre is placed in the same YZ plane (same X)
       as the rearmost outer bead centre;
    5) intermediate inner bead centres are equally spaced in global X between
       those two inner boundary centres;
    6) bead-plane angles are DERIVED from each outer/inner centre pair.  They
       are not prescribed or angle-interpolated.
    """
    if not spec.enabled:
        return {'enabled': False, 'count': 0, 'sets': []}

    H = float(can_info.length)
    R = float(can_info.transition_radius)
    rear_x = float(can_info.rear_x)
    center_y = float(can_info.center_y)
    plane = can_info.attachment_plane
    bl, _, _ = blends(can, H, R)
    _, ro = can.corner_radii()

    def y_outer(u):
        # LH vehicle outer = more-negative Y = Y- wall.
        return center_y + wall_value(u, H, can, R, bl['Y-'])

    def y_inner(u):
        return center_y + wall_value(u, H, can, R, bl['Y+'])

    def z_low(u): return wall_value(u, H, can, R, bl['Z-'])
    def z_high(u): return wall_value(u, H, can, R, bl['Z+'])

    def x_at(u, y):
        f = _orientation_factor(u, H, can)
        return rear_x + direction*u + f*(plane.x_at(y)-plane.x_center)

    def xo(u): return x_at(u, y_outer(u))
    def xi(u): return x_at(u, y_inner(u))

    front_outer_x = xo(H); rear_outer_x = xo(0.0)
    front_inner_x = xi(H); rear_inner_x = xi(0.0)
    available_outer_x = abs(rear_outer_x-front_outer_x)
    available_inner_x = abs(rear_inner_x-front_inner_x)

    def solve_x(xfun, target: float, label: str) -> float:
        # Robust scan + local bisection; works even if station orientation makes
        # the X(u) relation mildly non-linear.
        samples=360
        vals=[(H*j/samples, xfun(H*j/samples)-target) for j in range(samples+1)]
        roots=[]
        for (u0,g0),(u1,g1) in zip(vals,vals[1:]):
            if abs(g0)<1e-9: roots.append(u0); continue
            if g0*g1<0:
                lo,hi=u0,u1; flo=g0
                for _ in range(70):
                    mid=(lo+hi)/2; fm=xfun(mid)-target
                    if abs(fm)<1e-11: lo=hi=mid; break
                    if flo*fm<=0: hi=mid
                    else: lo=mid; flo=fm
                roots.append((lo+hi)/2)
        if roots:
            # X(u) is normally monotone; choose the root nearest the front if
            # numerical station orientation creates a duplicate.
            return max(roots)
        u_best,g_best=min(vals,key=lambda q:abs(q[1]))
        if abs(g_best)<0.03:return u_best
        raise ValueError(f'Could not place {label} at X={target:.3f} mm')

    def solve_distance_from_front(xfun, front_x: float, distance: float, label: str) -> float:
        target = front_x - direction*distance
        return solve_x(xfun,target,label)

    # Same user flat region at the front and between beads.
    front_flat = float(spec.clear_spacing_x)
    first_center_d = front_flat + spec.width/2.0
    pitch = spec.width + front_flat

    outer_centres=[]
    i=0
    while i<500:
        d=first_center_d+i*pitch
        if d+spec.width/2 > available_outer_x+1e-9: break
        remaining=available_outer_x-(d+spec.width/2)
        uo=solve_distance_from_front(xo,front_outer_x,d,f'outer bead {i+1}')
        outer_centres.append({'distance_from_front':d,'remaining':remaining,'u':uo,
                              'x':xo(uo),'y':y_outer(uo)})
        if remaining < spec.minimum_rear_remainder-1e-9: break
        i+=1

    if not outer_centres:
        raise ValueError(
            f'No bead set fits on the vehicle-outer sidewall: available X length={available_outer_x:.3f} mm, '
            f'front flat={front_flat:.3f} mm, width={spec.width:.3f} mm')

    n=len(outer_centres)

    # Inner boundary condition 1: same front flat land as the outer wall.
    ui_first=solve_distance_from_front(xi,front_inner_x,first_center_d,'inner first bead')
    xi_first=xi(ui_first)

    if n==1:
        inner_targets=[xi_first]
        single_rule='equal_front_flat'
    else:
        # Inner boundary condition 2: rearmost inner bead shares the same YZ
        # plane as the rearmost outer bead -> identical global X coordinate.
        x_last_target=outer_centres[-1]['x']
        ui_last=solve_x(xi,x_last_target,'inner rearmost bead')
        xi_last=xi(ui_last)
        # Equispace intermediate INNER bead centres in global X.
        inner_targets=[xi_first+(xi_last-xi_first)*j/(n-1) for j in range(n)]
        single_rule=None

    inner_centres=[]
    for j,target in enumerate(inner_targets,1):
        ui=solve_x(xi,target,f'inner bead {j}')
        inner_centres.append({'u':ui,'x':xi(ui),'y':y_inner(ui),
                              'distance_from_front_x':abs(xi(ui)-front_inner_x)})

    # Guard against inner-wall bead overlap caused by the boundary constraints.
    if n>1:
        inner_steps=[abs(inner_centres[j+1]['x']-inner_centres[j]['x']) for j in range(n-1)]
        min_clear=min(step-spec.width for step in inner_steps)
        if min_clear < -1e-6:
            raise ValueError(
                f'Corrected bead layout causes inner-sidewall bead overlap: minimum clear X gap={min_clear:.3f} mm')
    else:
        inner_steps=[]; min_clear=None

    out=[]
    side_sense=spec.sidewall_sense
    top_bottom_sense=_opposite_sense(side_sense)

    def local_metrics(u,set_index):
        zl,zh=z_low(u),z_high(u); h=zh-zl; zc=(zh+zl)/2
        bead_h=h-2*ro-2*spec.flat_land_z
        if bead_h<=0:
            raise ValueError(
                f'Bead set {set_index} has no usable sidewall height after outer radius ({ro:.3f} mm) '
                f'and flat land ({spec.flat_land_z:.3f} mm) are reserved')
        return h,zc,bead_h,zl+ro+spec.flat_land_z,zh-ro-spec.flat_land_z

    for j,(oc,ic) in enumerate(zip(outer_centres,inner_centres),1):
        dy=ic['y']-oc['y']
        if abs(dy)<1e-12: raise ValueError(f'Bead set {j} has coincident inner/outer sidewall Y coordinates')
        dxdy=(ic['x']-oc['x'])/dy
        theta=math.degrees(math.atan(dxdy))

        ho,zco,bho,zbo0,zbo1=local_metrics(oc['u'],j)
        hi,zci,bhi,zbi0,zbi1=local_metrics(ic['u'],j)
        depths,ov=_depths_for_set(spec,j)
        cuts={'top':bool(ov.cut_top) if ov else False,
              'inner':bool(ov.cut_inner) if ov else False,
              'bottom':bool(ov.cut_bottom) if ov else False,
              'outer':bool(ov.cut_outer) if ov else False}
        out.append({
            'index':j,
            'outer_center_from_front':oc['distance_from_front'],
            'outer_center_x':oc['x'],'outer_center_y':oc['y'],'outer_station_u':oc['u'],
            'inner_center_from_front_x':ic['distance_from_front_x'],
            'inner_center_x':ic['x'],'inner_center_y':ic['y'],'inner_station_u':ic['u'],
            'plane_angle_deg':theta,'plane_dx_dy':dxdy,
            'remaining_rear_flat_x':oc['remaining'],
            'outer_local_height':ho,'inner_local_height':hi,
            'outer_local_center_z':zco,'inner_local_center_z':zci,
            'outer_bead_height':bho,'inner_bead_height':bhi,
            'outer_bead_z_min':zbo0,'outer_bead_z_max':zbo1,
            'inner_bead_z_min':zbi0,'inner_bead_z_max':zbi1,
            'depths':depths,
            'sense':{'outer':side_sense,'inner':side_sense,'top':top_bottom_sense,'bottom':top_bottom_sense},
            'cut_radii':cuts,
            'mode':'cut_radii' if any(cuts.values()) else 'normal',
        })

    return {
        'enabled':True,'count':n,
        'outer_available_x':available_outer_x,'inner_available_x':available_inner_x,
        'front_flat_x':front_flat,'pitch_x':pitch,
        'front_interface_angle_deg':float(plane.angle_deg),
        'first_derived_plane_angle_deg':out[0]['plane_angle_deg'],
        'last_derived_plane_angle_deg':out[-1]['plane_angle_deg'],
        'inner_center_step_x':(abs(inner_targets[-1]-inner_targets[0])/(n-1) if n>1 else None),
        'minimum_inner_clear_x':min_clear,
        'single_set_rule':single_rule,
        'sets':out,
    }
