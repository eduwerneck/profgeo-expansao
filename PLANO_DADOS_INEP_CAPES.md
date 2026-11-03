# Plano de reconstrução das camadas educacionais (INEP e CAPES)

Estado: fontes oficiais identificadas; microdados ainda não extraídos nem validados. Não usar valores estimados como dados observados.

## INEP — Censo da Educação Superior 2024
Fonte: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior
Unidade: registro de curso/local de oferta conforme dicionário do arquivo anual.
Extrair apenas Geografia (licenciatura e bacharelado), preservando código do curso, IES, modalidade, grau, município/local de oferta, situação, matrículas e ano. Validar filtros com o dicionário oficial, inclusive código CINE e nomes. Não atribuir polos EAD a partir da sede da IES; mapear locais apenas quando o dado permite.

## CAPES — Sucupira / dados abertos 2021–2024
Fonte: https://dadosabertos.capes.gov.br/
Extrair programas/cursos, IES, município de oferta, área de avaliação, área de concentração, linha de pesquisa, situação e ano. Identificar linhas de ensino de Geografia por leitura e validação manual; não usar somente o nome do programa como prova de linha específica.
Verificar se a localização corresponde à sede administrativa ou à oferta efetiva.

## Integração e regras
- Chaves preferenciais: código de IES/curso, código de programa CAPES, município IBGE e campus validado.
- Não transformar presença de graduação em habilitação automática.
- Condição A/B somente após validação de cursos e unidade de oferta.
- Distinguir fotografia histórica do artigo e cenário atual da rede de 18 polos.
- Preservar fonte, ano, data de extração, critérios de filtro, dicionário e limitações.
- Não construir índice composto antes de validar variáveis e pesos.

## Situação
Fontes e procedimento documentados. Dados tabulares de graduação, matrícula e pós-graduação ainda não incorporados ao aplicativo.
