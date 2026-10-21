# Genera el Calabozo ampliado: conserva intacto el mapa actual (centro) y genera alrededor
# con los edificios de Overture y las calles/lugares del OSM, con las mismas reglas del original.
import json, sys, math, base64, random, unicodedata, collections
import numpy as np

M = sys.argv[1]
OUT = sys.argv[2]
d = json.load(open(M + '/D_old.json'))
o = json.load(open(M + '/osm.json'))
xf = json.load(open(M + '/xfa.json'))
gj = json.load(open('/Users/angel/Downloads/calabozo_edificios.geojson'))
random.seed(20261017)

OW, OH = d['w'], d['h']
X0, Y0, X1, Y1 = 0, -500, 2150, 950             # extensión nueva, en coordenadas del mapa ACTUAL (hacia la represa)
W, H = X1 - X0, Y1 - Y0
OX, OY = -X0, -Y0                              # dónde cae (0,0) del mapa viejo en el nuevo
OLD = np.zeros((H, W), bool); OLD[OY:OY + OH, OX:OX + OW] = True
p = xf['p']; lat0, lon0 = xf['lat0'], xf['lon0']
def T(lat, lon):
    u = (lon - lon0) * math.cos(math.radians(lat0)) * 111320; v = -(lat - lat0) * 110574
    return p[0] * u + p[1] * v + p[4] + 270 + OX, p[2] * u + p[3] * v + p[5] + 40 + OY
nodes = o['nodes']

G = np.zeros((H, W), np.uint8)                 # 0 = monte
G[OY:OY + OH, OX:OX + OW] = np.frombuffer(base64.b64decode(d['g']), np.uint8).reshape(OH, OW)
def inside(x, y): return 0 <= x < W and 0 <= y < H
def put(x, y, k, force=False):
    if inside(x, y) and (force or not OLD[y, x]): G[y, x] = k

# ---------- polígonos (relleno por líneas)
def fill_poly(pts, k, only=None):
    ys = [q[1] for q in pts]; y0 = max(0, int(min(ys))); y1 = min(H - 1, int(max(ys)) + 1)
    n = len(pts)
    for y in range(y0, y1 + 1):
        yc = y + 0.5; xs = []
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            if (ay <= yc < by) or (by <= yc < ay): xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(max(0, int(math.ceil(xs[i] - 0.5))), min(W - 1, int(xs[i + 1] - 0.5)) + 1):
                if OLD[y, x]: continue
                if only is None or G[y, x] in only: G[y, x] = k

def line_raster(pts, w, k, force_old=False):
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = max(1, int(math.hypot(bx - ax, by - ay) * 2))
        r = w / 2
        for s in range(L + 1):
            x = ax + (bx - ax) * s / L; y = ay + (by - ay) * s / L
            for yy in range(int(math.floor(y - r + 0.5)), int(math.floor(y + r - 0.5)) + 1):
                for xx in range(int(math.floor(x - r + 0.5)), int(math.floor(x + r - 0.5)) + 1):
                    put(xx, yy, k, force_old)

ways = o['ways']
def wpts(nd): return [T(*nodes[r]) for r in nd if r in nodes]

# ---------- 1) zona urbana: alrededor de edificios → solar (1); lejos → monte (0)
polys = []
BLD = np.zeros((H, W), bool)
for f in gj['features']:
    g = f['geometry']; ring = g['coordinates'][0] if g['type'] == 'Polygon' else g['coordinates'][0][0]
    pts = [T(lat, lon) for lon, lat in ring]
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    r = [int(round(min(xs))), int(round(min(ys))), int(round(max(xs))), int(round(max(ys)))]
    if r[2] - r[0] < 1 or r[3] - r[1] < 1 or r[2] < 0 or r[3] < 0 or r[0] >= W or r[1] >= H: continue
    polys.append(r); BLD[max(0, r[1]):min(H, r[3]), max(0, r[0]):min(W, r[2])] = True
