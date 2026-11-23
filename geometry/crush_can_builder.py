from __future__ import annotations
from dataclasses import dataclass, replace
import math
import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.gp import gp_Vec
from config_models import CrushCanSpec, FrontInterfaceSpec


@dataclass
class AttachmentPlane:
    """Vertical local attachment plane, expressed as X(Y)."""
    y_outer: float
    y_inner: float
    x_outer: float
    x_inner: float
    center_y: float
    x_center: float
    dx_dy: float
    angle_deg: float

    def x_at(self, y: float) -> float:
        return self.x_center + self.dx_dy * (y - self.center_y)


@dataclass
class CanBuildInfo:
    # Nominal centreline distance from rear datum to attachment plane.
    length: float
    transition_radius: float
    contact_x: float | None
    rear_x: float
    center_y: float
    warnings: list[str]
    attachment_plane: AttachmentPlane


def analytic_c_wire(w, d, zc, s: CrushCanSpec, name, center_y, base_x,
                    attachment_plane: AttachmentPlane | None = None,
                    orientation_factor: float = 0.0):
    """Build a *true curved-edge* C-profile instead of a faceted polygon.

    Each section has four quarter-circle/ellipse arc edges (two outside, two
    inside) irrespective of ``corner_samples``. The 12 edges appear in the same
    topological order at every station, allowing a single smooth loft face per
    corner all the way along the can (rather than one face for each facet).

    At an inclined attachment station, the original global-Y width convention
    is preserved. The shear X += slope*(Y-Ycentre) turns a YZ circle into an
    *exact elliptical arc* in that inclined section plane; hence an ellipse
    rather than a three-point circular approximation is used there.
    """
    t=float(s.thickness)
    ri,ro=s.corner_radii()
    large=(name == s.larger_half)
    if large:
        ow,od,dy,dz=w,d,0.0,0.0
    elif s.split=='top_bottom':
        ow,od=w-2*t,d-t
        dy=0.0
        dz=t/2 if name=='top' else -t/2
    else:
        ow,od=w-t,d-2*t
        dy=t/2 if name=='inner' else -t/2
        dz=0.0

    if min(ow,od)<=2*ro+1e-8:
        raise ValueError('Crush-can section is too small for selected OUTER corner radius')
    cy=center_y+dy
    zcenter=zc+dz
    yl,yh=cy-ow/2,cy+ow/2
    zl,zh=zcenter-od/2,zcenter+od/2
    yi_l,yi_h=yl+t,yh-t
    zi_l,zi_h=zl+t,zh-t
    if min(yi_h-yi_l,zi_h-zi_l)<=2*ri+1e-8:
        raise ValueError('Crush-can inner section is too small for selected INNER bend radius')

    slope=(orientation_factor*attachment_plane.dx_dy) if attachment_plane is not None else 0.0
    y_ref=attachment_plane.center_y if attachment_plane is not None else center_y
    stretch=math.hypot(1.0,slope)

    def P(y,z):
        return cq.Vector(base_x+slope*(y-y_ref),y,z)

    edges=[]
    def line(a,b):
        if (P(*a)-P(*b)).Length<=1e-8:
            raise ValueError('Degenerate crush-can section edge at a split')
        edges.append(cq.Edge.makeLine(P(*a),P(*b)))

    def arc(cy0,cz0,r,ang0,ang1):
        # YZ arcs retain exact circular geometry for zero station skew; with
        # skew they are exact ellipses, not piecewise straight approximations.
        if abs(slope)<1e-7:
            def at(ang):
                aa=math.radians(ang)
                return P(cy0+r*math.cos(aa),cz0+r*math.sin(aa))
            edges.append(cq.Edge.makeThreePointArc(at(ang0),at((ang0+ang1)/2),at(ang1)))
        else:
            e=cq.Edge.makeEllipse(r*stretch,r,
                pnt=P(cy0,cz0),
                dir=(1,-slope,0), xdir=(slope,1,0),
                angle1=min(ang0,ang1),angle2=max(ang0,ang1),
                sense=1 if ang1>ang0 else -1)
            edges.append(e)

    if s.split=='top_bottom':
        cut=s.rear_z + (-s.overlap/2 if name=='top' else s.overlap/2)
        # Both free leg ends must be inside straight sidewall portions.
        if not (zl+ro+1e-7<cut<zh-ro-1e-7):
            raise ValueError('Top/bottom split intersects the corner radius at a section; '
                             'adjust split/overlap, can Z offset, or bend radius')
        if name=='top':
            line((yh,cut),(yh,zh-ro))
            arc(yh-ro,zh-ro,ro,0,90)
            line((yh-ro,zh),(yl+ro,zh))
            arc(yl+ro,zh-ro,ro,90,180)
            line((yl,zh-ro),(yl,cut))
            line((yl,cut),(yi_l,cut))
            line((yi_l,cut),(yi_l,zi_h-ri))
            arc(yi_l+ri,zi_h-ri,ri,180,90)
            line((yi_l+ri,zi_h),(yi_h-ri,zi_h))
            arc(yi_h-ri,zi_h-ri,ri,90,0)
            line((yi_h,zi_h-ri),(yi_h,cut))
            line((yi_h,cut),(yh,cut))
        elif name=='bottom':
            line((yl,cut),(yl,zl+ro))
            arc(yl+ro,zl+ro,ro,180,270)
            line((yl+ro,zl),(yh-ro,zl))
            arc(yh-ro,zl+ro,ro,270,360)
            line((yh,zl+ro),(yh,cut))
            line((yh,cut),(yi_h,cut))
            line((yi_h,cut),(yi_h,zi_l+ri))
            arc(yi_h-ri,zi_l+ri,ri,0,-90)
            line((yi_h-ri,zi_l),(yi_l+ri,zi_l))
            arc(yi_l+ri,zi_l+ri,ri,270,180)
            line((yi_l,zi_l+ri),(yi_l,cut))
            line((yi_l,cut),(yl,cut))
        else:
            raise ValueError(f'Unexpected C-half {name!r}')
    elif s.split=='inner_outer':
        cut=center_y + (-s.overlap/2 if name=='inner' else s.overlap/2)
        if not (yl+ro+1e-7<cut<yh-ro-1e-7):
            raise ValueError('Inner/outer split intersects the corner radius at a section; '
                             'adjust split/overlap, can width, or bend radius')
        if name=='inner':
            line((cut,zh),(yh-ro,zh))
            arc(yh-ro,zh-ro,ro,90,0)
            line((yh,zh-ro),(yh,zl+ro))
            arc(yh-ro,zl+ro,ro,0,-90)
            line((yh-ro,zl),(cut,zl))
            line((cut,zl),(cut,zi_l))
            line((cut,zi_l),(yi_h-ri,zi_l))
            arc(yi_h-ri,zi_l+ri,ri,270,360)
            line((yi_h,zi_l+ri),(yi_h,zi_h-ri))
            arc(yi_h-ri,zi_h-ri,ri,0,90)
            line((yi_h-ri,zi_h),(cut,zi_h))
            line((cut,zi_h),(cut,zh))
        elif name=='outer':
            line((cut,zl),(yl+ro,zl))
            arc(yl+ro,zl+ro,ro,270,180)
            line((yl,zl+ro),(yl,zh-ro))
            arc(yl+ro,zh-ro,ro,180,90)
            line((yl+ro,zh),(cut,zh))
            line((cut,zh),(cut,zi_h))
            line((cut,zi_h),(yi_l+ri,zi_h))
            arc(yi_l+ri,zi_h-ri,ri,90,180)
            line((yi_l,zi_h-ri),(yi_l,zi_l+ri))
            arc(yi_l+ri,zi_l+ri,ri,180,270)
            line((yi_l+ri,zi_l),(cut,zi_l))
            line((cut,zi_l),(cut,zl))
        else:
            raise ValueError(f'Unexpected C-half {name!r}')
    else:
        raise ValueError(f'Unexpected split orientation {s.split!r}')

    # The wire is a closed 12-edge loop: 8 planar wall segments + 4 exact arcs.
    if len(edges)!=12:
        raise RuntimeError(f'Expected 12 analytic profile edges, found {len(edges)}')
    result=cq.Wire.assembleEdges(edges)
    if not result.IsClosed() or not result.isValid():
        raise RuntimeError(f'Invalid analytic C-profile wire for {name} at X={base_x:.3f}')
    return result


