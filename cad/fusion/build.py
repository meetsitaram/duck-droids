"""Build milli in Fusion from spec/robot.json and spec/parts.json (the scripts are the source of truth: never hand-edit
the document; change spec/robot.py, rerun the checks and tools/export_prints.py, rebuild).

One short job per MCP call (long calls time out and freeze Fusion; CDX-3R lessons 78-79):
  build.new_document()          a new Z-up design document with no timeline: a full model in about 80 features' time, not 1,800
  build.link('trunk')           build one link as its own component, at the zero pose: one body per printed part, with its holes
                                and pockets, ready to print; each bought part its own body; every screw
  build.parametric()            after the last link: turn on the timeline, which joints need
  build.joints()                as-built revolute joints at the spec origins and limits
  build.verify()                every printed body against the volume tools/export_prints.py exported
  build.status()                components, body counts, unhealthy features, duplicates
  build.pose({'L_elbow': -1})   set joint angles (rad); missing joints go to 0
  build.show(skins=False)       hide the skins to see the internals (and back)
  build.export_stl(folder)      one STL per link at the zero pose, for the URDF and the mesh checks

Frame: Fusion world = spec world (Z up, X forward, Y left); the API works in cm, the spec in m (figlib converts).
"""
import json
import os
import time

import adsk.core
import adsk.fusion

import figlib as F

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = 'duck-droids'
GLOSS, ALU, LENS = '#08090B', '#9EA3A8', '#0A1420'


def app():
    return adsk.core.Application.get()


def design():
    return adsk.fusion.Design.cast(app().activeProduct)


SPEC = 'robot.json'


def use(name):
    """Which spec to build: build.use('robot_big.json'), once after importing this."""
    global SPEC
    SPEC = name
    return json.load(open(os.path.join(REPO, 'spec', SPEC), encoding='utf-8'))['root']


def spec():
    return json.load(open(os.path.join(REPO, 'spec', SPEC), encoding='utf-8'))


def finish(g):
    return 'gloss' if g['color'] in (GLOSS, LENS) else 'metal' if g['color'] == ALU else 'matte'


def occurrences():
    return {o.component.name: o for o in design().rootComponent.occurrences}


def new_document():
    doc = app().documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d = design()
    d.designType = adsk.fusion.DesignTypes.DirectDesignType   # no timeline while the bodies go in (parametric() turns it on: joints need one)
    return f'new document, orientation {app().preferences.generalPreferences.defaultModelingOrientation} (1 = Z up)'


def parametric():
    d = design()
    d.designType = adsk.fusion.DesignTypes.ParametricDesignType
    return f'parametric, timeline {d.timeline.count}'


def _variant_file(stem):
    """robot.json -> parts.json; robot_dynamixel.json -> parts_dynamixel.json."""
    return SPEC.replace('robot', stem, 1)


def parts_spec():
    return json.load(open(os.path.join(REPO, 'spec', _variant_file('parts')), encoding='utf-8'))


