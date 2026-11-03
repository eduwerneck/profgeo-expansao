"""Cenário de ordenação exploratória: distância e REGIC, sem pesos numéricos.

Regra: preservar as categorias A1–B4 quando validadas; caso contrário,
usar faixas territoriais provisórias. REGIC desempata apenas dentro do mesmo
grupo de prioridade; a distância exata é o desempate residual.
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
    match = re.search(r"\((1[abc]|2[abc]|3[ab]|4[ab]|5)\)", s)
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
    # Categoria A/B validada é indispensável para um ranking A1–B4.
    # Na ausência dela, o resultado mantém a faixa territorial provisória.
    categorias_validas = (
        "categoria" in out.columns
        and out["categoria"].astype(str).str.fullmatch(r"[AB][1-4]").all()
    )
    if categorias_validas:
        # Prioridade acadêmico-territorial definida no artigo.
        out["_base"] = out["categoria"].map(
            {f"{letra}{numero}": (0 if letra == "A" else 4) + numero
             for letra in ("A", "B") for numero in (1, 2, 3, 4)}
        )
        out["criterio_primario"] = "Categoria acadêmico-territorial A1–B4"
    else:
        # Não presumir tipo A ou B: manter grupos territoriais provisórios.
        out["_base"] = out["faixa_prioridade_territorial"]
        out["criterio_primario"] = "Faixa territorial provisória (A/B não validado)"
    ordem_base = out.sort_values(
        ["_base", "_dist", "instituicao"],
        ascending=[True, False, True], kind="mergesort"
    )
    out["rank_base"] = pd.Series(range(1, len(out)+1), index=ordem_base.index).reindex(out.index)
    if out["_nivel"].isna().any():
        # REGIC ausente: não fabricar um nível urbano nem desempate.
        out["rank_cenario_regic"] = pd.NA
        out["variacao_posicoes"] = pd.NA
        out["status_ranking"] = "Ranking provisório: REGIC não verificada para todos os registros"
    else:
        # REGIC nunca altera a precedência entre categorias/faixas distintas.
        ordem = out.sort_values(
            ["_base", "_nivel", "_dist", "instituicao"],
            ascending=[True, True, False, True], kind="mergesort"
        )
        out["rank_cenario_regic"] = pd.Series(
            range(1, len(out)+1), index=ordem.index
        ).reindex(out.index)
        out["variacao_posicoes"] = out["rank_base"] - out["rank_cenario_regic"]
        out["status_ranking"] = (
            "REGIC apenas como desempate dentro da categoria A1–B4"
            if categorias_validas else
            "REGIC apenas como desempate dentro da faixa territorial provisória"
        )
    return out.drop(columns=["_nivel","_dist","_base"])
