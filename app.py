import pandas as pd
import pydeck as pdk
import streamlit as st
from engine import avaliar

st.set_page_config(page_title="PROFGEO — laboratório territorial", layout="wide")
st.title("PROFGEO | Laboratório de expansão territorial")
st.caption("Protótipo exploratório. Não atribui habilitação, suplência nem decisão institucional.")
st.info("A unidade espacial é o campus de oferta. As coordenadas de exemplo são pontos municipais aproximados, não coordenadas dos campi.")
with st.expander("Como funciona a classificação"):
    st.write("A = campus com pós-graduação em Geografia; B = campus com graduação em Geografia sem pós-graduação. A1/B1: >300 km; A2/B2: >200–300 km; A3/B3: >100–200 km; A4/B4: até 100 km.")
    st.write("Distâncias em linha reta, sem estimativa de tempo de viagem. REGIC e acessibilidade amazônica ainda não são calculadas.")
base = pd.read_csv("candidatos_exemplo.csv", keep_default_na=False)
rede = pd.read_csv("rede_existente_18_polos.csv")
rede["polo"] = rede["instituicao"] + " — " + rede["campus"]
modelo_polos = rede[["polo", "municipio", "uf", "lat", "lon", "fonte"]].copy()
st.subheader("Rede existente do PROFGEO — 18 instituições")
st.caption("Pontos municipais aproximados; alguns campi ainda precisam de validação.")
modo_mapa = st.radio("Visualização cartográfica", ["Mapa de calor", "Localização dos polos"], horizontal=True)
raio = st.slider("Raio visual da concentração (pixels)", 15, 90, 40, 5) if modo_mapa == "Mapa de calor" else 40
pontos = rede.dropna(subset=["lat", "lon"]).copy()
pontos["lat"] = pd.to_numeric(pontos["lat"], errors="coerce")
pontos["lon"] = pd.to_numeric(pontos["lon"], errors="coerce")
pontos = pontos.dropna(subset=["lat", "lon"])
pontos["peso"] = 1
camadas = []
if modo_mapa == "Mapa de calor":
    camadas.append(pdk.Layer("HeatmapLayer", data=pontos, get_position="[lon, lat]", get_weight="peso", radius_pixels=raio, intensity=1, threshold=0.03, pickable=False))
camadas.append(pdk.Layer("ScatterplotLayer", data=pontos, get_position="[lon, lat]", get_radius=12000 if modo_mapa == "Localização dos polos" else 6000, radius_min_pixels=4, radius_max_pixels=10, get_fill_color=[23, 87, 149, 210] if modo_mapa == "Localização dos polos" else [255, 255, 255, 210], get_line_color=[12, 32, 55], line_width_min_pixels=1, stroked=True, pickable=True))
st.pydeck_chart(pdk.Deck(
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    initial_view_state=pdk.ViewState(latitude=-14.5, longitude=-52.5, zoom=3.25, pitch=0),
    layers=camadas,
    tooltip={"html": "<b>{instituicao}</b><br/>{campus}<br/>{municipio} — {uf}", "style": {"color": "white"}}
))
st.caption("Calor = concentração visual de pontos municipais dos polos existentes, não demanda educacional, acessibilidade ou prioridade de expansão. O raio é apenas um parâmetro gráfico; não corresponde a quilômetros. Polos próximos podem se sobrepor.")
with st.expander("Consultar polos e ressalvas"):
    st.dataframe(rede, use_container_width=True, hide_index=True)
    st.download_button("Baixar rede de referência", rede.to_csv(index=False).encode("utf-8-sig"), "rede_existente_18_polos.csv", "text/csv")
esq, dir = st.columns(2)
with esq:
    st.subheader("Candidaturas")
    arquivo = st.file_uploader("Importar candidaturas CSV", type="csv", key="c")
    candidatos = pd.read_csv(arquivo, keep_default_na=False) if arquivo else base
    candidatos = st.data_editor(candidatos, num_rows="dynamic", hide_index=True, use_container_width=True)
    st.download_button("Baixar modelo de candidaturas", base.to_csv(index=False).encode("utf-8-sig"), "candidatos_exemplo.csv", "text/csv")
with dir:
    st.subheader("Polos existentes — rede atual")
    arquivo_polos = st.file_uploader("Importar polos existentes CSV", type="csv", key="p")
    polos = pd.read_csv(arquivo_polos) if arquivo_polos else modelo_polos
    polos = st.data_editor(polos, num_rows="dynamic", hide_index=True, use_container_width=True)
    st.download_button("Baixar polos de referência", modelo_polos.to_csv(index=False).encode("utf-8-sig"), "polos_modelo.csv", "text/csv")
if candidatos["tipo"].astype(str).str.strip().eq("").any():
    st.warning("Informe o tipo A/B dos candidatos para obter a categoria territorial.")
if st.button("Calcular prioridades territoriais", type="primary"):
    try:
        st.session_state["resultado"] = avaliar(candidatos, polos)
    except Exception as exc:
        st.error(str(exc))
if "resultado" in st.session_state:
    resultado = st.session_state["resultado"]
    st.subheader("Resultados calculados")
    st.dataframe(resultado, use_container_width=True, hide_index=True)
    st.download_button("Exportar resultado CSV", resultado.to_csv(index=False).encode("utf-8-sig"), "resultados_profgeo.csv", "text/csv")
    if not resultado.empty:
        st.map(resultado[["lat", "lon"]].dropna())
st.divider()
st.subheader("UEL × IFPR — contexto histórico")
st.write("Conforme informado pela comissão: houve empate, e o IFPR em Jaguariaíva foi selecionado pelo critério de interiorização. O cálculo territorial não reproduz automaticamente essa decisão.")
st.caption("Para validação retrospectiva: informar os polos existentes à época, a condição A/B dos campi e os dados oficiais da REGIC. Não usar polos implantados posteriormente.")