def link(name):
    """The link's component: its geoms, then each printed part joined, hollowed, holed and pocketed."""
    t = time.time()
    s = spec()
    d = design()
    root = d.rootComponent
    P_ = parts_spec()
    ps = {n: p for n, p in P_['parts'].items() if p['link'] == name}
    in_part = {g: n for n, p in ps.items() for g in p['geoms']}
    for o in list(root.occurrences):                     # rebuild: remove the old copy first (no "name (1)")
        if o.component.name == name or o.component.name.startswith(name + ' ('):
            if o.isGrounded:
                o.isGrounded = False                     # (a grounded occurrence refuses to go)
            o.deleteMe()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    b = F.Builder(comp)
    geoms = s['links'][name]['geoms']
    made = {}
    real = {n for p in P_['parts'].values() for n in p['geoms']}
    closer = {n: v for p in ps.values() for n, v in p.get('dense', {}).items()}
    for g in geoms:
        if g['role'] == 'cut':
            continue
        if g['role'] == 'decal' and 'fast' not in g and g['name'] not in real:
            continue                                     # a picture of a thing, not a thing: nothing to buy or print
        body = b.build(dict(g, sections=closer[g['name']]) if g['name'] in closer else g)
        body.name = g['name']
        body.appearance = F.appearance(d, g['color'], finish(g))
        made[g['name']] = body
    for g in geoms:                                      # cuts: windows through the bodies built above
        if g['role'] == 'cut':
            b.cut(b.build(g), [comp.bRepBodies.itemByName(n) for n in g['targets'] if comp.bRepBodies.itemByName(n)], g['name'])
    problems = []
    for pn, p in ps.items():                             # what you print: hollow first, as the next step cuts by these shapes
        for gn, inner in p.get('inner', {}).items():
            bd = comp.bRepBodies.itemByName(gn)
            b.cut_from(bd, b.build(dict(inner, name=f'{gn} hollow')))
    for pn, p in ps.items():                             # where a part gives way to its neighbour's exact shape
        for k in p['pockets']:
            if 'exact' not in k:
                continue
            tool = comp.bRepBodies.itemByName(k['exact'])
            for n in p['geoms']:
                ci = b.f.combineFeatures.createInput(comp.bRepBodies.itemByName(n), F.coll([tool]))
                ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                ci.isKeepToolBodies = True
                try:
                    b.f.combineFeatures.add(ci)
                except RuntimeError:                     # no overlap with this piece of the part
                    pass
    for pn, p in ps.items():                             # one body, with its screw holes and pockets
        bodies = [comp.bRepBodies.itemByName(n) for n in p['geoms']]
        whole = b.join(bodies, pn)
        whole.name = pn
        for k in p['pockets']:
            if 'exact' in k:
                continue
            k = dict(k, name=f"{pn} pocket")
            try:
                b.cut_from(whole, b.build(k))
            except RuntimeError as e:
                problems.append(f'{pn} pocket: {e}')
        for h in p['holes']:
            try:
                b.cut_from(whole, b.bore(tuple(h['p']), tuple(h['d']), h['r'], h['a'], h['b'], f'{pn} hole'))
            except RuntimeError as e:
                problems.append(f"{pn} hole {h['screw']}: {e}")
        if pn == 'hood':                                 # one body, in two colours: the orange band at its rim
            zcut = next(g['c'][2] - g['size'][2] / 2 for g in geoms if g['name'] == 'above the bill') * 100
            orange = F.appearance(d, next(g['color'] for g in geoms if g['name'] == 'upper bill'), 'matte')
            for i in range(whole.faces.count):
                if whole.faces.item(i).centroid.z < zcut:
                    whole.faces.item(i).appearance = orange
    if name == s['root']:
        occ.isGrounded = True
    else:
        occ.isGroundToParent = False                     # new occurrences come in grounded (CDX-3R lesson 24)
    return f'{name}: {comp.bRepBodies.count} bodies, {len(ps)} printed parts, {time.time() - t:.1f} s' + (f'; PROBLEMS {problems[:6]}' if problems else '')


def parts(geoms):
    """The geoms that are bodies ('cut' geoms are removed from others and leave none)."""
    return [g for g in geoms if g['role'] != 'cut']


def links(names):
    return [link(n) for n in names]


def _joint_sketch(root):
    for i in range(root.sketches.count):
        if root.sketches.item(i).name == 'joint points':
            return root.sketches.item(i)
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = 'joint points'
    sk.isVisible = False
    return sk


def joints(only=None):
    t = time.time()
    s = spec()
    root = design().rootComponent
    occ = occurrences()
    sk = _joint_sketch(root)
    dirs = {'x': adsk.fusion.JointDirections.XAxisJointDirection,
            'y': adsk.fusion.JointDirections.YAxisJointDirection,
            'z': adsk.fusion.JointDirections.ZAxisJointDirection}
    out = []
    for j in s['joints']:
        if only and j['name'] not in only:
            continue
        old = root.asBuiltJoints.itemByName(j['name'])
        if old:
            old.deleteMe()
        sp = sk.sketchPoints.add(sk.modelToSketchSpace(F.P(j['origin'])))
        geo = adsk.fusion.JointGeometry.createByPoint(sp)
        ji = root.asBuiltJoints.createInput(occ[j['child']], occ[j['parent']], geo)
        ji.setAsRevoluteJointMotion(dirs[j['axis']])
        jt = root.asBuiltJoints.add(ji)
        jt.name = j['name']
        lim = adsk.fusion.RevoluteJointMotion.cast(jt.jointMotion).rotationLimits
        lim.isMinimumValueEnabled = True
        lim.minimumValue = j['lower']
        lim.isMaximumValueEnabled = True
        lim.maximumValue = j['upper']
        out.append(j['name'])
    return f'{len(out)} joints, {time.time() - t:.1f} s'


