import streamlit as st

# Basic page config
st.set_page_config(layout="wide", page_title="PDF Assistant", page_icon="📄")

# Simple title
st.title("📄 PDF Assistant")
st.write("Welcome to the PDF Assistant!")

# Test basic functionality
if st.button("Test Button"):
    st.success("✅ App is working!")

# Simple file upload
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")
if uploaded_file:
    st.success(f"✅ File uploaded: {uploaded_file.name}")
    st.write(f"File size: {uploaded_file.size} bytes")

# Check environment variables
st.subheader("🔧 Environment Check")
st.write("Checking if environment variables are set...")

# Try to import and check config
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    # Check API keys
    api_key_1 = os.getenv('PERPLEXITY_API_KEY_1')
    api_key_2 = os.getenv('PERPLEXITY_API_KEY_2')
    
    if api_key_1:
        st.success("✅ PERPLEXITY_API_KEY_1 is set")
    else:
        st.warning("⚠️ PERPLEXITY_API_KEY_1 is not set")
        
    if api_key_2:
        st.success("✅ PERPLEXITY_API_KEY_2 is set")
    else:
        st.info("ℹ️ PERPLEXITY_API_KEY_2 is not set (optional)")
        
    # Check Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    if supabase_url:
        st.success("✅ SUPABASE_URL is set")
    else:
        st.warning("⚠️ SUPABASE_URL is not set")
        
except Exception as e:
    st.error(f"❌ Error checking environment: {e}")

st.write("✅ App is running successfully!") 