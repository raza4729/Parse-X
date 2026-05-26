# app/ui/components/model_selector.py
"""
Provider selector and per-provider settings panel.

The dropdown is fed by ``registry.available()`` so the UI never hard-codes
model names.  Settings are only shown for providers that support them — Fitz
has no configurable options, Docling has several.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from app.providers.registry import registry


# Settings that each provider exposes in the UI.
# Add an entry here when registering a new provider.
_PROVIDER_SETTINGS: Dict[str, list] = {
    "fitz":    [],   # no configurable options
    "docling": ["device", "threads", "do_ocr", "do_tables"],
    "xyz":     [],   # extend as needed
}

_DEVICE_OPTIONS = ["cpu", "cuda", "mps", "auto"]


def render(key_prefix: str = "") -> tuple[str, Dict[str, Any]]:
    """
    Render a provider dropdown and (if applicable) a settings expander.

    Parameters
    ----------
    key_prefix:
        Unique prefix for Streamlit widget keys.  Pass different prefixes on
        the compare page so two selectors coexist without key collisions.

    Returns
    -------
    provider_name:
        The selected provider string (e.g. ``"docling"``).
    settings:
        Dict of provider kwargs to forward to the constructor
        (e.g. ``{"device": "cuda", "do_ocr": True}``).
    """
    available = registry.available()

    provider_name: str = st.selectbox(
        "Extraction provider",
        options=available,
        key=f"{key_prefix}provider_select",
    )

    settings: Dict[str, Any] = {}
    supported = _PROVIDER_SETTINGS.get(provider_name, [])

    if supported:
        with st.expander("⚙️ Provider settings", expanded=False):
            if "device" in supported:
                settings["device"] = st.selectbox(
                    "Accelerator device",
                    options=_DEVICE_OPTIONS,
                    index=0,
                    key=f"{key_prefix}device",
                    help="'auto' lets Docling pick the best available device.",
                )
            if "threads" in supported:
                settings["threads"] = st.slider(
                    "CPU threads",
                    min_value=1,
                    max_value=16,
                    value=8,
                    key=f"{key_prefix}threads",
                )
            if "do_ocr" in supported:
                settings["do_ocr"] = st.toggle(
                    "Enable OCR",
                    value=False,
                    key=f"{key_prefix}do_ocr",
                    help="Enable for scanned or image-based PDFs.  Slower.",
                )
            if "do_tables" in supported:
                settings["do_tables"] = st.toggle(
                    "Enable table extraction",
                    value=False,
                    key=f"{key_prefix}do_tables",
                )
    else:
        st.caption(f"_{provider_name} has no configurable settings._")

    return provider_name, settings