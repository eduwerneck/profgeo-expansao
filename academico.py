"""Consulta acadêmica complementar, sem alterar a prioridade territorial.

Fonte INEP: Censo Superior 2024, oferta de graduação em Geografia.
Fonte CAPES: Sucupira 2024, cursos cuja área de conhecimento é Geografia.
Linhas de pesquisa em ensino NÃO são verificáveis nessas duas tabelas.
"""
from pathlib import Path
import unicodedata
import pandas as pd

BASE=Path(__file__).resolve().parent
ALIAS_IES={
    "UEL": "UNIVERSIDADE ESTADUAL DE LONDRINA",
    "UNESP": "UNIVERSIDADE ESTADUAL PAULISTA",
    "UFMT": "UNIVERSIDADE FEDERAL DE MATO GROSSO",
}
def normalizar(valor):
    return "".join(ch for ch in unicodedata.normalize("NFKD",str(valor or "").upper())
                   if not unicodedata.combining(ch)).strip()

def carregar_csv(nome):
    arq=BASE/nome
    if not arq.exists():return None
    return pd.read_csv(arq, dtype=str,encoding="utf-8-sig").fillna("")

def diagnosticar_academia(candidatos):
    """Uma linha por candidatura. Nada é presumido em instituições simuladas.

    Códigos IES são comparados com o e-MEC da CAPES; sempre se exige
    correspondência territorial adicional para afirmar oferta local.
    """
    inep=carregar_csv("inep_geografia_2024.csv")
    capes=carregar_csv("capes_geografia_2024.csv")
    resultados=[]
    if inep is not None:
        inep["municipio_ibge"]=inep["municipio_ibge"].astype(str).str.replace(r"\.0$","",regex=True).str.zfill(7)
        inep["_nome_ies"]=inep["nome_ies"].apply(normalizar)
        inep["_codigo_ies"]=inep["codigo_ies"].astype(str).str.lstrip("0")
    if capes is not None:
        capes["_municipio"]=capes["municipio"].apply(normalizar)
        capes["_uf"]=capes["uf"].astype(str).str.upper().str.strip()
        capes["_codigo_ies"]=capes["emec_ies"].astype(str).str.replace(r"\.0$","",regex=True).str.lstrip("0")
    for _, c in candidatos.iterrows():
        inst=str(c.get("instituicao","")).strip()
        mun=str(c.get("municipio","")).strip()
        uf=str(c.get("uf","")).strip().upper()
        codigo=str(c.get("codigo_ibge","")).strip().replace(".0","").zfill(7)
        alias=ALIAS_IES.get(inst.upper())
        c_inep=pd.DataFrame()
        c_capes=pd.DataFrame()
        id_ies=""
        if inep is not None:
            municipio=inep[inep["municipio_ibge"].eq(codigo)]
            if alias:
                # Não escolher uma instituição por mera coincidência municipal.
                matches=municipio[municipio["_nome_ies"].str.contains(alias,regex=False)]
                ids=sorted(set(matches["_codigo_ies"].astype(str)))
                if len(ids)==1:
                    id_ies=ids[0]
                    c_inep=matches.copy()
            else:
                # Apenas diagnóstico territorial para localidades simuladas.
                c_inep=municipio.copy()
        if capes is not None:
            municipio=capes[capes["_municipio"].eq(normalizar(mun)) & capes["_uf"].eq(uf)]
            if alias:
                # CAPES permite identificar a instituição pela denominação e
                # pelo município mesmo antes de concluir a extração INEP.
                # O e-MEC é conferido quando o INEP estiver disponível.
                candidatos_capes=municipio[
                    municipio["nome_ies"].apply(normalizar).str.contains(alias,regex=False)
                ].copy()
                if id_ies:
                    candidatos_capes=candidatos_capes[
                        candidatos_capes["_codigo_ies"].eq(id_ies)
                    ]
                ids_capes=set(candidatos_capes["_codigo_ies"].dropna().astype(str))
                if len(ids_capes)==1:
                    c_capes=candidatos_capes
            else:
                c_capes=municipio.copy()
        disponiveis=(inep is not None) and (capes is not None)
        tem_vinculo=bool(alias and id_ies)
        presenciais=(c_inep["modalidade_cod"].astype(str).str.strip().eq("1").sum()
                     if not c_inep.empty and "modalidade_cod" in c_inep else None)
        programas=(c_capes.loc[
            c_capes["situacao"].apply(normalizar).eq("EM FUNCIONAMENTO"),
            "codigo_programa"
        ].nunique() if not c_capes.empty and "codigo_programa" in c_capes else 0)
        projetos=(c_capes.loc[
            c_capes["situacao"].apply(normalizar).eq("EM PROJETO"),
            "codigo_programa"
        ].nunique() if not c_capes.empty and "codigo_programa" in c_capes else 0)
        cursos_ativos=(int(c_capes["situacao"].apply(normalizar).eq("EM FUNCIONAMENTO").sum())
                      if not c_capes.empty and "situacao" in c_capes else 0)
        graduacoes=(c_inep["codigo_curso"].nunique()
                    if not c_inep.empty and "codigo_curso" in c_inep else 0)
        matr=None
        if not c_inep.empty and "matriculas" in c_inep:
            valores=pd.to_numeric(c_inep["matriculas"].replace("",pd.NA),errors="coerce")
            if valores.notna().any():matr=int(valores.sum())
        tipo="Pendente"
        if disponiveis and tem_vinculo:
            if programas>0:tipo="A (a conferir)"
            elif presenciais and presenciais>0:tipo="B (a conferir)"
        if capes is not None and inep is None:
            status=("CAPES 2024 vinculada; graduação INEP pendente" if alias and not c_capes.empty
                    else "CAPES 2024: diagnóstico municipal; instituição não definida" if not alias
                    else "CAPES 2024: programa não encontrado na instituição/local; INEP pendente")
        elif not disponiveis:status="Aguardando processamento de INEP/CAPES"
        elif not alias:status="Município simulado; sem instituição candidata vinculada"
        elif not tem_vinculo:status="IES não identificada univocamente no município pelo INEP"
        else:status="Vínculo IES/município confirmado; avaliação acadêmica preliminar"
        resultados.append({
            "Instituição":inst, "Município/UF":f"{mun}/{uf}",
            "Código IES (INEP)":id_ies or "",
            "Graduações em Geografia (INEP)":graduacoes if inep is not None else None,
            "Cursos presenciais em Geografia (INEP)":presenciais,
            "Matrículas em Geografia (INEP)":matr,
            "Programas em funcionamento (CAPES)":programas if capes is not None else None,
            "Cursos em funcionamento (CAPES)":cursos_ativos if capes is not None else None,
            "Programas com curso em projeto (CAPES)":projetos if capes is not None else None,
            "Categoria acadêmica sugerida":tipo,
            "Estado de verificação":status,
        })
    return pd.DataFrame(resultados)
