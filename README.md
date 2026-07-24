# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com OCR seletivo, preservação visual, rastreabilidade, retomada de lotes e controle de qualidade.

Versão atual: **0.7.2**.

## Finalidade

O Conversor HIS prepara legislação municipal para leitura humana, auditoria e uso posterior em sistemas de recuperação de informação. O foco é preservar o conteúdo original, registrar as decisões de conversão e separar produtos leves de análise dos ativos visuais mais pesados.

A ferramenta não substitui revisão jurídica ou validação humana. Ela organiza evidências, identifica limitações e produz saídas rastreáveis.

## Princípios

- utiliza exclusivamente os diplomas indicados pelo município;
- preserva integralmente os arquivos originais;
- diagnostica cada página antes de escolher a rota de conversão;
- aplica extração nativa quando possível e OCR quando necessário;
- preserva simultaneamente imagem e texto em páginas visuais;
- combina evidência textual, vetorial e raster;
- preserva tabelas nativas, vetoriais e rasterizadas para revisão;
- separa registros de coordenadas das métricas de tabelas;
- distingue mapas confirmados, candidatos e capas cartográficas;
- preserva imagem de toda página com OCR médio ou baixo;
- registra decisões, avisos, tempos e artefatos em manifestos auditáveis;
- grava Markdown e manifestos de forma atômica;
- permite limitar, interromper e retomar lotes municipais;
- não corrige silenciosamente conteúdo jurídico;
- usa o gate canário para bloquear regressões conhecidas.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ocr]"
```

A série 0.7.x inclui `numpy` e `opencv-python-headless` para análise visual seletiva de páginas rasterizadas. O OCR depende do Tesseract instalado no sistema e do pacote opcional `pytesseract`.

## Uso

### Diagnóstico individual

```powershell
conversor-his diagnosticar `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

### Conversão individual

```powershell
conversor-his converter `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado" `
  --dpi 300
```

### Lote completo

O valor `0` em `--documentos` processa todos os PDFs elegíveis:

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0 `
  --dpi 300
```

### Retomada

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0 `
  --dpi 300 `
  --retomar
```

A retomada exige coincidência entre hash da fonte, versão do conversor, DPI e produtos finais existentes.

### Gate canário

O gate canário compara dispositivos esperados e termos críticos com o texto observado. O comando gera relatórios JSON e CSV e retorna código diferente de zero quando há regressão:

```powershell
conversor-his validar-canario `
  --entrada "D:\canarios\casos.json" `
  --saida "D:\canarios\resultado"
```

Saídas:

```text
resultado/
└── analise/
    ├── canary_results.json
    └── canary_results.csv
```

O gate atual é deliberadamente conservador. Ele identifica perdas e divergências, mas ainda não interpreta integralmente remissões, leis modificadoras ou tabelas por célula.

### Pacote leve de análise

Para gerar um ZIP com Markdown, CSV, JSON, JSONL e arquivos textuais auxiliares, sem imagens, PDFs ou binários:

```powershell
conversor-his empacotar-analise `
  --entrada "D:\corpus\processado" `
  --saida "D:\corpus\processado_analise.zip"
```

## Organização da saída

A conversão separa os produtos de análise dos ativos visuais:

```text
saida/
├── analise/
│   ├── documento.md
│   ├── documento.manifest.json
│   └── documento.ocr_tokens.jsonl
├── ativos/
│   └── documento/
│       └── pagina_*.png
└── documento.manifest.json
```

O manifesto na raiz é mantido por compatibilidade com a retomada dos lotes da série 0.7.x.

### Produtos de análise

- `<documento>.md`: conteúdo pesquisável e rastreável por página;
- `<documento>.manifest.json`: hashes, rotas, evidências, avisos e artefatos;
- `<documento>.ocr_tokens.jsonl`: tokens OCR com posição e confiança;
- `<nome-do-zip>.lote.manifest.json`: inventário incremental do lote;
- `canary_results.json` e `canary_results.csv`: resultado do gate canário.

### Ativos visuais

- páginas submetidas a OCR;
- tabelas e estruturas visuais preservadas;
- mapas e diagramas candidatos;
- imagens de revisão para OCR médio ou baixo.

