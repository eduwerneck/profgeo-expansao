"""Validação de camadas educacionais para o PROFGEO.

Entrada: CSV de cursos de graduação INEP ou programas CAPES, previamente
extraídos e harmonizados com o dicionário oficial do ano de referência.
Não presume campus, município, condição A/B nem geocodificação.
"""
import pandas as pd

CAMPOS = ["fonte", "ano", "instituicao", "campus", "municipio", "uf", "codigo_ibge",
          "curso_programa", "nivel", "modalidade", "matriculas", "lat", "lon",
          "identificador_origem", "url_fonte", "status_validacao"]

def validar_camadas(df):
    faltantes = sorted(set(CAMPOS) - set(df.columns))
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(faltantes))
    df = df.copy()
    df["fonte"] = df["fonte"].fillna("").astype(str).str.upper().str.strip()
    if not df["fonte"].isin(["INEP", "CAPES"]).all():
        raise ValueError("Fonte deve ser INEP ou CAPES.")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    if df["ano"].isna().any():
        raise ValueError("Ano inválido.")
    for col in ["lat", "lon", "matriculas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if (df["matriculas"].dropna() < 0).any():
        raise ValueError("Matrículas negativas.")
    if ((df["lat"].dropna() < -90) | (df["lat"].dropna() > 90)).any():
        raise ValueError("Latitude inválida.")
    if ((df["lon"].dropna() < -180) | (df["lon"].dropna() > 180)).any():
        raise ValueError("Longitude inválida.")
    if (df["lat"].isna() != df["lon"].isna()).any():
        raise ValueError("Latitude e longitude devem estar preenchidas juntas.")
    df["status_validacao"] = df["status_validacao"].fillna("Pendente")
    return df

def resumo(df):
    return df.groupby(["fonte", "ano", "nivel", "modalidade"], dropna=False).agg(
        registros=("instituicao", "size"),
        com_coordenadas=("lat", "count"),
        matriculas_informadas=("matriculas", "count")
    ).reset_index()
