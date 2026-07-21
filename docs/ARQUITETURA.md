# Arquitetura técnica inicial

## Escopo

O projeto converte exclusivamente os diplomas indicados pelo município e não amplia autonomamente o corpus.

## Pipeline

1. preservação e hash do original;
2. diagnóstico por documento e página;
3. escolha de rota nativa, OCR ou híbrida;
4. produção de Markdown e JSON estrutural;
5. cálculo de métricas sobre amostra de referência;
6. aplicação de thresholds;
7. geração de relatório e decisão de aceitação.

## Motores

- PyMuPDF: diagnóstico e extração nativa;
- Tesseract: baseline de OCR;
- OCRmyPDF: integração futura para PDF pesquisável intermediário;
- PaddleOCR: benchmark e fallback para layouts complexos.
