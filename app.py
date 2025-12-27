import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os, re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="PDF READER BOT",
    page_icon="📄",
    layout="centered"
)

# ---------------- GEMINI SETUP ----------------
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------- PDF FUNCTIONS ----------------
@st.cache_data
def read_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=400):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def get_relevant_chunks(question, chunks, top_k=3):
    q_words = set(re.findall(r"\w+", question.lower()))
    scored = []

    for chunk in chunks:
        c_words = set(re.findall(r"\w+", chunk.lower()))
        scored.append((len(q_words & c_words), chunk))

    scored.sort(reverse=True)
    return [c for s, c in scored[:top_k] if s > 0]

# ---------------- LOAD PDF ----------------
pdf_text = read_pdf("sample.pdf")
chunks = chunk_text(pdf_text)

# ---------------- UI ----------------
st.title("📄 PDF READER BOT")
st.caption("Ask questions strictly from the uploaded PDF")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask something from the PDF..."):

    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant message
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            relevant = get_relevant_chunks(prompt, chunks)

            if not relevant:
                answer = "❌ Not available in PDF"
            else:
                context = "\n".join(relevant)
                prompt_text = f"""
Answer ONLY using the context below.
If not found, say: Not available in PDF.

Context:
{context}

Question:
{prompt}
"""
                response = model.generate_content(prompt_text)
                answer = response.text

            st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
