# providers/docling_provider.py

from typing import Any, Dict, Iterable, Optional, Tuple

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from app.providers.base import TextProvider


class DoclingWrapper(TextProvider):
    """
    IBM Docling text-extraction provider.

    Docling runs a full document-understanding pipeline (layout analysis,
    optional OCR, optional table structure) and exposes rich semantic metadata
    (heading level, content layer, list markers) that Fitz does not provide.

    Configuration
    -------------
    All options are ``__init__`` parameters with sensible defaults.  Pass
    them from the provider registry or the Streamlit UI; never hard-code them
    at the class level so that different jobs can use different settings
    without subclassing.

        provider = DoclingWrapper(path, device="cuda", do_ocr=True)

    Coordinate convention
    ---------------------
    Docling reports bboxes as (l, b, r, t) in a bottom-left origin system.
    ``_bbox_xyxy_from_lbrt_top_left`` flips the y-axis so the emitted
    ``bbox_norm`` matches Fitz's top-left convention.

    When the page height is unavailable the normalised bbox is set to
    ``None`` (not zeroed) so downstream stages can detect and handle missing
    coordinates explicitly.
    """

    provider_name = "docling"

    _DEVICE_MAP = {
        "cpu":  AcceleratorDevice.CPU,
        "cuda": AcceleratorDevice.CUDA,
        "mps":  AcceleratorDevice.MPS,
        "auto": AcceleratorDevice.AUTO,
    }

    def __init__(
        self,
        file_path: str,
        *,
        device: str = "cpu",
        threads: int = 8,
        do_ocr: bool = False,
        do_tables: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        file_path:  Path to the PDF file.
        device:     Accelerator — ``"cpu"``, ``"cuda"``, ``"mps"``, ``"auto"``.
        threads:    Number of CPU threads for the accelerator.
        do_ocr:     Enable OCR for scanned / image-based pages.
        do_tables:  Enable table-structure recognition.
        """
        super().__init__(file_path)
        self._device  = self._DEVICE_MAP.get(device, AcceleratorDevice.CPU)
        self._threads = threads
        self._do_ocr  = do_ocr
        self._do_tables = do_tables

    # extraction 
    def iter_spans(self) -> Iterable[Dict[str, Any]]:
        """
        Yield one span per Docling text item.

        Docling builds its document model upfront (unlike Fitz which streams
        page-by-page), so there is no incremental open/close lifecycle to
        manage — no ``close()`` override is needed.
        """
        converter = self._build_converter()
        doc = converter.convert(self.file_path).document

        # Cache page sizes as we encounter them; used for y-flip and page_size field.
        page_sizes: Dict[int, Tuple[float, float]] = {}

        for idx, item in enumerate(getattr(doc, "texts", [])):
            txt = self._norm_text(getattr(item, "text", ""))
            if not txt:
                continue

            prov_item = (item.prov[0] if getattr(item, "prov", None) else None)
            page_no:   Optional[int]   = getattr(prov_item, "page_no", None)

            # page size
            pw, ph = self._extract_page_size(prov_item, page_no, page_sizes)

            # bbox
            bbox_norm, bbox_raw = self._extract_bbox(prov_item, ph)

            # semantic metadata 
            level         = int(getattr(item, "level", 0))
            self_ref      = getattr(item, "self_ref", None)
            label         = str(getattr(item, "label", ""))         or None
            content_layer = str(getattr(item, "content_layer", "")) or None
            marker        = getattr(item, "marker", "") or ""
            enumerated    = bool(getattr(item, "enumerated", False))

            children = [
                getattr(c, "self_ref", None)
                for c in (getattr(item, "children", []) or [])
            ]

            yield self._emit(
                provider=self.provider_name,
                provider_span_id=self._id(
                    self.provider_name, page_no, self_ref or idx
                ),
                text=txt,
                page=int(page_no) if page_no is not None else None,
                bbox_norm=bbox_norm,
                bbox_raw=bbox_raw,
                page_size=(pw, ph),
                # Docling may expose a per-item probability; fall back to 0.5.
                conf=float(getattr(item, "prob", 0.5)),
                preceding_line_breaks=0,    # Docling works at item level, not raw spans
                level=level,
                label=label,
                enumerated=enumerated,
                marker=marker,
                content_layer=content_layer,
                extra={
                    "original_text": getattr(item, "orig", ""),
                    "children":      children,
                },
            )

    # private helpers 
    def _build_converter(self) -> DocumentConverter:
        accel = AcceleratorOptions(
            num_threads=self._threads,
            device=self._device,
        )
        pipe = PdfPipelineOptions()
        pipe.accelerator_options          = accel
        pipe.do_ocr                       = self._do_ocr
        pipe.do_table_structure           = self._do_tables
        pipe.table_structure_options.do_cell_matching = False
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipe)}
        )

    def _extract_page_size(
        self,
        prov_item: Any,
        page_no: Optional[Any],
        page_sizes: Dict[int, Tuple[float, float]],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Read and cache page dimensions from the provenance item."""
        if prov_item is not None and page_no is not None:
            page_rect = getattr(prov_item, "page_rect", None)
            pw = getattr(page_rect, "width",  None)
            ph = getattr(page_rect, "height", None)
            if pw is not None and ph is not None:
                page_sizes[int(page_no)] = (float(pw), float(ph))

        key = int(page_no) if page_no is not None else -1
        return page_sizes.get(key, (None, None))

    def _extract_bbox(
        self,
        prov_item: Any,
        ph: Optional[float],
    ) -> Tuple[Optional[Tuple[float, float, float, float]],
               Optional[Tuple[float, float, float, float]]]:
        """
        Return ``(bbox_norm, bbox_raw)``.

        ``bbox_norm`` is in top-left (x0, y0, x1, y1) convention.
        ``bbox_raw``  is Docling's native (l, b, r, t) bottom-left convention.

        Both are ``None`` when the provenance or page height are absent.
        ``bbox_norm`` is explicitly ``None`` (not zeroed) when the y-flip
        cannot be performed, so downstream stages can detect missing data.
        """
        if prov_item is None or not hasattr(prov_item, "bbox"):
            return None, None

        raw_bbox = prov_item.bbox
        l = float(getattr(raw_bbox, "l", 0.0))
        b = float(getattr(raw_bbox, "b", 0.0))
        r = float(getattr(raw_bbox, "r", 0.0))
        t = float(getattr(raw_bbox, "t", 0.0))
        bbox_raw = (round(l, 2), round(b, 2), round(r, 2), round(t, 2))

        if ph is None:
            # Cannot flip coordinates without page height - return raw only.
            return None, bbox_raw

        bbox_norm = self._bbox_xyxy_from_lbrt_top_left(l, b, r, t, ph)
        return bbox_norm, bbox_raw