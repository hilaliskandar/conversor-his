# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com suporte a OCR seletivo, rastreabilidade e controle de qualidade.

Versão atual: **0.4.0**.

## Princípios

- utiliza exclusivamente os diplomas indicados pelo município;
- preserva integralmente os arquivos originais;
- diagnostica cada página antes de escolher a rota de conversão;
- aplica extração nativa quando possível e OCR quando necessário;
- preserva mapas como imagens vinculadas ao Markdown;
- distingue imagens de conteúdo de elementos gráficos decorativos recorrentes;
- registra as decisões de conversão em diagnóstico e manifesto auditáveis;
- avalia a qualidade do OCR e sinaliza páginas que exigem revisão humana;
- prevê medição de CER, WER, fidelidade estrutural e correspondência de elementos críticos;
- bloqueia a entrada no corpus quando os thresholds de validação não são atingidos.

## Arquitetura atual

- `pypdf`: leitura, diagnóstico, extração nativa e inspeção de objetos gráficos;
- `pypdfium2`: renderização de páginas para OCR, mapas e inspeção;
- Tesseract: OCR local seletivo e fornecimento de dados de confiança;
- Pillow: gravação e tratamento das imagens geradas;
- Typer e Rich: interface de linha de comando;
- Docling: rota estrutural opcional planejada para layouts e tabelas complexas;
- PaddleOCR: componente opcional planejado para benchmark e fallback;
- OCRmyPDF: integração opcional separada.

O núcleo não depende de PyMuPDF nem de Ghostscript.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Para OCR com Tesseract:

```powershell
pip install -e ".[dev,ocr]"
```

Para a rota estrutural com Docling e pdfplumber, quando disponibilizada:

```powershell
pip install -e ".[dev,structured]"
```

## Uso inicial

Diagnóstico do documento:

```powershell
conversor-his diagnosticar `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

Conversão:

```powershell
conversor-his converter `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

## Produtos gerados

O comando de diagnóstico produz:

- `<documento>.diagnostico.json`: condição das páginas e decisão preliminar de rota.

O comando de conversão pode produzir:

- `<documento>.md`: conteúdo convertido, com rastreabilidade por página;
- `<documento>.manifest.json`: descrição da operação executada e dos artefatos gerados;
- `<documento>_assets/`: imagens de mapas e outros ativos preservados;
- advertências no Markdown e no manifesto para páginas que exigem revisão.

## Histórico de versões

### 0.4.0 — controle de qualidade pós-OCR e manifesto de conversão

- acrescenta métricas pós-OCR por página: quantidade de caracteres, palavras, proporção alfanumérica e confiança média;
- classifica o resultado OCR como `high`, `medium` ou `low`;
- registra `requires_review` e as razões da revisão;
- sinaliza no Markdown resultados OCR que não devem ser tratados como transcrição normativa confiável;
- cria um manifesto de conversão distinto do diagnóstico;
- registra hash e tamanho do Markdown, ativos gerados, páginas OCR, páginas cartográficas, páginas para revisão, DPI e versão do conversor;
- amplia, de forma conservadora, a tolerância geométrica para ocorrências periféricas de um gráfico já confirmado como decorativo;
- mantém como conteúdo qualquer ocorrência ampliada ou deslocada para o interior da página.

### 0.3.0 — supressão lógica de gráficos repetitivos

- inventaria XObjects gráficos e calcula fingerprints SHA-256;
- identifica elementos gráficos recorrentes, pequenos, periféricos e geometricamente estáveis;
- preserva o PDF original e realiza apenas supressão lógica para fins de roteamento;
- diferencia `raw_image_count`, `decorative_image_count` e `content_image_count`;
- elimina falsos alertas de página híbrida causados por logomarcas, cabeçalhos e rodapés repetitivos;
- registra os elementos decorativos identificados no diagnóstico e no manifesto;
- mantém mapas e outras imagens relevantes fora da supressão decorativa.

### 0.2.2 — correção de empacotamento e estabilidade da instalação

- corrige o arquivo `pyproject.toml` truncado;
- simplifica a configuração de empacotamento;
- restabelece a instalação editável e o funcionamento do comando `conversor-his`.

### 0.2.0 — arquitetura permissiva de conversão

- substitui o backend obrigatório PyMuPDF por componentes com licenças permissivas;
- estabelece `pypdf` como base de leitura, diagnóstico e extração nativa;
- utiliza `pypdfium2` para renderização;
- introduz OCR seletivo com Tesseract;
- estrutura os comandos `diagnosticar` e `converter`;
- estabelece Markdown, diagnóstico e manifesto como produtos centrais do fluxo.

## Estado atual

A versão `0.4.0` consolida as rotas de extração nativa, OCR seletivo, preservação cartográfica, supressão lógica de elementos gráficos repetitivos e controle preliminar de qualidade pós-OCR.

A qualidade de tabelas, layouts complexos, segmentação jurídica e normalização textual continuará sendo medida e aprimorada por meio do benchmark do corpus legislativo.

## Licenciamento

- código-fonte, testes, scripts e automações próprios: **MIT License**;
- documentação, metodologia, diagramas e materiais formativos: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências, modelos e pesos: licença própria de cada componente;
- legislação municipal e conteúdos de terceiros: não são relicenciados.

Consulte `LICENSING.md` e `THIRD_PARTY_NOTICES.md`.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho. Esses artefatos devem permanecer em armazenamento controlado.
