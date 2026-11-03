"""Motor territorial exploratório PROFGEO. Distâncias geodésicas entre pontos, não tempos de viagem."""
from math import radians, sin, cos, asin, sqrt
import pandas as pd

def distancia_km(lat1,lon1,lat2,lon2):
    a1,a2=radians(float(lat1)),radians(float(lat2))
    da=a2-a1;dl=radians(float(lon2)-float(lon1))
    h=sin(da/2)**2+cos(a1)*cos(a2)*sin(dl/2)**2
    return 6371.0088*2*asin(min(1,sqrt(h)))

def categoria(tipo,dist):
    if tipo not in ('A','B'): return 'Pendente'
    n=1 if dist>300 else 2 if dist>200 else 3 if dist>100 else 4
    return f'{tipo}{n}'

def avaliar(candidatos,polos):
    cols=['instituicao','campus','municipio','uf','lat','lon','tipo']
    required_p=['polo','lat','lon']
    for name,frame,req in [('candidatos',candidatos,cols),('polos',polos,required_p)]:
        missing=set(req)-set(frame.columns)
        if missing:raise ValueError(f'Colunas ausentes em {name}: {sorted(missing)}')
    if polos.empty: raise ValueError('Cadastre pelo menos um polo de referência.')
    if candidatos.empty:return pd.DataFrame()
    rows=[]
    for _,c in candidatos.iterrows():
        distances=[(distancia_km(c.lat,c.lon,p.lat,p.lon),p.polo) for _,p in polos.iterrows()]
        d,nome=min(distances)
        r=c.to_dict();r.update(polo_mais_proximo=nome,distancia_km=round(d,1),categoria=categoria(str(c.tipo).upper().strip(),d))
        rows.append(r)
    return pd.DataFrame(rows)
