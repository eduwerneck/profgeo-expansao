"""Extrai registros de Geografia da CAPES 2024 preservando instituição e município.

Entradas: planilha pública da CAPES, versão 2025-12-01 (ano-base 2024).
Saída: capes_geografia_2024.csv; não comprova linha de pesquisa em ensino.
"""
import os
import re
import unicodedata
import requests
import time
import zipfile
from pathlib import Path
import pandas as pd

URL = ("https://dadosabertos.capes.gov.br/dataset/"
       "3a1264d8-b17c-4e6f-9282-601d04049e7b/resource/"
       "d024d60f-6876-41d3-b50d-da1a2e49bf39/download/"
       "br-capes-colsucup-curso-2024-2025-12-01.xlsx")
URL_CSV = "https://dadosabertos.capes.gov.br/dataset/3a1264d8-b17c-4e6f-9282-601d04049e7b/resource/4939da83-fe0f-41f7-b4aa-f9b6c2a28981/download/br-capes-colsucup-curso-2024-2025-12-01.csv"
BASE = Path(__file__).resolve().parent

def normalizar(value):
    return "".join(c for c in unicodedata.normalize("NFKD",str(value or "").upper())
                   if not unicodedata.combining(c)).strip()

def extrair(caminho):
    df = None
    exigidas = {"NM_AREA_CONHECIMENTO", "NM_MUNICIPIO_PROGRAMA_IES", "SG_ENTIDADE_ENSINO"}
    if caminho.suffix.lower() == ".xlsx":
        arquivo = pd.ExcelFile(caminho)
        for aba in arquivo.sheet_names:
            dados = pd.read_excel(caminho, sheet_name=aba, dtype=str)
            dados.columns = [str(x).strip().upper() for x in dados.columns]
            if exigidas.issubset(dados.columns):
                df = dados
                break
    else:
        for codificacao in ("utf-8-sig", "latin1"):
            for sep in (";", ","):
                try:
                    dados = pd.read_csv(caminho, encoding=codificacao, sep=sep, dtype=str, low_memory=False)
                    dados.columns = [str(x).strip().upper() for x in dados.columns]
                    if exigidas.issubset(dados.columns):
                        df = dados
                        break
                except (UnicodeError, ValueError):
                    pass
            if df is not None:
                break
    if df is None:
        raise ValueError("Arquivo CAPES sem as colunas obrigatorias: " + str(caminho))
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

def extrair_api_capes():
    """Terceira via: API oficial CKAN Datastore (dados de 2024)."""
    import requests
    endpoint = "https://dadosabertos.capes.gov.br/api/3/action/datastore_search"
    recurso = "4939da83-fe0f-41f7-b4aa-f9b6c2a28981"
    registros = []
    offset = 0
    while True:
        resposta = requests.get(
            endpoint,
            params={"resource_id": recurso, "limit": 1000, "offset": offset},
            headers={"User-Agent": "PROFGEO-academic-validation/1.0"},
            timeout=(15, 35),
        )
        resposta.raise_for_status()
        payload = resposta.json()
        if not payload.get("success"):
            raise RuntimeError("CKAN retornou success=false")
        lote = payload["result"].get("records", [])
        if not lote:
            break
        registros.extend(lote)
        offset += len(lote)
        total = payload["result"].get("total", 0)
        print(f"CAPES CKAN: {offset}/{total} registros", flush=True)
        if total and offset >= total:
            break
        if offset > 20000:
            raise ValueError("API CAPES retornou mais de 20 mil cursos: verificar recurso")
    if not registros:
        raise RuntimeError("API CAPES retornou zero registros")
    tabela = pd.DataFrame(registros).drop(columns=["_id"], errors="ignore")
    tabela.columns = [str(col).strip().upper() for col in tabela.columns]
    exigidas = {"NM_AREA_CONHECIMENTO", "NM_MUNICIPIO_PROGRAMA_IES", "SG_ENTIDADE_ENSINO"}
    if not exigidas.issubset(tabela.columns):
        raise ValueError(f"API CAPES sem campos obrigatorios: {sorted(exigidas - set(tabela.columns))}")
    caminho = BASE / "capes_cursos_2024_fonte_api.csv"
    tabela.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho

def baixar_fonte():
    """Tenta XLSX e, em caso de falha, CSV da mesma fonte CAPES oficial."""
    local = BASE / "capes_cursos_2024_fonte.xlsx"
    if local.exists() and local.stat().st_size > 10000:
        if not zipfile.is_zipfile(local):
            raise ValueError("Planilha CAPES local XLSX invalida")
        print("CAPES: fonte local fornecida pelo usuario; sem acesso externo.", flush=True)
        return local
    falhas = []
    for url, extensao in ((URL_CSV, "csv"), (URL, "xlsx")):
        destino = BASE / ("capes_cursos_2024_fonte." + extensao)
        for tentativa in range(1, 3):
            try:
                with requests.get(url, stream=True, timeout=(15, 35), headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"}) as resposta:
                    resposta.raise_for_status()
                    with destino.open("wb") as saida:
                        for bloco in resposta.iter_content(chunk_size=65536):
                            if bloco:
                                saida.write(bloco)
                if destino.stat().st_size < 10000:
                    raise ValueError("Arquivo vazio/incompleto")
                if extensao == "xlsx" and not zipfile.is_zipfile(destino):
                    raise ValueError("XLSX invalido")
                print(f"CAPES {extensao}: {destino.stat().st_size} bytes", flush=True)
                return destino
            except Exception as erro:
                falhas.append(f"{extensao} tentativa {tentativa}: {type(erro).__name__}: {erro}")
                destino.unlink(missing_ok=True)
                time.sleep(tentativa * 2)
    try:
        return extrair_api_capes()
    except Exception as exc:
        falhas.append("CKAN API: " + repr(exc))
    raise RuntimeError("Fontes CAPES indisponiveis: " + " | ".join(falhas))

def main():
    arquivo = baixar_fonte()
    try:
        rec = extrair(arquivo)
        saida = BASE / "capes_geografia_2024.csv"
        rec.to_csv(saida, index=False, encoding="utf-8-sig")
        print(f"CAPES: {len(rec)} cursos; {rec.codigo_programa.nunique()} programas; {rec.sigla_ies.nunique()} IES", flush=True)
        for mun in ["LONDRINA", "MONTES CLAROS", "BELO HORIZONTE", "VITORIA DA CONQUISTA", "PRESIDENTE PRUDENTE", "BARRA DO GARCAS"]:
            sub = rec[rec["municipio"].apply(normalizar).eq(mun)]
            print(mun, len(sub), sorted(sub["sigla_ies"].unique().tolist()), flush=True)
    finally:
        arquivo.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
