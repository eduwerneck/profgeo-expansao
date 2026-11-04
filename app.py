"""PROFGEO Expansão — diagnóstico nacional; sem candidaturas simuladas na interface."""
from pathlib import Path
import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="PROFGEO | Diagnóstico nacional", layout="wide")
st.title("Diagnóstico territorial da expansão do PROFGEO")
st.caption(
    "Matriz nacional de triagem acadêmica e territorial, com classificação operacional A–D. "
    "Os indicadores não constituem comprovação de elegibilidade nem decisão da comissão."
)

GRUPOS = {
    "A": "Estrutura acadêmica em Geografia identificada",
    "B": "Graduação em Geografia, sem PPG Geografia identificado",
    "C": "Instituto Federal multicampi: campus-sede não inferido da graduação",
    "D": "Outra configuração acadêmica a analisar",
}

@st.cache_data
def ler_polos():
    caminho = Path("rede_existente_18_polos.csv")
    if not caminho.exists():
        return pd.DataFrame()
    polos = pd.read_csv(caminho)
    if {"instituicao", "campus"}.issubset(polos):
        polos["polo"] = polos["instituicao"].astype(str) + " — " + polos["campus"].astype(str)
    return polos

@st.cache_data
def ler_nacional_local():
    caminho = Path("classificacao_ad_app_2026.csv")
    if caminho.exists():
        return pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return None

def carregar_tabela(arquivo):
    if arquivo.name.lower().endswith(".xlsx"):
        return pd.read_excel(arquivo, dtype=str, keep_default_na=False, engine="openpyxl")
    return pd.read_csv(arquivo, dtype=str, keep_default_na=False, encoding="utf-8-sig")

def preparar_nacional(tabela):
    df = tabela.copy()
    obrigatorias = {"instituicao", "municipio_nome_IBGE", "UF", "grupo_estrutural"}
    faltantes = obrigatorias - set(df.columns)
    if faltantes:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(sorted(faltantes)))
    if "grupo_operacional_app" not in df.columns:
        eh_if = df["instituicao"].str.upper().str.startswith("INSTITUTO FEDERAL DE EDUCAÇÃO")
        df["grupo_operacional_app"] = df["grupo_estrutural"].where(
            df["grupo_estrutural"].isin(["A", "B"]), "D"
        )
        df.loc[eh_if, "grupo_operacional_app"] = "C"
    if not df["grupo_operacional_app"].isin(GRUPOS).all():
        raise ValueError("Há registros sem grupo operacional válido A–D.")
    for coluna, valor in [
        ("status_validacao_institucional", "Não verificada"),
        ("campus_sede_proposto", ""),
        ("municipio_sede_proposto", ""),
    ]:
        if coluna not in df.columns:
            df[coluna] = valor
    return df

with st.sidebar:
    st.header("Base nacional")
    arquivo = st.file_uploader(
        "Importar classificação A–D (CSV ou Excel)",
        type=["csv", "xlsx"], key="arquivo_nacional"
    )
    st.caption("Origem: aba 'Classificação A-D app 2026', da matriz nacional no Google Drive.")
    st.link_button(
        "Abrir matriz de referência",
        "https://docs.google.com/spreadsheets/d/1zaR85SZIM3LxaA07eqWejr45emIFPX4JHDSeLYlRgM8/edit"
    )

st.subheader("Rede PROFGEO — polos de referência")
polos = ler_polos()
if not polos.empty and {"lat", "lon"}.issubset(polos.columns):
    polos["lat"] = pd.to_numeric(polos["lat"], errors="coerce")
    polos["lon"] = pd.to_numeric(polos["lon"], errors="coerce")
    polos = polos.dropna(subset=["lat", "lon"])
    if not polos.empty:
        camada = pdk.Layer(
            "ScatterplotLayer", data=polos,
            get_position="[lon, lat]", get_radius=7500,
            radius_min_pixels=5, radius_max_pixels=11,
            get_fill_color=[24, 75, 138, 240], pickable=True
        )
        mapa = pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=-14.5, longitude=-52.5, zoom=3.4),
            layers=[camada],
            tooltip={"text": "{polo}"}
        )
        st.pydeck_chart(mapa, use_container_width=True)
    else:
        st.info("Coordenadas dos polos não disponíveis.")
else:
    st.info("Arquivo de polos da rede não disponível.")
st.caption("O mapa mostra somente polos existentes; não contém candidaturas demonstrativas.")

st.subheader("Ranking nacional — grupos A–D")
fonte = carregar_tabela(arquivo) if arquivo is not None else ler_nacional_local()
if fonte is None:
    st.info(
        "Importe o CSV da aba 'Classificação A-D app 2026' para consultar os 222 "
        "registros. A tela não carrega candidaturas simuladas."
    )
else:
    try:
        nacional = preparar_nacional(fonte)
        contagens = nacional["grupo_operacional_app"].value_counts()
        metricas = st.columns(4)
        for coluna, grupo in zip(metricas, GRUPOS):
            coluna.metric("Grupo " + grupo, int(contagens.get(grupo, 0)))
        st.caption(
            f"{len(nacional)} combinações IES–município. A classificação A–D é operacional "
            "e independente da validação de candidatura e do campus-sede."
        )
        filtros = st.columns(3)
        with filtros[0]:
            grupos = st.multiselect(
                "Grupo", list(GRUPOS), default=list(GRUPOS), key="grupo_nacional"
            )
        with filtros[1]:
            ufs = st.multiselect(
                "UF", sorted(nacional["UF"].unique()),
                default=sorted(nacional["UF"].unique()), key="uf_nacional"
            )
        with filtros[2]:
            somente_fora = st.checkbox("Somente fora da rede atual", value=False)
        selecao = nacional[
            nacional["grupo_operacional_app"].isin(grupos) & nacional["UF"].isin(ufs)
        ].copy()
        if somente_fora:
            if "rede_PROFGEO_2026_IES_associada" in selecao.columns:
                selecao = selecao[
                    selecao["rede_PROFGEO_2026_IES_associada"].str.lower().eq("false")
                ]
            else:
                st.warning("O arquivo não possui coluna de associação à rede.")
        exibicao = [
            "posicao_triagem_total", "instituicao", "municipio_nome_IBGE", "UF",
            "grupo_operacional_app", "grupo_estrutural",
            "status_validacao_institucional", "campus_sede_proposto",
            "municipio_sede_proposto", "dist_polo_km", "REGIC_2018",
            "rede_PROFGEO_2026_IES_associada",
        ]
        st.dataframe(
            selecao[[c for c in exibicao if c in selecao.columns]],
            hide_index=True, use_container_width=True
        )
        st.download_button(
            "Baixar seleção (CSV)",
            selecao.to_csv(index=False).encode("utf-8-sig"),
            file_name="profgeo_ranking_nacional_ad_2026.csv",
            mime="text/csv"
        )
        with st.expander("Critérios e limites metodológicos"):
            for letra, descricao in GRUPOS.items():
                st.write(f"**{letra} —** {descricao}.")
            st.write(
                "Os 222 registros representam ofertas de graduação presencial em Geografia "
                "na combinação IES–município (INEP 2024), e não todos os campi do país. "
                "Os Institutos Federais podem propor campus-sede distinto daquele "
                "registrado na oferta de graduação. A distância existente refere-se "
                "ao município da oferta INEP e deve ser recalculada para o campus proposto."
            )
            st.write(
                "As verificações de candidatura, linhas de pesquisa, estrutura e "
                "campus-sede continuam independentes da classificação A–D."
            )
    except Exception as exc:
        st.error(f"Não foi possível analisar a matriz: {exc}")