urban = BLD.copy()
for _ in range(7):
    n = urban.copy(); n[1:] |= urban[:-1]; n[:-1] |= urban[1:]; n[:, 1:] |= urban[:, :-1]; n[:, :-1] |= urban[:, 1:]; urban = n
G[urban & ~OLD] = 1

# ---------- 2) usos del suelo y agua
LAND = {('landuse', 'grass'): 2, ('landuse', 'meadow'): 13, ('natural', 'wetland'): 13, ('landuse', 'cemetery'): 12, ('amenity', 'grave_yard'): 12,
        ('amenity', 'parking'): 10, ('landuse', 'industrial'): 10, ('leisure', 'pitch'): 2, ('leisure', 'park'): 11, ('natural', 'wood'): 11,
        ('landuse', 'farmland'): 0, ('natural', 'water'): 8, ('waterway', 'riverbank'): 8, ('landuse', 'reservoir'): 8, ('leisure', 'swimming_pool'): 8}
PLAZAS = []
for wid, t, nd in ways:
    if len(nd) < 4 or nd[0] != nd[-1]: continue
    k = None
    for kv, v in LAND.items():
        if t.get(kv[0]) == kv[1]: k = v
    nm = t.get('name', '')
    if t.get('leisure') == 'park' and ('plaza' in nm.lower()): k = 'plaza'
    if k is None: continue
    pts = wpts(nd)
    if k == 'plaza': PLAZAS.append((pts, nm)); continue
    fill_poly(pts, k)
WATERW = {'river': 5, 'canal': 3, 'stream': 2}  # sin acequias: cruzan manzanas y bloquean el paso
for wid, t, nd in ways:
    w = WATERW.get(t.get('waterway'))
    if w: line_raster(wpts(nd), w, 8)

# ---------- 3) calles: casi rectas → se enderezan sobre el hueco real entre manzanas (como el original)
HW = {'residential': (4.0, 0), 'living_street': (4.0, 0), 'unclassified': (4.0, 0), 'tertiary': (4.0, 0), 'tertiary_link': (4.0, 0),
      'secondary': (6.0, 0), 'secondary_link': (4.0, 0), 'primary': (6.0, 0), 'primary_link': (4.0, 0), 'trunk': (6.0, 0), 'trunk_link': (4.0, 0),
      'service': (3.5, 0), 'track': (3.5, 1), 'pedestrian': (4.0, 2)}
names = list(d['names']); NI = {n: i for i, n in enumerate(names)}
oldlines = [[l[0] + OX, l[1] + OY, l[2] + OX, l[3] + OY] + l[4:] for l in d['lines']]
def occ_band(o_, c, a, b, w):
    a, b = int(max(0, a)), int(min((W if o_ == 'H' else H), b))
    lo, hi = int(round(c - w / 2 - 1)), int(round(c + w / 2 + 1))
    if o_ == 'H': sub = BLD[max(0, lo):max(0, hi), a:b]
    else: sub = BLD[a:b, max(0, lo):max(0, hi)]
    return sub.sum() / max(1, (b - a))
def snap_c(o_, c, a, b, w):
    # si continúa una calle del centro, usa su misma línea
    for l in oldlines:
        lo = 'H' if abs(l[1] - l[3]) < 0.01 else ('V' if abs(l[0] - l[2]) < 0.01 else 'D')
        if lo != o_: continue
        lc = l[1] if o_ == 'H' else l[0]
        la, lb = (min(l[0], l[2]), max(l[0], l[2])) if o_ == 'H' else (min(l[1], l[3]), max(l[1], l[3]))
        if abs(lc - c) < 9 and la - 6 <= b and lb + 6 >= a: return lc
    best, bc = occ_band(o_, c, a, b, w), c
    for dc in np.arange(-8, 8.01, 0.5):
        s = occ_band(o_, c + dc, a, b, w) + abs(dc) * 0.02
        if s < best - 0.05: best, bc = s, c + dc
    return bc
