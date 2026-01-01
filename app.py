import streamlit as st
from google import genai
from pypdf import PdfReader
import os, re
from difflib import SequenceMatcher

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="PDF READER BOT",
    page_icon="📄",
    layout="centered"
)

# ---------------- API KEY ----------------
API_KEY = st.secrets.get("GOOGLE_API_KEY")
st.write("API key last 4 chars:", API_KEY[-4:])

if not API_KEY:
    st.error("❌ GOOGLE_API_KEY not found in environment variables")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ---------------- UTILITY FUNCTIONS ----------------
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

@st.cache_data(show_spinner=False)
def read_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=400):
    words = text.split()
    return [
        " ".join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]

def get_relevant_chunks(question, chunks, top_k=3):
    q_words = re.findall(r"\w+", question.lower())
    scored = []

    for chunk in chunks:
        chunk_words = re.findall(r"\w+", chunk.lower())
        score = 0

        for qw in q_words:
            if qw in chunk_words:
                score += 2
            else:
                for cw in chunk_words:
                    if similar(qw, cw) > 0.8:
                        score += 1
                        break

        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scored[:top_k] if s > 0]

# ---------------- UI ----------------
st.title("📄 PDF READER BOT")
st.caption("Ask questions strictly from the uploaded PDF")

uploaded_pdf = st.file_uploader(
    "Upload a PDF file",
    type=["pdf"]
)

if uploaded_pdf:
    with st.spinner("Reading PDF..."):
        pdf_text = read_pdf(uploaded_pdf)
        chunks = chunk_text(pdf_text)

    if not pdf_text.strip():
        st.error("❌ No readable text found in PDF")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask something from the PDF..."):

        st.session_state.messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                relevant = get_relevant_chunks(prompt, chunks)

                if not relevant:
                    answer = "❌ Not available in PDF"
                else:
                    context = "\n".join(relevant)

                    prompt_text = f"""
Answer ONLY using the context below.
You may answer YES or NO if the context clearly supports it.
If the answer is not supported by the context, say: Not available in PDF.

Context:
{context}

Question:
{prompt}
"""

                    try:
                        response = client.models.generate_content(
                            model="models/gemini-1.5-flash",
                            contents=[prompt_text]
                        )
                        answer = response.text
                    except Exception:
                        answer = "⚠️ API limit reached. Please wait and try again."

                st.markdown(answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

else:
    st.info("👆 Upload a PDF to start asking questions")


