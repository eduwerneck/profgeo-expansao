"""Filtra cursos de graduação em Geografia nos microdados oficiais INEP 2024.

Saída apenas acadêmica, sem atribuir categorias A/B; preserva o código IES,
código municipal, modalidade, grau, matrículas e rastreabilidade.
Usa processamento em blocos e não publica o ZIP de centenas de MB.
"""
import csv
import os
import re
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
URL = "https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_2024.zip"
ARQ = ROOT / "inep_censo_superior_2024_fonte.zip"
SAIDA = ROOT / "inep_geografia_2024.csv"

def norm(value):
    return "".join(ch for ch in unicodedata.normalize("NFKD",str(value or "").upper())
                   if not unicodedata.combining(ch)).strip()

def escolher_coluna(colunas,*possibilidades):
    mapa={norm(c):c for c in colunas}
    for c in possibilidades:
        if norm(c) in mapa:return mapa[norm(c)]
    return None

def baixar():
    """Usa certificados válidos; preserva ZIP local fornecido pelo usuário."""
    import requests
    import certifi
    if ARQ.exists() and ARQ.stat().st_size > 1000000:
        if not zipfile.is_zipfile(ARQ):
            raise ValueError("O ZIP local do INEP está corrompido")
        print('Fonte INEP local validada; download dispensado.', flush=True)
        return
    url = os.environ.get("INEP_2024_URL", URL)
    erros = []
    for tentativa in range(1, 5):
        try:
            with requests.get(url, stream=True, timeout=(25, 150),
                              headers={"User-Agent": "Mozilla/5.0",
                                       "Accept-Encoding": "identity"},
                              verify=certifi.where()) as resposta:
                resposta.raise_for_status()
                with ARQ.open("wb") as arq:
                    for bloco in resposta.iter_content(chunk_size=1024*1024):
                        if bloco:
                            arq.write(bloco)
            if ARQ.stat().st_size < 1000000 or not zipfile.is_zipfile(ARQ):
                raise ValueError("ZIP INEP invalido ou incompleto")
            print(f'INEP: fonte oficial recebida ({ARQ.stat().st_size} bytes).', flush=True)
            return
        except Exception as exc:
            erros.append(f'{tentativa}: {type(exc).__name__}: {exc}')
            ARQ.unlink(missing_ok=True)
            print('Falha download INEP: ' + erros[-1], flush=True)
            time.sleep(min(3*tentativa,12))
    raise RuntimeError("INEP indisponivel com SSL verificado: " + " | ".join(erros))

def analisar_csv(z, nome):
    print("Lendo CSV:",nome,flush=True)
    for encoding in ("latin1","utf-8-sig"):
        for separador in (";", ","):
            try:
                with z.open(nome) as arq:
                    import io
                    f=io.TextIOWrapper(arq,encoding=encoding)
                    cab=f.readline()
                col=[x.strip().strip('"') for x in next(csv.reader([cab],delimiter=separador))]
                if escolher_coluna(col,"NO_CURSO","NM_CURSO") and escolher_coluna(col,"CO_IES"):
                    return encoding,separador,col
            except (UnicodeError,UnicodeDecodeError):continue
    return None