newlines = []; roadsegs = []
for wid, t, nd in ways:
    hw = t.get('highway'); spec = HW.get(hw)
    if not spec: continue
    w, kind = spec; pts = wpts(nd); nm = t.get('name')
    if len(pts) < 2: continue
    if not any(inside(int(x), int(y)) and not OLD[int(y), int(x)] for x, y in pts): continue
    ni = -1
    if nm:
        if nm not in NI: NI[nm] = len(names); names.append(nm)
        ni = NI[nm]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ang = math.degrees(math.atan2(by - ay, bx - ax)) % 180
        if min(ang, 180 - ang) < 13: o_ = 'H'
        elif abs(ang - 90) < 13: o_ = 'V'
        else: o_ = 'D'
        if o_ == 'H':
            c = snap_c('H', (ay + by) / 2, min(ax, bx), max(ax, bx), w); seg = [ax, c, bx, c]
        elif o_ == 'V':
            c = snap_c('V', (ax + bx) / 2, min(ay, by), max(ay, by), w); seg = [c, ay, c, by]
        else: seg = [ax, ay, bx, by]
        roadsegs.append((seg, w, kind, o_)); newlines.append(seg + [w, ni, kind])
# dibujar: asfalto (3), tierra (5) o peatonal (9); en las esquinas, un cuadrado para que no queden escalones
for seg, w, kind, o_ in roadsegs:
    k = 3 if kind == 0 else (5 if kind == 1 else 9)
    line_raster([(seg[0], seg[1]), (seg[2], seg[3])], w, k)
    for (x, y) in ((seg[0], seg[1]), (seg[2], seg[3])):
        r = w / 2
        for yy in range(int(math.floor(y - r + 0.5)), int(math.floor(y + r - 0.5)) + 1):
            for xx in range(int(math.floor(x - r + 0.5)), int(math.floor(x + r - 0.5)) + 1): put(xx, yy, k)
# aceras: una casilla alrededor del asfalto
road = (G == 3)
side = np.zeros_like(road); side[1:] |= road[:-1]; side[:-1] |= road[1:]; side[:, 1:] |= road[:, :-1]; side[:, :-1] |= road[:, 1:]
side &= ~road & ~OLD & ~np.isin(G, [8, 5, 9])
G[side] = 4

# ---------- 4) plazas del OSM: adoquín con cuatro jardines, como la Plaza Bolívar
for pts, nm in PLAZAS:
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    bx0, by0, bx1, by1 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
    if bx1 - bx0 < 8 or by1 - by0 < 8: continue
    fill_poly(pts, 6, only={0, 1, 2, 11, 13, 10})
    mx, my = (bx0 + bx1) // 2, (by0 + by1) // 2; gw, gh = max(2, (bx1 - bx0) // 2 - 4), max(2, (by1 - by0) // 2 - 4)
    for (qx, qy) in ((bx0 + 2, by0 + 2), (mx + 2, by0 + 2), (bx0 + 2, my + 2), (mx + 2, my + 2)):
        for yy in range(qy, qy + gh):
            for xx in range(qx, qx + gw):
                if inside(xx, yy) and G[yy, xx] == 6 and not OLD[yy, xx]: G[yy, xx] = 2

