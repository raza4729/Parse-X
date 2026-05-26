# tests/providers/test_fitz_provider.py

def test_iter_spans_returns_spans(fitz_provider):
    with fitz_provider as p:
        spans = list(p.iter_spans())
    assert len(spans) > 0

def test_span_schema(fitz_provider):
    with fitz_provider as p:
        span = next(iter(p.iter_spans()))
    required = {"provider", "text", "page", "bbox_norm", "page_size", "conf"}
    assert required.issubset(span.keys())
    assert span["provider"] == "fitz"
    assert isinstance(span["text"], str) and span["text"]
    assert span["bbox_norm"] is not None   # Fitz always has coords

def test_no_empty_spans(fitz_provider):
    with fitz_provider as p:
        texts = [s["text"] for s in p.iter_spans()]
    assert all(t.strip() for t in texts)

def test_preceding_lb_resets_per_page(fitz_provider):
    with fitz_provider as p:
        spans = list(p.iter_spans())
    page_firsts = {}
    for s in spans:
        page_firsts.setdefault(s["page"], s)
    # First span of page 2+ should never carry lb from prior page
    for page, span in page_firsts.items():
        if page > 1:
            assert span["preceding_line_breaks"] == 0