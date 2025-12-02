import streamlit as st
import io
import zipfile
import re
from spellchecker import SpellChecker
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# ---------------------------------------------------
# MUST BE FIRST: Streamlit page settings
# ---------------------------------------------------
st.set_page_config(
    page_title="맞춤법 검사기",
    page_icon="📝",
    layout="centered"
)

# ---------------------------------------------------
# Tokenizer (preserves surface form)
# ---------------------------------------------------
def tokenize_text(text: str):
    raw_tokens = text.split()
    tokens = []

    for t in raw_tokens:
        clean = re.sub(r"[^A-Za-z]", "", t)
        if clean:
            tokens.append((t, clean))
    return tokens

# ---------------------------------------------------
# Candidate word rules
# ---------------------------------------------------
def is_candidate_word(tok: str) -> bool:
    return tok.isalpha() and len(tok) > 2 and not tok.isupper()

# ---------------------------------------------------
# Count English words
# ---------------------------------------------------
def count_real_words(text: str):
    return len(re.findall(r"[A-Za-z]+", text))

# ---------------------------------------------------
# Spelling analysis
# ---------------------------------------------------
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

# ---------------------------------------------------
# PDF Generator (Styled)
# ---------------------------------------------------
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

    # Divider
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.line(margin, y, width - margin, y)
    y -= 30

    # Summary
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

            c.drawString(margin, y, f"{wrong:<20} → {correct}")
            y -= 20

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------------------------------------------
# Streamlit UI
# ---------------------------------------------------
st.markdown(
    """
    <div style='background: linear-gradient(to right, #4b79a1, #283e51);
                padding: 18px; border-radius: 8px; margin-bottom: 20px;'>
        <h2 style='color: white; text-align: center; margin: 0;'>
            맞춤법 검사 프로그램 (Streamlit 업그레이드 버전)
        </h2>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("여러 개의 `.txt` 파일을 업로드하면 CSV와 PDF 결과가 ZIP으로 제공됩니다.")

uploaded_files = st.file_uploader(
    "📄 txt 파일 업로드",
    accept_multiple_files=True,
    type=["txt"],
)

if uploaded_files:
    st.success(f"{len(uploaded_files)}개의 파일이 업로드되었습니다.")
    st.write("##### 업로드된 파일 목록:")
    for f in uploaded_files:
        st.write("- " + f.name)
    st.divider()

if st.button("🚀 맞춤법 검사 실행"):
    if not uploaded_files:
        st.warning("txt 파일을 최소 1개 업로드해야 합니다.")
    else:
        spell = SpellChecker()
        zip_buffer = io.BytesIO()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        progress = st.progress(0)

        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for idx, file in enumerate(uploaded_files):
                text = file.read().decode("utf-8", errors="ignore")

                corrections, error_count = analyze_spelling(text, spell)
                total_words = count_real_words(text)

                # CSV
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["잘못된 단어", "수정 제안"])
                for wrong, correct in corrections.items():
                    writer.writerow([wrong, correct])
                writer.writerow([])
                writer.writerow(["총 단어 수", total_words])
                writer.writerow(["오류 단어 수", error_count])

                zipf.writestr(f"{file.name}_결과.csv", csv_buffer.getvalue())

                # PDF
                pdf_buffer = make_pdf(corrections, total_words, error_count)
                zipf.writestr(f"{file.name}_결과.pdf", pdf_buffer.read())

                progress.progress((idx + 1) / len(uploaded_files))

        zip_buffer.seek(0)

        st.success("모든 파일 처리가 완료되었습니다! 🎉")

        st.download_button(
            label="📦 ZIP 파일 다운로드",
            data=zip_buffer,
            file_name=f"맞춤법_검사_결과_{now}.zip",
            mime="application/zip",
        )