# ---------- 5) edificios: los del centro se copian; fuera, los de Overture recortados contra calles
B = [[b[0] + OX, b[1] + OY] + b[2:] for b in d['b']]
OCC = np.zeros((H, W), bool)
for b in B: OCC[b[1]:b[1] + b[3], b[0]:b[0] + b[2]] = True
SIGNS = sorted(set(b[10] for b in d['b'] if b[4] == 'tienda' and len(b) > 10 and b[10] and b[10].isupper()))
BAD = np.isin(G, [3, 4, 5, 8, 9, 6])
newb = []
for r in sorted(polys, key=lambda r: -(r[2] - r[0]) * (r[3] - r[1])):
    x0, y0, x1, y1 = max(0, r[0]), max(0, r[1]), min(W, r[2]), min(H, r[3])
    if (x1 - x0) > 44 or (y1 - y0) > 44: continue
    if OLD[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2].any(): continue
    for _ in range(4):   # recortar bordes que pisan calle o acera
        if x1 - x0 < 2 or y1 - y0 < 2: break
        if BAD[y0, x0:x1].any(): y0 += 1
        if BAD[y1 - 1, x0:x1].any(): y1 -= 1
        if BAD[y0:y1, x0].any(): x0 += 1
        if BAD[y0:y1, x1 - 1].any(): x1 -= 1
    if x1 - x0 < 2 or y1 - y0 < 2 or BAD[y0:y1, x0:x1].any(): continue
    if OCC[y0:y1, x0:x1].mean() > 0.3: continue
    OCC[y0:y1, x0:x1] = True; G[y0:y1, x0:x1] = np.where(G[y0:y1, x0:x1] == 0, 1, G[y0:y1, x0:x1])
    # fachada hacia la calle más cercana
    dist = {}
    for f_, (sx, sy, ex, ey, dx, dy) in {'N': (x0, y0, x1, y0, 0, -1), 'S': (x0, y1 - 1, x1, y1 - 1, 0, 1), 'O': (x0, y0, x0, y1, -1, 0), 'E': (x1 - 1, y0, x1 - 1, y1, 1, 0)}.items():
        best = 99
        for s in range(1, 14):
            xs_ = range(sx, ex if ex > sx else sx + 1); ys_ = range(sy, ey if ey > sy else sy + 1)
            hit = False
            for xx in (xs_ if dy else [sx]):
                for yy in (ys_ if dx else [sy]):
                    X, Y = xx + dx * s, yy + dy * s
                    if inside(X, Y) and G[Y, X] in (3, 4, 5): hit = True; break
                if hit: break
            if hit: best = s; break
        dist[f_] = best
    face = min(dist, key=lambda k: (dist[k], 'SNOE'.index(k)))
    area = (x1 - x0) * (y1 - y0)
    rec = [x0, y0, x1 - x0, y1 - y0, 'casa', face, random.choices(['teja', 'zinc', 'plata'], [40, 35, 25])[0], random.randrange(10), 2 if (area > 160 and random.random() < 0.3) else 1, random.randrange(65536)]
    if dist[face] <= 2 and random.random() < 0.11 and SIGNS: rec[4] = 'tienda'; rec.append(random.choice(SIGNS))
    newb.append(rec)

# ---------- 6) lugares con nombre del OSM (fuera del centro)
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').strip()
oldnames = set(norm(q[2]) for q in d['pois'])
def kind_of(t):
    a, sh, le, to = t.get('amenity'), t.get('shop'), t.get('leisure'), t.get('tourism')
    if a in ('school', 'college', 'university', 'kindergarten'): return 'escuela'
    if a in ('hospital', 'clinic', 'doctors', 'dentist'): return 'clinica'
    if a == 'pharmacy': return 'farmacia'
    if a in ('bank', 'atm', 'bureau_de_change'): return 'banco'
    if a == 'place_of_worship': return 'iglesia'
    if a in ('restaurant', 'fast_food', 'cafe', 'bar', 'ice_cream'): return 'comida'
    if a == 'police': return 'policia'
    if a == 'townhall': return 'alcaldia'
    if a == 'marketplace': return 'mercado'
    if a in ('theatre', 'arts_centre', 'library', 'community_centre', 'cinema'): return 'cultura'
    if sh == 'bakery': return 'panaderia'
    if sh: return 'tienda'
    if to in ('hotel', 'guest_house', 'motel'): return 'hotel'
    if le == 'park': return 'parque'
    if le in ('pitch', 'stadium', 'sports_centre'): return 'cancha'
    return None
