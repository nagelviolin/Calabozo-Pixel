# Detalla la represa de Calabozo sobre el mapa ampliado: cruces peatonales, jardín del letrero, estacionamiento con rayas,
# quiosco de techo azul, árboles, bancos, postes y carros. Entrada: D_ext.json  Salida: D_presa.json
import json, base64, math, random
import numpy as np
random.seed(2026102101)
D = json.load(open('D_ext.json')); W, H = D['w'], D['h']
G = np.frombuffer(base64.b64decode(D['g']), np.uint8).reshape(H, W).copy()
def inside(x, y): return 0 <= x < W and 0 <= y < H
OKG = {0, 1, 2, 10, 11, 12, 13}                        # solo se pinta sobre terreno libre (no calles, no agua)
def setk(x, y, k, force=False):
    if inside(x, y) and (force or int(G[y, x]) in OKG): G[y, x] = k

# ---- dimensiones de la presa (coordenadas del mapa)
DX, DY0, DY1 = 1874, 114, 178                          # eje de la carretera sobre la presa, y tramo de compuertas
# ---- cruces peatonales en los dos extremos de la presa (cebra: casillas blancas alternas)
for y in (111, 112, 180, 181):
    for x in range(1871, 1877):
        if x % 2 == 0 and int(G[y, x]) == 3: G[y, x] = 14

# ---- jardín con el letrero «♥ CALABOZO»
GX, GY, RX, RY = 1927, 238, 22, 17
for y in range(GY - RY - 3, GY + RY + 4):
    for x in range(GX - RX - 3, GX + RX + 4):
        e = ((x - GX) / RX) ** 2 + ((y - GY) / RY) ** 2
        if e <= 0.66: setk(x, y, 2)                    # césped
        elif e <= 0.92: setk(x, y, 4)                  # camino de concreto en anillo
        elif e <= 1.0: setk(x, y, 2)
for x in range(1883, GX - RX + 2):                     # camino desde la acera de la carretera hasta el jardín
    for y in (GY - 1, GY, GY + 1): setk(x, y, 4)
for y in range(GY + RY - 2, GY + RY + 10):             # y otro hacia el estacionamiento
    for x in (GX - 1, GX, GX + 1): setk(x, y, 4)
for x in range(GX + RX - 2, 1957):
    for y in (GY - 1, GY, GY + 1): setk(x, y, 4)
for dy in range(-3, 4):                                # medio óvalo de flores alrededor del letrero (adoquín claro)
    for dx in range(-9, 10):
        if (dx / 9) ** 2 + (dy / 3.2) ** 2 <= 1 and abs(dx) < 8: setk(GX + dx, GY + 7 + dy, 4)

# ---- estacionamiento grande: dos pasillos anchos (donde la gente se reúne), cuatro filas de puestos con rayas
LX0, LX1, LY0, LY1 = 1956, 2036, 208, 243
BAYROWS = [(208, 211), (222, 225), (226, 229), (240, 243)]
for y in range(LY0 - 1, LY1 + 2):
    for x in range(LX0 - 1, LX1 + 2):
        edge = x in (LX0 - 1, LX1 + 1) or y in (LY0 - 1, LY1 + 1)
        setk(x, y, 4 if edge else 3)
for (a, b) in BAYROWS:
    for y in range(a, b + 1):
        for x in range(LX0, LX1 + 1):
            if (x - LX0) % 2 == 0 and inside(x, y) and int(G[y, x]) == 3: G[y, x] = 15

# ---- quiosco / pabellón de techo azul detrás del estacionamiento
B = D['b']
B.append([1996, 252, 34, 11, 'comida', 'N', 'azul', 4, 1, 40111, 'KIOSCO LA REPRESA'])
for y in range(251, 266):
    for x in range(1992, 2034):
        if int(G[y, x]) in OKG: G[y, x] = 4 if y in (251, 264) or x in (1992, 2033) else 1
# ---- caminos de acceso al quiosco
for y in range(LY1 + 2, 252):
    for x in (1990, 1991, 1992): setk(x, y, 4)

# ---- limpiar objetos que ya había en estas zonas
def in_zone(x, y):
    if LX0 - 3 <= x <= LX1 + 3 and LY0 - 3 <= y <= LY1 + 3: return True
    if 1990 <= x <= 2036 and 249 <= y <= 268: return True
    if ((x - GX) / (RX + 3)) ** 2 + ((y - GY) / (RY + 3)) ** 2 <= 1.0: return True
    if 1871 <= x <= 1884 and DY0 - 4 <= y <= DY1 + 6: return True
    return False
P = [q for q in D['p'] if not in_zone(q[1], q[2])]
taken = set()
def prop(k, x, y):
    if not inside(x, y) or (x, y) in taken: return False
    taken.add((x, y)); P.append([k, x, y]); return True
# carros en los puestos (algo más de la mitad ocupados)
for (a, b) in BAYROWS:
    for x in range(LX0 + 1, LX1, 2):
        if random.random() < 0.3: prop('carro', x, (a + b) // 2)
# árboles de sombra: borde del estacionamiento y del jardín
for x in range(LX0 + 3, LX1, 9): prop(random.choice(['samán', 'mango']), x, LY0 - 3); prop(random.choice(['samán', 'palma']), x + 3, LY1 + 3)
for y in range(LY0 + 4, LY1, 9): prop(random.choice(['samán', 'mango']), LX0 - 3, y); prop(random.choice(['samán', 'mango']), LX1 + 3, y)
for a in range(0, 360, 28):
    x = int(round(GX + (RX + 2.5) * math.cos(math.radians(a)))); y = int(round(GY + (RY + 2.5) * math.sin(math.radians(a))))
    prop(random.choice(['samán', 'palma', 'mango']), x, y)
for x in (GX - 6, GX + 6, GX - 12, GX + 12): prop('palma', x, GY - 7)
# bancos y postes de luz: anillo del jardín, pasillos del estacionamiento y la carretera de la presa
for a in range(10, 360, 45):
    x = int(round(GX + (RX * 0.8) * math.cos(math.radians(a)))); y = int(round(GY + (RY * 0.8) * math.sin(math.radians(a))))
    prop('banco', x, y)
for a in range(0, 360, 36):
    x = int(round(GX + RX * 0.97 * math.cos(math.radians(a)))); y = int(round(GY + RY * 0.97 * math.sin(math.radians(a))))
    prop('poste', x, y)
for x in range(LX0 + 6, LX1, 16):
    prop('poste', x, 216); prop('poste', x, 235)
for y in range(DY0 + 4, DY1, 14):
    prop('poste', 1870, y); prop('poste', 1878, y)
for y in range(190, 262, 12): prop('poste', 1884, y)
D['p'] = P
# ---- metadatos y lugares
D['dam'] = {'x': DX, 'y0': DY0, 'y1': DY1, 'sign': [GX, GY + 7], 'lot': [LX0, LY0, LX1, LY1], 'kiosk': [1996, 252, 34, 11]}
D['pois'] += [[DX + 0.5, 146.0, 'Compuertas de la Represa de Calabozo', 'parque'], [GX + 0.5, GY + 0.5, 'Letrero ♥ CALABOZO', 'parque'], [2013.0, 258.0, 'Kiosco La Represa', 'comida']]
D['g'] = base64.b64encode(G.tobytes()).decode()
json.dump(D, open('D_presa.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('ok | carros', sum(1 for q in P if q[0] == 'carro'), '| objetos', len(P), '| edificios', len(B))
