import streamlit as st

st.set_page_config(layout="wide", page_title="AI Test", page_icon="📄")
st.title("AI Initialization Test")

st.write("Testing AI initialization step by step...")

# Test 1: Basic imports
try:
    from dotenv import load_dotenv
    load_dotenv()
    st.write("✅ dotenv loaded")
except Exception as e:
    st.error(f"❌ dotenv failed: {e}")

# Test 2: Config import
try:
    from config import Config
    st.write("✅ Config imported")
except Exception as e:
    st.error(f"❌ Config import failed: {e}")

# Test 3: Check API keys
try:
    has_keys = Config.has_api_keys()
    st.write(f"✅ API keys check: {has_keys}")
except Exception as e:
    st.error(f"❌ API keys check failed: {e}")

# Test 4: Config validation
try:
    if Config.has_api_keys():
        Config.validate_config()
        st.write("✅ Config validation passed")
    else:
        st.write("⚠️ No API keys, skipping validation")
except Exception as e:
    st.error(f"❌ Config validation failed: {e}")

# Test 5: HybridAI import
try:
    from hybrid_ai import HybridAI
    st.write("✅ HybridAI imported")
except Exception as e:
    st.error(f"❌ HybridAI import failed: {e}")

# Test 6: HybridAI initialization
try:
    if Config.has_api_keys():
        ai = HybridAI()
        st.write("✅ HybridAI initialized")
    else:
        st.write("⚠️ No API keys, skipping HybridAI init")
except Exception as e:
    st.error(f"❌ HybridAI initialization failed: {e}")

st.write("✅ All tests completed!") 