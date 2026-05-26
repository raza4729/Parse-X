# app/ui/components/result_viewer.py
"""
Extraction result viewer.

Renders the span table and provides JSON / CSV download buttons.
Designed to be called with the raw list of span dicts returned by the
orchestrator so it stays decoupled from any specific provider.
"""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st


# Columns shown in the span table (subset of full schema — keep it readable).
_TABLE_COLUMNS = [
    "page",
    "text",
    "conf",
    "label",
    "level",
    "bbox_norm",
    "provider",
    "provider_span_id",
]


def render(spans: List[Dict[str, Any]], provider_name: str = "") -> None:
    """
    Render the full result section for a completed extraction.

    Parameters
    ----------
    spans:
        List of span dicts produced by the orchestrator.
    provider_name:
        Used as a label and in default download filenames.
    """
    if not spans:
        st.warning("Extraction returned no spans.")
        return

    st.success(f"✅ {len(spans):,} spans extracted")

    # ── span table ────────────────────────────────────────────────────────────
    with st.expander("📋 Span table", expanded=True):
        df = _to_dataframe(spans)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "conf":     st.column_config.NumberColumn("Conf", format="%.2f"),
                "bbox_norm":st.column_config.TextColumn("BBox (x0,y0,x1,y1)"),
                "text":     st.column_config.TextColumn("Text", width="large"),
            },
        )

    # ── downloads ─────────────────────────────────────────────────────────────
    st.markdown("**Download results**")
    col_json, col_csv = st.columns(2)

    with col_json:
        st.download_button(
            label="⬇️ JSON",
            data=_to_json(spans),
            file_name=f"{provider_name}_spans.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_csv:
        st.download_button(
            label="⬇️ CSV",
            data=_to_csv(df),
            file_name=f"{provider_name}_spans.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ── private helpers ───────────────────────────────────────────────────────────

def _to_dataframe(spans: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for s in spans:
        row = {col: s.get(col) for col in _TABLE_COLUMNS}
        # Stringify bbox tuple for readable display
        bn = row.get("bbox_norm")
        row["bbox_norm"] = (
            f"({bn[0]:.1f}, {bn[1]:.1f}, {bn[2]:.1f}, {bn[3]:.1f})"
            if bn else "—"
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=_TABLE_COLUMNS)


def _to_json(spans: List[Dict[str, Any]]) -> str:
    # bbox tuples aren't JSON serialisable by default
    return json.dumps(spans, default=str, indent=2)


def _to_csv(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()