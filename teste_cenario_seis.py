"""Teste de regressão: cenário oficial de seis localidades do protótipo.

Executar na raiz: python teste_cenario_seis.py
Não interpreta A/B como comprovado; verifica apenas o cenário provisório.
"""
import csv
from pathlib import Path
from math import asin, cos, radians, sin, sqrt
import re

ROOT = Path(__file__).parent

def ler(nome):
    with (ROOT / nome).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def distancia(a, b, c, d):
    p1, p2 = radians(float(a)), radians(float(c))
    da, dl = p2-p1, radians(float(d)-float(b))
    h = sin(da/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*6371.0088*asin(min(1, sqrt(h)))

def testar():
    candidatos = ler("candidatos_exemplo.csv")
    polos = ler("rede_existente_18_polos.csv")
    regic = {r["codigo_ibge"]: r for r in ler("regic_municipios_2018.csv")}
    niveis = {c: i for i, c in enumerate(
        ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "4A", "4B", "5"), 1)}
    esperado = [
        ("Vitória da Conquista", 594.5, "2B"),
        ("Montes Claros", 408.3, "2B"),
        ("Barra do Garças", 479.5, "3A"),
        ("Presidente Prudente", 296.1, "2C"),
        ("Londrina", 177.8, "2B"),
        ("Belo Horizonte", 58.0, "1C"),
    ]
    calculado = []
    for c in candidatos:
        assert c.get("tipo", "").strip() == "", "Categoria A/B não deve ser presumida"
        menor = min(distancia(c["lat"], c["lon"], p["lat"], p["lon"]) for p in polos)
        dist = round(menor, 1)
        hierarquia = regic[c["codigo_ibge"]]["hierarquia_regic"]
        m = re.search(r"\((1[ABC]|2[ABC]|3[AB]|4[AB]|5)\)", hierarquia, re.I)
        assert m, f"REGIC inválida: {c['municipio']}"
        nivel = m.group(1).upper()
        faixa = 1 if menor > 300 else 2 if menor > 200 else 3 if menor > 100 else 4
        calculado.append((c["municipio"], dist, nivel, faixa, niveis[nivel]))
    calculado.sort(key=lambda x: (x[3], x[4], -x[1], x[0]))
    assert len(calculado) == len(esperado) == 6
    for atual, (mun, dist, nivel) in zip(calculado, esperado):
        assert atual[:3] == (mun, dist, nivel), f"Esperado {(mun,dist,nivel)}; encontrado {atual[:3]}"
    print("APROVADO: distâncias, REGIC e ordem das seis localidades.")
    print("Observação: categoria A/B acadêmica não foi validada.")
    for i, (mun, dist, nivel, *_) in enumerate(calculado, 1):
        print(f"{i}. {mun}: {dist:.1f} km — REGIC {nivel}")

if __name__ == "__main__":
    testar()
