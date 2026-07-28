"""Live taxonomic resolution against public authority APIs (프롬프트 A01, §6).

Resolves accepted names and stable identifiers from GBIF and WoRMS, caches the
raw responses, and reconciles them against `taxonomy/taxon_index.csv`.

Design rules this module enforces:

* **API over scraping** (규칙 9) — both backends are official REST endpoints.
* **Never invent data.** If the network is unreachable the resolver records
  `status="unreachable"` with the transport error and returns no values. A
  blocked run must be distinguishable from a run that found nothing, and both
  must be distinguishable from a successful one.
* **Conflicts are not silently averaged** (규칙 8, §6). When two authorities
  disagree on the accepted name, both are kept and the disagreement is
  reported for red-team review rather than resolved by fiat.
* **Everything is stamped** with source, endpoint, HTTP status and
  `retrieved_at`, so a resolved name can be traced back to the exact call.

Stdlib only — no new dependency, and `urllib` already honours the proxy
environment, so this works wherever the operator's network policy allows it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import csv
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request

from . import paths

CACHE_DIR = paths.PROJECT_ROOT / ".cache" / "etl"
USER_AGENT = "biogen/0.1 (procedural biology pipeline; taxonomic reconciliation)"
TIMEOUT_S = 20

GBIF_MATCH = "https://api.gbif.org/v1/species/match?name={name}"
WORMS_BY_NAME = ("https://www.marinespecies.org/rest/AphiaRecordsByName/"
                 "{name}?like=false&marine_only=false")

# Recorded in the resolution report so downstream consumers can honour terms.
SOURCE_LICENSE = {"gbif": "CC-BY 4.0", "worms": "CC-BY 4.0"}


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------
def _ssl_context() -> ssl.SSLContext:
    """Trust the operator's CA bundle when one is configured.

    Never disables verification — an un-verifiable endpoint is a failed fetch,
    not an excuse to fall back to plaintext trust.
    """
    bundle = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        return ssl.create_default_context(cafile=bundle)
    return ssl.create_default_context()


@dataclass
class Fetch:
    """One HTTP attempt, successful or not. This is the provenance atom."""
    url: str
    status: Optional[int] = None          # HTTP status, None if no response
    ok: bool = False
    body: Optional[str] = None
    error: Optional[str] = None
    retrieved_at: Optional[str] = None
    from_cache: bool = False

    def json(self) -> Any:
        if not self.ok or self.body is None:
            return None
        try:
            return json.loads(self.body)
        except json.JSONDecodeError as exc:
            self.error = f"invalid JSON: {exc}"
            self.ok = False
            return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _cache_path(url: str):
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")


def fetch(url: str, use_cache: bool = True) -> Fetch:
    """GET a URL, caching successful responses on disk.

    Cached responses keep their original `retrieved_at`, so re-running the
    resolver never back-dates or fresh-dates provenance it did not re-fetch.
    """
    cp = _cache_path(url)
    if use_cache and cp.exists():
        try:
            rec = json.loads(cp.read_text(encoding="utf-8"))
            return Fetch(url=url, status=rec.get("status"), ok=True,
                         body=rec.get("body"), retrieved_at=rec.get("retrieved_at"),
                         from_cache=True)
        except (json.JSONDecodeError, OSError):
            pass  # unreadable cache entry is simply a miss

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S,
                                    context=_ssl_context()) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            f = Fetch(url=url, status=resp.status, ok=200 <= resp.status < 300,
                      body=body, retrieved_at=_now())
    except urllib.error.HTTPError as exc:
        # A 404 is a real answer from the authority: the name is not known.
        return Fetch(url=url, status=exc.code, ok=False,
                     error=f"HTTP {exc.code}", retrieved_at=_now())
    except Exception as exc:  # transport-level: DNS, TLS, proxy denial, timeout
        return Fetch(url=url, status=None, ok=False,
                     error=f"{type(exc).__name__}: {exc}", retrieved_at=_now())

    if f.ok and use_cache:
        paths.ensure_dir(CACHE_DIR)
        cp.write_text(json.dumps({"url": url, "status": f.status,
                                  "retrieved_at": f.retrieved_at, "body": f.body}),
                      encoding="utf-8")
    return f


# --------------------------------------------------------------------------
# response parsing  (pure functions — unit-tested against recorded fixtures)
# --------------------------------------------------------------------------
@dataclass
class Resolution:
    source_id: str
    query: str
    status: str                      # matched | no_match | unreachable | error
    accepted_name: Optional[str] = None
    rank: Optional[str] = None
    identifier: Optional[str] = None
    taxonomic_status: Optional[str] = None
    match_confidence: Optional[float] = None
    classification: Dict[str, str] = field(default_factory=dict)
    endpoint: Optional[str] = None
    http_status: Optional[int] = None
    retrieved_at: Optional[str] = None
    from_cache: bool = False
    note: Optional[str] = None


def parse_gbif(payload: Any, query: str) -> Resolution:
    """GBIF /species/match returns a single best match with a confidence score.

    `matchType == "NONE"` means the backbone has no match — that is a real
    negative answer, not a failure.
    """
    r = Resolution(source_id="gbif", query=query, status="no_match")
    if not isinstance(payload, dict):
        r.status = "error"
        r.note = "unexpected payload shape"
        return r
    if payload.get("matchType") in (None, "NONE"):
        r.note = f"matchType={payload.get('matchType')}"
        return r

    r.status = "matched"
    r.accepted_name = payload.get("species") or payload.get("scientificName")
    r.rank = (payload.get("rank") or "").lower() or None
    key = payload.get("acceptedUsageKey") or payload.get("usageKey")
    r.identifier = f"gbif:{key}" if key else None
    r.taxonomic_status = payload.get("status")
    conf = payload.get("confidence")
    r.match_confidence = float(conf) / 100.0 if isinstance(conf, (int, float)) else None
    r.classification = {k: payload[k] for k in
                        ("kingdom", "phylum", "class", "order", "family", "genus")
                        if payload.get(k)}
    if payload.get("matchType") == "FUZZY":
        r.note = "fuzzy match — verify before use"
    return r


def parse_worms(payload: Any, query: str) -> Resolution:
    """WoRMS returns a list of Aphia records; prefer the accepted one.

    An unaccepted record still carries `valid_name`, which is the accepted
    name we actually want — following it is the documented WoRMS workflow.
    """
    r = Resolution(source_id="worms", query=query, status="no_match")
    if payload in (None, []):
        return r
    if not isinstance(payload, list):
        r.status = "error"
        r.note = "unexpected payload shape"
        return r

    accepted = next((x for x in payload
                     if isinstance(x, dict) and x.get("status") == "accepted"), None)
    rec = accepted or next((x for x in payload if isinstance(x, dict)), None)
    if rec is None:
        return r

    r.status = "matched"
    r.accepted_name = rec.get("valid_name") or rec.get("scientificname")
    r.rank = (rec.get("rank") or "").lower() or None
    aid = rec.get("valid_AphiaID") or rec.get("AphiaID")
    r.identifier = f"worms:{aid}" if aid else None
    r.taxonomic_status = rec.get("status")
    r.classification = {k: rec[k] for k in
                        ("kingdom", "phylum", "class", "order", "family", "genus")
                        if rec.get(k)}
    if accepted is None:
        r.note = f"no accepted record; followed valid_name from status={rec.get('status')}"
    return r


# --------------------------------------------------------------------------
# resolver
# --------------------------------------------------------------------------
def _unreachable(source_id: str, name: str, f: Fetch) -> Resolution:
    return Resolution(source_id=source_id, query=name, status="unreachable",
                      endpoint=f.url, http_status=f.status,
                      retrieved_at=f.retrieved_at, note=f.error)


def resolve_one(name: str, use_cache: bool = True) -> List[Resolution]:
    """Resolve a scientific name against every configured authority."""
    out: List[Resolution] = []
    for source_id, tmpl, parser in (
        ("gbif", GBIF_MATCH, parse_gbif),
        ("worms", WORMS_BY_NAME, parse_worms),
    ):
        url = tmpl.format(name=quote(name))
        f = fetch(url, use_cache=use_cache)
        if not f.ok:
            # HTTP 404 from WoRMS is its "not found" convention, not an outage.
            if f.status == 404:
                r = Resolution(source_id=source_id, query=name, status="no_match")
            else:
                r = _unreachable(source_id, name, f)
        else:
            r = parser(f.json(), name)
        r.endpoint = url
        r.http_status = f.status
        r.retrieved_at = f.retrieved_at
        r.from_cache = f.from_cache
        out.append(r)
    return out


def reconcile(expected: str, resolutions: List[Resolution]) -> Dict[str, Any]:
    """Compare authority answers against the name the project already asserts.

    Returns a verdict rather than a mutation: nothing is auto-applied to the
    taxon index. Disagreements surface for review (규칙 8).
    """
    matched = [r for r in resolutions if r.status == "matched" and r.accepted_name]
    names = {r.accepted_name for r in matched}
    reachable = [r for r in resolutions if r.status != "unreachable"]

    if not reachable:
        verdict = "unresolved_network"
    elif not matched:
        verdict = "no_authority_match"
    elif names == {expected}:
        verdict = "agree"
    elif expected in names and len(names) > 1:
        verdict = "partial_disagreement"
    else:
        verdict = "disagreement"

    return {
        "expected_name": expected,
        "verdict": verdict,
        "authority_names": sorted(names),
        "identifiers": sorted(r.identifier for r in matched if r.identifier),
        "sources": [asdict(r) for r in resolutions],
        "requires_review": verdict in ("disagreement", "partial_disagreement",
                                       "no_authority_match"),
    }


def resolve_index(use_cache: bool = True) -> Dict[str, Any]:
    """Resolve every taxon in `taxonomy/taxon_index.csv` and write a report."""
    rows = list(csv.DictReader(
        open(paths.TAXONOMY / "taxon_index.csv", encoding="utf-8")))

    entries = {}
    for row in rows:
        name = row["accepted_scientific_name"]
        entries[row["taxon_id"]] = reconcile(name, resolve_one(name, use_cache))

    verdicts: Dict[str, int] = {}
    for e in entries.values():
        verdicts[e["verdict"]] = verdicts.get(e["verdict"], 0) + 1

    network_ok = any(s["status"] != "unreachable"
                     for e in entries.values() for s in e["sources"])

    report = {
        "generated_at": _now(),
        "network_reachable": network_ok,
        "licenses": SOURCE_LICENSE,
        "verdict_counts": verdicts,
        "requires_review": [k for k, v in entries.items() if v["requires_review"]],
        "entries": entries,
    }
    if not network_ok:
        report["note"] = (
            "No authority was reachable from this environment, so no name was "
            "verified. Nothing in the taxon index was changed. This is a "
            "blocked run, not a clean one — do not read it as confirmation."
        )
    out = paths.TAXONOMY / "resolution_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["_path"] = str(out)
    return report
