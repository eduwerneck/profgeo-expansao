# Integração acadêmica PROFGEO — protocolo de validação (2024)

## Bases e versões
- **INEP:** Censo da Educação Superior, ano-base 2024. Fonte: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior. Extração `extrair_inep_2024.py`, resultado `inep_geografia_2024.csv`.
- **CAPES:** Sucupira, Cursos da Pós-Graduação Stricto Sensu, ano-base 2024, versão de dados 01/12/2025. Fonte: https://dadosabertos.capes.gov.br/dataset/3a1264d8-b17c-4e6f-9282-601d04049e7b/resource/d024d60f-6876-41d3-b50d-da1a2e49bf39. Extração `extrair_capes_2024.py`, resultado `capes_geografia_2024.csv`.
- **IBGE:** REGIC 2018 e malha de municípios 2022; são anos distintos e devem ser identificados na comunicação.
- **Artigo de referência:** *Formação de professores de Geografia no Brasil e expansão da Rede PROFGEO*, Geografia Ensino & Pesquisa, 29, e91098 (2025). Quatro etapas: graduação, matrículas, mestrados/linhas em ensino e rede PROFGEO; oito categorias A1–B4.

## Unidade de análise e regra de pareamento
O candidato institucional é identificado por **código e-MEC/INEP da IES** e por **município de oferta**; cursos de outra IES no mesmo município **não são transferidos** para a candidata. Um município sem IES candidata, como os três cenários geográficos simulados, é apresentado **somente como diagnóstico municipal**.

A planilha INEP preserva o código do curso, código IES, nome IES, código IBGE do município, grau, modalidade e matrícula quando disponíveis. Cursos EaD devem ser separados de oferta presencial; a localização administrativa do curso não comprova polo presencial de EaD.

A planilha CAPES preserva código do programa, IES, código e-MEC, município, curso, grau e situação. O filtro de *NM_AREA_CONHECIMENTO = GEOGRAFIA* delimita a extração, mas **não demonstra linhas de pesquisa em ensino de Geografia**. Essas linhas exigem outra fonte e conferência individual.

## Categorias A1–B4
O artigo estabelece A (instituições com pós-graduação em Geografia), B (com graduação em Geografia e sem pós-graduação em Geografia), cruzadas com as quatro faixas de distância aos polos: acima de 300 km (1), acima de 200 até 300 (2), acima de 100 até 200 (3), até 100 (4). Nunca presumir A ou B quando o cruzamento institucional não for comprovado.

A saída `academico.py` indica **A (a conferir)** ou **B (a conferir)** somente quando as duas bases estão disponíveis e a correspondência institucional é unívoca. **Não converte esses indicadores em tipo A/B definitivo**, nem altera a classificação do mapa ou ranking automaticamente.

## Regra de ordenação
O ranking exploratório por distância usa faixas territoriais; quando A/B for validado, poderá adotar A1–B4 como categorias primárias. A **REGIC 2018 atua exclusivamente para desempatar candidaturas dentro da mesma categoria primária**, seguida da distância exata. Nenhum peso composto foi validado pela comissão.

## Critérios de aprovação de base
1. Base oficial, ano e versão rastreáveis; sem linhas duplicadas por código de curso ou programa.
2. Identidade da IES por código e-MEC/INEP, não apenas sigla ou município.
3. Campus/local de oferta identificado quando necessário; modalidade presencial/EaD discriminada.
4. CAPES com programa na área de Geografia não equivale a linha de pesquisa em ensino confirmada.
5. Matrícula faltante não deve ser interpretada como zero.
6. Candidaturas genéricas ou simuladas não podem receber A/B institucional.
7. Validação da classificação A/B individual documentada antes de incluí-la no ranking oficial.
8. Distâncias são geodésicas entre coordenadas municipais representativas, **não** tempos ou distâncias rodoviárias.
9. Os dois registros cartográficos de lagoas (Mirim e Patos) não são municípios da REGIC.
10. Todas as alterações precisam passar nos testes do GitHub Actions.

## Estado desta integração
Os scripts e a interface de evidência acadêmica foram adicionados ao repositório. **A inclusão de registros acadêmicos depende de os arquivos derivados serem efetivamente produzidos e auditados pelos workflows.** A ausência desses arquivos não autoriza inferir ausência de cursos.


## Fonte adicional identificada para linhas de pesquisa
A CAPES também publica a base **Projetos dos Programas de Pós-Graduação Stricto Sensu 2021–2024** (ano-base 2024). Seus metadados incluem `NM_LINHA_PESQUISA`, `CD_PROGRAMA_IES`, `NM_AREA_CONCENTRACAO` e `NM_PROJETO`. Essa fonte permite localizar **linhas declaradas associadas a projetos**, mas não prova, isoladamente, que todas as linhas do programa estejam representadas por projetos ativos. A validação da presença de ensino de Geografia deve ser acompanhada de inspeção manual da ficha do programa na Plataforma Sucupira.
Fonte: https://dadosabertos.capes.gov.br/dataset/1e577e61-729f-473a-8dd6-4918401c18a9
