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
ai_available = False
ai = None

try:
    # Check if we have API keys before trying to validate
    if Config.has_api_keys():
        # Validate configuration first
        Config.validate_config()
        ai = HybridAI()
        ai_available = True
    else:
        st.warning("⚠️ No API keys found. AI features will be disabled.")
        st.info("To enable AI features, add your Perplexity API keys to Streamlit Cloud secrets.")
        ai_available = False
        ai = None
except Exception as e:
    st.error(f"⚠️ AI Configuration Error: {e}")
    st.error("Please ensure your API keys are configured in Streamlit Cloud secrets.")
    st.info("Go to your app settings → Secrets and add your environment variables.")
    ai_available = False
    ai = None

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

# Show API usage stats in sidebar - DISABLED
# if ai_available and st.sidebar.checkbox("Show API Usage Stats"):
#     try:
#         stats = ai.get_usage_stats()
#         st.sidebar.subheader("API Usage Statistics")
#         for key_name, key_stats in stats.items():
#             st.sidebar.metric(
#                 label=f"{key_name.upper()}",
#                 value=f"{key_stats['requests']} requests",
#                 delta=f"{key_stats['success_rate']:.1f}% success"
#             )
#     except Exception as e:
#         st.sidebar.error(f"Could not load stats: {e}")
# elif not ai_available:
#     st.sidebar.warning("⚠️ AI features unavailable - configure API keys first")

