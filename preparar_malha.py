"""Pré-processa a malha IBGE 2022 em GeoJSON municipal simplificado.

Uso: python preparar_malha.py /caminho/BR_Municipios_2022.zip
Requer: geopandas, shapely, pandas. Executar uma vez fora do Streamlit.
"""
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
from engine import distancia_km

ARQUIVO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("BR_Municipios_2022.zip")
DESTINO = Path("municipios_profgeo_2022.geojson")
REDE = Path("rede_existente_18_polos.csv")
if not ARQUIVO.exists():
    raise SystemExit(f"Malha não encontrada: {ARQUIVO}")
gdf = gpd.read_file("zip://" + str(ARQUIVO.resolve()))
campos = {c.upper(): c for c in gdf.columns}
codigo = campos.get("CD_MUN") or campos.get("CD_GEOCMU")
nome = campos.get("NM_MUN")
uf = campos.get("SIGLA_UF")
if not codigo:
    raise ValueError(f"Identificador municipal IBGE ausente: {list(gdf.columns)}")
gdf = gdf.to_crs("EPSG:4674")
gdf = gdf.rename(columns={codigo: "codigo_ibge"})
gdf["codigo_ibge"] = gdf["codigo_ibge"].astype(str).str.zfill(7)
gdf["municipio"] = gdf[nome].astype(str) if nome else ""
gdf["uf"] = gdf[uf].astype(str) if uf else ""
pontos = gdf.to_crs("EPSG:5880").representative_point().to_crs("EPSG:4674")
gdf["lat"] = pontos.y
gdf["lon"] = pontos.x
rede = pd.read_csv(REDE)
distancias = []
polos = []
for r in gdf.itertuples():
    proximos = [(distancia_km(r.lat, r.lon, p.lat, p.lon), p.instituicao + " — " + p.campus) for p in rede.itertuples()]
    d, polo = min(proximos)
    distancias.append(round(d, 1))
    polos.append(polo)
gdf["distancia_km"] = distancias
gdf["polo_proximo"] = polos
gdf["faixa"] = pd.cut(gdf["distancia_km"], bins=[-1,100,200,300,float("inf")], labels=["Até 100 km","100–200 km","200–300 km","Mais de 300 km"]).astype(str)
# Simplificação em projeção métrica para preservar a topologia aproximada e reduzir tamanho.
gdf["geometry"] = gdf.to_crs("EPSG:5880").geometry.simplify(1200, preserve_topology=True).to_crs("EPSG:4674")
colunas = ["codigo_ibge","municipio","uf","lat","lon","distancia_km","polo_proximo","faixa","geometry"]
gdf[colunas].to_file(DESTINO, driver="GeoJSON")
print(f"Gerados {len(gdf)} municípios em {DESTINO} ({DESTINO.stat().st_size/1e6:.1f} MB)")
