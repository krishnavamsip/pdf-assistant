import streamlit as st
import pdfplumber
import uuid

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# --- Sidebar ---
st.set_page_config(layout="wide", page_title="PDF Assistant", page_icon="📄")
st.sidebar.title("📄 PDF Assistant")
st.sidebar.markdown("""
**Upload, summarize, and quiz yourself on any PDF.**
- Summary will be comprehensive and well-structured
- MCQs are generated based on the PDF content
- Working on QA functionality
- All files are stored securely in the cloud
""")
st.sidebar.info("Developed using Streamlit and AI.")

# --- Main Title ---
st.title("PDF Assistant")
st.markdown(
    "<style>div.block-container{padding-top:2rem;} .stButton>button{background:#4F8BF9;color:white;} .stFileUploader{border:2px solid #4F8BF9;border-radius:8px;} .stRadio>div{gap:1rem;}</style>",
    unsafe_allow_html=True
)

# --- Session State for File Caching ---
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = None

# --- PDF Upload ---
st.header("1. Upload a PDF")
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file:
    st.success(f"File uploaded: {uploaded_file.name}")
    
    # Simple text extraction
    if st.button("Extract Text"):
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                
                st.session_state.pdf_text = text
                st.success(f"Text extracted! Length: {len(text)} characters")
                
        except Exception as e:
            st.error(f"Error extracting text: {e}")

# Show extracted text if available
if st.session_state.pdf_text:
    st.header("2. Extracted Text")
    st.text_area("Text Preview", st.session_state.pdf_text[:1000] + "...", height=200)

st.write("App is working!") 