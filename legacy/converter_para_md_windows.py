#!/usr/bin/env python3
"""
Conversor de documentos (.pdf, .epub, .docx) para Markdown estruturado com OCR, detecção de idioma (fastText)
e separação por idioma em diretórios distintos. Compatível com Windows nativo (sem WSL).
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# OCR e imagem
import pytesseract
from pdf2image import convert_from_path

# PDF, EPUB, DOCX
import fitz  # PyMuPDF
import docx
import fasttext
import tempfile

# EPUB parsing
from ebooklib import epub
from bs4 import BeautifulSoup

# Detecção de idioma com fasttext
MODEL_PATH = "lid.176.ftz"
if not os.path.exists(MODEL_PATH):
    import urllib.request
    print("📥 Baixando modelo fastText...")
    urllib.request.urlretrieve(
        "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
        MODEL_PATH
    )
lang_model = fasttext.load_model(MODEL_PATH)

# Caminhos padrão no Windows
ENTRADA = Path(r"D:\Alê_2_0\dados\documentos")
SAIDA_PT = Path(r"D:\Alê_2_0\dados\documentos_md\pt")
SAIDA_EN = Path(r"D:\Alê_2_0\dados\documentos_md\en")
SAIDA_OUTROS = Path(r"D:\Alê_2_0\dados\documentos_md\outros")
ORIGINAIS = Path(r"D:\Alê_2_0\dados\documentos_bruto")

# Criação dos diretórios se necessário
for pasta in [SAIDA_PT, SAIDA_EN, SAIDA_OUTROS, ORIGINAIS]:
    pasta.mkdir(parents=True, exist_ok=True)

def detectar_idioma(texto):
    resultado = lang_model.predict(texto.replace("\n", " ")[:1000])
    idioma = resultado[0][0].replace("__label__", "")
    prob = resultado[1][0]
    return idioma, prob

def salvar_md(texto_md, destino, nome, idioma):
    if idioma == "pt":
        saida = SAIDA_PT
    elif idioma == "en":
        saida = SAIDA_EN
    else:
        saida = SAIDA_OUTROS
    saida.mkdir(parents=True, exist_ok=True)
    caminho_md = saida / (nome.stem + ".md")
    with open(caminho_md, "w", encoding="utf-8") as f:
        f.write(texto_md)
    return caminho_md

def mover_original(origem):
    destino = ORIGINAIS / origem.name
    shutil.move(str(origem), destino)

def extrair_texto_pdf(path_pdf, forcar_ocr=False):
    doc = fitz.open(path_pdf)
    texto_total = ""
    for i, pagina in enumerate(doc, 1):
        texto = pagina.get_text()
        if not texto.strip() or forcar_ocr:
            imagens = convert_from_path(str(path_pdf), dpi=300, first_page=i, last_page=i)
            texto = pytesseract.image_to_string(imagens[0], lang="por", config="--psm 6")
        texto_total += f"\n\n### 📄 Página {i}\n\n{texto.strip()}\n\n"
    return texto_total

def extrair_texto_docx(path_docx):
    doc = docx.Document(path_docx)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extrair_texto_epub(path_epub):
    book = epub.read_epub(str(path_epub))
    texto = ""
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            texto += soup.get_text(separator="\n").strip() + "\n\n"
    return texto

def processar_arquivo(caminho, args):
    ext = caminho.suffix.lower()
    if ext == ".pdf":
        texto = extrair_texto_pdf(caminho, forcar_ocr=args.forcar_ocr)
    elif ext == ".docx":
        texto = extrair_texto_docx(caminho)
    elif ext == ".epub":
        texto = extrair_texto_epub(caminho)
    else:
        return False, "Formato não suportado"

    idioma, prob = detectar_idioma(texto)
    if args.idiomas and idioma not in args.idiomas:
        return False, f"Idioma {idioma} ignorado por filtro"

    header = f"<!-- arquivo_original: {caminho.name} -->\n<!-- idioma_detectado: {idioma} ({prob:.2f}) -->\n\n"
    texto_md = header + texto.strip()

    salvar_md(texto_md, destino=None, nome=caminho.name, idioma=idioma)
    if not args.dry_run:
        mover_original(caminho)

    return True, f"{idioma.upper()}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--forcar-ocr", action="store_true")
    parser.add_argument("--idiomas", nargs="*", help="Ex: pt en fr")
    parser.add_argument("--reprocessar", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--limite", type=int, default=None)
    args = parser.parse_args()

    arquivos = list(ENTRADA.rglob("*"))
    arquivos = [f for f in arquivos if f.suffix.lower() in [".pdf", ".epub", ".docx"]]

    if args.limite:
        arquivos = arquivos[:args.limite]

    for i, caminho in enumerate(arquivos, 1):
        if not args.reprocessar:
            nome_md = caminho.with_suffix(".md").name
            if any((SAIDA_PT / nome_md).exists(),
                   (SAIDA_EN / nome_md).exists(),
                   (SAIDA_OUTROS / nome_md).exists()):
                continue
        try:
            sucesso, msg = processar_arquivo(caminho, args)
            prefixo = "✅" if sucesso else "⚠️"
        except Exception as e:
            prefixo = "❌"
            msg = str(e)
        print(f"{prefixo} [{i}/{len(arquivos)}] {caminho.name} → {msg}")

if __name__ == "__main__":
    main()
