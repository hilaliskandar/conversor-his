# Avisos de componentes de terceiros

Cada componente permanece sujeito à sua própria licença. A MIT License do código do Conversor HIS não substitui nem modifica licenças de terceiros.

## Dependências do núcleo

| Componente | Função | Licença | Situação |
|---|---|---|---|
| pypdf | leitura e extração textual de PDF | BSD-3-Clause | núcleo |
| pypdfium2 / PDFium | renderização de páginas | Apache-2.0 ou BSD-3-Clause e avisos do PDFium | núcleo |
| Pydantic | modelos e validação | MIT | núcleo |
| PyYAML | configuração | MIT | núcleo |
| Typer | CLI | MIT | núcleo |
| Rich | terminal | MIT | núcleo |
| python-docx | DOCX | MIT | núcleo |
| Pillow | imagens | HPND | núcleo |

## Dependências opcionais

| Componente | Função | Licença | Situação |
|---|---|---|---|
| pytesseract | integração com Tesseract | Apache-2.0 | extra `ocr` |
| Tesseract OCR | OCR | Apache-2.0 | programa externo |
| Docling | estrutura e Markdown/JSON | MIT; modelos verificados separadamente | extra `structured` |
| pdfplumber | layout e tabelas | MIT | extra `structured` |
| PaddleOCR | OCR e layout | Apache-2.0 | extra `paddle` |
| OCRmyPDF | PDF pesquisável e OCR | MPL-2.0 | extra `ocrmypdf` |

## Componentes não integrantes do núcleo

PyMuPDF foi removido das dependências obrigatórias na versão 0.2.0. Ghostscript não integra o pacote, instalador, contêiner ou distribuição oficial. Qualquer instalação independente permanece sujeita à licença do respectivo fornecedor.

## Modelos e pesos

Modelos de OCR, arquivos `traineddata`, pesos de layout e modelos de tabelas não são automaticamente MIT. Versão, origem, hash e licença devem ser registrados no manifesto do ambiente.

## Documentos processados

Legislação municipal, PDFs, anexos, mapas, tabelas e demais documentos de terceiros não são relicenciados pela execução do Conversor HIS.
