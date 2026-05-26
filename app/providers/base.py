# providers/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Tuple


class TextProvider(ABC):
    """
    Abstract base for every PDF text-extraction provider.

    Contract
    --------
    - Subclasses receive ``file_path`` via ``__init__`` and store it on
      ``self.file_path``.
    - ``iter_spans`` must yield dicts produced by ``_emit``.  Every key
      emitted here is part of the public schema consumed by the pipeline.
    - Providers that hold an open file handle must override ``close()``.
      The base ``__enter__`` / ``__exit__`` will call it automatically, so
      callers can always use ``with provider:`` regardless of provider type.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    # context manager (override close() if you hold a resource)

    def __enter__(self) -> "TextProvider":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Release any held resource.  No-op by default."""

    # public interface
    @abstractmethod
    def iter_spans(self) -> Iterable[Dict[str, Any]]:
        """
        Yield one normalised span dict per text span found in the PDF.

        Every span dict must be produced via ``self._emit(...)`` so the
        schema stays consistent across providers.
        """

    # shared helpers (concrete, available to every subclass)
    def _emit(
        self,
        *,
        provider: str,
        provider_span_id: str,
        text: str,
        page: Optional[int],
        bbox_norm: Optional[Tuple[float, float, float, float]],
        page_size: Tuple[Optional[float], Optional[float]],
        conf: float,
        preceding_line_breaks: int = 0,
        level: Optional[int] = None,
        label: Optional[str] = None,
        enumerated: bool = False,
        marker: str = "",
        content_layer: Optional[str] = None,
        bbox_raw: Optional[Tuple[float, float, float, float]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build a span dict with a fixed schema.

        Using keyword-only arguments makes call sites self-documenting and
        prevents positional-order mistakes when new fields are added.

        ``bbox_norm``  – (x0, y0, x1, y1) in top-left coordinates, normalised
                         to page points.  ``None`` when coordinates are
                         genuinely unavailable; downstream stages must handle
                         this explicitly rather than receiving silent zeros.
        ``bbox_raw``   – provider-native coordinates (e.g. Docling's l/b/r/t),
                         preserved for debugging.  ``None`` when not applicable.
        ``conf``       – extraction confidence in [0, 1].
        ``extra``      – provider-specific fields (font name, flags, children…).
        """
        return {
            "provider":              provider,
            "provider_span_id":      provider_span_id,
            "text":                  text,
            "page":                  page,
            "bbox_norm":             bbox_norm,
            "bbox_raw":              bbox_raw,
            "page_size":             page_size,
            "conf":                  conf,
            "preceding_line_breaks": preceding_line_breaks,
            "level":                 level,
            "label":                 label,
            "enumerated":            enumerated,
            "marker":                marker,
            "content_layer":         content_layer,
            "extra":                 extra or {},
        }

    def _norm_text(self, text: Optional[str]) -> str:
        """Strip and return text; return empty string for None / whitespace."""
        return (text or "").strip()

    def _id(self, *parts: Any) -> str:
        """Build a colon-separated span ID from arbitrary parts."""
        return ":".join(str(p) for p in parts)

    def _bbox_xyxy_from_lbrt_top_left(
        self,
        l: float,
        b: float,
        r: float,
        t: float,
        page_height: float,
    ) -> Tuple[float, float, float, float]:
        """
        Convert Docling's bottom-left (l, b, r, t) bbox to top-left (x0, y0, x1, y1).

        Docling reports coordinates in a bottom-left origin system.
        PyMuPDF (Fitz) uses top-left origin.  This helper flips the y-axis so
        all providers emit coordinates in the same convention.

            y_top_left = page_height - y_bottom_left
        """
        x0 = l
        y0 = page_height - t   # top edge in top-left coords
        x1 = r
        y1 = page_height - b   # bottom edge in top-left coords
        return x0, y0, x1, y1