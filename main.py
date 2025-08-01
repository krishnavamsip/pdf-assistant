import streamlit as st
import pdfplumber
import uuid
from hybrid_ai import HybridAI
from supabase_client import upload_pdf_to_supabase, delete_pdf_from_supabase
from config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize HybridAI with Perplexity
try:
    # Validate configuration first
    Config.validate_config()
    ai = HybridAI()
except Exception as e:
    st.error(f"Failed to initialize AI: {e}")
    st.error("Please ensure both PERPLEXITY_API_KEY_1 and PERPLEXITY_API_KEY_2 are set in your .env file")
    st.stop()

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

# Show API usage stats in sidebar
if st.sidebar.checkbox("Show API Usage Stats"):
    try:
        stats = ai.get_usage_stats()
        st.sidebar.subheader("API Usage Statistics")
        for key_name, key_stats in stats.items():
            st.sidebar.metric(
                label=f"{key_name.upper()}",
                value=f"{key_stats['requests']} requests",
                delta=f"{key_stats['success_rate']:.1f}% success"
            )
    except Exception as e:
        st.sidebar.error(f"Could not load stats: {e}")

# --- Main Title ---
st.title("PDF Assistant")
st.markdown(
    "<style>div.block-container{padding-top:2rem;} .stButton>button{background:#4F8BF9;color:white;} .stFileUploader{border:2px solid #4F8BF9;border-radius:8px;} .stSuccess{background:#e6f7ff;} .stError{background:#fff1f0;} .stRadio>div{gap:1rem;}</style>",
    unsafe_allow_html=True
)

# --- Session State for File Caching ---
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None
if 'public_url' not in st.session_state:
    st.session_state.public_url = None
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = None
if 'unique_filename' not in st.session_state:
    st.session_state.unique_filename = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]  # Generate a unique user ID for this session

# --- Delete file only if a new file is uploaded ---
def clear_uploaded_file():
    if st.session_state.unique_filename:
        try:
            delete_pdf_from_supabase(st.session_state.unique_filename)
        except Exception as e:
            st.warning(f"Could not delete previous file: {e}")
    st.session_state.uploaded_filename = None
    st.session_state.public_url = None
    st.session_state.pdf_text = None
    st.session_state.unique_filename = None
    # Clear any generated content when a new file is uploaded
    if 'summary' in st.session_state:
        st.session_state.summary = None
    if 'mcqs' in st.session_state:
        del st.session_state.mcqs
    if 'mcq_answers' in st.session_state:
        del st.session_state.mcq_answers

# --- PDF Upload ---
st.header("1. Upload a PDF")
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

# Only process a new file upload
if uploaded_file and uploaded_file.name != st.session_state.uploaded_filename:
    clear_uploaded_file()
    with st.spinner("Uploading to cloud..."):
        try:
            public_url, unique_filename = upload_pdf_to_supabase(uploaded_file, st.session_state.user_id)
            st.session_state.public_url = public_url
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.unique_filename = unique_filename
            st.success(f"✅ Uploaded to cloud: [Open PDF]({public_url})")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")
            st.stop()
    uploaded_file.seek(0)
    with st.spinner("Extracting text from PDF..."):
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages)
            st.session_state.pdf_text = text
        except Exception as e:
            st.error(f"❌ Failed to extract text: {e}")
            st.stop()

# If a file is already uploaded and processed, show its status
if st.session_state.uploaded_filename and st.session_state.public_url:
    st.success(f"✅ Uploaded: [Open PDF]({st.session_state.public_url})")

# Only show options if a file is uploaded and text is extracted
if st.session_state.pdf_text:
    st.header("2. Choose an action")
    option = st.selectbox("What would you like to do?", ["Summarize", "Generate MCQs", "Ask Questions (QA)"])

    if option == "Summarize":
        if 'summary' not in st.session_state:
            st.session_state.summary = None
        
        if st.button("Generate Summary", type="primary"):
            progress = st.progress(0, text="Summarizing...")
            def update_progress(val):
                progress.progress(val, text=f"Summarizing... {int(val*100)}%")
            try:
                summary = ai.get_summary(st.session_state.pdf_text, progress_callback=update_progress)
                progress.empty()
                st.session_state.summary = summary
                with st.expander("📌 Summary", expanded=True):
                    st.markdown(summary)
            except Exception as e:
                progress.empty()
                st.error(f"❌ Summary generation failed: {e}")
        elif st.session_state.summary:
            with st.expander("📌 Summary", expanded=True):
                st.markdown(st.session_state.summary)
            if st.button("Regenerate Summary"):
                st.session_state.summary = None
                st.experimental_rerun()
        else:
            st.info("Click 'Generate Summary' to create a comprehensive summary of your PDF.")

    elif option == "Generate MCQs":
        num_qs = st.selectbox("Select number of questions", [5, 10, 20], key="num_qs")
        
        if 'mcqs' not in st.session_state:
            st.session_state.mcqs = None
            st.session_state.mcq_answers = None
        
        if st.button("Generate MCQs", type="primary"):
            with st.spinner("Generating MCQs..."):
                try:
                    st.session_state.mcqs = ai.generate_mcqs(st.session_state.pdf_text, num_qs)
                    st.session_state.mcq_answers = [None] * len(st.session_state.mcqs)
                except Exception as e:
                    st.error(f"❌ MCQ generation failed: {e}")
                    st.stop()
        
        if st.session_state.mcqs:
            with st.expander("📝 Multiple Choice Questions", expanded=True):
                for i, q in enumerate(st.session_state.mcqs):
                    st.markdown(f"**Q{i+1}. {q['question']}**")
                    selected = st.radio(
                        "Choose answer",
                        q['options'],
                        key=f"mcq_{i}",
                        index=q['options'].index(st.session_state.mcq_answers[i]) if st.session_state.mcq_answers[i] in q['options'] else None
                    )
                    if selected != st.session_state.mcq_answers[i]:
                        st.session_state.mcq_answers[i] = selected
                    if selected:
                        if selected == q['answer']:
                            st.success(f"✅ Correct! The answer is: {q['answer']}")
                        else:
                            st.error(f"❌ Wrong! The correct answer is: {q['answer']}")
                if st.button("Regenerate MCQs"):
                    st.session_state.mcqs = None
                    st.session_state.mcq_answers = None
                    st.experimental_rerun()
        elif not st.session_state.mcqs and not st.button("Generate MCQs", type="primary"):
            st.info("Click 'Generate MCQs' to create multiple choice questions based on your PDF.")

    elif option == "Ask Questions (QA)":
        user_q = st.text_input("Ask a question based on the PDF")
        if user_q:
            with st.spinner("Thinking..."):
                try:
                    answer, used_context = ai.answer_question(st.session_state.pdf_text, user_q)
                    st.markdown(f"**Answer:** {answer}")
                    with st.expander("Show context used for answer"):
                        st.write(used_context)
                except Exception as e:
                    st.error(f"❌ Question answering failed: {e}")

# If no file is uploaded or processed, prompt user
if not st.session_state.pdf_text:
    st.info("Please upload a PDF to get started.")

# --- (Future) List uploaded PDFs ---
# st.header("Your Uploaded PDFs")
# TODO: List PDFs from Supabase bucket and allow users to open them