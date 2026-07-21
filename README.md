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
- pypdfium2 para renderização, conforme a rota escolhida;
- OCRmyPDF, a ser integrado em etapa posterior;
- PaddleOCR, opcional para benchmark e fallback.

Ghostscript não integra a distribuição oficial recomendada. Seu uso, quando presente no ambiente, depende de avaliação específica de licença.

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

A implementação inicial ainda utiliza PyMuPDF. Essa dependência será substituída por uma rota permissiva somente após benchmark no corpus legislativo, para preservar a qualidade de extração, estrutura e rastreabilidade.

## Licenciamento

O projeto adota licenciamento por camadas:

- código-fonte, testes, scripts e automações próprios: **MIT License**;
- documentação, metodologia, diagramas e materiais formativos produzidos pelo projeto: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências, modelos e pesos: licença própria de cada componente;
- legislação municipal, documentos recebidos e demais conteúdos de terceiros: não são relicenciados pelo projeto.

Consulte [`LICENSING.md`](LICENSING.md) para a delimitação completa e [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) para os avisos de componentes externos.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho. Esses artefatos são excluídos por `.gitignore` e devem permanecer em armazenamento controlado.