def walls(s):
    return {'Y-':(-s.rear_width/2,-s.front_width/2),
            'Y+':( s.rear_width/2, s.front_width/2),
            'Z-':(s.rear_z-s.rear_depth/2,s.front_z-s.front_depth/2),
            'Z+':(s.rear_z+s.rear_depth/2,s.front_z+s.front_depth/2)}


def blends(s,H,R):
    a=s.rear_straight; b=H-s.front_straight; T=b-a
    if T<=0: raise ValueError('Straight lengths consume the entire can')
    result={};limits=[]
    for name,(v0,v1) in walls(s).items():
        delta=v1-v0; theta=math.atan2(abs(delta),T)
        if abs(delta)<1e-10 or R==0:
            result[name]=(v0,v1,delta,theta,[]);continue
        k=math.tan(theta/2)
        n=int(a>0)+int(s.front_straight>0)
        if a>0: limits.append(((a/k)-s.thickness,name+' rear straight'))
        if s.front_straight>0: limits.append(((s.front_straight/k)-s.thickness,name+' front straight'))
        if n: limits.append((T/(n*k*math.cos(theta))-s.thickness,name+' shared taper'))
        arcs=[]; tangent=R*k; axial=tangent*math.cos(theta)
        if a>0: arcs.append((a-tangent,a+axial,'start'))
        if s.front_straight>0: arcs.append((b-axial,b+tangent,'end'))
        result[name]=(v0,v1,delta,theta,arcs)
    maxr=min((v for v,_ in limits),default=float('inf'))
    return result,maxr,[name for v,name in limits if abs(v-maxr)<1e-6]


