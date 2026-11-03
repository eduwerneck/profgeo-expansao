import pandas as pd
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
modelo_polos = pd.read_csv("polos_modelo.csv")
esq, dir = st.columns(2)
with esq:
    st.subheader("Candidaturas")
    arquivo = st.file_uploader("Importar candidaturas CSV", type="csv", key="c")
    candidatos = pd.read_csv(arquivo, keep_default_na=False) if arquivo else base
    candidatos = st.data_editor(candidatos, num_rows="dynamic", hide_index=True, use_container_width=True)
    st.download_button("Baixar modelo de candidaturas", base.to_csv(index=False).encode("utf-8-sig"), "candidatos_exemplo.csv", "text/csv")
with dir:
    st.subheader("Polos existentes na data de referência")
    arquivo_polos = st.file_uploader("Importar polos existentes CSV", type="csv", key="p")
    polos = pd.read_csv(arquivo_polos) if arquivo_polos else modelo_polos
    polos = st.data_editor(polos, num_rows="dynamic", hide_index=True, use_container_width=True)
    st.download_button("Baixar modelo de polos", modelo_polos.to_csv(index=False).encode("utf-8-sig"), "polos_modelo.csv", "text/csv")
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
