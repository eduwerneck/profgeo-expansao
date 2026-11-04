"""PROFGEO Expansão — interface cartográfica simplificada."""
import math
import json
from io import BytesIO
import unicodedata
from pathlib import Path
import pandas as pd
import pydeck as pdk
import streamlit as st
from engine import avaliar, distancia_km
from ranking_regic import ordenar_cenarios
from academico import diagnosticar_academia

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
    return pd.read_csv("candidatos_exemplo.csv", dtype={"codigo_ibge": str}, keep_default_na=False)

def ler_candidaturas_enviadas(arquivo):
    if arquivo is None:
        return ler_pilotos().copy()
    if arquivo.name.lower().endswith(".xlsx"):
        return pd.read_excel(arquivo, dtype={"codigo_ibge": str}, keep_default_na=False, engine="openpyxl")
    return pd.read_csv(arquivo, dtype={"codigo_ibge": str}, keep_default_na=False)

def montar_planilha_excel(df, nome_aba):
    memoria = BytesIO()
    with pd.ExcelWriter(memoria, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=nome_aba, index=False)
        ws = writer.sheets[nome_aba]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        from openpyxl.styles import PatternFill, Font, Alignment
        for celula in ws[1]:
            celula.fill = PatternFill("solid", fgColor="173B5F")
            celula.font = Font(color="FFFFFF", bold=True)
            celula.alignment = Alignment(wrap_text=True)
        for coluna in ws.columns:
            letra = coluna[0].column_letter
            maior = max(len(str(celula.value or "")) for celula in coluna)
            ws.column_dimensions[letra].width = min(max(maior+2, 13), 52)
    return memoria.getvalue()

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

@st.cache_data(show_spinner=False)
def indice_municipios():
    # Índice tabular leve; não carregar as geometrias municipais para consultar REGIC.
    caminho = Path("indice_municipios_profgeo.csv")
    if not caminho.exists():
        return {}
    tabela = pd.read_csv(caminho, dtype={"codigo_ibge": str}, keep_default_na=False)
    return {
        (chave_nome(r.municipio), str(r.uf).upper().strip()): str(r.codigo_ibge).zfill(7)
        for r in tabela.itertuples()
    }

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
    # Não enviar 5570 polígonos municipais ao navegador.
    # Camada agregada de quatro classes tem geometria muito mais compacta.
    malha = Path("cobertura_profgeo_agregada.geojson")
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
if not Path("cobertura_profgeo_agregada.geojson").exists():
    st.info("Camada cartográfica agregada em preparação; exibindo cobertura provisória até a publicação automática.")
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

