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
st.subheader("Diagnóstico territorial da expansão do PROFGEO")
camada_territorial = st.radio("Camada temática", ["Distância à rede", "Oportunidade territorial preliminar"], horizontal=True, key="camada_territorial")
st.caption("Análise de distância geodésica entre pontos representativos municipais do IBGE 2022 e os 18 polos. Não representa acessibilidade real.")
municipios_arquivo = st.file_uploader("Carregar pontos municipais IBGE 2022 (CSV)", type="csv", key="municipios")
if municipios_arquivo is None:
    st.info("Para habilitar o mapa nacional, carregue o arquivo municipios_ibge_2022_pontos.csv disponibilizado com o projeto. O cálculo é executado no navegador após o envio do arquivo.")
else:
    try:
        import numpy as np
        municipios = pd.read_csv(municipios_arquivo, dtype={"codigo_ibge": str})
        exigidas = {"codigo_ibge", "municipio", "uf", "lat", "lon"}
        if not exigidas.issubset(municipios.columns):
            raise ValueError("CSV municipal deve conter: codigo_ibge, municipio, uf, lat, lon.")
        if municipios["codigo_ibge"].duplicated().any():
            raise ValueError("Há códigos IBGE duplicados no arquivo.")
        municipios["lat"] = pd.to_numeric(municipios["lat"], errors="coerce")
        municipios["lon"] = pd.to_numeric(municipios["lon"], errors="coerce")
        if municipios[["lat", "lon"]].isna().any().any():
            raise ValueError("Há coordenadas municipais ausentes ou inválidas.")
        pl = np.radians(rede[["lat", "lon"]].to_numpy(dtype=float))
        ml = np.radians(municipios[["lat", "lon"]].to_numpy(dtype=float))
        dlat = ml[:, None, 0] - pl[None, :, 0]
        dlon = ml[:, None, 1] - pl[None, :, 1]
        h = np.sin(dlat / 2) ** 2 + np.cos(ml[:, None, 0]) * np.cos(pl[None, :, 0]) * np.sin(dlon / 2) ** 2
        dist = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
        indice = np.argmin(dist, axis=1)
        municipios["distancia_km"] = np.round(dist[np.arange(len(municipios)), indice], 1)
        municipios["polo_proximo"] = rede.iloc[indice]["instituicao"].to_numpy()
        municipios["faixa"] = pd.cut(municipios["distancia_km"], bins=[-0.01, 100, 200, 300, np.inf], labels=["Até 100 km", "100–200 km", "200–300 km", "Mais de 300 km"], include_lowest=True)
        paleta = {"Até 100 km": [38, 136, 94, 180], "100–200 km": [119, 185, 84, 180], "200–300 km": [245, 171, 64, 185], "Mais de 300 km": [197, 65, 62, 195]}
        municipios["cor"] = municipios["faixa"].astype(str).map(paleta)
        oportunidades = {
            "Até 100 km": "Menor lacuna de proximidade",
            "100–200 km": "Lacuna moderada de proximidade",
            "200–300 km": "Lacuna elevada de proximidade",
            "Mais de 300 km": "Lacuna muito elevada de proximidade",
        }
        municipios["oportunidade_preliminar"] = municipios["faixa"].astype(str).map(oportunidades)
        if camada_territorial == "Oportunidade territorial preliminar":
            st.info("Camada exploratória baseada SOMENTE na distância à rede. Uma lacuna de proximidade maior sugere investigar a expansão, mas não demonstra potencial institucional, demanda, elegibilidade ou acessibilidade.")
            st.markdown("**Legenda — oportunidade de investigação por lacuna de proximidade**")
        else:
            st.markdown("**Legenda — distância geodésica ao polo PROFGEO mais próximo (km)**")
        legenda = [
            ("#26885E", "Até 100 km"),
            ("#77B954", "Mais de 100 até 200 km"),
            ("#F5AB40", "Mais de 200 até 300 km"),
            ("#C5413E", "Mais de 300 km"),
        ]
        if camada_territorial == "Oportunidade territorial preliminar":
            legenda = [(cor, oportunidades[faixa]) for (cor, _), faixa in zip(legenda, ["Até 100 km", "100–200 km", "200–300 km", "Mais de 300 km"])]
        cols_legenda = st.columns(4)
        for coluna, (cor, rotulo) in zip(cols_legenda, legenda):
            with coluna:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0 12px 0;">'
                    f'<span style="display:inline-block;flex-shrink:0;width:24px;height:17px;background:{cor};border:1px solid #888;border-radius:3px;"></span>'
                    f'<span style="font-size:0.85rem;">{rotulo}</span></div>',
                    unsafe_allow_html=True,
                )
        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=-14.5, longitude=-52.5, zoom=3.2),
            layers=[pdk.Layer("ScatterplotLayer", data=municipios, get_position="[lon, lat]", get_fill_color="cor", get_radius=7500, radius_min_pixels=2, radius_max_pixels=8, pickable=True)],
            tooltip={"html": "<b>{municipio} ({uf})</b><br/>Polo mais próximo: {polo_proximo}<br/>Distância: {distancia_km} km<br/>{faixa}<br/>{oportunidade_preliminar}"}
        ))
        resumo = municipios.groupby("faixa", observed=False).size().rename("municípios").reset_index()
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        st.download_button("Baixar diagnóstico territorial municipal", municipios.drop(columns=["cor"]).to_csv(index=False).encode("utf-8-sig"), "profgeo_distancias_municipios_2022.csv", "text/csv")
        st.caption("Mapa pontual, não coroplético: cada círculo corresponde a um ponto municipal, sem preencher o polígono do município. Distância municipal não é classificação institucional A1–B4.")
    except Exception as exc:
        st.error(f"Não foi possível calcular as distâncias: {exc}")

st.divider()
st.subheader("UEL × IFPR — contexto histórico")
st.write("Conforme informado pela comissão: houve empate, e o IFPR em Jaguariaíva foi selecionado pelo critério de interiorização. O cálculo territorial não reproduz automaticamente essa decisão.")
st.caption("Para validação retrospectiva: informar os polos existentes à época, a condição A/B dos campi e os dados oficiais da REGIC. Não usar polos implantados posteriormente.")
