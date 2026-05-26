# tests/providers/test_docling_provider.py
from unittest.mock import MagicMock, patch
import pytest
from app.providers.docling_provider import DoclingWrapper

def test_bbox_norm_none_when_no_page_height(sample_pdf):
    """When Docling can't provide page height, bbox_norm must be None not zeros."""
    provider = DoclingWrapper(sample_pdf)
    # Simulate a prov_item with bbox but no page_rect
    bbox_norm, bbox_raw = provider._extract_bbox(
        prov_item=MagicMock(bbox=MagicMock(l=10, b=20, r=100, t=80), spec=["bbox"]),
        ph=None,
    )
    assert bbox_norm is None
    assert bbox_raw is not None

def test_configurable_device(sample_pdf):
    from docling.datamodel.accelerator_options import AcceleratorDevice
    p = DoclingWrapper(sample_pdf, device="cuda")
    assert p._device == AcceleratorDevice.CUDA

@pytest.mark.slow
def test_iter_spans_schema(docling_provider):
    with patch.object(DoclingWrapper, "_build_converter") as mock_conv:
        # Return a minimal mock document
        mock_doc = MagicMock()
        mock_doc.texts = []
        mock_conv.return_value.convert.return_value.document = mock_doc
        spans = list(docling_provider.iter_spans())
    assert spans == []   # empty doc → empty spans, no crash