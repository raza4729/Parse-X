# app/ui/app.py
"""
Streamlit entrypoint.

Run with:
    streamlit run app/ui/app.py

Routing is handled by st.navigation — each page is a thin module with a
single render() function.  No logic lives here.
"""

import streamlit as st
from app.UI.pages import extract, compare
import warnings

# suppress warnings from docling, which are noisy and not actionable for users
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

st.set_page_config(
    page_title="PDF Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Extract":  extract.render,
    "Compare":  compare.render,
}

with st.sidebar:
    st.title("📄 PDF Extractor")
    st.divider()
    selection = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed")
    st.divider()

pages[selection]()