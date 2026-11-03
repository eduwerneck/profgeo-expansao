"""Auditoria reproduzível das bases operacionais do PROFGEO Expansão.

Executar: python validar_bases.py
Usa apenas a biblioteca padrão; não atribui classificação A/B automaticamente.
"""
import csv
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def ler(nome):
    with (ROOT / nome).open(encoding="utf-8-sig", newline="") as arq:
        return list(csv.DictReader(arq))

def validar():
    erros, alertas = [], []
    regic = ler("regic_municipios_2018.csv")
    indice = ler("indice_municipios_profgeo.csv")
    polos = ler("rede_existente_18_polos.csv")
    casos = ler("candidatos_exemplo.csv")

    def codigos_unicos(linhas, nome, esperado=None):
        codigos = [str(l["codigo_ibge"]).strip() for l in linhas]
        if esperado is not None and len(linhas) != esperado:
            erros.append(f"{nome}: esperado {esperado} linhas; encontrado {len(linhas)}")
        if any(not re.fullmatch(r"\\d{7}", c) for c in codigos):
            erros.append(f"{nome}: código IBGE inválido")
        if len(set(codigos)) != len(codigos):
            erros.append(f"{nome}: código IBGE duplicado")
        return set(codigos)

    regic_ids = codigos_unicos(regic, "REGIC", 5570)
    indice_ids = codigos_unicos(indice, "Índice municipal", 5570)
    if regic_ids != indice_ids:
        erros.append("Diferença entre códigos dos municípios REGIC e malha IBGE")

    if len(polos) != 18:
        erros.append(f"Rede de polos: esperado 18, encontrado {len(polos)}")
    if len(casos) != 6:
        erros.append(f"Simulação: esperado 6, encontrado {len(casos)}")

    def coordenadas(linhas, nome):
        pontos = []
        for idx, linha in enumerate(linhas, start=2):
            try:
                lat, lon = float(linha["lat"]), float(linha["lon"])
                if not (math.isfinite(lat) and math.isfinite(lon) and -34 <= lat <= 6 and -74 <= lon <= -32):
                    raise ValueError("fora da extensão do Brasil")
                pontos.append((lat, lon))
            except (ValueError, KeyError, TypeError):
                erros.append(f"{nome}: coordenada inválida na linha {idx}")
        return pontos

    polo_pts = coordenadas(polos, "Polos")
    coordenadas(casos, "Candidaturas")
    duplicados = {p: n for p, n in Counter(polo_pts).items() if n > 1}
    if duplicados:
        alertas.append("Há polos distintos com coordenadas municipais idênticas; distância não é logística de transporte")
    regic_por_codigo = {r["codigo_ibge"]: r for r in regic}
    for caso in casos:
        codigo = caso["codigo_ibge"]
        if codigo not in regic_por_codigo:
            erros.append(f"{caso['municipio']}/{caso['uf']}: sem vínculo com a REGIC")
        else:
            hierarquia = regic_por_codigo[codigo]["hierarquia_regic"]
            if not re.search(r"\\((?:1[ABC]|2[ABC]|3[AB]|4[AB]|5)\\)", hierarquia, flags=re.I):
                erros.append(f"{caso['municipio']}: hierarquia REGIC não reconhecida: {hierarquia}")
        if caso.get("tipo", "").strip():
            alertas.append(f"{caso['municipio']}: tipo A/B informado sem comprovação acadêmica automatizada")
    alertas.append("INEP 2024 e CAPES 2024 ainda não foram vinculados por código de IES/campus; A1–B4 pendente")
    print(f"REGIC: {len(regic)} municípios | IBGE: {len(indice)} | Polos: {len(polos)} | Casos: {len(casos)}")
    for a in alertas: print("ATENÇÃO:", a)
    for e in erros: print("ERRO:", e)
    if erros:
        raise SystemExit(1)
    print("APROVADO: integridade tabular, códigos, coordenadas e REGIC dos casos de teste.")
    print("NÃO APROVADO: classificação acadêmica A/B sem integração documentada INEP/CAPES.")

if __name__ == "__main__":
    validar()