# --- Main Title ---
st.title("PDF Assistant")
st.markdown(
    "<style>div.block-container{padding-top:2rem;} .stButton>button{background:#4F8BF9;color:white;} .stFileUploader{border:2px solid #4F8BF9;border-radius:8px;} .stRadio>div{gap:1rem;}</style>",
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
    
    # Upload progress
    upload_progress = st.progress(0, text="Uploading to cloud...")
    try:
        public_url, unique_filename = upload_pdf_to_supabase(uploaded_file, st.session_state.user_id)
        upload_progress.progress(100, text="✅ Uploaded to cloud!")
        st.session_state.public_url = public_url
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.unique_filename = unique_filename
        st.success(f"✅ Uploaded to cloud: [Open PDF]({public_url})")
    except Exception as e:
        upload_progress.empty()
        st.error(f"❌ Upload failed: {e}")
        st.stop()
    
    # Text extraction progress
    uploaded_file.seek(0)
    extract_progress = st.progress(0, text="Extracting text from PDF...")
    try:
        # Try pdfplumber first
        with pdfplumber.open(uploaded_file) as pdf:
            total_pages = len(pdf.pages)
            text_parts = []
            
            for i, page in enumerate(pdf.pages):
                # Try multiple extraction methods
                page_text = page.extract_text() or ""
                
                # If no text found, try alternative extraction methods
                if not page_text.strip():
                    # Method 1: Try extracting tables
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            page_text += " ".join([str(cell) for cell in row if cell]) + "\n"
                
                # Method 2: Try extracting words directly
                if not page_text.strip():
                    words = page.extract_words()
                    page_text = " ".join([word['text'] for word in words])
                
                # Method 3: Try extracting text with different parameters
                if not page_text.strip():
                    page_text = page.extract_text(layout=True) or ""
                
                # Method 4: Try extracting text with different encoding
                if not page_text.strip():
                    try:
                        page_text = page.extract_text(encoding='utf-8') or ""
                    except:
                        pass
                
                text_parts.append(page_text)
                
                # Update progress
                progress_percent = (i + 1) / total_pages
                extract_progress.progress(progress_percent, text=f"Extracting text from PDF... Page {i+1}/{total_pages}")
            
            text = "".join(text_parts)
            extract_progress.progress(100, text="✅ Text extraction complete!")
            st.session_state.pdf_text = text
            
            # Show basic extraction info
            st.success(f"✅ Successfully extracted {len(text):,} characters from {total_pages} pages")
            
    except Exception as e:
        extract_progress.empty()
        st.warning(f"⚠️ pdfplumber failed: {e}")
        st.info("🔄 Trying alternative extraction method...")
        
        # Try PyPDF2 as fallback
        try:
            uploaded_file.seek(0)
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            total_pages = len(pdf_reader.pages)
            text_parts = []
            
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
                
                # Update progress
                progress_percent = (i + 1) / total_pages
                extract_progress.progress(progress_percent, text=f"Extracting with PyPDF2... Page {i+1}/{total_pages}")
            
            text = "".join(text_parts)
            extract_progress.progress(100, text="✅ Text extraction complete!")
            st.session_state.pdf_text = text
            
            st.success("✅ Successfully extracted text using PyPDF2!")
            st.info(f"📊 Extracted {len(text)} characters from {total_pages} pages")
            
        except Exception as e2:
            extract_progress.empty()
            st.error(f"❌ Both extraction methods failed: {e2}")
            st.stop()

# If a file is already uploaded and processed, show its status
if st.session_state.uploaded_filename and st.session_state.public_url:
    st.success(f"✅ Uploaded: [Open PDF]({st.session_state.public_url})")

# Only show options if a file is uploaded and text is extracted
if st.session_state.pdf_text:
    st.header("2. Choose an action")
    
    if not ai_available:
        st.error("❌ AI features are not available. Please configure your API keys in Streamlit Cloud secrets.")
        st.info("Go to your app settings → Secrets and add your environment variables.")
        st.stop()
    
    option = st.selectbox("What would you like to do?", ["Summarize", "Generate MCQs", "Ask Questions (QA)"])

    if option == "Summarize":
        if 'summary' not in st.session_state:
            st.session_state.summary = None

        if not ai_available:
            st.error("❌ AI features are not available. Please configure your API keys.")
            st.info("Go to your app settings → Secrets and add your Perplexity API keys.")
            st.stop()

        # Detect chapters in the text
        try:
            chapters = ai.detect_chapters(st.session_state.pdf_text)
        except Exception as e:
            st.error(f"Error detecting chapters: {e}")
            chapters = []
        
        if chapters:
            st.subheader("📚 Available Chapters")
            st.write("Select a chapter to summarize:")
            
            # Create chapter selection
            chapter_options = ["All Chapters (Full Book Summary)"] + [f"{ch['title']} (Pages {ch['start_page']}-{ch['end_page']})" for ch in chapters]
            selected_chapter = st.selectbox("Choose chapter:", chapter_options, key="chapter_selector")
            
            if st.button("Generate Summary", type="primary"):
                progress = st.progress(0, text="Summarizing...")
                def update_progress(val, text=None):
                    if text:
                        progress.progress(val, text=text)
                    else:
                        progress.progress(val, text=f"Summarizing... {int(val*100)}%")
                
                try:
                    if selected_chapter == "All Chapters (Full Book Summary)":
                        # Generate full book summary
                        summary = ai.get_summary(st.session_state.pdf_text, progress_callback=update_progress)
                    else:
                        # Generate chapter-specific summary
                        try:
                            chapter_index = chapter_options.index(selected_chapter) - 1  # -1 because of "All Chapters" option
                            selected_chapter_data = chapters[chapter_index]
                            chapter_text = ai.extract_chapter_text(st.session_state.pdf_text, selected_chapter_data)
                            summary = ai.get_summary(chapter_text, progress_callback=update_progress)
                        except Exception as e:
                            st.error(f"Error extracting chapter text: {e}")
                            summary = "Error: Could not extract chapter content"
                    
                    progress.empty()
                    st.session_state.summary = summary
                    with st.expander("📌 Summary", expanded=True):
                        st.markdown(summary)
                except Exception as e:
                    progress.empty()
                    st.error(f"❌ Summary generation failed: {e}")
        else:
            # Fallback for documents without clear chapters
            st.info("📖 No clear chapters detected. Generating full document summary...")
            
            if st.button("Generate Summary", type="primary"):
                progress = st.progress(0, text="Summarizing...")
                def update_progress(val, text=None):
                    if text:
                        progress.progress(val, text=text)
                    else:
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
        
        # Show existing summary if available
        if st.session_state.summary:
            with st.expander("📌 Summary", expanded=True):
                st.markdown(st.session_state.summary)
            if st.button("Regenerate Summary"):
                st.session_state.summary = None
                st.rerun()
        else:
            st.info("Click 'Generate Summary' to create a comprehensive summary of your PDF.")

    elif option == "Generate MCQs":
        if not ai_available:
            st.error("❌ AI features are not available. Please configure your API keys.")
            st.info("Go to your app settings → Secrets and add your Perplexity API keys.")
            st.stop()
            
        num_qs = st.selectbox("Select number of questions", [5, 10, 20], key="num_qs")
        
        # Initialize session state
        if 'mcqs' not in st.session_state:
            st.session_state.mcqs = None
        if 'mcq_answers' not in st.session_state:
            st.session_state.mcq_answers = None
        
        # Generate MCQs button
        if st.button("Generate MCQs", type="primary", key="generate_mcqs"):
            with st.spinner("Generating MCQs..."):
                try:
                    st.session_state.mcqs = ai.generate_mcqs(st.session_state.pdf_text, num_qs)
                    if st.session_state.mcqs:
                        st.session_state.mcq_answers = [None] * len(st.session_state.mcqs)
                    else:
                        st.error("❌ No MCQs were generated. Please try again.")
                except Exception as e:
                    st.error(f"❌ MCQ generation failed: {e}")
                    st.session_state.mcqs = None
                    st.session_state.mcq_answers = None
        
        # Display MCQs if available
        if st.session_state.mcqs and len(st.session_state.mcqs) > 0:
            # Regenerate button at the top of the MCQ section
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### 📝 Multiple Choice Questions")
            with col2:
                if st.button("🔄 Regenerate", key="regenerate_mcqs", help="Generate new MCQs"):
                    st.session_state.mcqs = None
                    st.session_state.mcq_answers = None
                    st.rerun()
            
            # Display the questions
            for i, q in enumerate(st.session_state.mcqs):
                if isinstance(q, dict) and 'question' in q and 'options' in q and 'answer' in q:
                    st.markdown(f"**Q{i+1}. {q['question']}**")
                    
                    # Ensure mcq_answers has the right length
                    while len(st.session_state.mcq_answers) <= i:
                        st.session_state.mcq_answers.append(None)
                    
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
                else:
                    st.error(f"❌ Invalid question format for Q{i+1}")
        elif not st.session_state.mcqs:
            st.info("Click 'Generate MCQs' to create multiple choice questions based on your PDF.")

    elif option == "Ask Questions (QA)":
        if not ai_available:
            st.error("❌ AI features are not available. Please configure your API keys.")
            st.info("Go to your app settings → Secrets and add your Perplexity API keys.")
            st.stop()
            
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