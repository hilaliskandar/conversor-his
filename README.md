# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com OCR seletivo, rastreabilidade e controle de qualidade.

Versão atual: **0.5.3**.

## Princípios

- utiliza exclusivamente os diplomas indicados pelo município;
- preserva integralmente os arquivos originais;
- diagnostica cada página antes de escolher a rota de conversão;
- aplica extração nativa quando possível e OCR quando necessário;
- preserva simultaneamente imagem e texto em páginas visuais;
- preserva tabelas confirmadas e candidatas como texto linear e imagem;
- compara extrações `layout` e simples quando encontra texto rotacionado;
- distingue imagens de conteúdo de elementos gráficos decorativos recorrentes;
- registra decisões, avisos, tempos e artefatos em manifestos auditáveis;
- grava Markdown e manifestos de forma atômica;
- permite limitar, interromper e retomar lotes municipais.

## Arquitetura atual

- `pypdf`: leitura, diagnóstico, extração nativa e inspeção de objetos gráficos;
- `pypdfium2`: renderização de páginas para OCR, mapas, tabelas e inspeção;
- Tesseract: OCR local seletivo e dados de confiança;
- Pillow: gravação e tratamento das imagens geradas;
- Typer e Rich: interface de linha de comando;
- biblioteca padrão `zipfile`: processamento seguro de lotes municipais compactados.

O núcleo não depende de PyMuPDF nem de Ghostscript.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ocr]"
```

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

### Lote municipal completo

O valor `0` em `--documentos` processa todos os PDFs elegíveis:

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0
```

### Amostra limitada

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio_teste" `
  --documentos 10
```

A forma abreviada também é aceita:

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio_teste" `
  -n 10
```

### Retomada

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0 `
  --retomar
```

A retomada reutiliza documentos concluídos somente quando coincidem o hash da fonte, a versão do conversor, o DPI e os produtos finais existentes.

Por padrão, uma pasta-raiz única dentro do ZIP é removida para evitar estruturas duplicadas. Para mantê-la:

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --manter-raiz-comum
```

## Comportamento do lote

- percorre subdiretórios internos do ZIP;
- ordena os PDFs por caminho para tornar amostras reproduzíveis;
- ignora arquivos não PDF;
- rejeita travessia de diretórios, caminhos absolutos e links simbólicos;
- detecta duplicidade de caminho e conteúdo por SHA-256;
- não converte duas vezes PDFs exatamente iguais;
- isola falhas por documento;
- atualiza o manifesto geral antes e depois de cada PDF;
- registra estados `processing`, `success`, `failed`, `duplicate` e `interrupted`;
- mantém produtos já concluídos quando a execução é interrompida.

## Produtos gerados

O comando de conversão produz:

- `<documento>.md`: conteúdo convertido e rastreável por página;
- `<documento>.manifest.json`: operação, hashes, rotas, avisos e tempo;
- `<documento>_assets/`: imagens visuais e tabulares preservadas.

O comando `converter-lote` também produz:

- `<nome-do-zip>.lote.manifest.json`: inventário incremental do lote, com limite, pendências, sucessos, falhas, duplicados, tempos e caminhos internos.

## Histórico de versões

### 0.5.3 — preservação visual e execução retomável

- acrescenta `--documentos` e `-n`, com `0` significando todos;
- cria manifesto incremental atualizado após cada documento;
- acrescenta `--retomar` com verificação de hash, versão, DPI e produtos;
- detecta PDFs duplicados por conteúdo antes da conversão;
- remove por padrão uma raiz comum redundante do ZIP;
- exibe no terminal o documento em processamento;
- registra tempo por documento e por lote;
- captura avisos de texto rotacionado e compara extração `layout` e simples;
- registra modo escolhido e contagens de caracteres por página;
- preserva texto junto à imagem em páginas classificadas como visuais;
- preserva também a imagem das candidatas a tabela;
- escreve Markdown e manifestos atomicamente.

### 0.5.2 — processamento seguro de lotes municipais em ZIP

- acrescenta o comando `converter-lote`;
- preserva a árvore interna de diretórios;
- mantém o ZIP intacto e usa extração temporária por documento;
- isola falhas por diploma;
- valida caminhos e assinatura PDF.

### 0.5.1 — estabilização inicial da detecção tabular

- introduz os estados `not_table`, `candidate` e `confirmed`;
- restringe a confirmação tabular e reduz falsos positivos jurídicos;
- registra candidatas separadamente no manifesto.

## Estado atual

A série `0.5.x` permanece experimental. A promoção para `0.6.0` dependerá de precisão mínima de 0,95, revocação mínima de 0,90, F1 mínima de 0,92 e ausência de regressões nas rotas de mapas, OCR, tabelas e páginas decorativas.

## Licenciamento

- código-fonte, testes, scripts e automações próprios: **MIT License**;
- documentação, metodologia, diagramas e materiais formativos: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências, modelos e pesos: licença própria de cada componente;
- legislação municipal e conteúdos de terceiros: não são relicenciados.

Consulte `LICENSING.md` e `THIRD_PARTY_NOTICES.md`.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho. Esses artefatos devem permanecer em armazenamento controlado.
