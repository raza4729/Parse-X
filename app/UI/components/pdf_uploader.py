# app/ui/components/pdf_uploader.py
"""
PDF upload component.

Handles the Streamlit file-uploader widget and persists the uploaded bytes
to a temporary file on disk so providers (which need a real path) can open it.

The temp file is stored in session state and recreated on each upload so
Streamlit's rerun cycle doesn't lose it between interactions.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import streamlit as st


_SS_KEY = "_pdf_tmp_path"


def render() -> Optional[str]:
    """
    Render the file uploader and return the path to the uploaded PDF,
    or ``None`` if nothing has been uploaded yet.

    The returned path points to a temp file that lives for the duration of
    the session.  Do not delete it manually — it will be cleaned up when
    the OS reclaims the temp directory.
    """
    uploaded = st.file_uploader(
        "Upload a PDF",
        type=["pdf"],
        help="The file is stored in a temporary location; it is not persisted.",
    )

    if uploaded is None:
        # Clear stale temp path when the user removes the file
        st.session_state.pop(_SS_KEY, None)
        return None

    # Re-write only when a new file is uploaded (avoid re-writing on every rerun)
    current_path: Optional[str] = st.session_state.get(_SS_KEY)
    if current_path is None or Path(current_path).stat().st_size != uploaded.size:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        ) as tmp:
            tmp.write(uploaded.getbuffer())
            st.session_state[_SS_KEY] = tmp.name

    path = st.session_state[_SS_KEY]
    st.caption(f"📄 **{uploaded.name}** — {uploaded.size / 1024:.1f} KB")
    return path