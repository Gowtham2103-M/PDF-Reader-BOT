import streamlit as st
from google import genai
from pypdf import PdfReader
import os, re

st.set_page_config(
    page_title="PDF READER BOT",
    page_icon="📄",
    layout="centered"
)

API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)


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
        score = len(q_words & c_words)
        scored.append((score, chunk))

    scored.sort(reverse=True)
    return [c for s, c in scored[:top_k] if s > 0]


pdf_text = read_pdf("sample.pdf")
chunks = chunk_text(pdf_text)

st.title("📄 PDF READER BOT")
st.caption("Ask questions strictly from the uploaded PDF")

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
If not found, say: Not available in PDF.

Context:
{context}

Question:
{prompt}
"""

                response = client.models.generate_content(
                    model="models/gemini-2.5-flash",
                    contents=prompt_text
                )
                answer = response.text

            st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
