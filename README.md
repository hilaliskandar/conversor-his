# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com suporte a OCR, rastreabilidade e controle de qualidade.

## Princípios

- utiliza exclusivamente os diplomas indicados pelo município;
- preserva integralmente os arquivos originais;
- diagnostica cada página antes de escolher a rota de conversão;
- aplica extração nativa quando possível e OCR quando necessário;
- produz Markdown, manifesto e trilha de conversão;
- prevê medição de CER, WER, fidelidade estrutural e correspondência de elementos críticos;
- bloqueia a entrada no corpus quando os thresholds não são atingidos.

## Arquitetura da versão 0.2

- `pypdf`: leitura, diagnóstico e extração nativa;
- `pypdfium2`: renderização de páginas para OCR e inspeção;
- Tesseract: OCR local seletivo;
- Docling: rota estrutural opcional para layouts e tabelas complexas;
- PaddleOCR: extra opcional para benchmark e fallback;
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

Para a rota estrutural com Docling e pdfplumber:

```powershell
pip install -e ".[dev,structured]"
```

## Uso inicial

```powershell
conversor-his diagnosticar `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

```powershell
conversor-his converter `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

## Estado

A versão `0.2.0` substitui o backend obrigatório PyMuPDF por componentes permissivos. A qualidade em layouts complexos e tabelas continuará sendo medida pelo benchmark do corpus legislativo.

## Licenciamento

- código-fonte, testes, scripts e automações próprios: **MIT License**;
- documentação, metodologia, diagramas e materiais formativos: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências, modelos e pesos: licença própria de cada componente;
- legislação municipal e conteúdos de terceiros: não são relicenciados.

Consulte `LICENSING.md` e `THIRD_PARTY_NOTICES.md`.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho. Esses artefatos devem permanecer em armazenamento controlado.
