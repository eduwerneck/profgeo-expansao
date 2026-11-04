"""Extrai cursos de Geografia dos CSVs oficiais do INEP 2024 já fornecidos.

Sem downloads externos. Entrada principal: dados/MICRODADOS_CADASTRO_CURSOS_2024.CSV.
Correspondência de IES: inep_ies_2024.csv (cadastro oficial já reduzido).
Unidade espacial: CO_MUNICIPIO (local de oferta), não CO_MUNICIPIO_IES.
"""
import argparse
import re
import unicodedata
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_CURSOS = ROOT / "MICRODADOS_CADASTRO_CURSOS_2024.CSV"
DEFAULT_IES = ROOT / "inep_ies_2024.csv"
DEFAULT_OUT = ROOT / "inep_geografia_2024.csv"

def norm(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "").upper())
                   if not unicodedata.combining(c)).strip()

def required(cols, *names):
    for name in names:
        if name in cols:
            return name
    raise ValueError("Faltam colunas obrigatorias (uma entre): " + ", ".join(names))

def optional(cols, *names):
    for name in names:
        if name in cols:
            return name
    return None

def convert(chunk, columns, names):
    curso = required(columns, "NO_CURSO")
    ies = required(columns, "CO_IES")
    codigo = required(columns, "CO_CURSO")
    local = required(columns, "CO_MUNICIPIO")
    modalidade = required(columns, "TP_MODALIDADE_ENSINO")
    grau = optional(columns, "TP_GRAU_ACADEMICO")
    matr = required(columns, "QT_MAT")
    uf = optional(columns, "CO_UF", "CO_UF_CURSO")
    cine = optional(columns, "CO_CINE_ROTULO")
    filtro = chunk[curso].fillna("").apply(norm).str.contains(r"\bGEOGRAFIA\b", regex=True)
    subset = chunk.loc[filtro].copy()
    if subset.empty:
        return None
    # Não converter campo ausente de matrícula em zero.
    def values(field):
        return subset[field].fillna("").astype(str) if field else pd.Series("", index=subset.index)
    resultado = pd.DataFrame({
        "codigo_ies": values(ies),
        "codigo_curso": values(codigo),
        "municipio_ibge": values(local),
        "nome_curso": values(curso),
        "modalidade_cod": values(modalidade),
        "grau_cod": values(grau),
        "matriculas": values(matr),
        "uf_codigo": values(uf),
        "cine_rotulo": values(cine),
    })
    resultado["codigo_ies"] = resultado["codigo_ies"].str.replace(r"\.0$", "", regex=True)
    resultado["municipio_ibge"] = resultado["municipio_ibge"].str.replace(r"\.0$", "", regex=True)
    resultado["codigo_curso"] = resultado["codigo_curso"].str.replace(r"\.0$", "", regex=True)
    resultado["nome_ies"] = resultado["codigo_ies"].map(names).fillna("")
    resultado["ano"] = "2024"
    resultado["fonte"] = "INEP - Microdados Censo Educacao Superior 2024 - arquivo do usuario"
    return resultado

def extrair(cursos, ies, output):
    if not cursos.is_file():
        raise FileNotFoundError("CSV de cursos INEP nao encontrado: " + str(cursos))
    if not ies.is_file():
        raise FileNotFoundError("Cadastro IES INEP nao encontrado: " + str(ies))
    sedes = pd.read_csv(ies, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    if not {"CO_IES", "NO_IES"}.issubset(sedes.columns):
        raise ValueError("Cadastro IES sem CO_IES ou NO_IES")
    sedes = sedes.drop_duplicates("CO_IES")
    nomes = dict(zip(sedes["CO_IES"], sedes["NO_IES"]))
    lidos = 0
    resultados = []
    # Microdados nacionais de 2024: CSV separado por ponto e vírgula.
    # Detectar codificacao para preservar nomes acentuados.
    with cursos.open("rb") as origem:
        amostra = origem.read(1048576)
    try:
        amostra.decode("utf-8-sig")
        codificacao = "utf-8-sig"
    except UnicodeDecodeError:
        codificacao = "latin1"
    print(f"Codificacao INEP detectada: {codificacao}", flush=True)
    for bloco in pd.read_csv(cursos, sep=";", encoding=codificacao, dtype=str,
                             chunksize=25000, low_memory=False, keep_default_na=False):
        cols = list(bloco.columns)
        if not lidos:
            print("Colunas do CSV: " + " | ".join(cols), flush=True)
        convertido = convert(bloco, cols, nomes)
        if convertido is not None:
            resultados.append(convertido)
        lidos += len(bloco)
        if lidos % 100000 == 0:
            print(f"INEP processados {lidos:,} registros", flush=True)
    if not resultados:
        raise ValueError("Nenhum registro com Geografia: conferir CSV INEP e filtro")
    result = pd.concat(resultados, ignore_index=True)
    if result["codigo_curso"].eq("").any():
        raise ValueError("Cursos de Geografia sem codigo de curso INEP")
    if result["codigo_ies"].eq("").any():
        raise ValueError("Cursos de Geografia sem codigo IES")
    if result["nome_ies"].eq("").any():
        raise ValueError("Uma ou mais IES de Geografia nao foram encontradas no cadastro")
    # Não remover múltiplas linhas por campus/local de oferta nem duplicar matrículas.
    keys = ["codigo_curso", "codigo_ies", "municipio_ibge"]
    if result.duplicated(keys).any():
        duplicados = result.loc[result.duplicated(keys, keep=False), keys]
        raise ValueError("Registros de cursos duplicados; investigar: " +
                         duplicados.head(8).to_json(orient="records"))
    result.to_csv(output, index=False, encoding="utf-8-sig")
    prec = result[result["modalidade_cod"].eq("1")]
    total = pd.to_numeric(result["matriculas"].replace("", pd.NA), errors="coerce")
    print(f"INEP: {lidos} registros lidos; {len(result)} cursos Geografia; "
          f"{len(prec)} presenciais; {result['codigo_ies'].nunique()} IES; "
          f"matriculas observadas={int(total.sum()) if total.notna().any() else 'NA'}", flush=True)
    print(f"Arquivo filtrado: {output} ({output.stat().st_size} bytes)", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cursos", type=Path, default=DEFAULT_CURSOS)
    parser.add_argument("--ies", type=Path, default=DEFAULT_IES)
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUT)
    options = parser.parse_args()
    extrair(options.cursos, options.ies, options.saida)
