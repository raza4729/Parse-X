# config_loader.py
import json
from app.config.config import AppConfig, Thresholds, Weights, RegexConfig

def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return AppConfig(
        thresholds=Thresholds(**d.get("thresholds", {})),
        weights=Weights(**d.get("weights", {})),
        regex=RegexConfig(**d.get("regex", {})),
        bold_keywords=d.get("bold_keywords", ["bold","black","heavy"]),
        bold_hint_fonts=set(d.get("bold_hint_fonts", ["cidfont+f2"]))
    )