## OCR posicional

Para páginas submetidas a OCR, `<documento>.ocr_tokens.jsonl` registra cada token com:

- texto;
- confiança;
- página;
- bloco;
- parágrafo;
- linha;
- palavra;
- caixa delimitadora (`left`, `top`, `width`, `height`).

Essa camada intermediária permite futura reconstrução de colunas, linhas, tabelas e estruturas jurídicas sem perder a relação com a imagem original.

## Arquitetura de classificação

### Texto nativo

O texto bruto em modo `layout` é analisado antes da normalização. O detector considera títulos, cabeçalhos, alinhamentos, códigos territoriais, parâmetros urbanísticos, linhas compactas, continuidade entre páginas e penalizações para prosa jurídica.

### Evidência vetorial

Páginas nativas também são avaliadas pelas operações gráficas do PDF:

- retângulos finos usados como bordas;
- linhas horizontais e verticais;
- grades parciais;
- pequenas regiões tabulares;
- proteção contra molduras simples e alinhamentos artificiais.

### Evidência raster

A análise raster é seletiva e se aplica principalmente às páginas encaminhadas ao OCR. Uma miniatura a até 150 DPI é examinada para localizar:

- linhas horizontais;
- linhas verticais;
- cruzamentos;
- regiões fechadas;
- proporção estruturada da página;
- conjuntos de caixas e conectores.

A análise não reconstrói células nem interpreta relações normativas. Seu objetivo é identificar e preservar estruturas visuais relevantes.

## Classes visuais

- `confirmed`: tabela nativa ou vetorial confirmada;
- `candidate`: candidata textual;
- `mixed_candidate`: página parcialmente tabular;
- `continuation_candidate`: continuação sem cabeçalho repetido;
- `visual_candidate`: grade vetorial com pouca evidência textual;
- `raster_table_candidate`: tabela identificada na imagem;
- `diagram_candidate`: possível fluxograma, organograma ou esquema;
- `coordinate_register`: registro de coordenadas ou memorial geométrico;
- `map_confirmed`: conteúdo cartográfico confirmado;
- `map_candidate`: provável conteúdo cartográfico;
- `map_cover`: capa ou índice que anuncia mapas;
- `ocr_review`: OCR médio ou baixo com imagem obrigatória;
- `not_table`: página sem estrutura tabular relevante.

## Preservação por classe

| Classe | Imagem | Texto | Revisão |
|---|---|---|---|
| tabela nativa/vetorial | sim, até 200 DPI | bruto | obrigatória |
| tabela raster | sim, até 200 DPI | OCR | obrigatória |
| diagrama | sim, até 250 DPI | OCR | obrigatória |
| coordenadas | sim, até 200 DPI | bruto ou OCR | obrigatória |
| mapa confirmado/candidato | sim, até 300 DPI | nativo ou OCR | obrigatória |
| capa cartográfica | sim | nativo ou OCR | classificatória |
| OCR médio/baixo | sim, até 300 DPI | OCR | obrigatória |
| texto rotacionado | sim, até 300 DPI | extração selecionada | obrigatória |

## Evidência raster inicial

Uma candidata raster exige, em termos gerais:

- pelo menos quatro linhas horizontais;
- pelo menos três linhas verticais;
- pelo menos seis cruzamentos;
- região estruturada equivalente a pelo menos 5% da página.

A evidência é considerada forte quando alcança:

- pelo menos oito linhas horizontais;
- pelo menos seis linhas verticais;
- pelo menos vinte cruzamentos;
- região estruturada equivalente a pelo menos 10% da página.

Esses limiares são provisórios e devem ser recalibrados no conjunto de referência do corpus.

## Gates de validação

| Métrica | Gate mínimo |
|---|---:|
| Revocação das tabelas raster do conjunto de referência | 0,95 |
| Precisão de tabelas raster | 0,80 |
| Revocação dos diagramas conhecidos | 0,90 |
| Precisão de mapas | 0,80 |
| Imagem disponível para OCR médio/baixo | 1,00 |
| Integridade de páginas, links e hashes | 1,00 |
| Aumento desejável do tempo total | no máximo 25% |