def pose(q):
    root = design().rootComponent
    for i in range(root.asBuiltJoints.count):
        jt = root.asBuiltJoints.item(i)
        adsk.fusion.RevoluteJointMotion.cast(jt.jointMotion).rotationValue = float(q.get(jt.name, 0.0))
    return f'posed {len(q)} joints'


def show(skins=True, internals=True):
    s = spec()
    role = {g['name']: g['role'] for l in s['links'].values() for g in l['geoms']}
    exposed = {g['name'] for l in s['links'].values() for g in l['geoms'] if g.get('exposed')}
    for j in s['joints']:
        if j['act'] and j['exposed']:
            exposed |= {f"{j['name']} flange"} if j['exposed'] == 'flange' else                 {f"{j['name']} actuator (buy) {j['act']}", f"{j['name']} flange"}
    n = 0
    for o in design().rootComponent.occurrences:
        for b in o.component.bRepBodies:
            b.isLightBulbOn = skins if role.get(b.name) in ('shell', 'decal') else (internals or b.name in exposed)
            n += 1
    return f'{n} bodies: skins {"on" if skins else "off"}, internals {"on" if internals else "off"}'


def verify():
    """Each printed body against the STL's volume: a pocket or hole that didn't cut, or a piece that didn't join, shows here."""
    P_ = parts_spec()
    occ = occurrences()
    out, bad = [], []
    for pn, p in P_['parts'].items():
        o = occ.get(p['link'])
        bodies = [o.component.bRepBodies.item(i) for i in range(o.component.bRepBodies.count)] if o else []
        b = next((x for x in bodies if x.name == pn), None)
        if b is None:
            bad.append(f'{pn}: no body')
            continue
        v = b.physicalProperties.volume
        e = abs(v - p['volume_cm3']) / p['volume_cm3']
        pieces = sum(1 for x in bodies if x.name.startswith(pn + ' ') and False)
        out.append((pn, round(v, 2), round(p['volume_cm3'], 2), round(e * 100, 1), b.isSolid))
        if e > 0.04 or not b.isSolid:
            bad.append(f"{pn}: Fusion {v:.2f} cm3, STL {p['volume_cm3']:.2f} ({e * 100:.1f} % off), solid {b.isSolid}")
    return dict(parts=len(out), worst=sorted(out, key=lambda r: -r[3])[:8], bad=bad)


def verify_points():
    """tools/verify_fusion.py: is each of its points inside the Fusion body? Written to reports/fusion_points.json."""
    t = time.time()
    data = json.load(open(os.path.join(REPO, 'spec', _variant_file('verify_points')), encoding='utf-8'))
    P_ = parts_spec()
    occ = occurrences()
    IN = adsk.fusion.PointContainment.PointInsidePointContainment
    out = {}
    for pn, v in data.items():
        c = occ[P_['parts'][pn]['link']].component
        body = next((c.bRepBodies.item(i) for i in range(c.bRepBodies.count) if c.bRepBodies.item(i).name == pn), None)
        if body is None:
            continue
        out[pn] = [1 if body.pointContainment(F.P(q)) == IN else 0 for q in v['pts']]
    json.dump(out, open(os.path.join(REPO, 'reports', _variant_file('fusion_points')), 'w', encoding='utf-8'))
    return f'{len(out)} parts, {time.time() - t:.1f} s'


