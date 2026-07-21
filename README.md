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

## Arquitetura inicial

- `diagnosticar`: classifica documentos e páginas;
- `converter`: executa extração direta ou OCR seletivo;
- `validar`: calculará métricas e aplicará thresholds;
- `benchmark-ocr`: comparará motores e configurações;
- `relatar`: consolidará resultados e trilha de auditoria.

Os comandos indicados no futuro estão registrados no roadmap e ainda não fazem parte da versão `0.1.0`.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ocr]"
```

Dependências externas recomendadas no Windows:

- Tesseract OCR com idioma `por`;
- Ghostscript e/ou pypdfium2 conforme a rota escolhida;
- OCRmyPDF, a ser integrado em etapa posterior;
- PaddleOCR, opcional para benchmark e fallback.

## Uso inicial

Diagnóstico de um PDF:

```powershell
conversor-his diagnosticar `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

Conversão de um PDF:

```powershell
conversor-his converter `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

## Estado

Versão inicial de arquitetura. Os módulos estão preparados para evolução incremental, comparação de motores de OCR e testes automatizados.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho. Esses artefatos são excluídos por `.gitignore` e devem permanecer em armazenamento controlado.
