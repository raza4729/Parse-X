# tests/conftest.py

import pytest
from pathlib import Path
from app.providers.fitz_provider import FitzWrapper
from app.providers.docling_provider import DoclingWrapper

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "20250711_ Genehmigungsbescheid E-STATCOM Oberjettingen.pdf"

@pytest.fixture
def sample_pdf(tmp_path):
    # Copy fixture to tmp so tests are isolated
    dest = tmp_path / "sample.pdf"
    dest.write_bytes(SAMPLE_PDF.read_bytes())
    return str(dest)

@pytest.fixture
def fitz_provider(sample_pdf):
    return FitzWrapper(sample_pdf)

@pytest.fixture
def docling_provider(sample_pdf):
    return DoclingWrapper(sample_pdf)