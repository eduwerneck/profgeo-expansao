"""Auditoria de integridade do extrato academico INEP/CAPES 2024."""
from pathlib import Path
import pandas as pd

BASE=Path(__file__).resolve().parent

def main():
    fonte=BASE/"inep_geografia_2024.csv"
    if not fonte.exists():
        raise FileNotFoundError("Extrato INEP Geografia 2024 ainda nao foi gerado")
    inep=pd.read_csv(fonte,dtype=str,encoding="utf-8-sig",keep_default_na=False)
    ies=pd.read_csv(BASE/"inep_ies_2024.csv",sep=";",dtype=str,encoding="utf-8-sig",
                    keep_default_na=False)
    capes=pd.read_csv(BASE/"capes_geografia_2024.csv",dtype=str,encoding="utf-8-sig",
                      keep_default_na=False)
    esperadas=["codigo_ies","nome_ies","codigo_curso","municipio_ibge","nome_curso",
               "modalidade_cod","matriculas","ano"]
    assert set(esperadas).issubset(inep.columns), "Colunas do extrato INEP incompletas"
    assert not inep.empty and len(inep)>20, "Quantidade INEP improvavel: revisar extracao"
    assert inep["ano"].eq("2024").all(), "Ano INEP incorreto"
    assert inep["codigo_curso"].ne("").all(), "Codigo de curso ausente"
    assert inep["codigo_ies"].ne("").all(), "Codigo de IES ausente"
    assert inep["codigo_ies"].isin(set(ies["CO_IES"])).all(), "IES fora do cadastro INEP"
    assert inep["nome_curso"].str.contains("GEOGRAFIA",case=False,na=False).all(), "Filtro indevido"
    assert not inep.duplicated(["codigo_ies","codigo_curso","municipio_ibge"]).any(), "Cursos repetidos"
    # Município ausente é permitido apenas nas linhas de EaD, conforme dicionário.
    presencial=inep[inep["modalidade_cod"].eq("1")]
    assert not presencial.empty, "Sem cursos presenciais de Geografia"
    valido=presencial["municipio_ibge"].str.fullmatch(r"\d{7}")
    assert valido.all(), "Curso presencial sem codigo municipal valido (CO_MUNICIPIO)"
    assert len(capes)==134 and len(capes.loc[capes["situacao"].eq("EM FUNCIONAMENTO")])==121
    assert len(capes.loc[capes["situacao"].eq("EM PROJETO")])==13
    assert len(set(capes["codigo_programa"]))==80
    assert inep["matriculas"].replace("",pd.NA).notna().any(), "Sem matriculas informadas"
    print(f"APROVADO: INEP {len(inep)} cursos de Geografia; "
          f"{len(presencial)} presenciais; {inep.codigo_ies.nunique()} IES; "
          "CAPES 134 cursos em 80 programas.")

if __name__=="__main__":
    main()
