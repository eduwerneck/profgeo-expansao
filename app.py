"""PROFGEO Expansão — interface cartográfica simplificada."""
import math
import json
import unicodedata
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

def chave_nome(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    return "".join(ch for ch in texto if not unicodedata.combining(ch)).strip()

@st.cache_data
def carregar_regic():
    caminho = Path("regic_municipios_2018.csv")
    if not caminho.exists():
        return None
    tabela = pd.read_csv(caminho, dtype={"codigo_ibge": str}, keep_default_na=False, encoding="utf-8-sig")
    colunas = {"codigo_ibge", "hierarquia_regic", "regiao_influencia_regic"}
    if not colunas.issubset(tabela.columns) or tabela["codigo_ibge"].duplicated().any():
        raise ValueError("Base REGIC inválida: cabeçalho incompleto ou municípios duplicados.")
    return tabela

@st.cache_data
def indice_municipios():
    caminho = Path("municipios_profgeo_2022.geojson")
    if not caminho.exists():
        return {}
    mapa = json.loads(caminho.read_text(encoding="utf-8"))
    indice = {}
    for feicao in mapa.get("features", []):
        p = feicao.get("properties", {})
        chave = (chave_nome(p.get("municipio")), str(p.get("uf", "")).upper().strip())
        if chave not in indice and p.get("codigo_ibge"):
            indice[chave] = str(p["codigo_ibge"]).zfill(7)
    return indice

def anexar_regic(resultado):
    resultado = resultado.copy()
    regic = carregar_regic()
    if regic is None:
        resultado["hierarquia_regic"] = "Não disponível: executar integração REGIC"
        resultado["regiao_influencia_regic"] = ""
        resultado["status_regic"] = "Aguardando processamento do IBGE"
        return resultado
    mapa_municipios = indice_municipios()
    if "codigo_ibge" not in resultado:
        resultado["codigo_ibge"] = ""
    resultado["codigo_ibge"] = [
        str(cod).strip().split(".")[0].zfill(7) if str(cod).strip() else mapa_municipios.get((chave_nome(mun),str(uf).upper().strip()), "")
        for cod,mun,uf in zip(resultado["codigo_ibge"],resultado["municipio"],resultado["uf"])
    ]
    resultado = resultado.merge(regic[["codigo_ibge","hierarquia_regic","regiao_influencia_regic"]],
                                on="codigo_ibge", how="left", validate="m:1")
    resultado["status_regic"] = resultado["hierarquia_regic"].notna().map({True:"Vinculado por código IBGE",False:"Município não identificado na REGIC"})
    return resultado

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

@st.cache_data(show_spinner=False)
def carregar_camada_cartografica(caminho, versao):
    """Deserializa e estiliza os municípios apenas uma vez por versão do arquivo."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    cores = {"Até 100 km": [38,136,94,185], "100–200 km": [119,185,84,185],
             "200–300 km": [245,171,64,185], "Mais de 300 km": [197,65,62,185]}
    for feicao in dados.get("features", []):
        props = feicao.setdefault("properties", {})
        props["cor"] = cores.get(props.get("faixa"), [140,140,140,100])
        props["identificacao"] = props.get("municipio", "Município")
        props["detalhe"] = str(props.get("distancia_km", "?")) + " km | " + str(props.get("faixa", ""))
    return dados

def montar_mapa(sedes, resultados):
    layers = []
    malha_leve = Path("municipios_profgeo_2022_leve.geojson")
    malha = malha_leve if malha_leve.exists() else Path("municipios_profgeo_2022.geojson")
    if malha.exists():
        dados = carregar_camada_cartografica(str(malha), malha.stat().st_mtime_ns)
        layers.append(pdk.Layer("GeoJsonLayer", data=dados, filled=True, stroked=False,
                                get_fill_color="properties.cor", pickable=True))
    else:
        # Visualização substituta enquanto a malha municipal processada não estiver no repositório.
        for km, cor in ((300,[221,120,70,38]), (200,[245,177,73,48]), (100,[51,157,111,64])):
            poligonos = [{"polygon": aneis(r.lat, r.lon, km)} for r in sedes.itertuples()]
            layers.append(pdk.Layer("PolygonLayer", data=poligonos, get_polygon="polygon", get_fill_color=cor, stroked=False, pickable=False))
    sedes = sedes.copy()
    sedes["identificacao"] = sedes["polo"]
    sedes["detalhe"] = "Polo PROFGEO existente"
    layers.append(pdk.Layer("ScatterplotLayer", data=sedes, get_position="[lon, lat]", get_radius=6500, radius_min_pixels=4, radius_max_pixels=9, get_fill_color=[24,75,138,255], get_line_color=[255,255,255,255], line_width_min_pixels=1, stroked=True, pickable=True))
    latitude_centro, longitude_centro, zoom = -14.5, -52.5, 3.5
    if resultados is not None and not resultados.empty:
        candidatos = resultados.copy()
        candidatos["identificacao"] = candidatos["instituicao"].astype(str) + " — " + candidatos["campus"].astype(str)
        candidatos["detalhe"] = candidatos["categoria"].astype(str) + " | " + candidatos["distancia_km"].astype(str) + " km do polo mais próximo"
        # Marcadores em duas camadas: não dependem da fonte Unicode para exibir estrelas.
        layers.append(pdk.Layer("ScatterplotLayer", data=candidatos, get_position="[lon, lat]",
                                get_radius=17000, radius_min_pixels=13, radius_max_pixels=19,
                                get_fill_color=[255,255,255,255], get_line_color=[20,20,20,255],
                                line_width_min_pixels=3, stroked=True, pickable=True))
        layers.append(pdk.Layer("ScatterplotLayer", data=candidatos, get_position="[lon, lat]",
                                get_radius=9000, radius_min_pixels=7, radius_max_pixels=11,
                                get_fill_color=[235,38,53,255], stroked=False, pickable=True))
        # Reenquadrar as duas candidaturas ao atualizar o mapa.
        latitude_centro = float(candidatos["lat"].mean())
        longitude_centro = float(candidatos["lon"].mean())
        amplitude = max(float(candidatos["lat"].max()-candidatos["lat"].min()),
                        float(candidatos["lon"].max()-candidatos["lon"].min()))
        zoom = 5.0 if amplitude < 3 else 4.4 if amplitude < 8 else 3.6
    return pdk.Deck(map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                    initial_view_state=pdk.ViewState(latitude=latitude_centro, longitude=longitude_centro, zoom=zoom, pitch=0),
                    layers=layers,
                    tooltip={"html":"<b>{identificacao}</b><br/>{detalhe}","style":{"color":"white"}})

sedes_padrao = normalizar_sedes(ler_sedes())
sedes = sedes_padrao
resultados = st.session_state.get("resultado_expansao")
if not Path("municipios_profgeo_2022.geojson").exists():
    st.warning("Mapa coroplético municipal ainda indisponível: falta gerar e publicar municipios_profgeo_2022.geojson a partir da malha IBGE 2022. A visualização abaixo é apenas provisória.")
st.pydeck_chart(montar_mapa(sedes, resultados), use_container_width=True, key="mapa_expansao_" + str(st.session_state.get("versao_mapa", 0)))
st.markdown("**Prioridade territorial preliminar — distância ao polo PROFGEO mais próximo**")
legenda = [
    ("#26885E", "Muito baixa", "Até 100 km"),
    ("#77B954", "Baixa", "Mais de 100 até 200 km"),
    ("#F5AB40", "Moderada", "Mais de 200 até 300 km"),
    ("#C5413E", "Alta", "Mais de 300 km"),
]
colunas_legenda = st.columns(4)
for coluna, (cor, nivel, distancia) in zip(colunas_legenda, legenda):
    with coluna:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:9px;padding:4px 0;">'
            f'<span style="display:inline-block;width:20px;height:20px;flex-shrink:0;background:{cor};border:1px solid #888;border-radius:3px;"></span>'
            f'<span style="font-size:0.85rem;"><b>{nivel}</b><br>{distancia}</span></div>',
            unsafe_allow_html=True,
        )
st.caption("● Azul: polo atual | ● Vermelho com contorno preto: candidatura (passe o cursor). As cores representam somente a lacuna de proximidade; não determinam prioridade institucional, elegibilidade ou decisão da comissão.")

with st.form("controles_expansao"):
    arq_candidatos = st.file_uploader("Carregar candidaturas (CSV)", type="csv")
    calcular = st.form_submit_button("Calcular expansão", type="primary", use_container_width=True)

if calcular:
    try:
        candidatos = normalizar_candidatos(pd.read_csv(arq_candidatos, keep_default_na=False) if arq_candidatos else ler_pilotos())
        resultado = anexar_regic(avaliar(candidatos, sedes_padrao))
        st.session_state["resultado_expansao"] = resultado
        st.session_state["versao_mapa"] = st.session_state.get("versao_mapa", 0) + 1
        st.rerun()
    except Exception as exc:
        st.error(f"Não foi possível calcular: {exc}")

if resultados is not None and not resultados.empty:
    if "status_regic" in resultados.columns:
        st.caption("REGIC das candidaturas: " + " | ".join(resultados["status_regic"].astype(str).unique()))
    st.download_button("Baixar resultados (CSV)", resultados.to_csv(index=False).encode("utf-8-sig"), "diagnostico_expansao_profgeo.csv", mime="text/csv", use_container_width=True)
    st.caption("Resultado calculado. REGIC 2018 é dimensão descritiva independente, sem peso na classificação por distância. Tipo A/B permanece pendente quando não comprovado.")
else:
    st.button("Baixar resultados (CSV)", disabled=True, use_container_width=True)
    st.caption("Carregue candidaturas ou utilize os dois casos-piloto incluídos; clique em Calcular expansão.")
