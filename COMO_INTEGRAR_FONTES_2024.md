# Integrar INEP e CAPES 2024 sem depender dos servidores externos

As tentativas anteriores falharam por conexão interrompida, timeout e HTTP 503. Por isso, os workflows agora são **manuais** e utilizam os **dois arquivos oficiais fornecidos pelo pesquisador** como anexos de uma versão GitHub, em vez de fazer novo download dos portais INEP e CAPES.

## Uma única preparação dos arquivos
1. No repositório, abra **Releases** > **Draft a new release**: https://github.com/eduwerneck/profgeo-expansao/releases/new
2. Em **Choose a tag**, crie e selecione **fontes-2024**. Preencha o título `Fontes acadêmicas oficiais 2024`.
3. Anexe os arquivos **originais, sem alterar os nomes**:
   - `br-capes-colsucup-curso-2024-2025-12-01.xlsx` (CAPES 2024, ~1 MB)
   - `microdados_censo_da_educacao_superior_2024.zip` (INEP 2024, ~457 MB)
4. Publique a versão. **Atenção:** o repositório é público; os anexos da release também serão públicos. Use somente os microdados públicos oficiais, nunca tabelas com dados pessoais ou arquivos privados.

## Processamento
Depois de publicar a release com os dois anexos, execute:
- https://github.com/eduwerneck/profgeo-expansao/actions/workflows/integrar_capes_2024.yml > **Run workflow** > **Run workflow**;
- https://github.com/eduwerneck/profgeo-expansao/actions/workflows/integrar_inep_2024.yml > **Run workflow** > **Run workflow**.

Os workflows não são mais acionados por push e não consultam automaticamente o site de dados públicos. Eles baixam exclusivamente os anexos `fontes-2024` hospedados no GitHub.

## Saídas verificáveis
- `capes_geografia_2024.csv`: cursos/programas da área Geografia; o arquivo não comprova linhas de pesquisa em ensino.
- `inep_geografia_2024.csv`: cursos de graduação e variáveis disponíveis por IES/município.
- `capes_processamento.log` e `inep_processamento.log`: auditoria do processamento.
- A ausência de arquivo produzido **não** representa ausência de cursos; significa que a integração falhou.
- **Não classificar A/B automaticamente** antes da conferência de campus/IES e das linhas de ensino. A REGIC continua exclusivamente como critério de desempate.

## Integridade e reprodutibilidade
Conservar as versões e anos de referência INEP/CAPES; conferir contagens, códigos IES, municípios e situações de curso; registrar exclusões e eventuais inconsistências. Para validar o processamento, usar o fluxo `validar_bases.yml`.

Em caso de falha após o upload, abrir a execução GitHub Actions e examinar a etapa **Extrair e filtrar dados de Geografia**, evitando criar arquivos de saída artificiais ou atribuir zero a campos ausentes.