def feasible_radius(s,H,requested):
    _,mx,lim=blends(s,H,requested)
    if requested <= mx-0.1: return requested,None
    if mx<=0.1: raise ValueError('No positive transition radius fits this can')
    revised=math.floor((mx-0.1)*100)/100
    return revised,(requested,mx,revised,lim)


def arc_value(x,x0,x1,y0,y1,slope0,slope1):
    nx,ny=-slope0,1.0;dx=x1-x0;dy=y1-y0
    denom=2*(dx*nx+dy*ny)
    if abs(denom)<1e-12:return y0+(y1-y0)*(x-x0)/(x1-x0)
    lam=(dx*dx+dy*dy)/denom;cx=x0+lam*nx;cy=y0+lam*ny
    rad=math.hypot(x0-cx,y0-cy);val=math.sqrt(max(0,rad*rad-(x-cx)**2))
    return cy+(1 if y0>=cy else -1)*val


def wall_value(u,H,s,R,blend):
    v0,v1,delta,theta,arcs=blend;a=s.rear_straight;b=H-s.front_straight;T=b-a;m=delta/T
    if not arcs:
        if u<=a:return v0
        if u>=b:return v1
        return v0+m*(u-a)
    for x0,x1,kind in arcs:
        if x0-1e-8<=u<=x1+1e-8:
            if kind=='start':return arc_value(u,x0,x1,v0,v0+m*(x1-a),0,m)
            return arc_value(u,x0,x1,v0+m*(x0-a),v1,m,0)
    if u<a:return v0
    if u>b:return v1
    return v0+m*(u-a)


def stations(s,H,bl):
    u={0.0,H,s.rear_straight,H-s.front_straight}
    for v in bl.values():
        for x0,x1,_ in v[-1]:
            for i in range(s.blend_samples+1):u.add(x0+(x1-x0)*i/s.blend_samples)
    return sorted(x for x in u if 0<=x<=H)


def _orientation_factor(u, attach_length, s:CrushCanSpec):
    """Ramp station orientation from rear datum to the local front plane.

    Rear straight stays normal to global X.  The final front straight is fully
    parallel to the attachment plane.  The taper smoothly carries the change in
    orientation between those two regions.
    """
    a=s.rear_straight
    b=attach_length-s.front_straight
    if u<=a+1e-12:return 0.0
    if u>=b-1e-12:return 1.0
    if b<=a+1e-12:return 1.0
    q=(u-a)/(b-a)
    # C1 smoothstep avoids an abrupt station-rotation change at straight/taper junctions.
    return q*q*(3.0-2.0*q)




