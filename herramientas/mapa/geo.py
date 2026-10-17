import json,sys,math,random,unicodedata
M=sys.argv[1]
d=json.load(open(M+'/D_old.json')); o=json.load(open(M+'/osm.json'))
nodes=o['nodes']
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn').strip()
cand={}
for name,(lat,lon),t in o['named']: cand.setdefault(norm(name),[]).append((lat,lon))
for wid,t,nd in o['ways']:
    if 'name' in t and 'highway' not in t:
        pts=[nodes[r] for r in nd if r in nodes]
        if pts: cand.setdefault(norm(t['name']),[]).append((sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts)))
pairs={}
for x,y,name,k in d['pois']:
    c=cand.get(norm(name))
    if c and len(c)==1: pairs[name]=(x,y,c[0][0],c[0][1])
print('pares',len(pairs))
lat0,lon0=8.934,-67.428
def proj(lat,lon): return ((lon-lon0)*math.cos(math.radians(lat0))*111320, -(lat-lat0)*110574)
P=[(proj(a,b),(x,y),n) for n,(x,y,a,b) in pairs.items()]
def fit(sub):
    n=len(sub); mu=sum(complex(*p[0]) for p in sub)/n; mt=sum(complex(*p[1]) for p in sub)/n
    den=sum(abs(complex(*p[0])-mu)**2 for p in sub)
    if den<1: return None
    num=sum((complex(*p[1])-mt)*(complex(*p[0])-mu).conjugate() for p in sub); a=num/den; return a, mt-a*mu
def err(a,b,p): return abs(a*complex(*p[0])+b-complex(*p[1]))
best=[]; random.seed(1)
for it in range(4000):
    f=fit(random.sample(P,2))
    if not f: continue
    inl=[p for p in P if err(f[0],f[1],p)<3]
    if len(inl)>len(best): best=inl
a,b=fit(best)
print('inliers',len(best),'de',len(P),'| m por casilla',round(1/abs(a),4),'| rotación',round(math.degrees(math.atan2(a.imag,a.real)),3),'°')
print('error medio (casillas)',round(sum(err(a,b,p) for p in best)/len(best),2))
json.dump({'a':[a.real,a.imag],'b':[b.real,b.imag],'lat0':lat0,'lon0':lon0},open(M+'/xf.json','w'))