st.download_button("Baixar modelo com seis localidades (Excel XLSX)",
                   montar_planilha_excel(ler_pilotos(), "Candidaturas"),
                   "candidaturas_simulacao_6.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.form("controles_expansao"):
    arq_candidatos = st.file_uploader("Carregar candidaturas (Excel XLSX ou CSV)", type=["xlsx", "csv"])
    calcular = st.form_submit_button("Calcular expansão", type="primary", use_container_width=True)

if calcular:
    try:
        candidatos = normalizar_candidatos(ler_candidaturas_enviadas(arq_candidatos))
        resultado = ordenar_cenarios(anexar_regic(avaliar(candidatos, sedes_padrao)))
        st.session_state["resultado_expansao"] = resultado
        st.session_state["versao_mapa"] = st.session_state.get("versao_mapa", 0) + 1
        st.rerun()
    except Exception as exc:
        st.error(f"Não foi possível calcular: {exc}")

if resultados is not None and not resultados.empty:
    st.subheader("Ranking preliminar das candidaturas")
    regic_disponivel = (
        "rank_cenario_regic" in resultados.columns
        and resultados["rank_cenario_regic"].notna().all()
    )
    tabela = resultados.copy()
    if regic_disponivel:
        tabela = tabela.sort_values("rank_cenario_regic", kind="stable")
        tabela["Posição"] = tabela["rank_cenario_regic"].astype(int)
        st.caption("A REGIC 2018 atua apenas como desempate: dentro da mesma categoria A1–B4 validada; enquanto A/B estiver pendente, dentro da mesma faixa territorial provisória. Distância exata resolve empates residuais. Não é uma decisão institucional.")
    else:
        tabela = tabela.sort_values("rank_base", kind="stable") if "rank_base" in tabela else tabela.sort_values("distancia_km", ascending=False, kind="stable")
        tabela["Posição"] = range(1, len(tabela) + 1)
        st.info("Ranking provisório")
    tabela["Instituição / campus"] = tabela["instituicao"].astype(str) + " — " + tabela["campus"].astype(str)
    tabela["Município / UF"] = tabela["municipio"].astype(str) + " / " + tabela["uf"].astype(str)
    tabela["Prioridade territorial"] = tabela["distancia_km"].apply(
        lambda d: "Alta" if d > 300 else "Moderada" if d > 200 else "Baixa" if d > 100 else "Muito baixa"
    )
    tabela["REGIC 2018"] = tabela["hierarquia_regic"] if "hierarquia_regic" in tabela else "Não verificada"
    tabela["Mudança com REGIC"] = (
        tabela["variacao_posicoes"].apply(lambda n: f"+{int(n)}" if n > 0 else str(int(n)))
        if regic_disponivel else "—"
    )
    colunas = ["Posição", "Instituição / campus", "Município / UF",
               "distancia_km", "REGIC 2018", "Prioridade territorial", "Mudança com REGIC"]
    def colorir_prioridade(valor):
        cores = {"Alta": "#F5D5D2", "Moderada": "#FCE8BA", "Baixa": "#E3F2D4", "Muito baixa": "#CBE8D8"}
        return "background-color: " + cores.get(valor, "transparent") + ";color:#17212b"
    quadro = tabela[colunas].rename(columns={"distancia_km": "Distância (km)"})
    st.dataframe(
        quadro.style.map(colorir_prioridade, subset=["Prioridade territorial"]),
        hide_index=True, use_container_width=True,
        column_config={
            "Posição": st.column_config.NumberColumn("Ranking", format="%dº", width="small"),
            "Distância (km)": st.column_config.NumberColumn("Distância (km)", format="%.1f", width="small"),
            "Mudança com REGIC": st.column_config.TextColumn("Variação", width="small"),
        },
    )
    st.caption("As cores mostram exclusivamente a proximidade à rede. A REGIC nunca altera a ordem entre categorias A1–B4 distintas; enquanto essas categorias não estiverem validadas, só desempata dentro de cada faixa territorial. Dados acadêmicos ainda precisam de validação.")
    with st.expander("Evidências acadêmicas — INEP e CAPES 2024", expanded=False):
        st.caption("Quadro complementar de oferta de graduação em Geografia e pós-graduação vinculada à área de Geografia. O vínculo é verificado por instituição e município. Para localidades simuladas, os totais são municipais e não representam uma candidatura institucional.")
        quadro_academico = diagnosticar_academia(resultados)
        st.dataframe(quadro_academico, hide_index=True, use_container_width=True)
        st.caption("Categorias A/B indicadas como 'a conferir' são sugestões, não classificação aprovada. A base de cursos CAPES não comprova linhas de pesquisa em ensino de Geografia. Estes indicadores não alteram o ranking até a conclusão da validação.")
    with st.expander("Exportação e dados técnicos", expanded=False):
        st.download_button("Baixar ranking completo (Excel XLSX)",
                           montar_planilha_excel(quadro, "Ranking"),
                           "ranking_expansao_profgeo.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Baixar resultados completos (CSV)",
                           resultados.to_csv(index=False).encode("utf-8-sig"),
                           "diagnostico_expansao_profgeo.csv", mime="text/csv")
else:
    st.caption("Carregue uma planilha XLSX/CSV ou utilize as seis localidades demonstrativas; clique em Calcular expansão para exibir o ranking.")


# Painel nacional A-D: independente da simulação de candidaturas acima.
st.divider()
st.header("Matriz nacional — classificação operacional A–D (2026)")
st.caption(
    "A/B reproduzem indícios acadêmicos; C identifica registros de Institutos Federais "
    "multicampi; D descreve outras configurações que requerem análise específica. "
    "Essas letras não comprovam elegibilidade nem candidatura formal."
)
st.info(
    "O levantamento original contém 222 combinações IES–município com graduação "
    "presencial em Geografia. Campi sem essa graduação, como IFC Brusque, podem "
    "estar fora do universo. O município da oferta INEP não é automaticamente o "
    "campus-sede de uma futura candidatura."
)
fonte_nacional = st.file_uploader(
    "Importar a aba 'Classificação A-D app 2026' como CSV ou Excel",
    type=["csv", "xlsx"], key="fonte_nacional_ad"
)
if fonte_nacional is not None:
    try:
        if fonte_nacional.name.lower().endswith(".xlsx"):
            base_nacional = pd.read_excel(fonte_nacional, dtype=str, keep_default_na=False)
        else:
            base_nacional = pd.read_csv(
                fonte_nacional, dtype=str, keep_default_na=False, encoding="utf-8-sig"
            )
        obrigatorias = {"instituicao", "municipio_nome_IBGE", "UF", "grupo_estrutural"}
        if not obrigatorias.issubset(base_nacional.columns):
            raise ValueError(
                "Colunas ausentes: " + ", ".join(sorted(obrigatorias - set(base_nacional.columns)))
            )
        nacional = base_nacional.copy()
        # Compatibilidade com o CSV original, sem modificar os resultados históricos.
        if "grupo_operacional_app" not in nacional:
            eh_if = nacional["instituicao"].str.upper().str.startswith("INSTITUTO FEDERAL DE EDUCAÇÃO")
            nacional["grupo_operacional_app"] = nacional["grupo_estrutural"].where(
                nacional["grupo_estrutural"].isin(["A", "B"]), "D"
            )
            nacional.loc[eh_if, "grupo_operacional_app"] = "C"
        if "status_validacao_institucional" not in nacional:
            nacional["status_validacao_institucional"] = "Não verificada"
        if "campus_sede_proposto" not in nacional:
            nacional["campus_sede_proposto"] = ""
        if "municipio_sede_proposto" not in nacional:
            nacional["municipio_sede_proposto"] = ""
        contagens = nacional["grupo_operacional_app"].value_counts()
        a, b, c, d = st.columns(4)
        for painel, grupo in zip((a, b, c, d), ("A", "B", "C", "D")):
            painel.metric("Grupo " + grupo, int(contagens.get(grupo, 0)))
        if nacional["grupo_operacional_app"].isin(["A", "B", "C", "D"]).all():
            st.success("Todos os registros importados possuem classificação operacional.")
        else:
            st.warning("Há códigos fora de A–D; confira a fonte antes de usar o ranking.")
        if "rede_PROFGEO_2026_IES_associada" in nacional:
            somente_fora = st.checkbox(
                "Exibir apenas instituições fora da rede atual", value=False,
                key="filtro_fora_rede_nacional"
            )
            if somente_fora:
                nacional = nacional[
                    nacional["rede_PROFGEO_2026_IES_associada"].astype(str).str.lower().eq("false")
                ]
        grupos_filtro = st.multiselect(
            "Grupos operacionais", ["A", "B", "C", "D"],
            default=["A", "B", "C", "D"], key="grupos_ad"
        )
        nacional = nacional[nacional["grupo_operacional_app"].isin(grupos_filtro)]
        exibicao = [
            "instituicao", "municipio_nome_IBGE", "UF", "grupo_estrutural",
            "grupo_operacional_app", "status_validacao_institucional",
            "campus_sede_proposto", "municipio_sede_proposto",
            "rede_PROFGEO_2026_IES_associada", "dist_polo_km",
            "REGIC_2018"
        ]
        st.dataframe(nacional[[c for c in exibicao if c in nacional]],
                     hide_index=True, use_container_width=True)
        st.download_button(
            "Baixar seleção nacional (CSV)",
            nacional.to_csv(index=False).encode("utf-8-sig"),
            "profgeo_matriz_nacional_ad_2026.csv", mime="text/csv",
            key="download_nacional_ad"
        )
        st.caption(
            "Distância original: município de oferta do INEP ao polo mais próximo. "
            "Ao definir outro campus-sede, será necessário geocodificar esse campus "
            "e recalcular a distância. Validação institucional permanece independente."
        )
    except Exception as exc:
        st.error(f"Não foi possível ler a matriz nacional: {exc}")
