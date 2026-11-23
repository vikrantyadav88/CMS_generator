from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from pathlib import Path
import traceback

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

from config_models import *
from geometry.validator import validate_config
from geometry.cms_builder import build_cms, export_result

ROOT = Path(__file__).resolve().parent
HELP_ROOT = ROOT / 'assets' / 'help'


# Stable help-image filenames. Replace any PNG in assets/help/... without changing Python.
HELP = {
    # Crossbeam
    'beam_type': ('crossbeam/beam_family.png','Beam family','Select the crossbeam section family.'),
    'beam_sweep_mode': ('crossbeam/sweep_source.png','Sweep source','Choose the internal constant-radius sweep or an imported STEP guideline.'),
    'beam_t': ('crossbeam/thickness.png','Crossbeam thickness','Sheet thickness used for the selected beam section.'),
    'beam_R': ('crossbeam/sweep_radius.png','Sweep radius','Constant-radius outer/front envelope sweep radius.'),
    'beam_L': ('crossbeam/beam_length.png','Beam length','Vehicle-Y span used by the constant-radius sweep.'),
    'beam_D': ('crossbeam/depth.png','Beam depth','Crossbeam section depth in vehicle X.'),
    'beam_H': ('crossbeam/height.png','Beam height','Crossbeam section height in vehicle Z.'),
    'steel': ('crossbeam/steel_grade.png','Steel grade','Steel grade used by the existing crossbeam bend-radius rules.'),
    'beam_z': ('crossbeam/front_face_center_z.png','Front-face centre Z','Global Z placement of the nominal front-face centre at Y=0.'),
    'beam_step': ('crossbeam/step_guideline.png','STEP sweep guideline','One continuous open, XY-planar, Y-symmetric curve on the beam outer/front envelope.'),

    # Beam plate
    'bp_enabled': ('beam_plate/use_beam_plate.png','Use beam plate','Enable or disable the physical beam plate.'),
    'bp_y': ('beam_plate/outer_y.png','Beam-plate outer Y','Vehicle-relative outer edge location of the LH beam plate.'),
    'bp_w': ('beam_plate/width.png','Beam-plate width','Chord width between the outer and inner beam-plate section stations.'),
    'bp_t': ('beam_plate/thickness.png','Beam-plate thickness','Beam-plate sheet thickness.'),
    'bp_overlap': ('beam_plate/beam_overlap.png','Beam overlap','Beam-plate flange overlap relative to the crossbeam.'),
    'bp_gap_outer': ('beam_plate/slip_gap_outer.png','Outer slip-plane gap','Slip-plane gap at the vehicle-outer end of the beam plate.'),
    'bp_gap_inner': ('beam_plate/slip_gap_inner.png','Inner slip-plane gap','Slip-plane gap at the vehicle-inner end of the beam plate.'),
    'bp_radius_basis': ('beam_plate/radius_basis.png','Beam-plate radius basis','Choose whether the editable multiplier defines the inside or outside bend radius.'),
    'bp_radius_k': ('beam_plate/bend_radius_input.png','Beam-plate bend radius','Editable bend-radius multiplier. The other radius is derived from sheet thickness.'),
    'bp_radius_other': ('beam_plate/bend_radius_derived.png','Derived beam-plate radius','Read-only counterpart radius derived by adding/subtracting one sheet thickness.'),

    # Crush can
    'cc_rw': ('crush_can/rear_width.png','Rear width','Maximum outside Y width at the rear construction datum.'),
    'cc_rd': ('crush_can/rear_height.png','Rear height','Maximum outside Z height at the rear construction datum.'),
    'cc_rz': ('crush_can/rear_center_z.png','Rear centre Z','Global Z coordinate of the rear-section centre.'),
    'cc_fw': ('crush_can/front_width.png','Front width','Maximum outside Y width at the nominal front section.'),
    'cc_fd': ('crush_can/front_height.png','Front height','Maximum outside Z height at the nominal front section.'),
    'cc_fz': ('crush_can/front_center_z.png','Front centre Z','Global Z coordinate of the front-section centre.'),
    'cc_t': ('crush_can/thickness.png','Crush-can thickness','Sheet thickness used by both C-section halves.'),
    'cc_radius_basis': ('crush_can/radius_basis.png','Crush-can radius basis','Choose whether the editable corner-radius multiplier refers to the inside or outside radius.'),
    'cc_radius_k': ('crush_can/bend_radius_input.png','Crush-can corner radius','Editable longitudinal corner-radius multiplier.'),
    'cc_radius_other': ('crush_can/bend_radius_derived.png','Derived crush-can radius','Read-only counterpart radius derived from sheet thickness.'),
    'cc_rs': ('crush_can/rear_straight.png','Rear straight','Straight longitudinal region before the taper begins.'),
    'cc_fs': ('crush_can/front_straight.png','Front straight','Straight longitudinal region adjacent to the front interface.'),
    'cc_tr': ('crush_can/transition_radius.png','Transition radius','Axial blend radius between straight and tapered regions.'),
    'cc_offset': ('crush_can/rear_datum_offset.png','Rear datum X offset','Global X distance from the crossbeam frontmost point (normally at Y=0) to the rearmost crush-can datum.'),
    'cc_y': ('crush_can/lh_center_y.png','LH centre Y','LH crush-can centre when no beam plate exists to determine it.'),

    # Split
    'split': ('split/split_orientation.png','Split orientation','Choose top/bottom or inner/outer C-section split.'),
    'larger': ('split/larger_half.png','Larger half','Choose which C-half owns the maximum outside envelope.'),
    'overlap': ('split/overlap.png','C-half overlap','Longitudinal mating overlap between the two C-section halves.'),

    # Rear interface
    'rear_arch': ('rear_interface/architecture.png','Rear architecture','Choose a physical back plate or rail through-bolts.'),
    'back_w': ('rear_interface/back_plate_width.png','Back-plate width','Physical back-plate Y width.'),
    'back_h': ('rear_interface/back_plate_height.png','Back-plate height','Physical back-plate Z height.'),
    'back_t': ('rear_interface/back_plate_thickness.png','Back-plate thickness','Physical back-plate thickness.'),
    'bolt_n': ('rear_interface/bolt_count.png','Bolt count','Number of through-bolts in the rear rail interface.'),
    'hole_d': ('rear_interface/hole_diameter.png','Hole diameter','Diameter of each matched hole through both sidewalls.'),
    'bolt_x': ('rear_interface/bolt_x_from_rear.png','Bolt X from rear','Longitudinal location of the through-bolt column from the rear can edge.'),
    'bolt_margin': ('rear_interface/vertical_edge_margin.png','Vertical edge margin','Minimum local Z edge margin for the equispaced bolt holes.'),

    # Front interface
    'front_mode': ('front_interface/mode.png','Front-interface mode','Stop at nominal contact or permit selected faces to flow over.'),
    'front_extra': ('front_interface/extra_after_contact.png','Extra after contact','Additional generated length available to permitted flow-over faces.'),
    'flow_top': ('front_interface/flow_top.png','Top flow','Continue the entire upper C-section region, including the adjacent upper sidewall portions, up to the limiter.'),
    'flow_bottom': ('front_interface/flow_bottom.png','Bottom flow','Continue the entire lower C-section region, including the adjacent lower sidewall portions, up to the limiter.'),
    'flow_inner': ('front_interface/flow_inner.png','Inner flow','Independent vehicle-inner flow is supported for beam-plate-limited designs only.'),
    'flow_outer': ('front_interface/flow_outer.png','Outer flow','Independent vehicle-outer flow is supported for beam-plate-limited designs only.'),

    # Beads - rule-based vehicle-face definition.
    'bead_enabled': ('beads/enable_beads.png','Continuous beads','Enable automatic front-to-rear bead-set layout.'),
    'bead_w': ('beads/bead_width.png','Bead width','Longitudinal bead width measured in X at the outer sidewall anchor.'),
    'bead_spacing': ('beads/clear_spacing_x.png','Flat X land / bead spacing','Same clear X flat land used from each sidewall front edge to bead 1 and between adjacent bead edges on the vehicle-outer anchor wall.'),
    'bead_rear_min': ('beads/minimum_rear_remainder.png','Minimum rear remainder','After a bead set leaves less than this rear flat distance, no further set is added.'),
    'bead_flat_land': ('beads/flat_land_z.png','Flat Z land','Flat sidewall land retained between each normal bead end and the local corner-radius tangency.'),
    'bead_sidewall_sense': ('beads/sidewall_sense.png','First-set sidewall sense','Choose inward or outward sidewall beads. Top and bottom use the opposite sense.'),
    'bead_depth_mode': ('beads/depth_mode.png','Bead depth mode','Use one depth on all faces or independent Top / Inner / Bottom / Outer depths.'),
    'bead_default_depth': ('beads/bead_depth.png','Uniform bead depth','Embossment magnitude normal to the local parent sheet surface.'),
    'bead_top_depth': ('beads/top_depth.png','Top bead depth','Top-face embossment depth magnitude.'),
    'bead_inner_depth': ('beads/inner_depth.png','Inner sidewall bead depth','Vehicle-inner sidewall embossment depth magnitude.'),
    'bead_bottom_depth': ('beads/bottom_depth.png','Bottom bead depth','Bottom-face embossment depth magnitude.'),
    'bead_outer_depth': ('beads/outer_depth.png','Outer sidewall bead depth','Vehicle-outer sidewall embossment depth magnitude.'),
    'bead_overrides': ('beads/set_overrides.png','Per-set overrides','Override depth and/or allow selected bead sets to cut chosen bend-radius regions.'),
    'bead_override_set': ('beads/override_set_number.png','Override set number','Automatically generated bead-set number to override.'),
    'bead_override_depth_mode': ('beads/override_depth_mode.png','Set depth override','Inherit global depth, use one set depth, or use face-specific set depths.'),
    'bead_override_uniform_depth': ('beads/override_uniform_depth.png','Set uniform depth','Uniform local-normal depth for this bead set.'),
    'bead_override_top_depth': ('beads/override_top_depth.png','Set top depth','Top-face depth override for this bead set.'),
    'bead_override_inner_depth': ('beads/override_inner_depth.png','Set inner depth','Inner-sidewall depth override for this bead set.'),
    'bead_override_bottom_depth': ('beads/override_bottom_depth.png','Set bottom depth','Bottom-face depth override for this bead set.'),
    'bead_override_outer_depth': ('beads/override_outer_depth.png','Set outer depth','Outer-sidewall depth override for this bead set.'),
    'bead_cut_top': ('beads/cut_radius_top.png','Cut top bend radius','Allow this bead set to continue through top-adjacent bend-radius regions.'),
    'bead_cut_inner': ('beads/cut_radius_inner.png','Cut inner bend radius','Allow this bead set to continue through inner-sidewall bend-radius regions.'),
    'bead_cut_bottom': ('beads/cut_radius_bottom.png','Cut bottom bend radius','Allow this bead set to continue through bottom-adjacent bend-radius regions.'),
    'bead_cut_outer': ('beads/cut_radius_outer.png','Cut outer bend radius','Allow this bead set to continue through outer-sidewall bend-radius regions.'),

    # Export
    'ex_assy': ('export/assembly_step.png','Assembly STEP','Export one CMS assembly STEP file.'),
    'ex_ind': ('export/individual_steps.png','Individual STEP files','Export one STEP file per generated component.'),
    'ex_json': ('export/config_json.png','Configuration JSON','Save the full reusable CMS configuration.'),
    'ex_sum': ('export/build_summary.png','Build summary','Save derived geometry values and warnings.'),
    'ex_ts': ('export/timestamp_names.png','Timestamp filenames','Append generation timestamp to exported filenames.'),
}

