"""Testes de integridade do vínculo IES + município na análise acadêmica."""
import unittest
from unittest.mock import patch
import pandas as pd
from academico import diagnosticar_academia

class AcademicoTestes(unittest.TestCase):
    def setUp(self):
        self.candidatos=pd.DataFrame([
            {"instituicao":"UEL","municipio":"Londrina","uf":"PR","codigo_ibge":"4113700"},
            {"instituicao":"Simulação Montes Claros","municipio":"Montes Claros","uf":"MG","codigo_ibge":"3143302"},
        ])
        self.inep=pd.DataFrame([
            {"codigo_ies":"100","nome_ies":"UNIVERSIDADE ESTADUAL DE LONDRINA",
             "municipio_ibge":"4113700","codigo_curso":"11","modalidade_cod":"1","matriculas":"120"},
            {"codigo_ies":"200","nome_ies":"OUTRA UNIVERSIDADE EM LONDRINA",
             "municipio_ibge":"4113700","codigo_curso":"22","modalidade_cod":"1","matriculas":"80"},
            {"codigo_ies":"300","nome_ies":"INSTITUIÇÃO TESTE",
             "municipio_ibge":"3143302","codigo_curso":"33","modalidade_cod":"1","matriculas":"40"},
        ])
        self.capes=pd.DataFrame([
            {"emec_ies":"100","municipio":"Londrina","uf":"PR","codigo_programa":"ABC"},
            {"emec_ies":"200","municipio":"Londrina","uf":"PR","codigo_programa":"DEF"},
            {"emec_ies":"300","municipio":"Montes Claros","uf":"MG","codigo_programa":"GHI"},
        ])

    def test_ies_nao_herda_cursos_de_outra_instituicao(self):
        def fonte(nome):
            return self.inep.copy() if nome.startswith("inep_") else self.capes.copy()
        with patch("academico.carregar_csv",side_effect=fonte):
            r=diagnosticar_academia(self.candidatos)
        uel=r.iloc[0]
        sim=r.iloc[1]
        self.assertEqual(uel["Código IES (INEP)"],"100")
        self.assertEqual(uel["Graduações em Geografia (INEP)"],1)
        self.assertEqual(uel["Matrículas em Geografia (INEP)"],120)
        self.assertEqual(uel["Programas de Geografia (CAPES)"],1)
        self.assertEqual(uel["Categoria acadêmica sugerida"],"A (a conferir)")
        self.assertEqual(sim["Categoria acadêmica sugerida"],"Pendente")
        self.assertIn("simulado",sim["Estado de verificação"].lower())

    def test_sem_capes_nao_vira_categoria_b(self):
        def fonte(nome):
            return self.inep.copy() if nome.startswith("inep_") else None
        with patch("academico.carregar_csv",side_effect=fonte):
            r=diagnosticar_academia(self.candidatos)
        self.assertEqual(r.iloc[0]["Categoria acadêmica sugerida"],"Pendente")
        self.assertIn("Aguardando",r.iloc[0]["Estado de verificação"])

if __name__=="__main__":
    unittest.main()
