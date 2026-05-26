# config.py
from dataclasses import dataclass, field
from typing import List, Set

@dataclass
class Thresholds:
    header_band_first_page: int = 100
    header_band: int = 55
    footer_band: int = 50
    top_k_sizes: int = 4
    heading_score_default: float = 0.55
    # Normalizer tuning:
    y_tol_factor: float = 0.5
    y_tol_min: float = 2.0
    default_font_size: float = 10.0
    hyphen_glue_ratio: float = 0.8
    space_gap_ratio: float = 0.4
    font_size_round: int = 2       # decimals to round sizes
    size_match_tol: float = 0.01  

@dataclass
class Weights:
    size_rank: float = 0.3
    bold: float = 0.4
    numbering: float = 0.3
    layout: float = 0.05

@dataclass
class RegexConfig:
    require_capital_title: bool = False
    # (optional) roman max length etc. can go here later
    allow_empty_title: bool = True
    roman_case_sensitive: bool = True

@dataclass
class AppConfig:
    thresholds: Thresholds = field(default_factory=Thresholds)
    weights: Weights = field(default_factory=Weights)
    regex: RegexConfig = field(default_factory=RegexConfig)
    # Bold detection hints:
    bold_keywords: List[str] = field(default_factory=lambda: ["bold","black","heavy"])
    bold_hint_fonts: Set[str] = field(default_factory=lambda: {"cidfont+f2"})