def build_raw(s,H,R,rear_x,center_y,direction=-1,
              attachment_plane:AttachmentPlane|None=None,attach_length:float|None=None,
              orientation_spec:CrushCanSpec|None=None):
    bl,_,_=blends(s,H,R);us=stations(s,H,bl)
    names=('top','bottom') if s.split=='top_bottom' else ('inner','outer')
    out={}
    for name in names:
        ws=[]
        for u in us:
            v={k:wall_value(u,H,s,R,item) for k,item in bl.items()}
            w=v['Y+']-v['Y-'];d=v['Z+']-v['Z-'];zc=(v['Z+']+v['Z-'])/2
            f=0.0
            if attachment_plane is not None and attach_length is not None:
                f=_orientation_factor(u,attach_length,orientation_spec or s)
            ws.append(analytic_c_wire(w,d,zc,s,name,center_y,
                             rear_x+direction*u,attachment_plane,f))
        # Smooth, compatible multi-section loft: each true arc maps to ONE
        # longitudinal BSpline surface; no corner polyline facets or ruled bands.
        loft_builder=BRepOffsetAPI_ThruSections(True, False)
        loft_builder.CheckCompatibility(False)
        loft_builder.SetMaxDegree(3)
        for w in ws:
            loft_builder.AddWire(w.wrapped)
        loft_builder.Build()
        sh=cq.Shape.cast(loft_builder.Shape()).clean()
        if not sh.isValid(): raise RuntimeError(f'Invalid {name} crush-can half')
        out[name]=sh
    return out


def _box(x0,x1,y0,y1,z0,z1):
    xa,xb=sorted((x0,x1));ya,yb=sorted((y0,y1));za,zb=sorted((z0,z1))
    return cq.Solid.makeBox(xb-xa,yb-ya,zb-za,cq.Vector(xa,ya,za))


def _xy_prism(points,z0,z1):
    """Vertical prism from a simple XY polygon."""
    if z1<=z0: raise ValueError('Invalid prism Z interval')
    wp=cq.Workplane('XY').workplane(offset=z0).polyline(points).close().extrude(z1-z0)
    return wp.val()


def limiter_local_bbox(component, s:CrushCanSpec, center_y, padding=None):
    if isinstance(component,cq.Workplane): component=component.val()
    bb=component.BoundingBox()
    pad=max(2.0*s.thickness,2.0) if padding is None else max(0.0,padding)
    half_y=max(s.rear_width,s.front_width)/2.0 + pad
    zlo=min(s.rear_z-s.rear_depth/2.0, s.front_z-s.front_depth/2.0) - pad
    zhi=max(s.rear_z+s.rear_depth/2.0, s.front_z+s.front_depth/2.0) + pad
    window=_box(bb.xmin-5.0,bb.xmax+5.0,center_y-half_y,center_y+half_y,zlo,zhi)
    inter=component.intersect(window)
    if inter.Volume()<=1e-8:return None
    return inter.BoundingBox()


def _section_envelope_x_at_y(component,y,zlo,zhi,prefer='max'):
    """Exact X envelope of limiter material at a vehicle-Y section.

    The component is cropped to the relevant Z band and sectioned exactly at Y.
    For a bare crossbeam this deliberately returns the rear-most land/envelope,
    so recessed B-section valleys do not pull the crush-can edge inward.
    """
    if isinstance(component,cq.Workplane):component=component.val()
    bb=component.BoundingBox()
    zpad=max(0.25,0.005*max(1.0,zhi-zlo))
    cropped=component.intersect(_box(bb.xmin-2,bb.xmax+2,bb.ymin-2,bb.ymax+2,zlo-zpad,zhi+zpad))
    if cropped.Volume()<=1e-9:
        raise RuntimeError(f'No limiting-component material in requested Z band at Y={y:.3f} mm')
    pl=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,1,0))
    sec=cq.Workplane(pl).newObject([cropped]).section().val()
    bb2=sec.BoundingBox()
    return bb2.xmax if prefer=='max' else bb2.xmin


