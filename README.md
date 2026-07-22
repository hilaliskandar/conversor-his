# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com OCR seletivo, preservação visual, rastreabilidade e controle de qualidade.

Versão atual: **0.8.0a1**.

A série 0.8 introduz a API principal em português brasileiro. Os nomes públicos da série 0.7 permanecem temporariamente disponíveis em módulos adaptadores, para facilitar a migração de integrações existentes.

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
python -m pip install -e ".[dev,ocr]"
```

A análise visual seletiva utiliza `numpy` e `opencv-python-headless`. O OCR opcional utiliza `pytesseract` e requer uma instalação funcional do Tesseract no sistema operacional.

## Interface de linha de comando

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

### Conversão de lote ZIP

O valor `0` em `--documentos` processa todos os PDFs elegíveis:

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0 `
  --dpi 300
```

### Retomada de lote

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0 `
  --dpi 300 `
  --retomar
```

A retomada exige coincidência entre o hash da fonte, a versão do conversor, o DPI e a existência dos produtos finais.

## API Python em português

```python
from pathlib import Path

from conversor_his.conversor import converter_pdf
from conversor_his.diagnostico import diagnosticar_pdf
from conversor_his.lote import converter_lote_zip
from conversor_his.manifesto import ler_manifesto

entrada = Path("lei.pdf")
saida = Path("processado")

diagnostico = diagnosticar_pdf(entrada)
caminho_markdown = converter_pdf(entrada, saida, dpi=300)
manifesto = ler_manifesto(saida / "lei.manifest.json")
```

Conversão em lote:

```python
from pathlib import Path

from conversor_his.lote import converter_lote_zip

resultado = converter_lote_zip(
    caminho_zip=Path("municipio.zip"),
    diretorio_saida=Path("processado/municipio"),
    limite_documentos=0,
    retomar=True,
)

print(resultado.quantidade_sucessos)
print(resultado.caminho_manifesto)
```

## Arquitetura principal

| Responsabilidade | Módulo principal |
|---|---|
| fluxo completo de conversão | `fluxo_conversao.py` |
| diagnóstico por página | `diagnostico.py` |
| modelos de dados | `modelos.py` |
| manifestos | `manifesto.py` |
| processamento em lote | `lote.py` |
| interface de linha de comando | `linha_comando.py` |
| tabelas | `tabelas.py` |
| mapas | `mapas.py` |
| avaliação visual de mapas | `visual_mapa.py` |
| avaliação visual raster | `visual_raster.py` |
| registros de coordenadas | `coordenadas.py` |
| normalização textual | `normalizacao_texto.py` |

Os módulos antigos em inglês são adaptadores temporários. Nenhuma lógica nova deve ser adicionada a esses arquivos.

## Arquitetura de classificação

### Texto nativo

O texto bruto em modo `layout` é analisado antes da normalização. O detector considera títulos, cabeçalhos, alinhamentos, códigos territoriais, parâmetros urbanísticos, linhas compactas, continuidade entre páginas e penalizações para prosa jurídica.

### Evidência vetorial

Páginas nativas também são avaliadas pelas operações gráficas do PDF, incluindo retângulos finos, linhas horizontais e verticais, grades parciais e pequenas regiões tabulares. Molduras simples e alinhamentos artificiais recebem proteção contra falso positivo.

### Evidência raster

A análise raster é seletiva e se aplica principalmente às páginas encaminhadas ao OCR. Uma miniatura de até 150 DPI é examinada para localizar linhas, cruzamentos, regiões fechadas, áreas estruturadas e conjuntos de caixas ou conectores.

A análise não reconstrói células nem interpreta relações normativas. Seu objetivo é identificar e preservar estruturas visuais relevantes.

## Classes internas de conteúdo

