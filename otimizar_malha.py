"""Gera GeoJSON cartográfico leve a partir da malha processada, mantendo o original.
A malha leve serve apenas à visualização; análises continuam no arquivo original.
"""
import json
from pathlib import Path
from shapely.geometry import shape, mapping

ORIGEM = Path("municipios_profgeo_2022.geojson")
DESTINO = Path("municipios_profgeo_2022_leve.geojson")
dados = json.loads(ORIGEM.read_text(encoding="utf-8"))
features = []
def arredondar(v):
    if isinstance(v, (float, int)):
        return round(v, 4)
    if isinstance(v, list):
        return [arredondar(x) for x in v]
    if isinstance(v, tuple):
        return [arredondar(x) for x in v]
    return v

for feature in dados["features"]:
    g = shape(feature["geometry"])
    # Geometria simplificada em metros, por projeção métrica na malha principal.
    # Na malha leve em graus, 0.025 grau equivale aproximadamente a 2–3 km.
    simples = g.simplify(0.022, preserve_topology=True)
    if simples.is_empty:
        simples = g
    props = feature.get("properties", {})
    features.append({"type": "Feature",
                     "properties": {
                         "codigo_ibge": str(props.get("codigo_ibge", "")),
                         "municipio": props.get("municipio", ""),
                         "uf": props.get("uf", ""),
                         "faixa": props.get("faixa", ""),
                         "distancia_km": props.get("distancia_km", None)},
                     "geometry": arredondar(mapping(simples)["coordinates"]) and {
                         "type": mapping(simples)["type"],
                         "coordinates": arredondar(mapping(simples)["coordinates"])
                     }})
saida = {"type":"FeatureCollection","features":features}
DESTINO.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")),encoding="utf-8")
print("Municípios:",len(features),"GeoJSON original (MB):",round(ORIGEM.stat().st_size/1e6,2),
      "GeoJSON leve (MB):",round(DESTINO.stat().st_size/1e6,2))