def _planar_rear_face(component,s:CrushCanSpec,center_y,direction=-1):
    """Find the actual vertical rear attachment plane of a beam plate.

    Selection is geometric: large planar face, outward normal toward the cans,
    vertical plane, and overlap with the crush-can Y/Z footprint.
    """
    if isinstance(component,cq.Workplane):component=component.val()
    y0=center_y-s.front_width/2.0; y1=center_y+s.front_width/2.0
    z0=s.front_z-s.front_depth/2.0; z1=s.front_z+s.front_depth/2.0
    rear_sign=-direction
    candidates=[]
    for f in component.Faces():
        if f.geomType()!='PLANE':continue
        c=f.Center(); n=f.normalAt(c); bb=f.BoundingBox()
        if n.x*rear_sign <= 0.35:continue
        if abs(n.z)>0.15:continue
        oy=max(0.0,min(y1,bb.ymax)-max(y0,bb.ymin))
        oz=max(0.0,min(z1,bb.zmax)-max(z0,bb.zmin))
        if oy<=1e-6 or oz<=1e-6:continue
        candidates.append((f.Area()*oy,c,n,f))
    if not candidates:
        raise RuntimeError('Could not identify the planar rear attachment face of the beam plate')
    _,c,n,_=max(candidates,key=lambda q:q[0])
    if abs(n.x)<1e-9:raise RuntimeError('Selected beam-plate attachment face is parallel to X')
    def x_at(y):
        return c.x-(n.y/n.x)*(y-c.y)
    return x_at


def derive_attachment_plane(component,s:CrushCanSpec,center_y,direction=-1,limiter_kind='beam'):
    """Derive the nominal vertical front attachment plane.

    beam_plate: use the exact planar rear face of the plate.
    beam: use the rear-most flat-land envelope at the two can sidewalls; this
          intentionally bridges B-section valleys instead of entering them.
    """
    prefer='max' if direction<0 else 'min'
    y_outer=center_y-s.front_width/2.0
    y_inner=center_y+s.front_width/2.0
    zlo=s.front_z-s.front_depth/2.0
    zhi=s.front_z+s.front_depth/2.0
    if limiter_kind=='beam_plate':
        xfun=_planar_rear_face(component,s,center_y,direction)
        x_outer=xfun(y_outer); x_inner=xfun(y_inner)
    elif limiter_kind=='beam':
        x_outer=_section_envelope_x_at_y(component,y_outer,zlo,zhi,prefer)
        x_inner=_section_envelope_x_at_y(component,y_inner,zlo,zhi,prefer)
    else:
        raise ValueError("limiter_kind must be 'beam_plate' or 'beam'")
    dy=y_inner-y_outer
    if abs(dy)<1e-9:raise ValueError('Front width is too small to derive attachment-plane angle')
    dxdy=(x_inner-x_outer)/dy
    x_center=x_outer+dxdy*(center_y-y_outer)
    return AttachmentPlane(
        y_outer=y_outer,y_inner=y_inner,x_outer=x_outer,x_inner=x_inner,
        center_y=center_y,x_center=x_center,dx_dy=dxdy,
        angle_deg=math.degrees(math.atan(dxdy)),
    )



