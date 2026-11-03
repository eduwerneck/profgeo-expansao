"""Cenário de ordenação exploratória: distância e REGIC, sem pesos numéricos.

Regra: preservar as faixas territoriais do modelo, ordenar as cidades pela
hierarquia REGIC dentro de cada faixa, e desempatar pela distância exata.
Não considera capacidade acadêmica, demanda de professores ou deliberação.
"""
import pandas as pd

def nivel_regic(texto):
    s=str(texto or "").lower()
    # Hierarquia publicada pela REGIC (1 metrópole a 5 centro local).
    if "metrópole" in s or "metropole" in s:
        return 1, "Metrópole"
    if "capital regional" in s:
        return 2, "Capital Regional"
    if "centro sub-regional" in s or "centro subregional" in s:
        return 3, "Centro Sub-Regional"
    if "centro de zona" in s:
        return 4, "Centro de Zona"
    if "centro local" in s:
        return 5, "Centro Local"
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
