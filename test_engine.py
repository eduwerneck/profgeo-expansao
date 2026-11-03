from engine import categoria,distancia_km,avaliar
import pandas as pd
for d,expected in [(0,'A4'),(100,'A4'),(100.01,'A3'),(200,'A3'),(200.01,'A2'),(300,'A2'),(300.01,'A1')]:
 assert categoria('A',d)==expected
assert categoria('B',301)=='B1'
assert categoria('',301)=='Pendente'
assert abs(distancia_km(0,0,0,0))<1e-8
c=pd.DataFrame([{'instituicao':'Teste','campus':'C','municipio':'X','uf':'PR','lat':0,'lon':0,'tipo':'A'}])
p=pd.DataFrame([{'polo':'P','lat':0,'lon':0}])
r=avaliar(c,p)
assert r.iloc[0]['categoria']=='A4'
print('Testes básicos aprovados')
