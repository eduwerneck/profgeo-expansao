"""Gera diagnostico academico das seis localidades piloto sem alterar o ranking.

Usa os extratos oficiais ja integrados ao repositorio. Preserva
Pendente para categoria A/B enquanto avaliacao institucional estiver aberta.
"""
from pathlib import Path
import pandas as pd
from academico import diagnosticar_academia

BASE=Path(__file__).resolve().parent

def gerar():
    caminhos=[BASE/"capes_geografia_2024.csv",BASE/"inep_geografia_2024.csv",
              BASE/"candidatos_exemplo.csv"]
    faltantes=[str(p.name) for p in caminhos if not p.exists()]
    if faltantes:
        raise FileNotFoundError("Bases necessarias ausentes: "+", ".join(faltantes))
    candidatos=pd.read_csv(BASE/"candidatos_exemplo.csv",dtype={"codigo_ibge":str},
                            keep_default_na=False)
    diagnostico=diagnosticar_academia(candidatos)
    if len(diagnostico)!=6:
        raise ValueError(f"Esperadas seis localidades; recebidas {len(diagnostico)}")
    categorias=diagnostico["Categoria acadêmica sugerida"].astype(str)
    if not categorias.isin(["Pendente","A (a conferir)","B (a conferir)"]).all():
        raise ValueError("Classificacao inesperada")
    saida=BASE/"diagnostico_academico_seis_localidades_2024.csv"
    diagnostico.to_csv(saida,index=False,encoding="utf-8-sig")
    print(diagnostico.to_string(index=False))
    print("Arquivo de diagnostico gerado:",saida.name)

if __name__=="__main__":
    gerar()
