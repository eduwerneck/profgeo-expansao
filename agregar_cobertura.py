"""Gera mapa de cobertura leve por união das classes municipais.
O arquivo original com os 5570 municípios permanece intacto, assim como seus valores.
Este produto agregado é exclusivamente cartográfico.
"""
import json
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

origem=Path("municipios_profgeo_2022_leve.geojson")
destino=Path("cobertura_profgeo_agregada.geojson")
dados=json.loads(origem.read_text(encoding="utf-8"))
classes=["Até 100 km","100–200 km","200–300 km","Mais de 300 km"]
grupos={classe:[] for classe in classes}
for f in dados["features"]:
    faixa=f.get("properties",{}).get("faixa")
    if faixa in grupos and f.get("geometry"):
        g=shape(f["geometry"])
        if not g.is_empty:
            grupos[faixa].append(g)
saida=[]
for faixa, geometrias in grupos.items():
    if not geometrias:
        raise ValueError(f"Faixa sem municípios: {faixa}")
    unida=unary_union(geometrias)
    # Simplifica as geometrias já agregadas, sem alterar o dado municipal original.
    unida=unida.simplify(0.028,preserve_topology=True)
    if not unida.is_valid:
        unida=unida.buffer(0)
    coords=mapping(unida)
    saida.append({"type":"Feature","properties":{"faixa":faixa,"identificacao":faixa,
                    "detalhe":"Lacuna territorial de proximidade ao polo PROFGEO mais próximo"},
                  "geometry":coords})
resultado={"type":"FeatureCollection","features":saida}
destino.write_text(json.dumps(resultado,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
print("Original:",round(origem.stat().st_size/1e6,2),"MB; agregado:",round(destino.stat().st_size/1e6,2),"MB; feições:",len(saida))