def _beam_plate_directional_shadow(component,plane:AttachmentPlane,s:CrushCanSpec,
                                   center_y,direction=-1):
    """Return (shadow_cutter, contact_projection) for the actual beam plate.

    ``shadow_cutter`` removes every can point lying beyond the first real
    rear-facing plate surface seen along vehicle X.  It is made by extruding
    the plate's rear-visible faces toward the beam.

    ``contact_projection`` is the same rear-visible surface projected in both
    X directions.  It identifies the Y-Z contact zone.  This is used after the
    generic flow mask so material that correctly conforms to the flat face and
    bend radii is never clipped back to the old flat attachment plane.
    """
    if isinstance(component,cq.Workplane):
        component=component.val()

    rear_sign=-direction
    bb=component.BoundingBox()
    pad=max(2*s.thickness,1.0)
    y0=center_y-s.front_width/2.0-pad
    y1=center_y+s.front_width/2.0+pad
    z0=s.front_z-s.front_depth/2.0-pad
    z1=s.front_z+s.front_depth/2.0+pad

    reach=max(100.0, 2.0*max(s.rear_width,s.front_width,
                             s.rear_depth,s.front_depth),
              bb.xlen+50.0)

    forward=[]
    projection=[]
    for face in component.Faces():
        fb=face.BoundingBox()
        oy=max(0.0,min(y1,fb.ymax)-max(y0,fb.ymin))
        oz=max(0.0,min(z1,fb.zmax)-max(z0,fb.zmin))
        if oy<=1e-7 or oz<=1e-7:
            continue

        c=face.Center()
        try:
            n=face.normalAt(c)
        except Exception:
            continue
        if n.x*rear_sign <= 0.02:
            continue

        try:
            mkf=BRepPrimAPI_MakePrism(
                face.wrapped,gp_Vec(direction*reach,0.0,0.0),True
            )
            sf=cq.Shape.cast(mkf.Shape())
            if sf.Volume()<=1e-9:
                continue

            mkr=BRepPrimAPI_MakePrism(
                face.wrapped,gp_Vec(-direction*reach,0.0,0.0),True
            )
            sr=cq.Shape.cast(mkr.Shape())

            forward.append(sf)
            projection.append(sf)
            if sr.Volume()>1e-9:
                projection.append(sr)
        except Exception:
            continue

    if not forward:
        raise RuntimeError(
            'Could not construct rear-surface shadow of beam plate; '
            'no rear-visible plate faces overlap the crush-can footprint.'
        )

    shadow=cq.Compound.makeCompound([component]+forward)
    coverage=cq.Compound.makeCompound(projection)
    return shadow,coverage

def _beam_rear_envelope_cutter(component,plane:AttachmentPlane,s:CrushCanSpec,center_y,direction=-1,extension_reach=0.0):
    """Virtual solid that fills recessed crossbeam valleys behind the rear lands.

    It spans the actual beam Z envelope and the crush-can width.  Therefore a
    B-section valley cannot pull the can edge inward, while top/bottom material
    outside the beam height remains available for flow-over.
    """
    if isinstance(component,cq.Workplane):component=component.val()
    bb=component.BoundingBox(); pad=max(2*s.thickness,2.0)
    y0=center_y-s.front_width/2.0-pad; y1=center_y+s.front_width/2.0+pad
    xa0=plane.x_at(y0); xa1=plane.x_at(y1)
    # Extend the virtual valley bridge well beyond the requested flow distance.
    # Otherwise a large user-entered flow length could cross beyond the
    # cutter and re-enter the recessed central portion of a B-section.
    deep=max(50.0,bb.xlen+extension_reach+20.0)
    if direction<0:
        xf=bb.xmin-deep
    else:
        xf=bb.xmax+deep
    poly=[(xa0,y0),(xa1,y1),(xf,y1),(xf,y0)]
    return _xy_prism(poly,bb.zmin-0.5,bb.zmax+0.5)

def _retain_rear_connected(shape,rear_x,direction=-1):
    solids=shape.Solids() if not isinstance(shape,cq.Solid) else [shape]
    if not solids: raise RuntimeError('Boolean removed the complete crush-can half')
    key=(lambda q:q.BoundingBox().xmax) if direction<0 else (lambda q:-q.BoundingBox().xmin)
    return max(solids,key=key).clean()


def _rear_and_extension_regions(plane:AttachmentPlane,rear_x,extra,span,zspan,direction=-1):
    y0=plane.center_y-span;y1=plane.center_y+span
    xa0=plane.x_at(y0);xa1=plane.x_at(y1)
    rear_bound=rear_x-direction*5.0
    rear_poly=[(rear_bound,y0),(rear_bound,y1),(xa1,y1),(xa0,y0)]
    rear_region=_xy_prism(rear_poly,-zspan,zspan)
    ext_region=None
    if extra>0:
        xe0=xa0+direction*(extra+5.0)
        xe1=xa1+direction*(extra+5.0)
        ext_poly=[(xa0,y0),(xa1,y1),(xe1,y1),(xe0,y0)]
        ext_region=_xy_prism(ext_poly,-zspan,zspan)
    return rear_region,ext_region



def _safe_intersect(a,b):
    try:
        q=a.intersect(b)
    except Exception:
        return None
    try:
        return q if q.Volume()>1e-9 else None
    except Exception:
        return None

