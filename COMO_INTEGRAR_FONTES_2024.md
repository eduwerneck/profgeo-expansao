# Integração acadêmica INEP/CAPES 2024 — PROFGEO Expansão

## Fontes efetivamente fornecidas pelo pesquisador
- CAPES Cursos 2024: arquivo XLSX entregue no Drive, versão 2025-12-01. Foi lido e filtrado, originando `capes_geografia_2024.csv`.
- INEP Censo Educação Superior 2024: arquivos descompactados da pasta compartilhada pelo pesquisador:
  - [cadastro das IES](https://drive.google.com/file/d/13hJyqLGytJSNuiygutXSHmai5Zz4xnjU/view)
  - [cadastro dos cursos](https://drive.google.com/file/d/1ZQNOiyOmPK8zIGANYysS5ILinJ0lHbbl/view)
  - [dicionário oficial das variáveis](https://drive.google.com/file/d/1nanHqvrMRg_CbCFsVL7nVR4Ch2RiEA2-/view)
- O cadastro de IES já foi integrado como `inep_ies_2024.csv`. O CSV integral de cursos tem 452.844.981 bytes e **não deve ser versionado no GitHub**.

## Processamento correto
A extração não consulta os servidores INEP ou CAPES. O workflow `integrar_inep_2024.yml` acessa exclusivamente o CSV oficial compartilhado pelo usuário no Google Drive, verifica o tamanho e cabeçalho e o processa por blocos no GitHub Actions. A disponibilidade pública do link Drive foi confirmada pelos metadados.

O arquivo `extrair_inep_2024.py` usa:
- `NO_CURSO` para identificar oferta em Geografia;
- `CO_IES` para identificar a instituição;
- `CO_CURSO` para identificar o curso;
- `CO_MUNICIPIO` para identificar o **local de oferta**, diferente da sede administrativa da IES;
- `TP_MODALIDADE_ENSINO` para distinguir presencial e a distância;
- `QT_MAT` para matrículas por curso sem converter nulos em zero.

Executar localmente, caso prefira, com Python 3.11 e pandas:
`python extrair_inep_2024.py --cursos /caminho/MICRODADOS_CADASTRO_CURSOS_2024.CSV --ies inep_ies_2024.csv --saida inep_geografia_2024.csv`

Após a extração bem-sucedida, o workflow gera `diagnostico_academico_seis_localidades_2024.csv` com `gerar_diagnostico_academico_2024.py`. A integração continua **provisória para categoria A/B**, que exige validação de linhas e oferta institucional.

## Situação e testes
CAPES 2024: **integrada** — 134 registros de cursos de Geografia, 80 programas, 121 cursos em funcionamento e 13 em projeto. Um programa pode ter cursos em funcionamento e cursos em projeto, portanto esses conjuntos não são mutuamente exclusivos por programa.

INEP 2024: cadastro de IES integrado (2.561 IES); cadastro nacional de cursos preparado para processamento, sem afirmar resultados ainda não gerados.

O ranking territorial e as regras REGIC permanecem inalterados. A REGIC não substitui classificação institucional. As três simulações municipais não constituem IES candidatas identificadas.

## Controle de qualidade
- Não inferir oferta municipal a partir de `CO_MUNICIPIO_IES` (sede da IES).
- A oferta EaD não deve ser automaticamente atribuída ao município da sede.
- Não classificar como ativo um curso CAPES `EM PROJETO`.
- Conferir códigos da IES no INEP/CAPES e município de oferta antes de propor A/B.
- Não interpretar dados ausentes como ausência de cursos.
- Confirmar a execução completa dos testes de integridade e o processamento do arquivo de 453 MB antes de comunicar integração plena.
