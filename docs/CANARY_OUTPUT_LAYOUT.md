# Gate canário e saída leve

## Organização da saída

A conversão separa os produtos em duas categorias:

```text
saida/
├── analise/
│   ├── documento.md
│   ├── documento.manifest.json
│   └── documento.ocr_tokens.jsonl
└── ativos/
    └── documento/
        └── pagina_*.png
```

A pasta `analise/` pode ser compartilhada sem as imagens. Para gerar um ZIP
leve com Markdown, CSV, JSON, JSONL e arquivos textuais auxiliares:

```powershell
conversor-his empacotar-analise `
  --entrada "D:\corpus\processado" `
  --saida "D:\corpus\processado_analise.zip"
```

## Gate canário

O comando abaixo compara headings e termos críticos esperados com o texto
observado e devolve código de erro quando há regressão:

```powershell
conversor-his validar-canario `
  --entrada "D:\canarios\casos.json" `
  --saida "D:\canarios\resultado"
```

## OCR posicional

Para páginas submetidas a OCR, `documento.ocr_tokens.jsonl` registra cada token
com confiança, página, bloco, parágrafo, linha, palavra e bounding box. Essa
camada intermediária será usada na reconstrução de colunas e tabelas e na
revisão dirigida de números, símbolos e termos jurídicos críticos.
