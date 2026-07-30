"""ETL / taxonomic resolution tests.

These run entirely offline against recorded response shapes, so the parsing and
reconciliation logic is genuinely verified even where the network policy blocks
the authorities. The transport itself is exercised separately (and skipped when
egress is unavailable) — a blocked environment must not turn into a silent pass.
"""
import json
import pytest

from biogen import etl
from biogen.etl import Resolution, parse_gbif, parse_worms, reconcile

# --- recorded response shapes (GBIF /species/match, WoRMS AphiaRecordsByName) ---

GBIF_EXACT = {
    "usageKey": 2405149, "scientificName": "Clupea harengus Linnaeus, 1758",
    "canonicalName": "Clupea harengus", "rank": "SPECIES", "status": "ACCEPTED",
    "confidence": 98, "matchType": "EXACT",
    "kingdom": "Animalia", "phylum": "Chordata", "class": "Actinopterygii",
    "order": "Clupeiformes", "family": "Clupeidae", "genus": "Clupea",
    "species": "Clupea harengus",
}
GBIF_FUZZY = dict(GBIF_EXACT, matchType="FUZZY", confidence=82)
GBIF_NONE = {"confidence": 100, "matchType": "NONE", "synonym": False}
GBIF_SYNONYM = dict(GBIF_EXACT, status="SYNONYM", acceptedUsageKey=999,
                    usageKey=111, species="Clupea harengus")

WORMS_ACCEPTED = [{
    "AphiaID": 126417, "scientificname": "Clupea harengus", "status": "accepted",
    "valid_AphiaID": 126417, "valid_name": "Clupea harengus", "rank": "Species",
    "kingdom": "Animalia", "phylum": "Chordata", "class": "Teleostei",
    "order": "Clupeiformes", "family": "Clupeidae", "genus": "Clupea",
}]
WORMS_UNACCEPTED = [{
    "AphiaID": 158711, "scientificname": "Salmo gairdneri", "status": "unaccepted",
    "valid_AphiaID": 127185, "valid_name": "Oncorhynchus mykiss", "rank": "Species",
}]


# ------------------------------ GBIF parsing ------------------------------
def test_gbif_exact_match():
    r = parse_gbif(GBIF_EXACT, "Clupea harengus")
    assert r.status == "matched"
    assert r.accepted_name == "Clupea harengus"
    assert r.identifier == "gbif:2405149"
    assert r.rank == "species"
    assert r.match_confidence == pytest.approx(0.98)
    assert r.classification["family"] == "Clupeidae"


def test_gbif_no_match_is_a_real_answer():
    r = parse_gbif(GBIF_NONE, "Nonexistus fakus")
    assert r.status == "no_match"
    assert r.accepted_name is None


def test_gbif_fuzzy_match_is_flagged():
    """A fuzzy hit must never pass as a clean identification."""
    r = parse_gbif(GBIF_FUZZY, "Clupea harengis")
    assert r.status == "matched"
    assert "fuzzy" in (r.note or "").lower()


def test_gbif_synonym_prefers_accepted_key():
    r = parse_gbif(GBIF_SYNONYM, "Clupea harengus")
    assert r.identifier == "gbif:999"       # acceptedUsageKey wins over usageKey
    assert r.taxonomic_status == "SYNONYM"


def test_gbif_rejects_garbage_payload():
    assert parse_gbif(["not", "a", "dict"], "x").status == "error"


# ------------------------------ WoRMS parsing ------------------------------
def test_worms_accepted_record():
    r = parse_worms(WORMS_ACCEPTED, "Clupea harengus")
    assert r.status == "matched"
    assert r.accepted_name == "Clupea harengus"
    assert r.identifier == "worms:126417"


def test_worms_follows_valid_name_for_unaccepted():
    """A junior synonym must resolve to the accepted name, and say so."""
    r = parse_worms(WORMS_UNACCEPTED, "Salmo gairdneri")
    assert r.status == "matched"
    assert r.accepted_name == "Oncorhynchus mykiss"
    assert r.identifier == "worms:127185"
    assert "valid_name" in (r.note or "")


def test_worms_empty_list_is_no_match():
    assert parse_worms([], "x").status == "no_match"
    assert parse_worms(None, "x").status == "no_match"


