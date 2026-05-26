# app/ui/state.py
"""
Session-state helpers for background extraction jobs.

WHY THE CONTAINER PATTERN
--------------------------
Streamlit's ``st.session_state[key] = value`` requires the main thread's
ScriptRunContext.  Background threads don't have it, so those writes are
silently dropped — the UI never sees the state transition and polls forever.

The fix: store a plain mutable dict in session state ONCE (on the main
thread), then let the background thread mutate that dict IN PLACE.  Mutating
an existing Python object bypasses Streamlit's API entirely, so it always
works from any thread.

    ✗  st.session_state["job_state"] = "done"   # dropped in background thread
    ✓  container["state"] = "done"               # plain dict mutation, always works

Job state machine
-----------------
    idle  ──►  running  ──►  done
                   │
                   └─────────►  error
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

import streamlit as st


def _container(slot: str) -> dict:
    """Return (and lazily create) the mutable job container for ``slot``."""
    if slot not in st.session_state:
        st.session_state[slot] = {
            "state":  "idle",
            "result": None,
            "error":  None,
            "thread": None,
        }
    return st.session_state[slot]  # type: ignore[return-value]


# ── public API ────────────────────────────────────────────────────────────────

def init(slot: str) -> None:
    """Initialise the job container for ``slot`` (idempotent)."""
    _container(slot)


def start(slot: str, fn: Callable[[], Any]) -> None:
    """
    Launch ``fn`` in a daemon thread and transition the slot to *running*.

    ``fn`` must be zero-argument — use ``functools.partial`` or a lambda to
    bind arguments before passing in.
    """
    c = _container(slot)
    # Reset on the main thread (safe)
    c["state"]  = "running"
    c["result"] = None
    c["error"]  = None

    def _run() -> None:
        # Mutate the dict in-place — no Streamlit API calls, always works.
        try:
            c["result"] = fn()
            c["state"]  = "done"
        except Exception as exc:  # noqa: BLE001
            c["error"] = str(exc)
            c["state"] = "error"

    thread = threading.Thread(target=_run, daemon=True)
    c["thread"] = thread
    thread.start()


def poll(slot: str, interval: float = 0.4) -> None:
    """
    If the job is still running, sleep briefly then trigger a rerun.

    The main thread reads ``container["state"]`` directly — no Streamlit API
    involved — so it always sees the latest value written by the worker thread.
    """
    if get_state(slot) == "running":
        time.sleep(interval)
        st.rerun()


def reset(slot: str) -> None:
    """Return a slot to *idle*, clearing result and error."""
    c = _container(slot)
    c["state"]  = "idle"
    c["result"] = None
    c["error"]  = None
    c["thread"] = None


# ── read helpers ──────────────────────────────────────────────────────────────

def get_state(slot: str) -> str:
    return _container(slot)["state"]


def get_result(slot: str) -> Optional[Any]:
    return _container(slot)["result"]


def get_error(slot: str) -> Optional[str]:
    return _container(slot)["error"]


def is_running(slot: str) -> bool:
    return get_state(slot) == "running"


def is_done(slot: str) -> bool:
    return get_state(slot) == "done"


def is_error(slot: str) -> bool:
    return get_state(slot) == "error"