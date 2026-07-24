"""Gate G2: every resolved preset in the vertical slice validates against the
species-preset schema and the biomechanical/provenance sanity checks."""
import pytest
from biogen.taxon_profile import load_profile
from biogen.validate import validate_taxon, audit_evidence_ledger


def _slice():
    return load_profile().vertical_slice


@pytest.mark.parametrize("taxon_id", _slice())
def test_preset_validates(taxon_id):
    result = validate_taxon(taxon_id)
    assert result["ok"], result["errors"]


def test_evidence_ledger_integrity():
    audit = audit_evidence_ledger()
    assert audit["problems"] == [], audit["problems"]
    # all four evidence classes should be represented (규칙 2)
    assert set(audit["counts"]) == {"Measured", "Derived", "Inferred", "ArtistAuthored"}


def test_inferred_values_have_low_confidence():
    """Data-poor anglerfish inferences must not masquerade as measured (규칙 3)."""
    import csv
    from biogen import paths
    with open(paths.EVIDENCE / "evidence_ledger.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    inferred = [r for r in rows if r["evidence_class"] == "Inferred"]
    assert inferred, "expected some Inferred rows"
    assert all(float(r["confidence"]) < 0.7 for r in inferred)
