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


def test_required_ledger_fields_are_never_blank():
    """규칙 4: every parameter must state sample size, season, size, context…
    A blank is an unanswered question, not an answer."""
    import csv
    from biogen import paths
    from biogen.validate import REQUIRED_FIELDS
    with open(paths.EVIDENCE / "evidence_ledger.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    blanks = [f"{r['parameter_id']}.{f}" for r in rows for f in REQUIRED_FIELDS
              if not (r.get(f) or "").strip()]
    assert blanks == [], blanks


def test_sample_size_is_a_count_or_an_explicit_non_count():
    """We never invent N. Anything that is not a digit must name the kind of
    un-counted evidence, so 'unknown' can't hide as an empty cell."""
    import csv
    from biogen import paths
    from biogen.validate import SAMPLE_SIZE_VOCAB
    with open(paths.EVIDENCE / "evidence_ledger.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    bad = [(r["parameter_id"], r["sample_size"]) for r in rows
           if not (r["sample_size"].isdigit() or r["sample_size"] in SAMPLE_SIZE_VOCAB)]
    assert bad == [], bad


def test_derived_values_carry_a_formula():
    """A Derived value with no formula is really an Inferred estimate
    mislabelled — the distinction is the whole point of the class."""
    import csv
    from biogen import paths
    with open(paths.EVIDENCE / "evidence_ledger.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    bad = [r["parameter_id"] for r in rows
           if r["evidence_class"] == "Derived"
           and not (r["derivation_formula"] or "").strip()]
    assert bad == [], bad


def test_numeric_parameters_record_a_range():
    """규칙 6: a scalar with no min/max hides its spread. Categorical values
    must NOT carry a numeric range."""
    import csv
    from biogen import paths
    from biogen.validate import CATEGORICAL_UNITS
    with open(paths.EVIDENCE / "evidence_ledger.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    missing = [r["parameter_id"] for r in rows if r["unit"] not in CATEGORICAL_UNITS
               and not (r["min_value"].strip() and r["max_value"].strip())]
    bogus = [r["parameter_id"] for r in rows if r["unit"] in CATEGORICAL_UNITS
             and (r["min_value"].strip() or r["max_value"].strip())]
    assert missing == [], f"numeric without range: {missing}"
    assert bogus == [], f"categorical with range: {bogus}"


def test_inferred_values_have_low_confidence():
    """Data-poor anglerfish inferences must not masquerade as measured (규칙 3)."""
    import csv
    from biogen import paths
    with open(paths.EVIDENCE / "evidence_ledger.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    inferred = [r for r in rows if r["evidence_class"] == "Inferred"]
    assert inferred, "expected some Inferred rows"
    assert all(float(r["confidence"]) < 0.7 for r in inferred)
