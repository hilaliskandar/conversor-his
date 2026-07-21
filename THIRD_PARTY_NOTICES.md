# Avisos de componentes de terceiros

Este arquivo registra dependencias e componentes externos relevantes ao Conversor HIS. Cada componente permanece sujeito a sua propria licenca. A MIT License do codigo do projeto nao substitui nem modifica as licencas de terceiros.

## Dependencias atuais

| Componente | Funcao | Licenca declarada pelo projeto | Situacao no Conversor HIS |
|---|---|---|---|
| PyMuPDF | leitura, diagnostico e extracao de PDF | AGPL-3.0 ou comercial | dependencia temporaria; substituicao planejada por componentes permissivos |
| Pydantic | validacao e modelos de dados | MIT | dependencia do nucleo |
| PyYAML | leitura de configuracao | MIT | dependencia do nucleo |
| Typer | interface de linha de comando | MIT | dependencia do nucleo |
| Rich | saida formatada no terminal | MIT | dependencia do nucleo |
| python-docx | leitura de DOCX | MIT | dependencia do nucleo |
| Pillow | processamento de imagens | HPND | dependencia do nucleo |
| pytesseract | integracao Python com Tesseract | Apache-2.0 | dependencia opcional de OCR |
| Tesseract OCR | reconhecimento optico de caracteres | Apache-2.0 | programa externo opcional |
| OCRmyPDF | processamento e OCR de PDFs | MPL-2.0 | integracao opcional planejada; nao modificar ou redistribuir sem preservar a MPL-2.0 |
| PaddleOCR | OCR e analise estrutural | Apache-2.0 | dependencia opcional para benchmark e fallback |

## Componentes planejados para a rota permissiva

| Componente | Funcao pretendida | Licenca esperada |
|---|---|---|
| pypdf | leitura e extracao textual de PDF | BSD-3-Clause |
| pdfminer.six | extracao com informacao de layout | MIT |
| pdfplumber | analise geometrica e tabelas | MIT |
| pypdfium2 | renderizacao de paginas | Apache-2.0 ou BSD-3-Clause, alem dos avisos aplicaveis ao PDFium |
| Docling | reconstrucao estrutural e exportacao para Markdown/JSON | MIT; modelos devem ser verificados separadamente |

## PyMuPDF

A versao inicial do projeto ainda utiliza PyMuPDF. Essa dependencia nao esta abrangida pela MIT License do Conversor HIS. Antes de uma distribuicao publica tratada como integralmente permissiva, o projeto devera:

1. substituir PyMuPDF por uma rota permissiva validada; ou
2. cumprir a AGPL-3.0; ou
3. obter licenca comercial adequada.

A substituicao sera realizada somente apos benchmark no corpus de legislacao municipal, para evitar perda de qualidade documental.

## Ghostscript

Ghostscript nao deve integrar o pacote, instalador, conteiner ou distribuicao oficial do Conversor HIS sem avaliacao especifica de sua licenca AGPL ou contratacao de licenca comercial. Quando presente no ambiente do usuario, sua instalacao e uso permanecem sujeitos aos termos do fornecedor.

## Modelos e pesos

Modelos de OCR, arquivos `traineddata`, pesos de deteccao de layout, modelos de tabelas e outros artefatos baixados separadamente nao sao automaticamente licenciados sob MIT. A versao, a origem, o hash e a licenca de cada modelo devem ser registrados no manifesto de execucao ou no inventario do ambiente.

## Documentos processados

Legislacao municipal, PDFs, anexos, mapas, tabelas e demais documentos recebidos de terceiros nao sao relicenciados por este projeto. A execucao do Conversor HIS sobre um documento nao transfere direitos sobre o original nem torna a saida automaticamente aberta.

Este inventario devera ser atualizado sempre que uma dependencia, modelo ou componente externo for adicionado, removido ou alterado.