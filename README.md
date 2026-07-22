# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com OCR seletivo, preservação visual, rastreabilidade e controle de qualidade.

Versão atual: **0.7.0**.

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
- permite limitar, interromper e retomar lotes municipais.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ocr]"
```

A série 0.7.x inclui `numpy` e `opencv-python-headless` para análise visual seletiva de páginas rasterizadas.

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
  --saida "D:\corpus\processado"
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

Esses limiares são provisórios e devem ser recalibrados no gold set do corpus.

## Manifesto

Além dos campos anteriores, a 0.7.0 registra:

- `raster_table_pages`;
- `diagram_pages`;
- `coordinate_register_pages`;
- `map_candidate_pages`;
- `map_cover_pages`;
- `ocr_review_image_pages`;
- evidências raster por página;
- disponibilidade de imagem de revisão.

## Gates de validação da 0.7.0

| Métrica | Gate mínimo |
|---|---:|
| Revocação das tabelas raster do gold set | 0,95 |
| Precisão de tabelas raster | 0,80 |
| Revocação dos diagramas conhecidos | 0,90 |
| Precisão de mapas | 0,80 |
| Imagem disponível para OCR médio/baixo | 1,00 |
| Integridade de páginas, links e hashes | 1,00 |
| Aumento desejável do tempo total | no máximo 25% |

## Produtos gerados

- `<documento>.md`: conteúdo pesquisável e rastreável por página;
- `<documento>.manifest.json`: hashes, rotas, evidências, avisos e artefatos;
- `<documento>_assets/`: imagens visuais, tabulares e de revisão;
- `<nome-do-zip>.lote.manifest.json`: inventário incremental do lote.

## Histórico de versões

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

A 0.7.0 é uma versão de validação ampliada. A arquitetura está preparada para preservar estruturas rasterizadas e organizar a revisão, mas seus thresholds devem ser medidos no gold set antes de uso consolidado sem supervisão humana.

## Licenciamento

- código-fonte, testes e automações próprios: **MIT License**;
- documentação e metodologia: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências e modelos: licença própria;
- legislação e conteúdos de terceiros não são relicenciados.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho.
