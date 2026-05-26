# app/ui/pages/extract.py
"""
Extract page — single-provider extraction.

Flow
----
idle:    user uploads PDF, selects provider, configures settings, clicks Run
running: background thread executes orchestrator.run(); UI polls every 0.4 s
done:    results rendered via result_viewer
error:   error message shown with option to retry
"""

from __future__ import annotations

import functools

import streamlit as st

from app.pipeline.orchestrator import orchestrator
from app.UI import state
from app.UI.components import model_selector, pdf_uploader, result_viewer

_SLOT = "extract"


def render() -> None:
    st.title("📄 Extract")
    st.caption("Upload a PDF, choose a provider, and extract text spans.")

    state.init(_SLOT)

    # ── sidebar: upload + provider config ─────────────────────────────────────
    with st.sidebar:
        st.header("Configuration")
        file_path = pdf_uploader.render()
        st.divider()
        provider_name, settings = model_selector.render(key_prefix="extract_")
        st.divider()

        ready = file_path is not None and not state.is_running(_SLOT)
        if st.button("▶ Run extraction", disabled=not ready, width='stretch', type="primary"):
            state.start(
                _SLOT,
                functools.partial(
                    orchestrator.run,
                    file_path,
                    provider_name,
                    settings,
                ),
            )
            st.rerun()

        if state.is_done(_SLOT) or state.is_error(_SLOT):
            if st.button("↺ Reset", width='stretch'): # for False use 'content'
                state.reset(_SLOT)
                st.rerun()

    # ── main area: status + results ───────────────────────────────────────────
    job_state = state.get_state(_SLOT)

    if job_state == "idle":
        if file_path is None:
            st.info("Upload a PDF in the sidebar to get started.")
        else:
            st.info("PDF loaded. Press **Run extraction** in the sidebar.")

    elif job_state == "running":
        with st.spinner(f"Running **{provider_name}** extraction…"):
            _show_timing_placeholder()
            state.poll(_SLOT)   # sleeps 0.4 s then triggers st.rerun()

    elif job_state == "done":
        result = state.get_result(_SLOT)
        _show_meta(result["meta"])
        result_viewer.render(result["spans"], provider_name=provider_name)

    elif job_state == "error":
        st.error(f"Extraction failed:\n\n```\n{state.get_error(_SLOT)}\n```")
        st.info("Check the logs for a full traceback, then press **Reset** to try again.")


# ── helpers ───────────────────────────────────────────────────────────────────
def _show_timing_placeholder() -> None:
    st.caption("Extraction is running in the background. The page refreshes automatically.")


def _show_meta(meta: dict) -> None:
    timing = meta.get("timing", {})
    cols = st.columns(4)
    cols[0].metric("Spans",    f"{meta.get('span_count', 0):,}")
    cols[1].metric("Provider", meta.get("provider", "—").title())
    cols[2].metric("Parse",    f"{timing.get('parse', 0):.2f}s")
    cols[3].metric("Total",    f"{timing.get('total', 0):.2f}s")
    st.divider()