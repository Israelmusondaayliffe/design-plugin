#!/usr/bin/env python3
"""Refresh public-source health and content hashes for every alpha case."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "corpus/cases"
DEFAULT_REPORT = ROOT / "review/wave-11-source-health.json"
USER_AGENT = "Mozilla/5.0 (compatible; DesignCorpusSourceAudit/1.0; +https://github.com/israelayliffe/design-plugin)"
HASH_KIND = "canonical-source-identity-v1"
BOUND_FILES = ("metadata.json", "evidence.json", "source.json")
INTERNAL_LOCATOR_PREFIXES = ("DESIGN.md:", "Analyst synthesis", "Cross-guidance synthesis", "Cross-system synthesis")


class VisibleTextParser(HTMLParser):
    """Extract stable source-identity fields while ignoring executable payloads."""

    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []
        self.capture_tag: str | None = None
        self.capture_parts: list[str] = []
        self.titles: list[str] = []
        self.descriptions: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth += 1
        if not self.skip_depth and tag in {"title", "h1", "h2", "h3"} and self.capture_tag is None:
            self.capture_tag = tag
            self.capture_parts = []
        if not self.skip_depth and tag == "meta":
            values = {key.lower(): value for key, value in attrs if key and value}
            if values.get("name", "").lower() == "description" or values.get("property", "").lower() == "og:description":
                description = " ".join(values.get("content", "").split())
                if description:
                    self.descriptions.append(description)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.capture_tag == tag:
            text = " ".join("".join(self.capture_parts).split())
            if text:
                if tag == "title":
                    self.titles.append(text)
                else:
                    self.headings.append(text)
            self.capture_tag = None
            self.capture_parts = []
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)
                if self.capture_tag:
                    self.capture_parts.append(data)


def canonical_source_identity(payload: bytes, source_url: str) -> bytes:
    """Create a stable requested-source identity, independent of redirect routing."""
    text = payload.decode("utf-8", errors="replace")
    if re.search(r"<\s*!doctype\s+html|<\s*html\b", text[:4096], re.IGNORECASE):
        parser = VisibleTextParser()
        parser.feed(text)
        identity_text = next((item for item in parser.titles if item), "")
        if not identity_text:
            identity_text = next((item for item in parser.descriptions if item), "")
        if not identity_text:
            identity_text = next((item for item in parser.headings if item), "")
        if not identity_text:
            identity_text = " ".join(parser.parts[:20])
        text = f"{source_url}\n{identity_text}"
    else:
        text = f"{source_url}\n{text}"
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text.encode("utf-8")


def visible_locator_text(payload: bytes) -> str:
    """Return normalized fetched text for transient locator checks."""
    text = payload.decode("utf-8", errors="replace")
    if re.search(r"<\s*!doctype\s+html|<\s*html\b", text[:4096], re.IGNORECASE):
        parser = VisibleTextParser()
        parser.feed(text)
        text = "\n".join((*parser.titles, *parser.descriptions, *parser.headings, *parser.parts))
    return " ".join(text.casefold().split())


def locator_matches(locator: str, source_url: str, visible_text: str) -> bool:
    locator = locator.strip()
    if locator.startswith(INTERNAL_LOCATOR_PREFIXES):
        return True
    if locator.startswith("URL: "):
        return locator[5:].strip() == source_url
    return " ".join(locator.casefold().split()) in visible_text


def effective_url_collisions(results: dict[str, dict]) -> list[dict]:
    effective_urls: dict[str, list[str]] = {}
    for requested_url, result in sorted(results.items()):
        effective_urls.setdefault(result["effective_url"], []).append(requested_url)
    return [
        {"effective_url": url, "requested_urls": requested_urls}
        for url, requested_urls in sorted(effective_urls.items()) if len(requested_urls) > 1
    ]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_binding(case_records: dict[str, dict]) -> tuple[str, dict[str, dict[str, str]]]:
    digest = hashlib.sha256()
    bindings = {}
    for slug, record in sorted(case_records.items()):
        files = {}
        for name in BOUND_FILES:
            path = record["case_dir"] / name
            value = sha256_file(path)
            files[name] = value
            digest.update(f"{slug}/{name}\0{value}\n".encode("utf-8"))
        bindings[slug] = files
    return digest.hexdigest(), bindings


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(url: str, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="design-source-audit-") as temp_dir:
        body = Path(temp_dir) / "response.bin"
        completed = subprocess.run(
            [
                "curl", "--location", "--silent", "--show-error", "--compressed",
                "--retry", "2", "--retry-all-errors", "--connect-timeout", "10",
                "--max-time", str(timeout), "--user-agent", USER_AGENT,
                "--output", str(body), "--write-out", "%{http_code}\t%{url_effective}", url,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        output = completed.stdout.strip().split("\t", 1)
        try:
            status = int(output[0]) if output else 0
        except ValueError:
            status = 0
        effective_url = output[1] if len(output) == 2 else url
        payload = body.read_bytes() if body.exists() else b""
        canonical = canonical_source_identity(payload, url)
        return {
            "url": url,
            "effective_url": effective_url,
            "http_status": status,
            "content_sha256": hashlib.sha256(canonical).hexdigest(),
            "raw_response_sha256": hashlib.sha256(payload).hexdigest(),
            "hash_kind": HASH_KIND,
            "content_bytes": len(payload),
            "canonical_text_bytes": len(canonical),
            "curl_exit_code": completed.returncode,
            "error": completed.stderr.strip() or None,
            "pass": completed.returncode == 0 and 200 <= status <= 399 and bool(payload),
            "_locator_text": visible_locator_text(payload),
        }


def collect_urls() -> tuple[dict[str, dict], dict[str, list[str]], dict[str, list[dict]]]:
    case_records = {}
    url_cases: dict[str, list[str]] = {}
    url_evidence: dict[str, list[dict]] = {}
    for case_dir in sorted(path for path in CASES.iterdir() if path.is_dir()):
        metadata = read_json(case_dir / "metadata.json")
        evidence = read_json(case_dir / "evidence.json")
        urls = {metadata["source_url"], *(item["source_url"] for item in evidence["items"])}
        case_records[case_dir.name] = {"case_dir": case_dir, "metadata": metadata, "evidence": evidence, "urls": sorted(urls)}
        for url in urls:
            url_cases.setdefault(url, []).append(case_dir.name)
        for item in evidence["items"]:
            url_evidence.setdefault(item["source_url"], []).append({"slug": case_dir.name, **item})
    return case_records, url_cases, url_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    case_records, url_cases, url_evidence = collect_urls()
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch, url, args.timeout): url for url in url_cases}
        for future in as_completed(futures):
            result = future.result()
            result["case_slugs"] = sorted(url_cases[result["url"]])
            results[result["url"]] = result

    failures = [result for result in results.values() if not result["pass"]]
    locator_mismatches = []
    for url, items in sorted(url_evidence.items()):
        visible = results[url]["_locator_text"]
        for item in items:
            locator = item["locator"].strip()
            if not locator_matches(locator, url, visible):
                locator_mismatches.append(
                    {"slug": item["slug"], "evidence_id": item["id"], "source_url": url, "locator": locator}
                )
    stored_hash_mismatches = []
    for slug, record in sorted(case_records.items()):
        source = read_json(record["case_dir"] / "source.json")
        live_hash = results[record["metadata"]["source_url"]]["content_sha256"]
        if source["content_sha256"] != live_hash:
            stored_hash_mismatches.append(slug)
    if not args.check_only:
        today = date.today().isoformat()
        for record in case_records.values():
            source_path = record["case_dir"] / "source.json"
            source = read_json(source_path)
            canonical = results[record["metadata"]["source_url"]]
            if canonical["pass"]:
                limitations = [
                    item for item in source["limitations"]
                    if "must be refreshed" not in item.lower() and "placeholder" not in item.lower()
                ]
                if not limitations:
                    limitations = ["The live public source may change after the recorded response hash."]
                external_locators = sorted({
                    item["locator"] for item in record["evidence"]["items"]
                    if not item["locator"].startswith(INTERNAL_LOCATOR_PREFIXES)
                })
                source.update(
                    {
                        "effective_url": canonical["effective_url"],
                        "retrieved_at": today,
                        "http_status": canonical["http_status"],
                        "content_sha256": canonical["content_sha256"],
                        "source_version": f"live-public-source-{today}:{canonical['content_sha256'][:12]}",
                        "inspected_locators": external_locators or [f"URL: {record['metadata']['source_url']}"],
                        "limitations": limitations,
                    }
                )
                write_json(source_path, source)

    collisions = effective_url_collisions(results)
    tree_sha256, case_bindings = corpus_binding(case_records)
    unresolved_mismatches = stored_hash_mismatches if args.check_only else []

    report = {
        "schema_version": "1.0",
        "audit_date": date.today().isoformat(),
        "method": "Ordinary public HTTPS GET with redirects, retries, a named user agent, response hashing, and no retained source payloads.",
        "hash_kind": HASH_KIND,
        "hash_method": "SHA-256 of the requested owner URL plus the first available stable source-identity field: HTML title, description, heading, or a bounded visible-text fallback. Redirect destinations are recorded and collision-checked separately, so harmless routing changes cannot alter the identity hash. The value is not a claim-support or full-page change detector. Raw response hashes remain diagnostic only.",
        "corpus_binding_sha256": tree_sha256,
        "bound_files": list(BOUND_FILES),
        "case_bindings": case_bindings,
        "case_count": len(case_records),
        "unique_url_count": len(results),
        "passing_url_count": len(results) - len(failures),
        "failing_url_count": len(failures),
        "stored_hash_mismatch_count": len(unresolved_mismatches),
        "stored_hash_mismatch_slugs": unresolved_mismatches,
        "canonical_effective_collision_count": len(collisions),
        "canonical_effective_collisions": collisions,
        "locator_mismatch_count": len(locator_mismatches),
        "locator_mismatches": locator_mismatches,
        "status": "pass" if not failures and not unresolved_mismatches and not collisions and not locator_mismatches else "fail",
        "results": [{key: value for key, value in results[url].items() if not key.startswith("_")} for url in sorted(results)],
    }
    write_json(args.report, report)
    print(json.dumps({key: report[key] for key in ("status", "case_count", "unique_url_count", "passing_url_count", "failing_url_count")}, indent=2))
    if failures:
        for failure in sorted(failures, key=lambda item: item["url"]):
            print(f"FAIL {failure['http_status']} curl={failure['curl_exit_code']} {failure['url']}")
    if unresolved_mismatches:
        for slug in unresolved_mismatches:
            print(f"DRIFT {slug}: stored source hash differs from the current canonical text")
    if collisions:
        for collision in collisions:
            print(f"COLLISION {collision['effective_url']}: {', '.join(collision['requested_urls'])}")
    if locator_mismatches:
        for mismatch in locator_mismatches:
            print(f"LOCATOR {mismatch['slug']}/{mismatch['evidence_id']}: {mismatch['locator']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
