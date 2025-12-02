import streamlit as st
import zipfile
import io
import re
from pathlib import Path
from spellchecker import SpellChecker
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# -----------------------------------
# Text Processing (NLTK → 정규식으로 교체)
# -----------------------------------
def tokenize_text(text: str):
    # 영어 알파벳 단어만 추출
    return re.findall(r"[A-Za-z]+", text)

def is_candidate_word(tok: str) -> bool:
    if not tok.isalpha():
        return False
    if len(tok) <= 2:
        return False
    if tok.isupper():
        return False
    return True

def count_real_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+", text))

def analyze_spelling(text: str, spell_checker: SpellChecker):
    tokens = tokenize_text(text)
    candidate_words = [t.lower() for t in tokens if is_candidate_word(t)]
    misspelled = spell_checker.unknown(candidate_words)

    corrections = {}
    error_count = 0

    for surface in candidate_words:
        if surface in misspelled:
            suggestion = spell_checker.correction(surface) or surface
            corrections[surface] = suggestion
            error_count += 1

    return corrections, error_count

# -----------------------------------
# PDF 생성 함수
# -----------------------------------
def make_pdf(corrections: dict, total_words: int, error_words: int):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "맞춤법 검사 결과 보고서")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"총 단어 수: {total_words}")
    y -= 20
    c.drawString(50, y, f"오류 단어 수: {error_words}")
    y -= 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "오류 단어 목록:")
    y -= 30

    c.setFont("Helvetica", 11)
    for wrong, correct in corrections.items():
        c.drawString(60, y, f"{wrong} → {correct}")
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

    c.save()
    buffer.seek(0)
    return buffer

# -----------------------------------
# Streamlit UI
# -----------------------------------
st.title("맞춤법 검사 프로그램 (Streamlit 버전)")
st.write("여러 개의 `.txt` 파일을 업로드하면 CSV와 PDF 결과를 ZIP으로 다운로드할 수 있습니다.")

uploaded_files = st.file_uploader(
    "txt 파일 업로드",
    accept_multiple_files=True,
    type=["txt"]
)

if st.button("맞춤법 검사 실행"):
    if not uploaded_files:
        st.warning("txt 파일을 최소 1개 업로드해야 합니다.")
    else:
        spell = SpellChecker()

        zip_buffer = io.BytesIO()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for file in uploaded_files:
                text = file.read().decode("utf-8", errors="ignore")

                corrections, error_count = analyze_spelling(text, spell)
                total_words = count_real_words(text)

                # CSV 생성
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["잘못된 단어", "수정 제안"])
                for wrong, correct in corrections.items():
                    writer.writerow([wrong, correct])
                writer.writerow([])
                writer.writerow(["총 단어 수", total_words])
                writer.writerow(["오류 단어 수", error_count])

                csv_filename = f"{file.name}_결과.csv"
                zipf.writestr(csv_filename, csv_buffer.getvalue())

                # PDF 생성
                pdf_buffer = make_pdf(corrections, total_words, error_count)
                pdf_filename = f"{file.name}_결과.pdf"
                zipf.writestr(pdf_filename, pdf_buffer.read())

        zip_buffer.seek(0)

        st.success("처리가 완료되었습니다!")

        st.download_button(
            label="ZIP 파일 다운로드",
            data=zip_buffer,
            file_name=f"맞춤법_검사_결과_{now}.zip",
            mime="application/zip"
        )
