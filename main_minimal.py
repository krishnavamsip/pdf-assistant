import streamlit as st

# Basic page config
st.set_page_config(layout="wide", page_title="PDF Assistant", page_icon="📄")

# Simple title
st.title("PDF Assistant - Minimal Test")

# Test if basic Streamlit works
st.write("If you can see this, basic Streamlit is working!")

# Test session state
if 'test_var' not in st.session_state:
    st.session_state.test_var = 0

# Test button
if st.button("Test Button"):
    st.session_state.test_var += 1
    st.success(f"Button clicked {st.session_state.test_var} times!")

# Test file uploader
uploaded_file = st.file_uploader("Test PDF upload", type="pdf")
if uploaded_file:
    st.success(f"File uploaded: {uploaded_file.name}")

st.write("✅ Minimal app is working!") 