def status():
    s = spec()
    d = design()
    occ = occurrences()
    rows, problems = [], []
    P_ = parts_spec()
    for name, l in s['links'].items():
        o = occ.get(name)
        if not o:
            problems.append(f'missing {name}')
            continue
        nb = o.component.bRepBodies.count
        real = {n for p in P_['parts'].values() for n in p['geoms']}
        nreal = [g for g in parts(l['geoms']) if not (g['role'] == 'decal' and 'fast' not in g and g['name'] not in real)]
        want = len(nreal) - sum(len(p['geoms']) - 1 for p in P_['parts'].values() if p['link'] == name)
        if nb != want:
            problems.append(f'{name}: {nb} bodies, spec has {want}')
        rows.append(f'{name}:{nb}')
    extra = [n for n in occ if n not in s['links']]
    if extra:
        problems.append(f'extra components {extra}')
    count = 0
    nj = 0
    if d.designType == adsk.fusion.DesignTypes.ParametricDesignType:    # no timeline, and no joints, until parametric()
        tl = d.timeline
        count = tl.count
        for i in range(tl.count):
            it = tl.item(i)
            if not it.isGroup and it.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
                problems.append(f'unhealthy: {it.name} {it.errorOrWarningMessage}')
        nj = d.rootComponent.asBuiltJoints.count
    return {'links': len(rows), 'joints': nj, 'timeline': count, 'problems': problems[:30]}


EXTENT_PER_CM = 1.0       # orthographic viewExtents per cm of visible height (calibrated by tools/compare.py)
VIEWS = {
    # name: (azimuth deg from the robot's front, towards its left; elevation deg), as the reference photos
    # '34' at 60 deg: the reveal frame's silhouette widths fit best there (rms 3 cm, 2026-10-31); at 40 deg every
    # width was 10 cm too wide and the legs read heavy
    'front': (0, 0), 'side': (90, 0), 'back': (180, 0), '34': (60, 8), 'hero': (40, 8),
}


def render(path, view='side', w=800, h=600, height_cm=190.0, target_z_cm=86.0):
    """Orthographic picture of the whole robot from one of VIEWS, saved as PNG (for tools/compare.py)."""
    import math
    az, el = (math.radians(v) for v in VIEWS[view])
    vp = app().activeViewport
    vp.visualStyle = adsk.core.VisualStyles.ShadedVisualStyle   # no edge lines: they made the model look busy
    cam = vp.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isSmoothTransition = False
    t = adsk.core.Point3D.create(0, 0, target_z_cm)
    d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
    cam.target = t
    cam.eye = adsk.core.Point3D.create(600 * d[0], 600 * d[1], target_z_cm + 600 * d[2])
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
    cam.viewExtents = height_cm * EXTENT_PER_CM
    vp.camera = cam
    vp.refresh()
    root = design().rootComponent
    root.isJointsFolderLightBulbOn = False
    root.isSketchFolderLightBulbOn = False
    root.isConstructionFolderLightBulbOn = False
    if os.path.exists(path):              # so 'written' means this save wrote it (an old file fooled the check)
        os.remove(path)
    ok = vp.saveAsImageFile(path, w, h)
    written = os.path.exists(path)
    src = os.path.join(os.path.dirname(path), 'replica_source.txt')   # tools/render_pose.py's label for compare.py
    if written and os.path.basename(path).startswith('replica_') and os.path.exists(src):
        os.remove(src)
    return f'{view}: {path} ({ok}, written: {written})'


def render_posed(q, shots):
    """render() for each (path, view, w, h, height_cm, target_z_cm) in shots, in pose q. While a moved joint's
    position is uncaptured, saveAsImageFile returns True and writes nothing (2026-10-31): capture it (a snapshot),
    render, then delete the snapshot and go back to the zero pose."""
    d = design()
    pose(q)
    snap = d.snapshots.add()
    out = [render(*s) for s in shots]
    snap.deleteMe()
    pose({})
    return out + [f'pending position after: {d.snapshots.hasPendingSnapshot}']


def export_stl(folder):
    t = time.time()
    os.makedirs(folder, exist_ok=True)
    em = design().exportManager
    out = []
    for name, o in occurrences().items():
        path = os.path.join(folder, f'{name}.stl')
        opt = em.createSTLExportOptions(o, path)
        opt.isBinaryFormat = True
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
        em.execute(opt)
        out.append(name)
    return f'{len(out)} STLs in {folder}, {time.time() - t:.1f} s'