# ---------------------------- reconciliation ----------------------------
def _res(source, name, status="matched", ident=None):
    return Resolution(source_id=source, query=name, status=status,
                      accepted_name=name if status == "matched" else None,
                      identifier=ident)


def test_reconcile_agreement():
    v = reconcile("Clupea harengus", [
        _res("gbif", "Clupea harengus", ident="gbif:1"),
        _res("worms", "Clupea harengus", ident="worms:2")])
    assert v["verdict"] == "agree"
    assert v["requires_review"] is False
    assert v["identifiers"] == ["gbif:1", "worms:2"]


def test_reconcile_disagreement_keeps_both_names():
    """규칙 8: conflicting authorities are surfaced, never silently merged."""
    v = reconcile("Clupea harengus", [
        Resolution("gbif", "Clupea harengus", "matched", accepted_name="Clupea harengus"),
        Resolution("worms", "Clupea harengus", "matched", accepted_name="Clupea pallasii")])
    assert v["verdict"] == "partial_disagreement"
    assert v["requires_review"] is True
    assert v["authority_names"] == ["Clupea harengus", "Clupea pallasii"]


def test_reconcile_total_disagreement():
    v = reconcile("Clupea harengus", [
        Resolution("gbif", "q", "matched", accepted_name="Sardina pilchardus")])
    assert v["verdict"] == "disagreement"
    assert v["requires_review"] is True


def test_reconcile_blocked_network_is_not_a_pass():
    """A blocked run must be distinguishable from a verified one."""
    v = reconcile("Clupea harengus", [
        Resolution("gbif", "q", "unreachable", note="CONNECT 403"),
        Resolution("worms", "q", "unreachable", note="CONNECT 403")])
    assert v["verdict"] == "unresolved_network"
    assert v["authority_names"] == []


def test_reconcile_no_match_requires_review():
    v = reconcile("Clupea harengus", [
        Resolution("gbif", "q", "no_match"), Resolution("worms", "q", "no_match")])
    assert v["verdict"] == "no_authority_match"
    assert v["requires_review"] is True


# ------------------------------ transport ------------------------------
def test_fetch_reports_transport_failure_without_raising(monkeypatch):
    """A proxy denial must come back as a recorded failure, not an exception."""
    def boom(*a, **k):
        raise OSError("CONNECT tunnel failed, response 403")
    monkeypatch.setattr(etl.urllib.request, "urlopen", boom)
    f = etl.fetch("https://api.gbif.org/v1/species/match?name=x", use_cache=False)
    assert f.ok is False
    assert f.status is None
    assert "403" in f.error
    assert f.json() is None


def test_resolve_one_marks_sources_unreachable_when_blocked(monkeypatch):
    monkeypatch.setattr(etl, "fetch", lambda url, use_cache=True: etl.Fetch(
        url=url, status=None, ok=False, error="blocked", retrieved_at="t"))
    out = etl.resolve_one("Clupea harengus")
    assert {r.source_id for r in out} == {"gbif", "worms"}
    assert all(r.status == "unreachable" for r in out)
    assert all(r.accepted_name is None for r in out)


def test_http_404_is_no_match_not_an_outage(monkeypatch):
    """WoRMS answers 404 for unknown names — that is data, not a failure."""
    monkeypatch.setattr(etl, "fetch", lambda url, use_cache=True: etl.Fetch(
        url=url, status=404, ok=False, error="HTTP 404", retrieved_at="t"))
    out = etl.resolve_one("Nonexistus fakus")
    assert all(r.status == "no_match" for r in out)


def test_cache_preserves_original_retrieved_at(tmp_path, monkeypatch):
    """Re-running must not fresh-date provenance it did not actually re-fetch."""
    monkeypatch.setattr(etl, "CACHE_DIR", tmp_path)
    url = "https://example.invalid/x"
    etl._cache_path(url).write_text(json.dumps(
        {"url": url, "status": 200, "retrieved_at": "2020-01-01T00:00:00Z",
         "body": json.dumps(GBIF_EXACT)}), encoding="utf-8")
    f = etl.fetch(url)
    assert f.from_cache is True
    assert f.retrieved_at == "2020-01-01T00:00:00Z"
    assert parse_gbif(f.json(), "Clupea harengus").identifier == "gbif:2405149"
