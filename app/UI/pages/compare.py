# app/ui/pages/compare.py
"""
Compare page — two providers run in parallel, results shown side by side.

Both providers run in their own background threads simultaneously.
The page polls until both threads are finished, then renders the results
in two columns so the user can compare spans, span counts, and timings.
"""

from __future__ import annotations

import functools
import time

import streamlit as st

from app.pipeline.orchestrator import orchestrator
from app.UI import state
from app.UI.components import model_selector, pdf_uploader, result_viewer

_SLOT_L = "compare_left"
_SLOT_R = "compare_right"


def render() -> None:
    st.title("⚖️ Compare providers")
    st.caption("Run two providers on the same PDF and compare their output side by side.")

    state.init(_SLOT_L)
    state.init(_SLOT_R)

    # ── sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuration")
        file_path = pdf_uploader.render()
        st.divider()

        st.subheader("Provider A")
        provider_l, settings_l = model_selector.render(key_prefix="cmp_l_")
        st.divider()

        st.subheader("Provider B")
        provider_r, settings_r = model_selector.render(key_prefix="cmp_r_")
        st.divider()

        both_idle = not state.is_running(_SLOT_L) and not state.is_running(_SLOT_R)
        ready = file_path is not None and both_idle

        if st.button("▶ Run comparison", disabled=not ready, use_container_width=True, type="primary"):
            # Launch both threads simultaneously
            state.start(
                _SLOT_L,
                functools.partial(orchestrator.run, file_path, provider_l, settings_l),
            )
            state.start(
                _SLOT_R,
                functools.partial(orchestrator.run, file_path, provider_r, settings_r),
            )
            st.rerun()

        either_finished = state.is_done(_SLOT_L) or state.is_done(_SLOT_R) \
                       or state.is_error(_SLOT_L) or state.is_error(_SLOT_R)
        if either_finished:
            if st.button("↺ Reset", use_container_width=True):
                state.reset(_SLOT_L)
                state.reset(_SLOT_R)
                st.rerun()

    # ── main area ─────────────────────────────────────────────────────────────
    state_l = state.get_state(_SLOT_L)
    state_r = state.get_state(_SLOT_R)

    if state_l == "idle" and state_r == "idle":
        if file_path is None:
            st.info("Upload a PDF in the sidebar to get started.")
        else:
            st.info("PDF loaded. Configure both providers and press **Run comparison**.")
        return

    # Poll while either thread is still running
    if state.is_running(_SLOT_L) or state.is_running(_SLOT_R):
        _render_running(provider_l, provider_r)
        _poll_both()   # blocks 0.4 s then reruns
        return

    # Both finished — render side by side
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader(f"Provider A — {provider_l.title()}")
        _render_slot(_SLOT_L, provider_l)

    with col_r:
        st.subheader(f"Provider B — {provider_r.title()}")
        _render_slot(_SLOT_R, provider_r)

    # Diff summary below the columns
    if state.is_done(_SLOT_L) and state.is_done(_SLOT_R):
        _render_diff_summary(provider_l, provider_r)


# ── helpers ───────────────────────────────────────────────────────────────────

def _render_running(provider_l: str, provider_r: str) -> None:
    col_l, col_r = st.columns(2)
    state_l = state.get_state(_SLOT_L)
    state_r = state.get_state(_SLOT_R)

    with col_l:
        if state_l == "running":
            st.info(f"⏳ **{provider_l.title()}** running…")
        elif state_l == "done":
            result = state.get_result(_SLOT_L)
            st.success(f"✅ **{provider_l.title()}** done — {result['meta']['span_count']:,} spans")

    with col_r:
        if state_r == "running":
            st.info(f"⏳ **{provider_r.title()}** running…")
        elif state_r == "done":
            result = state.get_result(_SLOT_R)
            st.success(f"✅ **{provider_r.title()}** done — {result['meta']['span_count']:,} spans")


def _render_slot(slot: str, provider_name: str) -> None:
    if state.is_error(slot):
        st.error(f"Failed:\n```\n{state.get_error(slot)}\n```")
        return

    result = state.get_result(slot)
    if result is None:
        return

    timing = result["meta"].get("timing", {})
    c1, c2 = st.columns(2)
    c1.metric("Spans", f"{result['meta']['span_count']:,}")
    c2.metric("Total time", f"{timing.get('total', 0):.2f}s")

    result_viewer.render(result["spans"], provider_name=provider_name)


def _render_diff_summary(provider_l: str, provider_r: str) -> None:
    """Quick numeric diff between both providers."""
    result_l = state.get_result(_SLOT_L)
    result_r = state.get_result(_SLOT_R)

    st.divider()
    st.subheader("📊 Comparison summary")

    spans_l = result_l["meta"]["span_count"]
    spans_r = result_r["meta"]["span_count"]
    time_l  = result_l["meta"]["timing"]["total"]
    time_r  = result_r["meta"]["timing"]["total"]

    cols = st.columns(4)
    cols[0].metric(f"{provider_l.title()} spans",  f"{spans_l:,}")
    cols[1].metric(f"{provider_r.title()} spans",  f"{spans_r:,}",
                   delta=f"{spans_r - spans_l:+,}")
    cols[2].metric(f"{provider_l.title()} time",   f"{time_l:.2f}s")
    cols[3].metric(f"{provider_r.title()} time",   f"{time_r:.2f}s",
                   delta=f"{time_r - time_l:+.2f}s")


def _poll_both(interval: float = 0.4) -> None:
    """Sleep and rerun until both threads are no longer running."""
    time.sleep(interval)
    st.rerun()