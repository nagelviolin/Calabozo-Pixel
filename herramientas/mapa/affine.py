import json,sys,math,base64,numpy as np
M=sys.argv[1]
d=json.load(open(M+'/D_old.json')); o=json.load(open(M+'/osm.json')); xf=json.load(open(M+'/xf.json'))
W,H=d['w'],d['h']; G=np.frombuffer(base64.b64decode(d['g']),dtype=np.uint8).reshape(H,W)
ROAD=np.isin(G,[3,5])
# distancia (en casillas) a la calle más cercana, hasta 12
DIST=np.full((H,W),12.0,np.float32); cur=ROAD.copy(); DIST[cur]=0
for k in range(1,12):
    n=cur.copy(); n[1:]|=cur[:-1]; n[:-1]|=cur[1:]; n[:,1:]|=cur[:,:-1]; n[:,:-1]|=cur[:,1:]
    DIST[n&~cur]=k; cur=n
lat0,lon0=xf['lat0'],xf['lon0']; nodes=o['nodes']
def P(lat,lon): return ((lon-lon0)*math.cos(math.radians(lat0))*111320, -(lat-lat0)*110574)
S=[]
for wid,t,nd in o['ways']:
    if t.get('highway') not in ('residential','tertiary','secondary','primary','unclassified','living_street','trunk'): continue
    pts=[P(*nodes[r]) for r in nd if r in nodes]
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        L=max(1,int(math.hypot(x2-x1,y2-y1)/2))
        for k in range(L): S.append((x1+(x2-x1)*k/L, y1+(y2-y1)*k/L))
S=np.array(S)
a=complex(*xf['a']); b=complex(*xf['b'])
p=np.array([a.real,-a.imag,a.imag,a.real,b.real,b.imag])  # x=p0*u+p1*v+p4 ; y=p2*u+p3*v+p5
def score(p):
    x=p[0]*S[:,0]+p[1]*S[:,1]+p[4]; y=p[2]*S[:,0]+p[3]*S[:,1]+p[5]
    xi=np.floor(x).astype(int); yi=np.floor(y).astype(int); m=(xi>=0)&(yi>=0)&(xi<W)&(yi<H)
    if m.sum()<3000: return 99, 0
    return DIST[yi[m],xi[m]].mean(), (DIST[yi[m],xi[m]]==0).mean()
best=score(p)[0]; print('inicio', score(p))
steps=np.array([0.004,0.004,0.004,0.004,1.0,1.0])
for rnd in range(60):
    improved=False
    for i in range(6):
        for sgn in (1,-1):
            q=p.copy(); q[i]+=sgn*steps[i]
            # al cambiar la escala, compensa la traslación para mantener el centro del mapa
            if i<4:
                cu=np.array([W/2,H/2]); A=np.array([[p[0],p[1]],[p[2],p[3]]]); uv=np.linalg.solve(A,cu-p[4:6]); Aq=np.array([[q[0],q[1]],[q[2],q[3]]]); q[4:6]=cu-Aq@uv
            sc=score(q)[0]
            if sc<best-1e-4: best=sc; p=q; improved=True
    if not improved:
        steps*=0.5
        if steps[4]<0.05: break
print('final', score(p), 'escala x m/casilla', round(1/math.hypot(p[0],p[2]),4), 'escala y', round(1/math.hypot(p[1],p[3]),4))
json.dump({'p':p.tolist(),'lat0':lat0,'lon0':lon0},open(M+'/xfa.json','w'))
