import streamlit as st

# Step 1: Basic imports
st.write("Step 1: Basic Streamlit import - ✅ Working")

try:
    import pdfplumber
    st.write("Step 2: pdfplumber import - ✅ Working")
except Exception as e:
    st.write(f"Step 2: pdfplumber import - ❌ Failed: {e}")

try:
    import uuid
    st.write("Step 3: uuid import - ✅ Working")
except Exception as e:
    st.write(f"Step 3: uuid import - ❌ Failed: {e}")

try:
    from dotenv import load_dotenv
    st.write("Step 4: dotenv import - ✅ Working")
except Exception as e:
    st.write(f"Step 4: dotenv import - ❌ Failed: {e}")

try:
    from config import Config
    st.write("Step 5: config import - ✅ Working")
except Exception as e:
    st.write(f"Step 5: config import - ❌ Failed: {e}")

try:
    from hybrid_ai import HybridAI
    st.write("Step 6: hybrid_ai import - ✅ Working")
except Exception as e:
    st.write(f"Step 6: hybrid_ai import - ❌ Failed: {e}")

try:
    from supabase_client import upload_pdf_to_supabase, delete_pdf_from_supabase
    st.write("Step 7: supabase_client import - ✅ Working")
except Exception as e:
    st.write(f"Step 7: supabase_client import - ❌ Failed: {e}")

st.write("✅ All imports tested!") 