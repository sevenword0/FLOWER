"""Project path resolution. Keeps every module free of hard-coded absolute
paths and free of taxon literals."""
from __future__ import annotations
from pathlib import Path

# src/biogen/paths.py -> project root is two parents up from src/biogen
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG = PROJECT_ROOT / "config"
ADAPTATION_PROFILES = CONFIG / "adaptation_profiles"
SCHEMAS = PROJECT_ROOT / "schemas"
SOURCES = PROJECT_ROOT / "sources"
TAXONOMY = PROJECT_ROOT / "taxonomy"
EVIDENCE = PROJECT_ROOT / "evidence"
ONTOLOGY = PROJECT_ROOT / "ontology"
BASES = PROJECT_ROOT / "bases"
CLADE_BASES = BASES / "clade"
MORPHOTYPE_BASES = BASES / "morphotype"
PRESETS = PROJECT_ROOT / "presets"
EXPORTS = PROJECT_ROOT / "exports"
DOCS = PROJECT_ROOT / "docs"


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