PAGE_DEFAULT = {
    'Crossbeam':'crossbeam/overview.png','Beam Plate':'beam_plate/overview.png','Crush Can':'crush_can/overview.png',
    'Split':'split/overview.png','Rear Interface':'rear_interface/overview.png','Front Interface':'front_interface/overview.png',
    'Beads':'beads/overview.png','Review':'review/overview.png','Export':'export/overview.png'
}


class ScrollableForm(ttk.Frame):
    """Vertically scrollable form column; help panel remains fixed beside it."""
    def __init__(self,parent):
        super().__init__(parent)
        self.columnconfigure(0,weight=1); self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,highlightthickness=0,borderwidth=0)
        self.scroll=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0,column=0,sticky='nsew'); self.scroll.grid(row=0,column=1,sticky='ns')
        self.inner=ttk.Frame(self.canvas); self.inner.columnconfigure(1,weight=1)
        self._win=self.canvas.create_window((0,0),window=self.inner,anchor='nw')
        self.inner.bind('<Configure>',self._sync_region)
        self.canvas.bind('<Configure>',self._sync_width)
        # Mouse-wheel scroll works while the pointer is anywhere over this form,
        # including over entries/comboboxes.  Other pages ignore the event.
        self.bind_all('<MouseWheel>',self._wheel,add='+')

    def _sync_region(self,_=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    def _sync_width(self,event):
        self.canvas.itemconfigure(self._win,width=event.width)
    def _inside(self,w):
        while w is not None:
            if w is self:return True
            try:w=w.master
            except Exception:return False
        return False
    def _wheel(self,event):
        try:w=self.winfo_containing(event.x_root,event.y_root)
        except Exception:w=None
        if not self._inside(w):return
        delta=-1 if event.delta>0 else 1
        self.canvas.yview_scroll(delta*3,'units')
        return 'break'
    def scroll_to_top(self):self.canvas.yview_moveto(0.0)


class HelpImagePanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(8,0,0,0))
        self.columnconfigure(0,weight=1); self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,background='white',highlightthickness=1,highlightbackground='#b7b7b7')
        self.canvas.grid(row=0,column=0,columnspan=4,sticky='nsew')
        self.title_var=tk.StringVar(value='Context help')
        self.file_var=tk.StringVar(value='')
        self.text_var=tk.StringVar(value='Select an input to show its help image.')
        ttk.Button(self,text='Fit',command=self.fit).grid(row=1,column=0,sticky='w',pady=(8,0))
        ttk.Button(self,text='−',width=4,command=lambda:self.zoom_by(1/1.2)).grid(row=1,column=1,pady=(8,0))
        ttk.Button(self,text='+',width=4,command=lambda:self.zoom_by(1.2)).grid(row=1,column=2,pady=(8,0))
        ttk.Label(self,textvariable=self.title_var,style='HelpTitle.TLabel').grid(row=2,column=0,columnspan=4,sticky='w',pady=(8,2))
        ttk.Label(self,textvariable=self.text_var,wraplength=520).grid(row=3,column=0,columnspan=4,sticky='ew')
        ttk.Label(self,textvariable=self.file_var,style='HelpFile.TLabel',wraplength=520).grid(row=4,column=0,columnspan=4,sticky='ew',pady=(5,0))
        self._pil=None; self._photo=None; self._path=None; self._zoom=1.0; self._fit=True
        self.canvas.bind('<Configure>',lambda e:self._render() if self._fit else None)
        self.canvas.bind('<MouseWheel>',self._wheel)

    def show(self, path: Path, title='', text=''):
        self._path=Path(path); self.title_var.set(title or 'Context help'); self.text_var.set(text or '')
        try:self.file_var.set(str(self._path.relative_to(ROOT)))
        except:self.file_var.set(str(self._path))
        if Image is None:
            self._pil=None; self._draw_message('Pillow is required for dynamic fit/zoom help images.')
            return
        try:self._pil=Image.open(self._path).convert('RGB')
        except Exception:self._pil=None; self._draw_message(f'Missing help image:\n{self._path.name}\n\nReplace this file using the same filename.')
        self._fit=True; self._zoom=1.0; self._render()

    def _draw_message(self,msg):
        self.canvas.delete('all'); w=max(100,self.canvas.winfo_width()); h=max(100,self.canvas.winfo_height())
        self.canvas.create_text(w/2,h/2,text=msg,width=max(200,w-50),justify='center',font=('Segoe UI',13))

    def _render(self):
        if self._pil is None:return
        w=max(100,self.canvas.winfo_width()-20); h=max(100,self.canvas.winfo_height()-20)
        if self._fit: scale=min(w/self._pil.width,h/self._pil.height)
        else: scale=self._zoom
        scale=max(0.05,min(6.0,scale))
        size=(max(1,int(self._pil.width*scale)),max(1,int(self._pil.height*scale)))
        img=self._pil.resize(size,Image.Resampling.LANCZOS)
        self._photo=ImageTk.PhotoImage(img)
        self.canvas.delete('all'); self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self._photo,anchor='center')

    def fit(self):self._fit=True;self._zoom=1.0;self._render()
    def zoom_by(self,factor):
        self._fit=False
        if self._pil is not None:
            # Start manual zoom from current fit scale for a natural first click.
            w=max(100,self.canvas.winfo_width()-20); h=max(100,self.canvas.winfo_height()-20)
            if self._zoom==1.0:self._zoom=min(w/self._pil.width,h/self._pil.height)
            self._zoom=max(0.05,min(6.0,self._zoom*factor));self._render()
    def _wheel(self,event):self.zoom_by(1.12 if event.delta>0 else 1/1.12)


