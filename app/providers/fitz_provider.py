# providers/fitz_provider.py

import fitz  # PyMuPDF
from typing import Any, Dict, Iterable

from app.providers.base import TextProvider


class FitzWrapper(TextProvider):
    """
    PyMuPDF (Fitz) text-extraction provider.

    Yields one span per ``fitz`` span object, preserving font metadata.
    Coordinates are already in top-left origin (PyMuPDF's native system),
    so no axis flip is needed.

    Usage
    -----
        with FitzWrapper(path) as provider:
            for span in provider.iter_spans():
                ...

    The context manager ensures the underlying ``fitz.Document`` is always
    closed, even when iteration is interrupted by an exception.
    """

    provider_name = "fitz"

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        self._doc: fitz.Document | None = None

    # resource management 
    def __enter__(self) -> "FitzWrapper":
        self._doc = fitz.open(self.file_path)
        return self

    def close(self) -> None:
        if self._doc is not None:
            self._doc.close()
            self._doc = None

    # extraction 
    def iter_spans(self) -> Iterable[Dict[str, Any]]:
        """
        Iterate over every text span in the document.

        ``preceding_line_breaks`` counts blank/whitespace-only spans
        encountered since the last yielded span.  The counter resets to 0
        at the start of each page so it never bleeds across page boundaries.
        """
        if self._doc is None:
            # Support calling without the context manager (opens and closes inline).
            with self:
                yield from self.iter_spans()
            return

        for page_num, page in enumerate(self._doc, start=1):
            preceding_lb = 0  # reset per page — never bleed across boundaries

            d = page.get_text("dict") or {}
            pw = float(page.rect.width)
            ph = float(page.rect.height)

            for b_i, block in enumerate(d.get("blocks", []), start=1):
                if block.get("type", 0) != 0:   # 0 = text block; skip images etc.
                    continue

                for l_i, line in enumerate(block.get("lines", []), start=1):
                    for s_i, span in enumerate(line.get("spans", []), start=1):
                        txt = self._norm_text(span.get("text"))

                        if not txt:
                            preceding_lb += 1
                            continue

                        x0, y0, x1, y1 = map(float, span["bbox"])  # top-left origin

                        yield self._emit(
                            provider=self.provider_name,
                            provider_span_id=self._id(
                                self.provider_name, page_num, b_i, l_i, s_i
                            ),
                            text=txt,
                            page=page_num,
                            bbox_norm=(x0, y0, x1, y1),
                            bbox_raw=None,          # coords are already normalised
                            page_size=(pw, ph),
                            conf=0.99,              # Fitz is deterministic; high confidence
                            preceding_line_breaks=preceding_lb,
                            level=None,             # Fitz has no semantic heading level
                            label=None,
                            enumerated=False,
                            marker="",
                            content_layer=None,
                            extra={
                                "font_name":    span.get("font", ""),
                                "font_size":    float(span.get("size") or 0.0),
                                "engine_flags": span.get("flags"),
                                "block_idx":    b_i,
                                "line_idx":     l_i,
                                "span_idx":     s_i,
                            },
                        )
                        preceding_lb = 0