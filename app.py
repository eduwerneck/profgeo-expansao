"""PROFGEO Expansão — interface cartográfica simplificada."""
import math
import json
from pathlib import Path
import pandas as pd
import pydeck as pdk
import streamlit as st
from engine import avaliar, distancia_km

st.set_page_config(page_title="Diagnóstico territorial da expansão do PROFGEO", layout="wide")
st.title("Diagnóstico territorial da expansão do PROFGEO")
st.caption("Rede atual, faixas de distância geodésica e candidaturas. Análise exploratória; não constitui decisão institucional.")

@st.cache_data
def ler_sedes():
    df = pd.read_csv("rede_existente_18_polos.csv")
    df["polo"] = df["instituicao"].astype(str) + " — " + df["campus"].astype(str)
    return df

@st.cache_data
def ler_pilotos():
    return pd.read_csv("candidaturas_piloto.csv", keep_default_na=False)

def normalizar_sedes(df):
    df = df.copy()
    if "polo" not in df.columns:
        if {"instituicao", "campus"}.issubset(df.columns):
            df["polo"] = df["instituicao"].astype(str) + " — " + df["campus"].astype(str)
        else:
            raise ValueError("As sedes precisam da coluna 'polo' ou das colunas 'instituicao' e 'campus'.")
    for col in ("lat", "lon"):
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente nas sedes: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["lat", "lon"]].isna().any().any() or df.empty:
        raise ValueError("Todas as sedes precisam de coordenadas válidas.")
    return df

def normalizar_candidatos(df):
    df = df.copy()
    for col in ("instituicao", "campus", "municipio", "uf", "lat", "lon"):
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente nas candidaturas: {col}")
    for col in ("lat", "lon"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["lat", "lon"]].isna().any().any():
        raise ValueError("Todas as candidaturas precisam de latitude e longitude válidas.")
    if "tipo" not in df.columns:
        df["tipo"] = ""
    return df

def aneis(lat, lon, raio_km, passos=48):
    a = math.radians(float(lat))
    o = math.radians(float(lon))
    delta = raio_km / 6371.0088
    pts = []
    for k in range(passos):
        rumo = 2 * math.pi * k / passos
        phi = math.asin(math.sin(a)*math.cos(delta)+math.cos(a)*math.sin(delta)*math.cos(rumo))
        lam = o + math.atan2(math.sin(rumo)*math.sin(delta)*math.cos(a), math.cos(delta)-math.sin(a)*math.sin(phi))
        pts.append([math.degrees(lam), math.degrees(phi)])
    return pts

def montar_mapa(sedes, resultados):
    layers = []
    malha = Path("municipios_profgeo_2022.geojson")
    if malha.exists():
        dados = json.loads(malha.read_text(encoding="utf-8"))
        cores = {"Até 100 km": [38,136,94,185], "100–200 km": [119,185,84,185], "200–300 km": [245,171,64,185], "Mais de 300 km": [197,65,62,185]}
        for feicao in dados.get("features", []):
            props = feicao.setdefault("properties", {})
            props["cor"] = cores.get(props.get("faixa"), [140,140,140,100])
            props["identificacao"] = props.get("municipio", "Município")
            props["detalhe"] = str(props.get("distancia_km", "?")) + " km | " + str(props.get("faixa", ""))
        layers.append(pdk.Layer("GeoJsonLayer", data=dados, filled=True, stroked=False, get_fill_color="properties.cor", pickable=True))
    else:
        # Visualização substituta enquanto a malha municipal processada não estiver no repositório.
        for km, cor in ((300,[221,120,70,38]), (200,[245,177,73,48]), (100,[51,157,111,64])):
            poligonos = [{"polygon": aneis(r.lat, r.lon, km)} for r in sedes.itertuples()]
            layers.append(pdk.Layer("PolygonLayer", data=poligonos, get_polygon="polygon", get_fill_color=cor, stroked=False, pickable=False))
    sedes = sedes.copy()
    sedes["identificacao"] = sedes["polo"]
    sedes["detalhe"] = "Polo PROFGEO existente"
    layers.append(pdk.Layer("ScatterplotLayer", data=sedes, get_position="[lon, lat]", get_radius=6500, radius_min_pixels=4, radius_max_pixels=9, get_fill_color=[24,75,138,255], get_line_color=[255,255,255,255], line_width_min_pixels=1, stroked=True, pickable=True))
    if resultados is not None and not resultados.empty:
        candidatos = resultados.copy()
        candidatos["identificacao"] = candidatos["instituicao"].astype(str) + " — " + candidatos["campus"].astype(str)
        candidatos["detalhe"] = candidatos["categoria"].astype(str) + " | " + candidatos["distancia_km"].astype(str) + " km do polo mais próximo"
        candidatos["simbolo"] = "★"
        layers.append(pdk.Layer("TextLayer", data=candidatos, get_position="[lon, lat]", get_text="simbolo", get_size=38, size_units="pixels", get_color=[18,18,18,255], get_text_anchor="middle", get_alignment_baseline="center", pickable=True))
    return pdk.Deck(map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json", initial_view_state=pdk.ViewState(latitude=-14.5,longitude=-52.5,zoom=3.5,pitch=0), layers=layers, tooltip={"html":"<b>{identificacao}</b><br/>{detalhe}","style":{"color":"white"}})

sedes_padrao = normalizar_sedes(ler_sedes())
sedes = sedes_padrao
resultados = st.session_state.get("resultado_expansao")
st.pydeck_chart(montar_mapa(sedes, resultados), use_container_width=True)
st.caption("Azul: sedes atuais | ★: candidaturas calculadas | Verde: até 100 km | Verde-claro: 100–200 km | Amarelo: 200–300 km | Vermelho: mais de 300 km. Sem o GeoJSON municipal processado, o mapa usa círculos de cobertura provisórios.")

with st.form("controles_expansao"):
    arq_candidatos = st.file_uploader("Carregar candidaturas (CSV)", type="csv")
    calcular = st.form_submit_button("Calcular expansão", type="primary", use_container_width=True)

if calcular:
    try:
        candidatos = normalizar_candidatos(pd.read_csv(arq_candidatos, keep_default_na=False) if arq_candidatos else ler_pilotos())
        resultado = avaliar(candidatos, sedes_padrao)
        st.session_state["resultado_expansao"] = resultado
        st.rerun()
    except Exception as exc:
        st.error(f"Não foi possível calcular: {exc}")

if resultados is not None and not resultados.empty:
    st.download_button("Baixar resultados (CSV)", resultados.to_csv(index=False).encode("utf-8-sig"), "diagnostico_expansao_profgeo.csv", mime="text/csv", use_container_width=True)
    st.caption("Resultado calculado. Tipo A/B não comprovado permanece pendente; distância não equivale a acessibilidade ou prioridade institucional.")
else:
    st.button("Baixar resultados (CSV)", disabled=True, use_container_width=True)
    st.caption("Carregue candidaturas ou utilize os dois casos-piloto incluídos; clique em Calcular expansão.")
