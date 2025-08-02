import streamlit as st

st.set_page_config(layout="wide", page_title="Test App", page_icon="📄")

st.title("Test App")
st.write("If you can see this, Streamlit is working!")

# Test basic functionality
if st.button("Test Button"):
    st.success("Button works!")

# Test file uploader
uploaded_file = st.file_uploader("Test upload", type="pdf")
if uploaded_file:
    st.write(f"File uploaded: {uploaded_file.name}")

st.write("App is running successfully!") 