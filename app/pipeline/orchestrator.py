# app/pipeline/orchestrator.py
"""
Extraction orchestrator.

Responsibilities
----------------
1. Accept a file path, provider name, and optional provider settings.
2. Instantiate the correct provider via the registry (settings forwarded
   as kwargs to the provider constructor).
3. Run the provider inside a context manager (guarantees resource cleanup).
4. Pass the raw spans through each pipeline stage in order.
5. Return the merged result dict.

The orchestrator knows nothing about Fitz, Docling, or Streamlit.
It is safe to call from a background thread.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import structlog

from app.providers.registry import registry
from app.pipeline.stages import normalize, enrich, profile, merge

log = structlog.get_logger()


class Orchestrator:

    def run(
        self,
        file_path: str,
        provider_name: str,
        settings: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Run the full extraction pipeline and return a result dict.

        Parameters
        ----------
        file_path:
            Absolute path to the PDF on disk.
        provider_name:
            Registry key (e.g. ``"fitz"``, ``"docling"``).
        settings:
            Provider constructor kwargs forwarded verbatim
            (e.g. ``{"device": "cuda", "do_ocr": True}``).
            ``None`` is equivalent to ``{}``.

        Returns
        -------
        Dict with keys:
            ``spans``   – list of normalised span dicts (post all stages)
            ``profile`` – document profile report
            ``meta``    – timing and provider info
        """
        settings = settings or {}
        log.info("orchestrator.start", provider=provider_name, file=file_path, settings=settings)

        # ── 1. parse ──────────────────────────────────────────────────────────
        provider_cls = registry.get(provider_name)
        spans, t_parse = self._timed_parse(provider_cls, file_path, settings)
        log.debug("stage.parse", span_count=len(spans), elapsed=t_parse)

        # ── 2. normalize ──────────────────────────────────────────────────────
        spans, t_norm = self._timed(normalize.run, spans)
        log.debug("stage.normalize", span_count=len(spans), elapsed=t_norm)

        # ── 3. enrich (SpaCy NLP) ─────────────────────────────────────────────
        spans, t_enrich = self._timed(enrich.run, spans)
        log.debug("stage.enrich", elapsed=t_enrich)

        # ── 4. profile ────────────────────────────────────────────────────────
        report, t_profile = self._timed(profile.run, spans)
        log.debug("stage.profile", elapsed=t_profile)

        # ── 5. merge ──────────────────────────────────────────────────────────
        result, t_merge = self._timed(merge.run, spans, report)
        log.debug("stage.merge", elapsed=t_merge)

        meta = {
            "provider":    provider_name,
            "settings":    settings,
            "file":        file_path,
            "span_count":  len(spans),
            "timing": {
                "parse":     t_parse,
                "normalize": t_norm,
                "enrich":    t_enrich,
                "profile":   t_profile,
                "merge":     t_merge,
                "total":     round(t_parse + t_norm + t_enrich + t_profile + t_merge, 3),
            },
        }
        log.info("orchestrator.complete", **meta["timing"])

        return {"spans": spans, "profile": report, "meta": meta}

    # ── private helpers ───────────────────────────────────────────────────────

    def _timed_parse(
        self,
        provider_cls: type,
        file_path: str,
        settings: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], float]:
        """Instantiate provider, run iter_spans, close, return (spans, elapsed)."""
        t0 = time.perf_counter()
        with provider_cls(file_path, **settings) as provider:
            spans = list(provider.iter_spans())
        return spans, round(time.perf_counter() - t0, 3)

    @staticmethod
    def _timed(fn, *args) -> tuple[Any, float]:
        t0 = time.perf_counter()
        result = fn(*args)
        return result, round(time.perf_counter() - t0, 3)


# Module-level singleton — import this everywhere
orchestrator = Orchestrator()