def _apply_flow_face_mask(shape,plane:AttachmentPlane,rear_x,s,
                          front:FrontInterfaceSpec,center_y,direction=-1,
                          limiter_kind='beam'):
    """Keep connected upper/lower C-section regions, not thin face strips.

    Earlier versions used narrow bands around Z+/- and Y+/-, which allowed
    the top/bottom flat walls and corners to extend but cut the adjacent
    sidewall back to the attachment plane.  The selected top/bottom flow must
    instead include the ENTIRE respective half of the sheet-metal section:
    upper (or lower) sidewall portions, corners, and connecting flat wall.

    For a bare beam, the independent inner/outer face flags are intentionally
    disregarded.  Flow is only top/bottom and the beam's deep virtual bridge
    blocks the middle sidewall from entering a recessed B-profile valley.
    """
    span=max(s.rear_width,s.front_width,s.rear_depth,s.front_depth,100)*8
    rear_region,ext_region=_rear_and_extension_regions(
        plane,rear_x,front.extra_after_contact,span,span,direction)
    keep=_safe_intersect(shape,rear_region)
    if keep is None:
        raise RuntimeError('Attachment-plane clipping removed the complete crush-can half')
    if ext_region is None:
        return _retain_rear_connected(keep,rear_x,direction)
    ext_part=_safe_intersect(shape,ext_region)
    if ext_part is None:
        return _retain_rear_connected(keep,rear_x,direction)

    # The front Z-centre is the physical divider between upper and lower
    # portions of the C-section. The complete sidewall region above/below it
    # belongs to top/bottom flow respectively. Geometry itself remains intact.
    zmid=float(s.front_z)
    masks=[]
    if front.flow_top:
        masks.append(_box(-span,span,center_y-span,center_y+span,zmid,span))
    if front.flow_bottom:
        masks.append(_box(-span,span,center_y-span,center_y+span,-span,zmid))

    if limiter_kind=='beam_plate':
        # Optional independent complete sidewall flow applies to a beam plate.
        # A B-section does not allow it: only upper/lower flow is supported.
        y0=center_y-s.front_width/2.0
        y1=center_y+s.front_width/2.0
        sideband=max(5*s.thickness,6.0)
        if front.flow_inner:
            masks.append(_box(-span,span,y1-sideband,y1+sideband,-span,span))
        if front.flow_outer:
            masks.append(_box(-span,span,y0-sideband,y0+sideband,-span,span))

    for mask in masks:
        part=_safe_intersect(ext_part,mask)
        if part is not None:
            keep=keep.fuse(part)
    return _retain_rear_connected(keep.clean(),rear_x,direction)