newpois = []
cands = [(t, T(*ll)) for name, ll, t in o['named']]
for wid, t, nd in ways:
    if 'name' in t and 'highway' not in t and 'waterway' not in t:
        pts = wpts(nd)
        if pts: cands.append((t, (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))))
seenp = set()
for t, (x, y) in cands:
    nm = t.get('name'); k = kind_of(t)
    if not nm or not k or not inside(int(x), int(y)) or OLD[int(y), int(x)]: continue
    if norm(nm) in oldnames or norm(nm) in seenp: continue
    if 'plaza' in nm.lower() and k == 'parque': k = 'plaza'
    seenp.add(norm(nm)); newpois.append([round(x, 1), round(y, 1), nm, k])
    if k in ('parque', 'plaza', 'cancha'): continue
    best = None; bd = 6
    for b in newb:
        cx, cy = min(max(x, b[0]), b[0] + b[2]), min(max(y, b[1]), b[1] + b[3]); dd = math.hypot(x - cx, y - cy)
        if dd < bd: bd, best = dd, b
    if best is not None and best[4] in ('casa', 'tienda'):
        best[4] = k
        if len(best) > 10: best[10] = nm
        else: best.append(nm)

# ---------- 7) objetos: árboles en solares y parques, postes en aceras, tanques, tendederos, gallinas
props = [[q[0], q[1] + OY if False else q[1], q[2]] for q in []]
props = [[pp[0], pp[1] + OX, pp[2] + OY] for pp in d['p']]
nearB = OCC.copy(); n_ = nearB.copy(); n_[1:] |= nearB[:-1]; n_[:-1] |= nearB[1:]; n_[:, 1:] |= nearB[:, :-1]; n_[:, :-1] |= nearB[:, 1:]; nearB = n_
nearRoad = np.isin(G, [3, 4, 5, 9]); n_ = nearRoad.copy(); n_[1:] |= nearRoad[:-1]; n_[:-1] |= nearRoad[1:]; n_[:, 1:] |= nearRoad[:, :-1]; n_[:, :-1] |= nearRoad[:, 1:]; nearRoad = n_
taken = OCC.copy()
for y in range(1, H - 1):
    for x in range(1, W - 1):
        if OLD[y, x] or taken[y, x]: continue
        g = G[y, x]; r = random.random()
        if g == 1 and not nearB[y, x] and not nearRoad[y, x]:
            if r < 0.011: props.append([random.choices(['mango', 'samán', 'palma'], [62, 20, 18])[0], x, y]); taken[y - 1:y + 2, x - 1:x + 2] = True
            elif r < 0.0118: props.append([random.choice(['tanque', 'cuerda', 'gallinas']), x, y]); taken[y, x] = True
        elif g in (2, 11) and not nearRoad[y, x] and r < 0.03:
            props.append([random.choice(['samán', 'mango', 'palma']), x, y]); taken[y - 1:y + 2, x - 1:x + 2] = True
        elif g == 4 and (x * 7 + y * 13) % 29 == 0 and r < 0.6:
            props.append(['poste', x, y]); taken[y, x] = True

# ---------- 8) salida
lines = oldlines + [[round(v, 1) for v in l[:4]] + l[4:] for l in newlines]
D2 = {'w': W, 'h': H, 'mpt': d['mpt'], 'g': base64.b64encode(G.tobytes()).decode(), 'b': B + newb, 'p': props,
      'pois': [[q[0] + OX, q[1] + OY] + q[2:] for q in d['pois']] + newpois, 'lines': lines, 'names': names, 'walls': d['walls'],
      'spawn': [d['spawn'][0] + OX, d['spawn'][1] + OY]}
json.dump(D2, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('mapa', W, 'x', H, '| edificios', len(B), '+', len(newb), '| lugares nuevos', len(newpois), '| calles nuevas', len(newlines), '| objetos', len(props), '| plazas OSM', len(PLAZAS))
print('suelo', collections.Counter(G.ravel().tolist()).most_common())
