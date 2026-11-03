"""Cenário de ordenação exploratória: distância e REGIC, sem pesos numéricos.

Regra: preservar as faixas territoriais do modelo, ordenar as cidades pela
hierarquia REGIC dentro de cada faixa, e desempatar pela distância exata.
Não considera capacidade acadêmica, demanda de professores ou deliberação.
"""
import pandas as pd

def nivel_regic(texto):
    s=str(texto or "").lower()
    # Ordenação ordinal das subdivisões oficiais REGIC 2018.
    # Esta é apenas uma convenção de simulação, não um índice de capacidade.
    import re
    grupos = [
        ("1a", 1), ("1b", 2), ("1c", 3),
        ("2a", 4), ("2b", 5), ("2c", 6),
        ("3a", 7), ("3b", 8),
        ("4a", 9), ("4b", 10), ("5", 11),
    ]
    match = re.search(r"\\((1[abc]|2[abc]|3[ab]|4[ab]|5)\\)", s)
    if match:
        codigo=match.group(1)
        return dict(grupos)[codigo], codigo.upper()
    return None, "Não verificada"

def ordenar_cenarios(df):
    """Retorna mesmo conjunto de registros, acrescido de rankings auditáveis.

    Somente atribui ranking REGIC se todos os registros possuem hierarquia
    válida; não transforma valores ausentes em baixo desempenho.
    """
    out=df.copy()
    if out.empty:
        return out
    dist=pd.to_numeric(out["distancia_km"],errors="coerce")
    if dist.isna().any():
        raise ValueError("Distâncias ausentes: ranking não calculado.")
    out["_dist"]=dist
    out["faixa_prioridade_territorial"]=out["_dist"].map(
        lambda d: 1 if d>300 else 2 if d>200 else 3 if d>100 else 4)
    out["rank_distancia"]=out["_dist"].rank(method="min",ascending=False).astype(int)
    niveis=out["hierarquia_regic"].apply(nivel_regic) if "hierarquia_regic" in out else pd.Series([(None,"Não verificada")]*len(out),index=out.index)
    out["nivel_regic"]=niveis.map(lambda v: v[1])
    out["_nivel"]=pd.to_numeric(niveis.map(lambda v: v[0]),errors="coerce")
    if out["_nivel"].isna().any():
        out["rank_cenario_regic"]=pd.NA
        out["variacao_posicoes"]=pd.NA
        out["status_ranking"]="Pendente: hierarquia REGIC ausente em pelo menos uma candidatura"
    else:
        ordem=out.sort_values(["faixa_prioridade_territorial","_nivel","_dist","instituicao"],ascending=[True,True,False,True],kind="mergesort")
        out["rank_cenario_regic"]=pd.Series(range(1,len(out)+1),index=ordem.index).reindex(out.index)
        out["variacao_posicoes"]=out["rank_distancia"]-out["rank_cenario_regic"]
        out["status_ranking"]="Simulação: distância por faixa, REGIC como desempate, distância exata"
    return out.drop(columns=["_nivel","_dist"])
