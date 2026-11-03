"""Extrai registros de Geografia da CAPES 2024 preservando instituição e município.

Entradas: planilha pública da CAPES, versão 2025-12-01 (ano-base 2024).
Saída: capes_geografia_2024.csv; não comprova linha de pesquisa em ensino.
"""
import os
import re
import unicodedata
import urllib.request
from pathlib import Path
import pandas as pd

URL = ("https://dadosabertos.capes.gov.br/dataset/"
       "3a1264d8-b17c-4e6f-9282-601d04049e7b/resource/"
       "d024d60f-6876-41d3-b50d-da1a2e49bf39/download/"
       "br-capes-colsucup-curso-2024-2025-12-01.xlsx")
BASE = Path(__file__).resolve().parent

def normalizar(value):
    return "".join(c for c in unicodedata.normalize("NFKD",str(value or "").upper())
                   if not unicodedata.combining(c)).strip()

def extrair(caminho):
    xls = pd.ExcelFile(caminho)
    df = None
    for sheet in xls.sheet_names:
        d = pd.read_excel(caminho, sheet_name=sheet, dtype=str)
        d.columns = [str(c).strip().upper() for c in d.columns]
        if {"NM_AREA_CONHECIMENTO","NM_MUNICIPIO_PROGRAMA_IES","SG_ENTIDADE_ENSINO"}.issubset(d.columns):
            df=d
            break
    if df is None:
        raise ValueError("Planilha CAPES sem as colunas obrigatórias da documentação. Abas: "+str(xls.sheet_names))
    if "AN_BASE" in df:
        df=df[df["AN_BASE"].astype(str).str.contains("2024",regex=False,na=False)]
    # Área do conhecimento Geografia (não qualquer programa com geografia no nome).
    mask=df["NM_AREA_CONHECIMENTO"].apply(normalizar).eq("GEOGRAFIA")
    rec=df[mask].copy()
    if rec.empty:
        raise ValueError("Nenhum curso com NM_AREA_CONHECIMENTO = GEOGRAFIA foi encontrado.")
    cols=["CD_ENTIDADE_CAPES","CD_ENTIDADE_EMEC","SG_ENTIDADE_ENSINO","NM_ENTIDADE_ENSINO",
          "SG_UF_PROGRAMA","NM_MUNICIPIO_PROGRAMA_IES","CD_PROGRAMA_IES",
          "NM_PROGRAMA_IES","NM_CURSO","NM_GRAU_CURSO","NM_AREA_CONHECIMENTO",
          "DS_SITUACAO_CURSO","AN_BASE"]
    for col in cols:
        if col not in rec:rec[col]=""
    rec=rec[cols].fillna("").drop_duplicates()
    rec.columns=["capes_ies","emec_ies","sigla_ies","nome_ies","uf","municipio",
                 "codigo_programa","programa","curso","grau","area","situacao","ano"]
    rec["fonte"]="CAPES Sucupira — cursos 2024, extração 2025-12-01"
    rec["status_linha_ensino"]="Não verificada nesta base (exige linhas de pesquisa)"
    return rec

def main():
    arquivo=BASE/"capes_cursos_2024_fonte.xlsx"
    if not arquivo.exists():
        print("Obtendo a planilha CAPES 2024 da fonte pública...")
        urllib.request.urlretrieve(URL,arquivo)
    rec=extrair(arquivo)
    saida=BASE/"capes_geografia_2024.csv"
    rec.to_csv(saida,index=False,encoding="utf-8-sig")
    print(f"{len(rec)} registros de curso; {rec['codigo_programa'].nunique()} programas; {rec['sigla_ies'].nunique()} IES")
    for mun in ["LONDRINA","MONTES CLAROS","BELO HORIZONTE",
                "VITORIA DA CONQUISTA","PRESIDENTE PRUDENTE","BARRA DO GARCAS"]:
        sub=rec[rec["municipio"].apply(normalizar).eq(mun)]
        print(mun,":",len(sub),"registros;",sorted(sub["sigla_ies"].dropna().unique().tolist()))
    os.unlink(arquivo)

if __name__=="__main__":
    main()