class BeadOverrideDialog(tk.Toplevel):
    """Editor for set-specific bead depth/radius-cut overrides."""
    def __init__(self, parent, overrides):
        super().__init__(parent)
        self.title('Bead set overrides')
        sw,sh=parent.winfo_screenwidth(),parent.winfo_screenheight(); w=min(1320,max(960,sw-100)); h=min(760,max(660,sh-80)); self.geometry(f'{w}x{h}'); self.minsize(900,620)
        self.transient(parent)
        self.grab_set()
        self.result = [BeadSetOverride(**vars(x)) for x in overrides]
        self.vars = {}
        self.widgets = {}

        self.columnconfigure(0,weight=11); self.columnconfigure(1,weight=9); self.rowconfigure(0,weight=1)
        left=ttk.Frame(self,padding=14); left.grid(row=0,column=0,sticky='nsew'); left.columnconfigure(1,weight=1); left.rowconfigure(1,weight=1)
        self.help=HelpImagePanel(self); self.help.grid(row=0,column=1,sticky='nsew',padx=(0,14),pady=14)

        ttk.Label(left,text='Per-set bead overrides',style='Title.TLabel').grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,10))
        cols=('set','mode','uniform','top','inner','bottom','outer','cuts')
        self.tree=ttk.Treeview(left,columns=cols,show='headings',height=8)
        headings={'set':'Set','mode':'Depth mode','uniform':'Uniform','top':'Top','inner':'Inner','bottom':'Bottom','outer':'Outer','cuts':'Radius cuts'}
        widths={'set':55,'mode':120,'uniform':80,'top':70,'inner':70,'bottom':70,'outer':70,'cuts':180}
        for c in cols:self.tree.heading(c,text=headings[c]); self.tree.column(c,width=widths[c],anchor='center')
        self.tree.grid(row=1,column=0,columnspan=3,sticky='nsew',pady=(0,12)); self.tree.bind('<<TreeviewSelect>>',self._load_selected)

        editor=ttk.LabelFrame(left,text='Selected / new override',padding=10); editor.grid(row=2,column=0,columnspan=3,sticky='ew'); editor.columnconfigure(1,weight=1)
        self._entry(editor,0,'Bead set number','bead_override_set','1')
        self._combo(editor,1,'Depth override','bead_override_depth_mode','Inherit global',['Inherit global','Uniform override','Face-specific override'])
        self._entry(editor,2,'Uniform depth [mm]','bead_override_uniform_depth','1.2')
        self._entry(editor,3,'Top depth [mm]','bead_override_top_depth','1.2')
        self._entry(editor,4,'Inner sidewall depth [mm]','bead_override_inner_depth','1.2')
        self._entry(editor,5,'Bottom depth [mm]','bead_override_bottom_depth','1.2')
        self._entry(editor,6,'Outer sidewall depth [mm]','bead_override_outer_depth','1.2')
        self._check(editor,7,'Cut TOP bend radius','bead_cut_top',False)
        self._check(editor,8,'Cut INNER sidewall bend radii','bead_cut_inner',False)
        self._check(editor,9,'Cut BOTTOM bend radius','bead_cut_bottom',False)
        self._check(editor,10,'Cut OUTER sidewall bend radii','bead_cut_outer',False)
        self.vars['bead_override_depth_mode'].trace_add('write',lambda *_:self._refresh_states())

        bf=ttk.Frame(left); bf.grid(row=3,column=0,columnspan=3,sticky='ew',pady=(12,0))
        ttk.Button(bf,text='Add / Update',command=self._upsert).pack(side='left')
        ttk.Button(bf,text='Remove selected',command=self._remove).pack(side='left',padx=8)
        ttk.Button(bf,text='Clear editor',command=self._clear_editor).pack(side='left')
        ttk.Button(bf,text='Done',command=self._done).pack(side='right')
        ttk.Button(bf,text='Cancel',command=self._cancel).pack(side='right',padx=8)
        self.protocol('WM_DELETE_WINDOW',self._cancel)
        self._refresh_tree(); self._refresh_states()
        self.help.show(HELP_ROOT/HELP['bead_overrides'][0],HELP['bead_overrides'][1],HELP['bead_overrides'][2])

    def _bind(self,w,key):
        self.widgets[key]=w
        def show(_=None):
            rel,title,text=HELP[key]; self.help.show(HELP_ROOT/rel,title,text)
        w.bind('<FocusIn>',show,add='+'); w.bind('<Button-1>',show,add='+')

    def _entry(self,parent,row,label,key,val):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=4,padx=(0,10))
        v=tk.StringVar(value=val); self.vars[key]=v
        e=ttk.Entry(parent,textvariable=v,width=22); e.grid(row=row,column=1,sticky='ew',pady=4); self._bind(e,key); return e

    def _combo(self,parent,row,label,key,val,values):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=4,padx=(0,10))
        v=tk.StringVar(value=val); self.vars[key]=v
        c=ttk.Combobox(parent,textvariable=v,values=values,state='readonly',width=22); c.grid(row=row,column=1,sticky='ew',pady=4); self._bind(c,key); return c

    def _check(self,parent,row,text,key,val):
        v=tk.BooleanVar(value=val); self.vars[key]=v
        c=ttk.Checkbutton(parent,text=text,variable=v); c.grid(row=row,column=0,columnspan=2,sticky='w',pady=3); self._bind(c,key); return c

    def _mode_code(self):
        return {'Inherit global':'inherit','Uniform override':'uniform','Face-specific override':'face_specific'}[self.vars['bead_override_depth_mode'].get()]

    def _mode_label(self,code):
        return {'inherit':'Inherit global','uniform':'Uniform override','face_specific':'Face-specific override'}.get(code,'Inherit global')

    def _f_or_none(self,key):
        t=self.vars[key].get().strip()
        return None if not t else float(t)

    def _refresh_states(self):
        mode=self._mode_code()
        self.widgets['bead_override_uniform_depth'].configure(state='normal' if mode=='uniform' else 'disabled')
        for k in ('bead_override_top_depth','bead_override_inner_depth','bead_override_bottom_depth','bead_override_outer_depth'):
            self.widgets[k].configure(state='normal' if mode=='face_specific' else 'disabled')

    def _cuts_text(self,o):
        names=[n for n,v in [('Top',o.cut_top),('Inner',o.cut_inner),('Bottom',o.cut_bottom),('Outer',o.cut_outer)] if v]
        return ', '.join(names) if names else 'Normal'

    def _refresh_tree(self):
        for item in self.tree.get_children():self.tree.delete(item)
        for o in sorted(self.result,key=lambda x:x.set_index):
            vals=(o.set_index,self._mode_label(o.depth_mode),'' if o.uniform_depth is None else f'{o.uniform_depth:g}',
                  '' if o.top_depth is None else f'{o.top_depth:g}','' if o.inner_depth is None else f'{o.inner_depth:g}',
                  '' if o.bottom_depth is None else f'{o.bottom_depth:g}','' if o.outer_depth is None else f'{o.outer_depth:g}',self._cuts_text(o))
            self.tree.insert('', 'end', iid=str(o.set_index), values=vals)

    def _load_selected(self,_=None):
        sel=self.tree.selection()
        if not sel:return
        idx=int(sel[0]); o=next(x for x in self.result if x.set_index==idx)
        self.vars['bead_override_set'].set(str(o.set_index)); self.vars['bead_override_depth_mode'].set(self._mode_label(o.depth_mode))
        for key,val in [('bead_override_uniform_depth',o.uniform_depth),('bead_override_top_depth',o.top_depth),('bead_override_inner_depth',o.inner_depth),('bead_override_bottom_depth',o.bottom_depth),('bead_override_outer_depth',o.outer_depth)]:
            self.vars[key].set('' if val is None else str(val))
        for key,val in [('bead_cut_top',o.cut_top),('bead_cut_inner',o.cut_inner),('bead_cut_bottom',o.cut_bottom),('bead_cut_outer',o.cut_outer)]:self.vars[key].set(val)
        self._refresh_states()

    def _upsert(self):
        try:
            idx=int(float(self.vars['bead_override_set'].get())); mode=self._mode_code()
            if idx<1:raise ValueError('Set number must be at least 1')
            uniform=self._f_or_none('bead_override_uniform_depth') if mode=='uniform' else None
            vals={k:self._f_or_none(k) if mode=='face_specific' else None for k in ('bead_override_top_depth','bead_override_inner_depth','bead_override_bottom_depth','bead_override_outer_depth')}
            o=BeadSetOverride(set_index=idx,depth_mode=mode,uniform_depth=uniform,
                top_depth=vals['bead_override_top_depth'],inner_depth=vals['bead_override_inner_depth'],bottom_depth=vals['bead_override_bottom_depth'],outer_depth=vals['bead_override_outer_depth'],
                cut_top=bool(self.vars['bead_cut_top'].get()),cut_inner=bool(self.vars['bead_cut_inner'].get()),cut_bottom=bool(self.vars['bead_cut_bottom'].get()),cut_outer=bool(self.vars['bead_cut_outer'].get()))
            self.result=[x for x in self.result if x.set_index!=idx]+[o]; self._refresh_tree(); self.tree.selection_set(str(idx))
        except Exception as exc:messagebox.showerror('Bead override',str(exc),parent=self)

    def _remove(self):
        sel=self.tree.selection()
        if not sel:return
        idx=int(sel[0]); self.result=[x for x in self.result if x.set_index!=idx]; self._refresh_tree(); self._clear_editor()

    def _clear_editor(self):
        self.vars['bead_override_set'].set('1'); self.vars['bead_override_depth_mode'].set('Inherit global')
        for k in ('bead_override_uniform_depth','bead_override_top_depth','bead_override_inner_depth','bead_override_bottom_depth','bead_override_outer_depth'):self.vars[k].set('1.2')
        for k in ('bead_cut_top','bead_cut_inner','bead_cut_bottom','bead_cut_outer'):self.vars[k].set(False)
        self._refresh_states()

    def _done(self): self.grab_release(); self.destroy()
    def _cancel(self): self.result=None; self.grab_release(); self.destroy()


class CMSApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('CMS Generator v0.13');
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight(); w=min(1440,max(980,sw-80)); h=min(900,max(620,sh-120)); self.geometry(f'{w}x{h}'); self.minsize(960,600)
        self.cfg=CMSConfig(); self.frames={}; self.vars={}; self.last_result=None; self.help_panels={}; self.widgets={}; self.bead_overrides=[]
        self._style(); self._build_shell(); self._make_pages(); self.show_page('Crossbeam'); self.refresh_all(); self._update_radius_displays()

    def _style(self):
        s=ttk.Style(self)
        try:s.theme_use('vista')
        except:pass
        for name,size,weight in [('TkDefaultFont',12,'normal'),('TkTextFont',12,'normal'),('TkFixedFont',11,'normal')]:
            try:tkfont.nametofont(name).configure(family='Segoe UI',size=size,weight=weight)
            except:pass
        s.configure('.',font=('Segoe UI',12))
        s.configure('Nav.TButton',padding=(14,11),anchor='w',font=('Segoe UI',12))
        s.configure('Title.TLabel',font=('Segoe UI',20,'bold'))
        s.configure('HelpTitle.TLabel',font=('Segoe UI',13,'bold'))
        s.configure('HelpFile.TLabel',font=('Segoe UI',9),foreground='#666666')
        s.configure('TEntry',padding=(6,6)); s.configure('TCombobox',padding=(5,5)); s.configure('TCheckbutton',padding=(3,5))

    def _build_shell(self):
        self.columnconfigure(1,weight=1); self.rowconfigure(0,weight=1)
        nav=ttk.Frame(self,padding=12); nav.grid(row=0,column=0,sticky='ns'); nav.columnconfigure(0,weight=1)
        ttk.Label(nav,text='CMS GENERATOR',style='Title.TLabel').grid(row=0,column=0,pady=(0,18),sticky='w')
        names=['Crossbeam','Beam Plate','Crush Can','Split','Rear Interface','Front Interface','Beads','Review','Export']
        for i,n in enumerate(names,1):
            ttk.Button(nav,text=f'{i}. {n}',style='Nav.TButton',command=lambda x=n:self.show_page(x)).grid(row=i,column=0,sticky='ew',pady=2)
        ttk.Separator(nav).grid(row=11,column=0,sticky='ew',pady=12)
        ttk.Button(nav,text='Load preset',command=self.load_preset).grid(row=12,column=0,sticky='ew',pady=3)
        ttk.Button(nav,text='Save preset',command=self.save_preset).grid(row=13,column=0,sticky='ew',pady=3)
        ttk.Button(nav,text='Validate',command=self.validate_now).grid(row=14,column=0,sticky='ew',pady=3)
        ttk.Button(nav,text='Generate CMS',command=self.generate).grid(row=15,column=0,sticky='ew',pady=(14,3))
        self.host=ttk.Frame(self,padding=14); self.host.grid(row=0,column=1,sticky='nsew'); self.host.columnconfigure(0,weight=1); self.host.rowconfigure(0,weight=1)
        self.status=tk.StringVar(value='Ready'); ttk.Label(self,textvariable=self.status,anchor='w',relief='sunken',padding=(8,4)).grid(row=1,column=0,columnspan=2,sticky='ew')

    def _page(self,name,title):
        f=ttk.Frame(self.host); f.grid(row=0,column=0,sticky='nsew'); f.columnconfigure(0,weight=11); f.columnconfigure(1,weight=9); f.rowconfigure(1,weight=1)
        ttk.Label(f,text=title,style='Title.TLabel').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
        scroll_form=ScrollableForm(f); scroll_form.grid(row=1,column=0,sticky='nsew',padx=(0,18))
        form=scroll_form.inner; form.columnconfigure(1,weight=1); form.columnconfigure(2,weight=0)
        hp=HelpImagePanel(f); hp.grid(row=1,column=1,sticky='nsew'); self.help_panels[name]=hp
        self.frames[name]=(f,form); return form

    def _var(self,key,val,kind='str'):
        cls={'str':tk.StringVar,'bool':tk.BooleanVar,'int':tk.IntVar,'float':tk.DoubleVar}[kind]
        v=cls(value=val); self.vars[key]=v; return v

    def _bind_help(self,widget,key):
        self.widgets[key]=widget
        def show(_=None):self.show_help(key)
        widget.bind('<FocusIn>',show,add='+'); widget.bind('<Button-1>',show,add='+')
        return widget

    def show_help(self,key):
        spec=HELP.get(key)
        if not spec:return
        rel,title,text=spec
        # Find the page that owns the focused/highlighted control.
        widget=self.widgets.get(key); page=None
        if widget:
            for n,(frame,_) in self.frames.items():
                w=widget
                while w is not None:
                    if w==frame:page=n;break
                    try:w=w.master
                    except:w=None
                if page:break
        if page:self.help_panels[page].show(HELP_ROOT/rel,title,text)

    def _entry(self,parent,row,label,key,val,width=24,readonly=False):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var(key,val,'str'); e=ttk.Entry(parent,textvariable=v,width=width,state='readonly' if readonly else 'normal'); e.grid(row=row,column=1,sticky='ew',pady=7); self._bind_help(e,key); return e

    def _combo(self,parent,row,label,key,val,values):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var(key,val,'str'); c=ttk.Combobox(parent,textvariable=v,values=values,state='readonly',width=24); c.grid(row=row,column=1,sticky='ew',pady=7); self._bind_help(c,key); return c

    def _check(self,parent,row,text,key,val,command=None):
        v=self._var(key,val,'bool'); w=ttk.Checkbutton(parent,text=text,variable=v,command=command); w.grid(row=row,column=0,columnspan=2,sticky='w',pady=5); self._bind_help(w,key); return w

    def _file_row(self,parent,row,label,key):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var(key,'','str'); e=ttk.Entry(parent,textvariable=v,width=24); e.grid(row=row,column=1,sticky='ew',pady=7); self._bind_help(e,key)
        b=ttk.Button(parent,text='Browse…',command=self.select_guideline); b.grid(row=row,column=2,sticky='w',padx=(8,0)); self._bind_help(b,key)
        self.widgets[key+'_browse']=b; return e,b

    def _make_pages(self):
        f=self._page('Crossbeam','1. Crossbeam')
        self._combo(f,0,'Beam family','beam_type','Monoleg',['Monoleg','Power-B','Standard-B','D-section'])
        self._combo(f,1,'Sweep source','beam_sweep_mode','Constant radius',['Constant radius','STEP guideline'])
        self.vars['beam_sweep_mode'].trace_add('write',lambda *_:self.refresh_all())
        self._entry(f,2,'Thickness [mm]','beam_t',2)
        self.beam_radius_widget=self._entry(f,3,'Sweep radius [mm]','beam_R',2000)
        self.beam_length_widget=self._entry(f,4,'Length / Y span [mm]','beam_L',1200)
        self._entry(f,5,'Depth [mm]','beam_D',50); self._entry(f,6,'Height [mm]','beam_H',100)
        self._entry(f,7,'Steel grade [MPa]','steel',1300); self._entry(f,8,'Front-face centre Z [mm]','beam_z',0)
        self.beam_step_widget,self.beam_step_browse=self._file_row(f,9,'Sweep guideline STEP','beam_step')
        ttk.Label(f,text='STEP mode: the file must contain one open XY-planar, Y-symmetric curve on the outer/front beam envelope. Its shape and scale are preserved; translation is normalised automatically.',wraplength=700).grid(row=10,column=0,columnspan=3,sticky='w',pady=(12,0))

        f=self._page('Beam Plate','2. Beam Plate')
        self.bp_enable_widget=self._check(f,0,'Use beam plate','bp_enabled',True,self.refresh_all)
        self.bp_widgets=[]
        for r,(lab,key,val) in enumerate([('Outer Y [mm]','bp_y',485),('Width [mm]','bp_w',100),('Thickness [mm]','bp_t',3),('Beam overlap [mm]','bp_overlap',6),('Outer slip-plane gap [mm]','bp_gap_outer',2),('Inner slip-plane gap [mm]','bp_gap_inner',2)],1):
            self.bp_widgets.append(self._entry(f,r,lab,key,val))
        self.bp_widgets.append(self._combo(f,7,'Bend-radius input basis','bp_radius_basis','Inner radius',['Inner radius','Outer radius']))
        self.bp_radius_input_label=ttk.Label(f,text='Inner radius [×t]'); self.bp_radius_input_label.grid(row=8,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var('bp_radius_k',4.0,'str'); self.bp_radius_input=ttk.Entry(f,textvariable=v,width=24); self.bp_radius_input.grid(row=8,column=1,sticky='ew',pady=7); self._bind_help(self.bp_radius_input,'bp_radius_k'); self.bp_widgets.append(self.bp_radius_input)
        self.bp_radius_other_label=ttk.Label(f,text='Outer radius [×t] (derived)'); self.bp_radius_other_label.grid(row=9,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var('bp_radius_other','5.0','str'); self.bp_radius_other=ttk.Entry(f,textvariable=v,width=24,state='readonly'); self.bp_radius_other.grid(row=9,column=1,sticky='ew',pady=7); self._bind_help(self.bp_radius_other,'bp_radius_other'); self.bp_widgets.append(self.bp_radius_other)
        self.bp_note=tk.StringVar(); ttk.Label(f,textvariable=self.bp_note,wraplength=700).grid(row=10,column=0,columnspan=3,sticky='w',pady=12)
        for k in ('bp_t','bp_radius_basis','bp_radius_k'):self.vars[k].trace_add('write',lambda *_:self._update_radius_displays())

        f=self._page('Crush Can','3. Crush Can Geometry')
        fields=[('Rear width Wr [mm]','cc_rw',80),('Rear height Hr (Z) [mm]','cc_rd',80),('Rear centre Zr [mm]','cc_rz',0),('Front width Wf [mm]','cc_fw',80),('Front height Hf (Z) [mm]','cc_fd',80),('Front centre Zf [mm]','cc_fz',0),('Thickness t [mm]','cc_t',2)]
        r=0
        for lab,key,val in fields:self._entry(f,r,lab,key,val);r+=1
        self._combo(f,r,'Corner-radius input basis','cc_radius_basis','Inner radius',['Inner radius','Outer radius']);r+=1
        self.cc_radius_input_label=ttk.Label(f,text='Inner radius [×t]'); self.cc_radius_input_label.grid(row=r,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var('cc_radius_k',4.0,'str'); self.cc_radius_input=ttk.Entry(f,textvariable=v,width=24); self.cc_radius_input.grid(row=r,column=1,sticky='ew',pady=7); self._bind_help(self.cc_radius_input,'cc_radius_k');r+=1
        self.cc_radius_other_label=ttk.Label(f,text='Outer radius [×t] (derived)'); self.cc_radius_other_label.grid(row=r,column=0,sticky='w',pady=7,padx=(0,12))
        v=self._var('cc_radius_other','5.0','str'); self.cc_radius_other=ttk.Entry(f,textvariable=v,width=24,state='readonly'); self.cc_radius_other.grid(row=r,column=1,sticky='ew',pady=7); self._bind_help(self.cc_radius_other,'cc_radius_other');r+=1
        for lab,key,val in [('Rear straight [mm]','cc_rs',20),('Front straight [mm]','cc_fs',15),('Transition radius [mm]','cc_tr',60),('Rear datum X offset from beam frontmost point [mm]','cc_offset',200),('LH centre Y if no beam plate [mm]','cc_y',-435)]:self._entry(f,r,lab,key,val);r+=1
        ttk.Label(f,text='The editable corner radius may be defined from either sheet surface; the counterpart is always derived from thickness.',wraplength=700).grid(row=r,column=0,columnspan=3,sticky='w',pady=(12,0))
        for k in ('cc_t','cc_radius_basis','cc_radius_k'):self.vars[k].trace_add('write',lambda *_:self._update_radius_displays())

        f=self._page('Split','4. Crush-can C-section Split')
        self._combo(f,0,'Split orientation','split','Top / Bottom',['Top / Bottom','Inner / Outer'])
        self.large_combo=self._combo(f,1,'Larger half','larger','Top',['Top','Bottom']); self._entry(f,2,'Overlap [mm]','overlap',4)
        self.vars['split'].trace_add('write',lambda *_:self._split_changed())
        ttk.Label(f,text='Maximum section dimensions always refer to the outside envelope. The smaller C-half is inset by thickness while the mating band remains longitudinal.',wraplength=700).grid(row=4,column=0,columnspan=3,sticky='w',pady=12)

        f=self._page('Rear Interface','5. Rear Interface')
        self._combo(f,0,'Architecture','rear_arch','Back plate',['Back plate','Rail bolted']); self.vars['rear_arch'].trace_add('write',lambda *_:self.refresh_all())
        self.rear_groups=[self._entry(f,1,'Back plate width [mm]','back_w',100),self._entry(f,2,'Back plate height [mm]','back_h',200),self._entry(f,3,'Back plate thickness [mm]','back_t',3.5)]
        self.rail_widgets=[self._entry(f,5,'Number of through-bolts','bolt_n',2),self._entry(f,6,'Hole diameter [mm]','hole_d',12),self._entry(f,7,'Bolt-axis X from rear edge [mm]','bolt_x',15),self._entry(f,8,'Vertical edge margin [mm]','bolt_margin',8)]
        ttk.Label(f,text='Each rail bolt runs along vehicle Y through BOTH longitudinal sidewalls. Z positions are equispaced from the local sidewall height at the selected X.',wraplength=700).grid(row=10,column=0,columnspan=3,sticky='w',pady=12)

        f=self._page('Front Interface','6. Front Interaction')
        self.front_limiter=tk.StringVar(value='Beam plate'); ttk.Label(f,text='Limiting component').grid(row=0,column=0,sticky='w',pady=7); ttk.Label(f,textvariable=self.front_limiter).grid(row=0,column=1,sticky='w',pady=7)
        self._combo(f,1,'Mode','front_mode','Flow over',['Stop at contact','Flow over']); self.vars['front_mode'].trace_add('write',lambda *_:self.refresh_all())
        self.flow_widgets=[self._entry(f,2,'Extra after contact [mm]','front_extra',15)]
        self.flow_face_widgets={}
        for r,(lab,key,val) in enumerate([('Allow TOP flow (includes upper sidewalls)','flow_top',True),('Allow BOTTOM flow (includes lower sidewalls)','flow_bottom',True),('Allow INNER flow (beam plate only)','flow_inner',False),('Allow OUTER flow (beam plate only)','flow_outer',False)],3):
            cb=self._check(f,r,lab,key,val)
            self.flow_widgets.append(cb)
            self.flow_face_widgets[key]=cb
        ttk.Label(f,text='TOP/BOTTOM flow extends the whole connected upper/lower region, including the sidewall portions, until blocked by the limiting geometry. For a bare beam only TOP/BOTTOM flow is permitted; the central sidewalls stop on the rear-land envelope, never inside B-section valleys. Beam-plate contact remains conformal through its bend radii.',wraplength=700).grid(row=8,column=0,columnspan=3,sticky='w',pady=12)

        f=self._page('Beads','7. Continuous Beads')
        self._check(f,0,'Add continuous beads','bead_enabled',False,command=self.refresh_all)
        self.bead_widgets=[]
        self.bead_widgets.append(self._entry(f,1,'Bead width in X [mm]','bead_w',11))
        self.bead_widgets.append(self._entry(f,2,'Flat X land / clear bead spacing [mm]','bead_spacing',18))
        self.bead_widgets.append(self._entry(f,3,'Minimum rear flat remainder [mm]','bead_rear_min',10))
        self.bead_widgets.append(self._entry(f,4,'Flat Z land to bend tangency [mm]','bead_flat_land',8))
        self.bead_widgets.append(self._combo(f,5,'First-set sidewall sense','bead_sidewall_sense','Outward',['Outward','Inward']))
        self.bead_widgets.append(self._combo(f,6,'Depth definition','bead_depth_mode','Uniform',['Uniform','Face-specific']))
        self.vars['bead_depth_mode'].trace_add('write',lambda *_:self.refresh_all())
        self.bead_uniform_depth_widget=self._entry(f,7,'Uniform bead depth [mm]','bead_default_depth',1.2); self.bead_widgets.append(self.bead_uniform_depth_widget)
        self.bead_face_depth_widgets=[
            self._entry(f,8,'Top face depth [mm]','bead_top_depth',1.2),
            self._entry(f,9,'Inner sidewall depth [mm]','bead_inner_depth',1.2),
            self._entry(f,10,'Bottom face depth [mm]','bead_bottom_depth',1.2),
            self._entry(f,11,'Outer sidewall depth [mm]','bead_outer_depth',1.2),
        ]; self.bead_widgets.extend(self.bead_face_depth_widgets)
        self.bead_override_button=ttk.Button(f,text='Edit per-set depth / bend-radius overrides…',command=self.edit_bead_overrides)
        self.bead_override_button.grid(row=12,column=0,columnspan=2,sticky='w',pady=(10,5)); self._bind_help(self.bead_override_button,'bead_overrides'); self.bead_widgets.append(self.bead_override_button)
        self.bead_override_summary=tk.StringVar(value='No per-set overrides')
        ttk.Label(f,textvariable=self.bead_override_summary,wraplength=700).grid(row=13,column=0,columnspan=2,sticky='w',pady=(2,6))
        ttk.Label(f,text='Placement rule: the vehicle-outer sidewall is the anchor. Its beads use the entered width and flat X land from front to rear. The first inner bead keeps the same front flat land; the rearmost inner bead shares the same YZ plane as the rearmost outer bead; intermediate inner beads are equispaced in X. Bead-plane angles are derived from those matching centres. Local bead height adapts to can height/Z while preserving the entered flat Z land. Bead CAD embossment itself is the next milestone.',wraplength=700).grid(row=14,column=0,columnspan=3,sticky='w',pady=(8,18))

        f=self._page('Review','8. Review & Validation')
        self.review=tk.Text(f,height=26,width=70,wrap='word',state='disabled',font=('Segoe UI',12)); self.review.grid(row=0,column=0,columnspan=3,sticky='nsew'); f.rowconfigure(0,weight=1)
        ttk.Button(f,text='Refresh validation',command=self.validate_now).grid(row=1,column=0,sticky='w',pady=10)

        f=self._page('Export','9. Export')
        for r,(lab,key,val) in enumerate([('CMS assembly STEP','ex_assy',True),('Individual component STEP files','ex_ind',True),('Configuration JSON','ex_json',True),('Build summary','ex_sum',True),('Timestamp filenames','ex_ts',True)]):self._check(f,r,lab,key,val)
        ttk.Button(f,text='Generate and export…',command=self.generate).grid(row=7,column=0,sticky='w',pady=18)

    def _show_page_default(self,name):
        rel=PAGE_DEFAULT.get(name)
        if rel:self.help_panels[name].show(HELP_ROOT/rel,f'{name} help','Select an input to display its dedicated measurement/help image.')

    def show_page(self,name):
        self.frames[name][0].tkraise(); self._show_page_default(name)
        if name=='Review':self.validate_now()

    def select_guideline(self):
        p=filedialog.askopenfilename(title='Select crossbeam sweep guideline',filetypes=[('STEP files','*.step *.stp'),('All files','*.*')])
        if p:self.vars['beam_step'].set(p)

    def edit_bead_overrides(self):
        dlg=BeadOverrideDialog(self,self.bead_overrides)
        self.wait_window(dlg)
        if dlg.result is not None:
            self.bead_overrides=dlg.result
            self._update_bead_override_summary()

    def _update_bead_override_summary(self):
        if not hasattr(self,'bead_override_summary'):return
        if not self.bead_overrides:
            self.bead_override_summary.set('No per-set overrides — all sets use the global depth definition and normal (non-radius-cutting) beads.')
            return
        chunks=[]
        for o in sorted(self.bead_overrides,key=lambda x:x.set_index):
            cuts=[n for n,v in [('Top',o.cut_top),('Inner',o.cut_inner),('Bottom',o.cut_bottom),('Outer',o.cut_outer)] if v]
            chunks.append(f'Set {o.set_index}: {o.depth_mode.replace("_"," ")}; cuts={"+".join(cuts) if cuts else "normal"}')
        self.bead_override_summary.set(' | '.join(chunks))

    def _split_changed(self):
        if self.vars['split'].get()=='Top / Bottom':self.large_combo['values']=['Top','Bottom'];self.vars['larger'].set('Top')
        else:self.large_combo['values']=['Inner','Outer'];self.vars['larger'].set('Outer')

    def _update_radius_displays(self):
        for prefix,tkey in [('bp','bp_t'),('cc','cc_t')]:
            if prefix+'_radius_basis' not in self.vars:return
            basis=self.vars[prefix+'_radius_basis'].get(); key=prefix+'_radius_k'; other=prefix+'_radius_other'
            try:k=float(self.vars[key].get()); t=float(self.vars[tkey].get())
            except:self.vars[other].set('—');continue
            if basis=='Inner radius':
                ok=k+1.0; self.vars[other].set(f'{ok:g}')
                getattr(self,prefix+'_radius_input_label').configure(text=f'Inner radius [×t]  ({k*t:.3f} mm)')
                getattr(self,prefix+'_radius_other_label').configure(text=f'Outer radius [×t] (derived, {ok*t:.3f} mm)')
            else:
                ik=k-1.0; self.vars[other].set(f'{ik:g}')
                getattr(self,prefix+'_radius_input_label').configure(text=f'Outer radius [×t]  ({k*t:.3f} mm)')
                getattr(self,prefix+'_radius_other_label').configure(text=f'Inner radius [×t] (derived, {ik*t:.3f} mm)')

    def refresh_all(self):
        step=self.vars.get('beam_sweep_mode') and self.vars['beam_sweep_mode'].get()=='STEP guideline'
        for w in (getattr(self,'beam_radius_widget',None),getattr(self,'beam_length_widget',None)):
            if w:w.configure(state='disabled' if step else 'normal')
        if hasattr(self,'beam_step_widget'):self.beam_step_widget.configure(state='normal' if step else 'disabled')
        if hasattr(self,'beam_step_browse'):self.beam_step_browse.configure(state='normal' if step else 'disabled')

        bp=self.vars.get('bp_enabled'); enabled=bool(bp.get()) if bp else True
        for w in getattr(self,'bp_widgets',[]):
            try:
                if w is getattr(self,'bp_radius_other',None):w.configure(state='readonly' if enabled else 'disabled')
                elif isinstance(w,ttk.Combobox):w.configure(state='readonly' if enabled else 'disabled')
                else:w.configure(state='normal' if enabled else 'disabled')
            except:pass
        if hasattr(self,'front_limiter'):self.front_limiter.set('Beam plate' if enabled else 'Crossbeam')
        rail=self.vars.get('rear_arch') and self.vars['rear_arch'].get()=='Rail bolted'
        for w in getattr(self,'rear_groups',[]):w.configure(state='disabled' if rail else 'normal')
        for w in getattr(self,'rail_widgets',[]):w.configure(state='normal' if rail else 'disabled')
        flow=self.vars.get('front_mode') and self.vars['front_mode'].get()=='Flow over'
        for w in getattr(self,'flow_widgets',[]):
            try:w.configure(state='normal' if flow else 'disabled')
            except:pass
        # Standalone crossbeam: no independent inner/outer sidewall flow.
        # Top/Bottom include their adjoining sidewall regions automatically.
        for face in ('flow_inner','flow_outer'):
            w=getattr(self,'flow_face_widgets',{}).get(face)
            if w is not None:w.configure(state='normal' if (flow and enabled) else 'disabled')
        if hasattr(self,'bp_note'):
            self.bp_note.set('Independent beam-plate bend radius and separate outer/inner slip-plane gaps are active. Geometry is checked for beam interference.' if enabled else 'No beam plate will be built. The crossbeam becomes the front limiting component.')

        beads_on=bool(self.vars.get('bead_enabled').get()) if self.vars.get('bead_enabled') else False
        for w in getattr(self,'bead_widgets',[]):
            try:w.configure(state='normal' if beads_on else 'disabled')
            except:pass
        if beads_on and self.vars.get('bead_sidewall_sense'):
            try:self.widgets['bead_sidewall_sense'].configure(state='readonly')
            except:pass
            try:self.widgets['bead_depth_mode'].configure(state='readonly')
            except:pass
        depth_mode=self.vars.get('bead_depth_mode') and self.vars['bead_depth_mode'].get()
        if hasattr(self,'bead_uniform_depth_widget'):
            self.bead_uniform_depth_widget.configure(state='normal' if beads_on and depth_mode=='Uniform' else 'disabled')
        for w in getattr(self,'bead_face_depth_widgets',[]):
            w.configure(state='normal' if beads_on and depth_mode=='Face-specific' else 'disabled')
        if hasattr(self,'bead_override_button'):
            self.bead_override_button.configure(state='normal' if beads_on else 'disabled')
        self._update_bead_override_summary()
        self._update_radius_displays()

    def _f(self,k):return float(self.vars[k].get())
    def _i(self,k):return int(float(self.vars[k].get()))

    def collect(self):
        beam_map={'Monoleg':1,'Power-B':2,'Standard-B':3,'D-section':4}
        c=CMSConfig(); sm='step_guideline' if self.vars['beam_sweep_mode'].get()=='STEP guideline' else 'constant_radius'
        c.beam=BeamSpec(beam_type=beam_map[self.vars['beam_type'].get()],thickness=self._f('beam_t'),sweep_radius=self._f('beam_R'),length=self._f('beam_L'),depth=self._f('beam_D'),height=self._f('beam_H'),steel_grade=self._i('steel'),front_face_center_z=self._f('beam_z'),sweep_mode=sm,guideline_step_path=self.vars['beam_step'].get().strip())
        c.beam_plate=BeamPlateSpec(enabled=bool(self.vars['bp_enabled'].get()),outer_y=self._f('bp_y'),width=self._f('bp_w'),thickness=self._f('bp_t'),beam_overlap=self._f('bp_overlap'),slip_plane_gap_outer=self._f('bp_gap_outer'),slip_plane_gap_inner=self._f('bp_gap_inner'),bend_radius_basis='inner' if self.vars['bp_radius_basis'].get()=='Inner radius' else 'outer',bend_radius_multiplier=self._f('bp_radius_k'))
        split='top_bottom' if self.vars['split'].get()=='Top / Bottom' else 'inner_outer'; larger=self.vars['larger'].get().lower()
        c.crush_can=CrushCanSpec(rear_width=self._f('cc_rw'),rear_depth=self._f('cc_rd'),rear_z=self._f('cc_rz'),front_width=self._f('cc_fw'),front_depth=self._f('cc_fd'),front_z=self._f('cc_fz'),thickness=self._f('cc_t'),overlap=self._f('overlap'),split=split,larger_half=larger,rear_straight=self._f('cc_rs'),front_straight=self._f('cc_fs'),transition_radius=self._f('cc_tr'),rear_datum_offset=self._f('cc_offset'),lh_center_y=self._f('cc_y'),corner_radius_basis='inner' if self.vars['cc_radius_basis'].get()=='Inner radius' else 'outer',corner_radius_multiplier=self._f('cc_radius_k'))
        arch='back_plate' if self.vars['rear_arch'].get()=='Back plate' else 'rail_bolted'
        c.rear_mount=RearMountSpec(architecture=arch,back_plate_thickness=self._f('back_t'),back_plate_height=self._f('back_h'),back_plate_width=self._f('back_w'),bolt_count=self._i('bolt_n'),bolt_x_from_rear=self._f('bolt_x'),hole_diameter=self._f('hole_d'),vertical_edge_margin=self._f('bolt_margin'))
        mode='stop_at_contact' if self.vars['front_mode'].get()=='Stop at contact' else 'flow_over'
        c.front_interface=FrontInterfaceSpec(mode,self._f('front_extra'),bool(self.vars['flow_top'].get()),bool(self.vars['flow_bottom'].get()),bool(self.vars['flow_inner'].get()),bool(self.vars['flow_outer'].get()))
        c.beads=BeadSpec(
            enabled=bool(self.vars['bead_enabled'].get()),
            width=self._f('bead_w'),
            clear_spacing_x=self._f('bead_spacing'),
            minimum_rear_remainder=self._f('bead_rear_min'),
            flat_land_z=self._f('bead_flat_land'),
            depth_mode='uniform' if self.vars['bead_depth_mode'].get()=='Uniform' else 'face_specific',
            default_depth=self._f('bead_default_depth'),
            top_depth=self._f('bead_top_depth'),
            inner_depth=self._f('bead_inner_depth'),
            bottom_depth=self._f('bead_bottom_depth'),
            outer_depth=self._f('bead_outer_depth'),
            sidewall_sense='outward' if self.vars['bead_sidewall_sense'].get()=='Outward' else 'inward',
            set_overrides=[BeadSetOverride(**vars(x)) for x in self.bead_overrides],
        )
        c.export=ExportSpec(bool(self.vars['ex_assy'].get()),bool(self.vars['ex_ind'].get()),bool(self.vars['ex_json'].get()),bool(self.vars['ex_sum'].get()),bool(self.vars['ex_ts'].get()))
        self.cfg=c; return c

    def apply_config(self,c):
        names={1:'Monoleg',2:'Power-B',3:'Standard-B',4:'D-section'}; self.vars['beam_type'].set(names[c.beam.beam_type])
        vals={'beam_t':c.beam.thickness,'beam_R':c.beam.sweep_radius,'beam_L':c.beam.length,'beam_D':c.beam.depth,'beam_H':c.beam.height,'steel':c.beam.steel_grade,'beam_z':c.beam.front_face_center_z,'beam_step':c.beam.guideline_step_path,'bp_y':c.beam_plate.outer_y,'bp_w':c.beam_plate.width,'bp_t':c.beam_plate.thickness,'bp_overlap':c.beam_plate.beam_overlap,'bp_gap_outer':c.beam_plate.slip_plane_gap_outer,'bp_gap_inner':c.beam_plate.slip_plane_gap_inner,'bp_radius_k':c.beam_plate.bend_radius_multiplier,'cc_rw':c.crush_can.rear_width,'cc_rd':c.crush_can.rear_depth,'cc_rz':c.crush_can.rear_z,'cc_fw':c.crush_can.front_width,'cc_fd':c.crush_can.front_depth,'cc_fz':c.crush_can.front_z,'cc_t':c.crush_can.thickness,'cc_radius_k':c.crush_can.corner_radius_multiplier,'overlap':c.crush_can.overlap,'cc_rs':c.crush_can.rear_straight,'cc_fs':c.crush_can.front_straight,'cc_tr':c.crush_can.transition_radius,'cc_offset':c.crush_can.rear_datum_offset,'cc_y':c.crush_can.lh_center_y,'back_w':c.rear_mount.back_plate_width,'back_h':c.rear_mount.back_plate_height,'back_t':c.rear_mount.back_plate_thickness,'bolt_n':c.rear_mount.bolt_count,'bolt_x':c.rear_mount.bolt_x_from_rear,'hole_d':c.rear_mount.hole_diameter,'bolt_margin':c.rear_mount.vertical_edge_margin,'front_extra':c.front_interface.extra_after_contact,'bead_w':c.beads.width,'bead_spacing':c.beads.clear_spacing_x,'bead_rear_min':c.beads.minimum_rear_remainder,'bead_flat_land':c.beads.flat_land_z,'bead_default_depth':c.beads.default_depth,'bead_top_depth':c.beads.top_depth,'bead_inner_depth':c.beads.inner_depth,'bead_bottom_depth':c.beads.bottom_depth,'bead_outer_depth':c.beads.outer_depth}
        for k,v in vals.items():self.vars[k].set(str(v))
        self.vars['beam_sweep_mode'].set('STEP guideline' if c.beam.sweep_mode=='step_guideline' else 'Constant radius')
        self.vars['bp_enabled'].set(c.beam_plate.enabled); self.vars['bp_radius_basis'].set('Inner radius' if c.beam_plate.bend_radius_basis=='inner' else 'Outer radius'); self.vars['cc_radius_basis'].set('Inner radius' if c.crush_can.corner_radius_basis=='inner' else 'Outer radius')
        self.vars['split'].set('Top / Bottom' if c.crush_can.split=='top_bottom' else 'Inner / Outer'); self._split_changed(); self.vars['larger'].set(c.crush_can.larger_half.title())
        self.vars['rear_arch'].set('Back plate' if c.rear_mount.architecture=='back_plate' else 'Rail bolted'); self.vars['front_mode'].set('Stop at contact' if c.front_interface.mode=='stop_at_contact' else 'Flow over')
        for k,v in [('flow_top',c.front_interface.flow_top),('flow_bottom',c.front_interface.flow_bottom),('flow_inner',c.front_interface.flow_inner),('flow_outer',c.front_interface.flow_outer),('bead_enabled',c.beads.enabled)]:self.vars[k].set(v)
        self.vars['bead_sidewall_sense'].set('Outward' if c.beads.sidewall_sense=='outward' else 'Inward')
        self.vars['bead_depth_mode'].set('Uniform' if c.beads.depth_mode=='uniform' else 'Face-specific')
        self.bead_overrides=[BeadSetOverride(**vars(x)) for x in c.beads.set_overrides]
        self._update_bead_override_summary()
        self.refresh_all()

    def validate_now(self):
        try:c=self.collect(); r=validate_config(c); txt=['CONFIGURATION REVIEW','']
        except Exception as e:txt=['INPUT ERROR','',str(e)]; r=None
        if r:
            pri,pro=(c.beam_plate.bend_radii() if c.beam_plate.enabled else (None,None)); cri,cro=c.crush_can.corner_radii()
            txt += [f'Beam: {self.vars["beam_type"].get()}',f'Sweep source: {self.vars["beam_sweep_mode"].get()}',f'Beam front-face centre Z: {c.beam.front_face_center_z:.2f} mm',f'Beam plate: {"Yes" if c.beam_plate.enabled else "No"}']
            if c.beam_plate.enabled:txt += [f'Beam-plate radii: Ri={pri:.3f} mm, Ro={pro:.3f} mm',f'Slip gaps: outer={c.beam_plate.slip_plane_gap_outer:.3f} mm, inner={c.beam_plate.slip_plane_gap_inner:.3f} mm']
            txt += [f'Crush-can radii: Ri={cri:.3f} mm, Ro={cro:.3f} mm',f'Can split: {c.crush_can.split}',f'Rear architecture: {c.rear_mount.architecture}',f'Front mode: {c.front_interface.mode}']
            if c.beads.enabled:
                txt += [f'Beads: outer-wall anchored layout; width={c.beads.width:.2f} mm; front/inter-bead flat X land={c.beads.clear_spacing_x:.2f} mm; flat Z land={c.beads.flat_land_z:.2f} mm',f'Bead depth mode: {c.beads.depth_mode}; sidewall sense={c.beads.sidewall_sense}; set overrides={len(c.beads.set_overrides)}']
            else: txt += ['Beads: disabled']
            txt += ['']
            txt += ['ERRORS:']+(['  None'] if not r.errors else ['  X '+x for x in r.errors])+['','WARNINGS:']+(['  None'] if not r.warnings else ['  ! '+x for x in r.warnings])+['','NOTES:']+(['  None'] if not r.notes else ['  - '+x for x in r.notes])
        if hasattr(self,'review'):
            self.review.configure(state='normal'); self.review.delete('1.0','end'); self.review.insert('1.0','\n'.join(txt)); self.review.configure(state='disabled')
        self.status.set('Validation passed' if r and r.ok else 'Validation needs attention'); return r

    def radius_approval(self,requested,maximum,revised,limiting):
        return messagebox.askyesno('Revise transition radius?',f'Requested: {requested:.2f} mm\nMaximum conservative: {maximum:.2f} mm\nProposed: {revised:.2f} mm\nLimiting: {", ".join(limiting)}\n\nProceed?')

    def generate(self):
        try:
            c=self.collect(); r=validate_config(c)
            if not r.ok:messagebox.showerror('Cannot generate','\n'.join(r.errors));return
            out=filedialog.askdirectory(title='Choose CMS output folder')
            if not out:return
            self.status.set('Generating geometry...'); self.update_idletasks()
            res=build_cms(c,self.radius_approval); paths=export_result(res,c,out); self.last_result=res
            msg=f'CMS generated successfully.\n\nCan length: {res.derived["can_length"]:.2f} mm\nAttachment-plane centre X: {res.derived["contact_x"]:.2f} mm\nAttachment angle: {res.derived["front_attachment_plane"]["angle_deg"]:.3f} deg'
            if c.beads.enabled:
                msg += f'\nCalculated bead sets: {res.derived["bead_layout_lh"]["count"]} (layout only; embossment CAD not yet applied)'
            msg += f'\nFiles: {len(paths)}'
            if res.warnings:msg+='\n\nWarnings:\n- '+'\n- '.join(res.warnings)
            messagebox.showinfo('CMS generated',msg); self.status.set('Generation complete')
        except Exception as e:self.status.set('Generation failed');messagebox.showerror('Generation failed',f'{e}\n\n{traceback.format_exc(limit=6)}')

    def save_preset(self):
        try:
            c=self.collect(); p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')]); c.save_json(p) if p else None
        except Exception as e:messagebox.showerror('Save preset',str(e))
    def load_preset(self):
        try:
            p=filedialog.askopenfilename(filetypes=[('JSON','*.json')]);
            if p:self.apply_config(CMSConfig.load_json(p))
        except Exception as e:messagebox.showerror('Load preset',str(e))


if __name__=='__main__':CMSApp().mainloop()
