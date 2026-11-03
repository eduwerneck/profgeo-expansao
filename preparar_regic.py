"""Extrai REGIC 2018 (Municípios — Hierarquia e Região de Influência) com rastreabilidade.
O esquema do XLSX do IBGE é inspecionado antes de aceitar registros; falha explicitamente se ambíguo.
"""
import argparse
import csv
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen
from html.parser import HTMLParser
from openpyxl import load_workbook

DIRETORIO = "https://geoftp.ibge.gov.br/organizacao_do_territorio/divisao_regional/regioes_de_influencia_das_cidades/Regioes_de_influencia_das_cidades_2018_Resultados_definitivos/base_tabular/"
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k,v in attrs:
                if k == "href" and v:
                    self.links.append(v)

def normalizar(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s).lower()) if not unicodedata.combining(c)).strip()

def codigo(s):
    if s is None or isinstance(s,bool):
        return ""
    if isinstance(s,(int,float)):
        x = str(int(s)) if float(s).is_integer() else ""
    else:
        x = str(s).strip().replace(".0","")
    return x if re.fullmatch(r"\\d{7}",x) else ""

def obter():
    p=Links()
    p.feed(urlopen(DIRETORIO,timeout=45).read().decode("utf-8","replace"))
    candidatos=[x for x in p.links if x.lower().endswith(".xlsx") and "municipios" in normalizar(x)]
    candidatos=[x for x in candidatos if "hierarquia" in normalizar(x) or "regiao" in normalizar(x)]
    if len(candidatos)!=1:
        raise ValueError(f"Não foi possível identificar univocamente XLSX municipal da REGIC: {candidatos}")
    url=urljoin(DIRETORIO,candidatos[0])
    destino=Path("regic_municipios_fonte.xlsx")
    destino.write_bytes(urlopen(url,timeout=90).read())
    print("Origem oficial:",url,"bytes:",destino.stat().st_size)
    return destino,url

def executar():
    caminho,url=obter()
    wb=load_workbook(caminho,read_only=True,data_only=True)
    print("Planilhas:",wb.sheetnames)
    encontrados=[]
    for sheet in wb:
        inicio=list(sheet.iter_rows(min_row=1,max_row=16,values_only=True))
        print("AMOSTRA_CABECALHO",sheet.title,repr(inicio[:8])[:3500])
        for idx,row in enumerate(inicio):
            nomes=[normalizar(v) for v in row]
            cods=[i for i,s in enumerate(nomes) if ("cod" in s or "cd_" in s) and ("mun" in s or "ibge" in s)]
            hs=[i for i,s in enumerate(nomes) if "hierarquia" in s or "hierarquia urbana" in s]
            rs=[i for i,s in enumerate(nomes) if "regiao de influencia" in s or "regiao influencia" in s]
            if cods and hs and rs:
                encontrados.append((sheet,idx+1,cods[0],hs[0],rs[0],list(row)))
    if len(encontrados)!=1:
        raise ValueError("Cabeçalho não identificado univocamente; revisar amostra no log antes de fazer correspondência automática.")
    sheet,header_row,ic,ih,ir,headers=encontrados[0]
    rows=[]
    seen=set()
    for row in sheet.iter_rows(min_row=header_row+1,values_only=True):
        v=lambda i: row[i] if i<len(row) else None
        cd=codigo(v(ic))
        if not cd:continue
        if cd in seen:raise ValueError(f"Código IBGE duplicado: {cd}")
        seen.add(cd)
        rows.append({"codigo_ibge":cd,"hierarquia_regic":str(v(ih) or "").strip(),"regiao_influencia_regic":str(v(ir) or "").strip(),"fonte_regic":"IBGE REGIC 2018","ano_regic":"2018"})
    if not (5000<=len(rows)<=5700):
        raise ValueError(f"Total inesperado de municípios ({len(rows)}); verificar colunas e cabeçalho.")
    if sum(bool(r["hierarquia_regic"]) for r in rows)<5000:
        raise ValueError("Hierarquia vazia em quantidade incomum; extração não publicada.")
    output=Path("regic_municipios_2018.csv")
    with output.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("REGIC validada:",len(rows),"municípios; arquivo:",output,"fonte:",url)
    print("PRIMEIROS_REGISTROS:",rows[:5])
if __name__=="__main__":
    executar()