def generate_can(s:CrushCanSpec,front:FrontInterfaceSpec,component,rear_x,center_y,
                 direction=-1,interactive_radius_cb=None,limiter_kind='beam'):
    if s.split not in ('top_bottom','inner_outer'):raise ValueError('Invalid crush-can split')
    allowed=('top','bottom') if s.split=='top_bottom' else ('inner','outer')
    if s.larger_half not in allowed:raise ValueError(f'larger_half must be one of {allowed}')
    if min(s.thickness,s.overlap,s.rear_width,s.rear_depth,s.front_width,s.front_depth)<=0:
        raise ValueError('Crush-can dimensions must be positive')
    if front.mode not in ('stop_at_contact','flow_over'):raise ValueError('Invalid front-interface mode')
    if component is None:raise ValueError('A limiting component is required')
    if isinstance(component,cq.Workplane):component=component.val()

    local_bb=limiter_local_bbox(component,s,center_y)
    if local_bb is None:
        raise RuntimeError(
            'Selected limiting component does not overlap the crush-can Y-Z footprint. '
            'Check LH can Y position, front/rear height/Z inputs, or beam/beam-plate selection.'
        )

    plane=derive_attachment_plane(component,s,center_y,direction,limiter_kind)
    H=direction*(plane.x_center-rear_x)
    min_len=s.rear_straight+s.front_straight+1e-6
    if H<=min_len:
        raise ValueError(
            f'Attachment plane leaves only {H:.2f} mm centreline length, which is not enough for '
            f'rear/front straights totalling {s.rear_straight+s.front_straight:.2f} mm.'
        )

    radius,rad_warn=feasible_radius(s,H,s.transition_radius)
    if rad_warn:
        if interactive_radius_cb is None:
            raise ValueError('Requested transition radius is infeasible and requires user approval')
        if not interactive_radius_cb(*rad_warn):
            raise RuntimeError('User cancelled revised transition radius')

    extra=0.0 if front.mode=='stop_at_contact' else max(0.0,front.extra_after_contact)
    # Always overshoot the nominal interface before cutting.  This avoids a
    # coincident-face construction and makes the beam-plate interface exact.
    overshoot=max(2.0,2.0*s.thickness)
    build_spec=replace(s,front_straight=s.front_straight+extra+overshoot)
    raw_length=H+extra+overshoot
    halves=build_raw(build_spec,raw_length,radius,rear_x,center_y,direction,
                     attachment_plane=plane,attach_length=H,orientation_spec=s)

    effective_cutter=component
    beam_plate_contact_projection=None
    if limiter_kind=='beam_plate':
        # Preserve the continuous v0.5/v0.7 crush-can geometry, but trim it
        # with the directional shadow of the *actual* rear-facing plate surface.
        # Keep the corresponding Y-Z contact projection so the later flow-mask
        # step cannot clip radius-conforming material back to the flat plane.
        effective_cutter,beam_plate_contact_projection=_beam_plate_directional_shadow(
            component,plane,s,center_y,direction
        )
    elif limiter_kind=='beam':
        # Treat the rear flat lands as the attachment envelope: valleys/cavities
        # are virtually filled so the can cannot dive into a B-section valley.
        bridge=_beam_rear_envelope_cutter(component,plane,s,center_y,direction,extension_reach=extra+overshoot)
        effective_cutter=component.fuse(bridge).clean()

    cut={}
    span=max(s.rear_width,s.front_width,s.rear_depth,s.front_depth,100)*8
    rear_region,_=_rear_and_extension_regions(plane,rear_x,0.0,span,span,direction)
    for name,solid in halves.items():
        if limiter_kind == 'beam_plate':
            # A single Boolean against the compound of face-prism shadows can
            # trigger OpenCascade pathological BSpline intersections. Cutting
            # against its individual solids produces the same geometric
            # difference while retaining robust, bounded Boolean complexity.
            sh=solid
            for blocker in effective_cutter.Solids():
                sh=sh.cut(blocker)
            sh=sh.clean()
        else:
            sh=solid.cut(effective_cutter).clean()
        sh=_retain_rear_connected(sh,rear_x,direction)
        if front.mode=='flow_over' and extra>0:
            conformal=None
            if limiter_kind=='beam_plate' and beam_plate_contact_projection is not None:
                conformal=_safe_intersect(sh,beam_plate_contact_projection)
            sh=_apply_flow_face_mask(sh,plane,rear_x,s,front,center_y,direction,limiter_kind=limiter_kind)
            if conformal is not None:
                sh=sh.fuse(conformal).clean()
                sh=_retain_rear_connected(sh,rear_x,direction)
        else:
            clipped=_safe_intersect(sh,rear_region)
            if clipped is None:
                raise RuntimeError('Stop-at-contact clipping removed the complete crush-can half')
            sh=_retain_rear_connected(clipped.clean(),rear_x,direction)
        cut[name]=sh

    warns=[]
    if rad_warn:
        warns.append(f'Transition radius reduced from {rad_warn[0]:.2f} to {rad_warn[2]:.2f} mm after approval')
    if limiter_kind=='beam_plate':
        warns.append('Beam-plate interface uses the directional shadow of the actual rear-facing plate surface, and its true contact projection is preserved through flow masking; the can conforms to the flat face and bend radii without gap or wrap-around.')
    else:
        warns.append('Bare-beam flow is restricted to the connected top/bottom portions of the C-section; sidewall middle material stops at the full-depth rear-land valley bridge.')
    if abs(plane.angle_deg)>0.01:
        warns.append(
            f'Front attachment orientation: angle {plane.angle_deg:.3f} deg, '
            f'outer X={plane.x_outer:.2f} mm, inner X={plane.x_inner:.2f} mm.'
        )
    return cut,CanBuildInfo(H,radius,plane.x_center,rear_x,center_y,warns,plane)