O gate canário acrescenta uma verificação bloqueante para dispositivos esperados e termos críticos. O código de saída é `0` quando todos os casos passam e `1` quando existe ao menos uma regressão.

## Validação da versão atual

A infraestrutura incorporada à `main` foi validada com:

- `ruff check .` aprovado;
- `pytest -q` com 58 testes aprovados;
- conversão de PDF com texto nativo;
- conversão de PDF submetido a OCR;
- geração de tokens OCR posicionais;
- pacote leve sem imagens;
- canário sintético positivo e negativo;
- lote real de 13 páginas, com bloqueio dos casos que apresentaram divergências.

A reprovação de um caso real pelo gate não significa necessariamente falha operacional. Pode indicar erro de OCR, perda estrutural, comparação excessivamente literal ou limitação ainda não implementada.

## Limitações atuais

A versão atual ainda não implementa:

- interpretação completa da estrutura prevista na LC nº 95/1998;
- distinção contextual entre dispositivo principal e remissão;
- representação estruturada de leis modificadoras;
- consolidação temporal de dispositivos alterados ou revogados;
- reconstrução de tabelas por linha, coluna e célula;
- OCR com múltiplos motores;
- correção automática de erros jurídicos críticos.

Nenhuma dessas limitações deve ser contornada por correção silenciosa do texto-fonte. Divergências críticas devem permanecer visíveis e ser encaminhadas à revisão.

## Próximas etapas

1. validador jurídico básico e relatórios em português do Brasil;
2. reconhecimento de ordinais, sufixos e variações de `Art.` e `Artigo`;
3. distinção entre dispositivos principais e remissões;
4. reconstrução de linhas e blocos a partir das coordenadas;
5. representação de leis modificadoras e relações entre atos;
6. extração e validação de tabelas por célula.

## Histórico de versões

### 0.7.2 — infraestrutura de validação e saída leve

- preserva tokens OCR com posição e confiança;
- separa produtos em `analise/` e `ativos/`;
- mantém manifesto de compatibilidade na raiz;
- adiciona `validar-canario` com relatórios JSON e CSV;
- retorna código diferente de zero em regressões;
- adiciona `empacotar-analise` para compartilhamento sem imagens;
- acrescenta testes para OCR posicional, gate canário e pacote leve.

### 0.7.0 — preservação visual seletiva

- acrescenta análise raster seletiva às páginas OCR;
- preserva tabelas rasterizadas como `raster_table_candidate`;
- identifica possíveis diagramas;
- preserva imagem de todo OCR médio ou baixo;
- preserva imagem de páginas com texto rotacionado;
- separa registros de coordenadas das tabelas;
- distingue mapas, candidatos cartográficos e capas de mapas;
- registra métricas visuais e novas listas no manifesto;
- mantém OCR a 300 DPI e ativos tabulares em resolução menor;
- acrescenta testes sintéticos para grades, diagramas, coordenadas e mapas.

### 0.6.2 — evidência vetorial e continuidade

- detecta grades a partir das operações vetoriais do PDF;
- recupera quadros viários, tabelas genéricas e pequenas regiões tabulares;
- acrescenta `visual_candidate`;
- rebaixa prosa jurídica sem grade;
- reutiliza a extração nativa;
- limita imagens tabulares a 200 DPI.

### 0.6.1 — detecção tabular orientada pelo corpus

- usa o `layout` bruto para preservar alinhamentos;
- reconhece matrizes urbanísticas e suas continuações;
- acrescenta classes mistas e evidências de parâmetros urbanísticos.

### 0.6.0 — validação operacional

- valida conversão em amostra real;
- normaliza espaços e caracteres invisíveis;
- preserva texto bruto de tabelas;
- registra arquivos ignorados e estados do lote.

## Estado atual

A série 0.7.x é uma versão de validação ampliada. A arquitetura já preserva estruturas rasterizadas, tokens OCR posicionais e produtos leves de análise, mas os limiares e regras jurídicas devem continuar sendo medidos em conjuntos de referência antes de uso sem supervisão humana.

## Licenciamento

- código-fonte, testes e automações próprios: **MIT License**;
- documentação e metodologia: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências e modelos: licença própria;
- legislação e conteúdos de terceiros não são relicenciados.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho.