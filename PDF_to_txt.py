import streamlit as st
import io
import zipfile
import re
from spellchecker import SpellChecker
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# -----------------------------------
# Tokenizer preserving surface tokens
# -----------------------------------
def tokenize_text(text: str):
    raw_tokens = text.split()
    tokens = []

    for t in raw_tokens:
        clean = re.sub(r"[^A-Za-z]", "", t)
        if clean:
            tokens.append((t, clean))
    return tokens


# -----------------------------------
# Candidate word rules
# -----------------------------------
def is_candidate_word(tok: str) -> bool:
    return tok.isalpha() and len(tok) > 2 and not tok.isupper()


# -----------------------------------
# Count words
# -----------------------------------
def count_real_words(text: str):
    return len(re.findall(r"[A-Za-z]+", text))


# -----------------------------------
# Spelling analysis
# -----------------------------------
def analyze_spelling(text: str, spell_checker: SpellChecker):
    tokens = tokenize_text(text)
    corrections = {}
    errors = 0

    for surface, clean in tokens:
        if is_candidate_word(clean):
            lw = clean.lower()
            if lw in spell_checker.unknown([lw]):
                corrections[surface] = spell_checker.correction(lw) or surface
                errors += 1

    return corrections, errors


# -----------------------------------
# PDF (Upgraded layout)
# -----------------------------------
def make_pdf(corrections: dict, total_words: int, error_words: int):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    margin = 50
    y = height - margin

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(margin, y, "맞춤법 검사 결과 보고서")
    y -= 30

    # Date
    c.setFont("Helvetica", 12)
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.drawString(margin, y, f"생성 일시: {today}")
    y -= 20

    # Divider line
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.setLineWidth(1)
    c.line(margin, y, width - margin, y)
    y -= 30

    # Summary section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "요약 정보")
    y -= 25

    c.setFont("Helvetica", 12)
    c.drawString(margin, y, f"- 총 단어 수: {total_words}")
    y -= 20
    c.drawString(margin, y, f"- 오류 단어 수: {error_words}")
    y -= 35

    # Divider
    c.line(margin, y, width - margin, y)
    y -= 30

    # Error list
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "오류 단어 목록")
    y -= 25

    c.setFont("Helvetica", 12)

    if len(corrections) == 0:
        c.drawString(margin, y, "(오류 없음)")
        y -= 20
    else:
        for wrong, correct in corrections.items():
            if y < 70:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 12)

            c.drawString(margin, y, f"{wrong:<20}  →  {correct}")