Os valores textuais abaixo permanecem estáveis durante a transição, inclusive para leitura de manifestos anteriores:

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
| tabela nativa ou vetorial | sim, até 200 DPI | bruto | obrigatória |
| tabela raster | sim, até 200 DPI | OCR | obrigatória |
| diagrama | sim, até 250 DPI | OCR | obrigatória |
| coordenadas | sim, até 200 DPI | bruto ou OCR | obrigatória |
| mapa confirmado ou candidato | sim, até 300 DPI | nativo ou OCR | obrigatória |
| capa cartográfica | sim | nativo ou OCR | classificatória |
| OCR médio ou baixo | sim, até 300 DPI | OCR | obrigatória |
| texto rotacionado | sim, até 300 DPI | extração selecionada | obrigatória |

## Manifestos

Os manifestos individuais novos usam campos em português, incluindo:

- `caminho_origem`;
- `quantidade_paginas`;
- `caminho_markdown`;
- `paginas_com_ocr`;
- `paginas_de_mapa`;
- `paginas_de_tabela`;
- `paginas_de_tabela_raster`;
- `paginas_de_diagrama`;
- `paginas_de_registro_de_coordenadas`;
- `paginas_para_revisao`;
- `segundos_de_processamento`;
- `gerado_em`;
- `atualizado_em`.

`ler_manifesto()` aceita manifestos da série 0.7 e normaliza seus campos para os nomes portugueses.

O manifesto incremental de lote mantém temporariamente suas chaves históricas em inglês para permitir a retomada de lotes iniciados pela série 0.7. Essa é uma exceção explícita de compatibilidade, não o padrão para novos modelos públicos.

## Migração da API 0.7

| API 0.7 | API 0.8 |
|---|---|
| `convert_pdf` | `converter_pdf` |
| `diagnose_pdf` | `diagnosticar_pdf` |
| `convert_zip_batch` | `converter_lote_zip` |
| `write_manifest` | `escrever_manifesto` |
| `read_manifest` | `ler_manifesto` |
| `PageDiagnosis` | `DiagnosticoDePagina` |
| `DocumentDiagnosis` | `DiagnosticoDeDocumento` |
| `ConversionManifest` | `ManifestoDeConversao` |
| `TableAssessment` | `AvaliacaoDeTabela` |
| `CoordinateAssessment` | `AvaliacaoDeCoordenadas` |
| `RasterVisualAssessment` | `AvaliacaoVisualRaster` |

Os adaptadores antigos serão removidos em uma versão principal posterior à transição 0.8.

## Produtos gerados

- `<documento>.md`: conteúdo pesquisável e rastreável por página;
- `<documento>.manifest.json`: hashes, rotas, evidências, avisos e artefatos;
- `<documento>_assets/`: imagens visuais, tabulares e de revisão;
- `<nome-do-zip>.lote.manifest.json`: inventário incremental do lote.

## Validação local

```powershell
git pull
python -m pip install -e ".[dev,ocr]"
python -m pytest
python -m ruff check src tests
conversor-his --help
```

Os limiares visuais ainda devem ser medidos e recalibrados no conjunto-ouro do corpus antes de uso consolidado sem supervisão humana.

## Histórico recente

### 0.8.0a1 — API principal em português

- introduz módulos, funções, classes, parâmetros e campos públicos em português;
- move a implementação principal para `fluxo_conversao.py`;
- converte os módulos antigos em adaptadores de compatibilidade;
- produz manifestos individuais com campos em português;
- lê e normaliza manifestos produzidos pela série 0.7;
- preserva a retomada dos manifestos incrementais de lote;
- mantém estáveis as classificações internas persistidas durante a transição.

### 0.7.2 — preservação visual contextual

- combina evidência textual, vetorial e raster;
- preserva tabelas rasterizadas e diagramas candidatos;
- separa registros de coordenadas das tabelas;
- distingue mapas confirmados, candidatos e capas cartográficas;
- preserva imagens de revisão para OCR médio ou baixo e texto rotacionado.

## Licenciamento

- código-fonte, testes e automações próprios: **MIT License**;
- documentação e metodologia: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências e modelos: licença própria;
- legislação e conteúdos de terceiros não são relicenciados.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho.