def main():
    baixar()
    with zipfile.ZipFile(ARQ) as z:
        nomes=[n for n in z.namelist() if n.lower().endswith(".csv")]
        print("Arquivos CSV no ZIP:",len(nomes),flush=True)
        alvos=[n for n in nomes if "CURSO" in norm(n) and "DOCENTE" not in norm(n)]
        candidatos=alvos or nomes
        resultados=[]
        lidos=0
        for nome in candidatos:
            config=analisar_csv(z,nome)
            if not config:continue
            encoding,sep,colunas=config
            print("Colunas selecionadas:",colunas[:45],flush=True)
            curso=escolher_coluna(colunas,"NO_CURSO","NM_CURSO")
            ies=escolher_coluna(colunas,"CO_IES")
            codmun=escolher_coluna(colunas,"CO_MUNICIPIO","CO_MUNICIPIO_CURSO")
            modalidade=escolher_coluna(colunas,"TP_MODALIDADE_ENSINO")
            grau=escolher_coluna(colunas,"TP_GRAU_ACADEMICO")
            matr=escolher_coluna(colunas,"QT_MAT","QT_MATRICULA","QT_MATRICULAS")
            uf=escolher_coluna(colunas,"SG_UF","NO_UF","CO_UF")
            codigo=escolher_coluna(colunas,"CO_CURSO")
            if not codmun:
                raise ValueError("Microdados INEP sem código de município do curso; suspenso vínculo territorial")
            with z.open(nome) as arq:
                import io
                f=io.TextIOWrapper(arq,encoding=encoding)
                for chunk in pd.read_csv(f,sep=sep,dtype=str,low_memory=False,
                                         chunksize=40000,on_bad_lines="skip"):
                    lidos+=len(chunk)
                    normcurso=chunk[curso].fillna("").apply(norm)
                    subset=chunk[normcurso.str.contains(r"\bGEOGRAFIA\b",regex=True)].copy()
                    if subset.empty:continue
                    colmap={"codigo_ies":ies,"codigo_curso":codigo,"municipio_ibge":codmun,
                            "nome_curso":curso,"modalidade_cod":modalidade,"grau_cod":grau,
                            "matriculas":matr,"uf_codigo":uf}
                    saida=pd.DataFrame({k:(subset[v].astype(str) if v else "")
                                        for k,v in colmap.items()},index=subset.index)
                    saida["ano"]="2024"
                    saida["fonte"]="INEP — Censo da Educação Superior 2024"
                    resultados.append(saida)
        if not resultados:
            raise ValueError("Nenhum curso de Geografia encontrado. Verificar nome e esquema do ZIP INEP.")
        # A tabela de IES identifica o nome completo associado ao código CO_IES.
        # O vínculo não é inferido pelo município da sede da universidade.
        arquivos_ies=[n for n in nomes if ("IES_2024" in norm(n) or "CADASTRO_IES" in norm(n))]
        nomes_ies={}
        if not arquivos_ies:
            raise ValueError("Arquivo de instituições IES não localizado no pacote oficial INEP")
        for ies_nome in arquivos_ies:
            with z.open(ies_nome) as raw:
                import io
                fonte=io.TextIOWrapper(raw,encoding="latin1")
                dados_ies=pd.read_csv(fonte,sep=";",dtype=str,low_memory=False)
            dados_ies.columns=[str(x).strip() for x in dados_ies.columns]
            cod=escolher_coluna(dados_ies.columns,"CO_IES")
            nome=escolher_coluna(dados_ies.columns,"NO_IES")
            if cod and nome:
                nomes_ies=dict(zip(dados_ies[cod].astype(str), dados_ies[nome].astype(str)))
                break
        if not nomes_ies:
            raise ValueError("Não foi possível vincular os códigos de IES aos nomes oficiais INEP")
        resultado=pd.concat(resultados,ignore_index=True)
        resultado=resultado.drop_duplicates(subset=["codigo_ies","codigo_curso","municipio_ibge"])
        resultado.insert(1,"nome_ies",resultado["codigo_ies"].map(nomes_ies).fillna(""))
        # Retém apenas colunas observadas. Ausência de matrícula não equivale a zero.
        if not resultado["municipio_ibge"].astype(str).str.fullmatch(r"\d{7}").all():
            print("AVISO: existem códigos municipais não padronizados; conferir georreferenciamento.",flush=True)
        resultado.to_csv(SAIDA,index=False,encoding="utf-8-sig")
        print(f"Processadas {lidos} linhas; {len(resultado)} registros Geografia; "
              f"{resultado.codigo_ies.nunique()} códigos IES; "
              f"{resultado.municipio_ibge.nunique()} códigos municipais.",flush=True)
        exemplos={"4113700":"Londrina","3143302":"Montes Claros",
                  "3106200":"Belo Horizonte","2933307":"Vitória da Conquista",
                  "3541406":"Presidente Prudente","5101803":"Barra do Garças"}
        for cod,mun in exemplos.items():
            sub=resultado[resultado["municipio_ibge"].eq(cod)]
            print(f"{mun} ({cod}): {len(sub)} curso(s), {sub.codigo_ies.nunique()} IES",flush=True)
    ARQ.unlink(missing_ok=True)

if __name__=="__main__":
    main()
