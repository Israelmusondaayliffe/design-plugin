#!/usr/bin/env python3
"""Wave 11 tests for the public catalog build and Evidence Exchange Site."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CORPUS = ROOT / "corpus"
TOKENS = ROOT / ".design/system/tokens.source.json"


class Wave11SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build = subprocess.run(
            [sys.executable, str(CORPUS / "scripts/build_catalog.py"), "--visibility", "public"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        cls.report = json.loads(cls.build.stdout)
        cls.index = json.loads((SITE / "generated-data/catalog/index.json").read_text(encoding="utf-8"))
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.app = (SITE / "app.js").read_text(encoding="utf-8")
        cls.css = (SITE / "styles.css").read_text(encoding="utf-8")
        cls.readme = (SITE / "README.md").read_text(encoding="utf-8")
        cls.tokens = json.loads(TOKENS.read_text(encoding="utf-8"))

    def test_public_catalog_contains_all_reviewed_cases(self) -> None:
        self.assertEqual(self.report["visibility"], "public")
        self.assertEqual(self.report["case_count"], 60)
        self.assertEqual(self.index["visibility"], "public")
        self.assertEqual(self.index["case_count"], 60)
        self.assertEqual(len(self.index["cases"]), 60)
        self.assertTrue(all(case["publication_status"] == "public" for case in self.index["cases"]))
        self.assertIn('id="public-count">60</strong> reviewed public cases', self.html)

    def test_all_five_task_regions_are_explicit(self) -> None:
        for screen in ("catalog", "case", "package", "comparison", "method"):
            self.assertIn(f'data-screen="{screen}"', self.html)
        self.assertIn('aria-labelledby="catalog-title"', self.html)
        self.assertIn('aria-labelledby="case-title"', self.html)
        self.assertIn('aria-labelledby="package-title"', self.html)
        self.assertIn('aria-labelledby="compare-title"', self.html)
        self.assertIn('aria-labelledby="method-title"', self.html)
        self.assertIn('id="method" class="screen method-screen"', self.html)
        self.assertIn('href="#method"', self.html)

    def test_package_contract_precedes_download_actions_in_document_order(self) -> None:
        ordered_ids = (
            "package-context-region",
            "package-contents-region",
            "package-evidence-region",
            "package-provenance-region",
            "package-limits-region",
            "package-files-region",
            "package-actions-region",
            "download-readable",
            "download-structured",
        )
        positions = [self.html.index(f'id="{element_id}"') for element_id in ordered_ids]
        self.assertEqual(positions, sorted(positions))
        for label in (
            "Context",
            "Contents",
            "Evidence boundary",
            "Provenance",
            "Limitations and unknowns",
            "File details",
            "Choose a file",
        ):
            self.assertIn(label, self.html)

    def test_catalog_preserves_search_lanes_six_facets_sort_and_progressive_results(self) -> None:
        for element_id in (
            "search",
            "lane-filters",
            "platform",
            "product-type",
            "archetype",
            "media",
            "density",
            "evidence",
            "sort",
            "results",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertEqual(len(re.findall(r'<label for="(?:platform|product-type|archetype|media|density|evidence)">', self.html)), 6)
        self.assertEqual(len(re.findall(r'"[^"]+": "[^"]+",?', self.app.split("const LANE_LABELS =", 1)[1].split("};", 1)[0])), 6)
        self.assertIn('fetch("generated-data/catalog/index.json")', self.app)
        self.assertIn("state.catalog.case_count !== 60", self.app)

    def test_case_and_package_use_validated_progressive_download_routes(self) -> None:
        self.assertIn("generated-data/cases/${encodeURIComponent(slug)}/downloads", self.app)
        self.assertIn('fetch(`${root}/case.json`)', self.app)
        self.assertIn('fetch(`${root}/manifest.json`)', self.app)
        self.assertIn("validatePublicPackage(slug, model, manifest)", self.app)
        self.assertIn('model.publication_status !== "public"', self.app)
        self.assertIn('manifest.files.length !== 2', self.app)
        self.assertIn('safeDownloadRoute(file.route)', self.app)
        self.assertIn("No download is available while validation is unresolved.", self.app)

    def test_existing_query_contract_and_package_view_survive_reload(self) -> None:
        for query_key in ("q", "lane", "sort", "compare", "case"):
            self.assertRegex(self.app, rf'params\.(?:set|get)\("{re.escape(query_key)}"')
        for query_key in ("platform", "product-type", "archetype", "media", "density", "evidence"):
            self.assertRegex(self.app, rf'\s+"?{re.escape(query_key)}"?: "[^"]+",')
        self.assertIn("for (const id of Object.keys(FACETS))", self.app)
        self.assertIn("params.set(id, value)", self.app)
        self.assertIn("params.get(id)", self.app)
        self.assertIn('params.set("view", "package")', self.app)
        self.assertIn('params.get("view") === "package"', self.app)
        self.assertIn("URLSearchParams", self.app)

    def test_method_deep_link_is_restored_after_catalog_settlement(self) -> None:
        helper = self.app.split("function restoreMethodRouteAfterCatalogRender()", 1)[1].split("function wireEvents()", 1)[0]
        self.assertIn('window.location.hash !== "#method"', helper)
        self.assertEqual(helper.count("window.requestAnimationFrame"), 2)
        self.assertIn('$("method").scrollIntoView({ behavior: "auto", block: "start" })', helper)
        self.assertIn('document.documentElement.style.scrollBehavior = "auto"', helper)
        self.assertIn("document.documentElement.style.scrollBehavior = previousScrollBehavior", helper)
        self.assertIn('window.addEventListener("load", alignAfterLayout, { once: true })', helper)
        self.assertIn("document.fonts?.ready", helper)
        start = self.app.split("async function start()", 1)[1]
        self.assertLess(start.index("render();"), start.index("restoreMethodRouteAfterCatalogRender();"))

    def test_comparison_enforces_two_to_five_public_cases(self) -> None:
        self.assertIn('id="comparison-limit-note"', self.html)
        self.assertRegex(self.app, r"state\.selected\.size\s*<\s*5")
        self.assertIn("state.selected.size < 2 || state.selected.size > 5", self.app)
        self.assertIn("slice(0, 5)", self.app)
        self.assertIn('role="region" aria-label="Selected case comparison table"', self.html)
        self.assertIn('scope="row"', self.app)
        self.assertIn('scope="col"', self.app)
        self.assertIn("else if (state.selected.size >= 2)", self.app)
        self.assertIn("openCompareDialog(null)", self.app)

    def test_semantic_landmarks_headings_labels_and_live_status_are_present(self) -> None:
        for tag in ("<header", "<nav", "<main", "<section", "<article", "<aside", "<footer", "<dialog"):
            self.assertIn(tag, self.html)
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertGreaterEqual(len(re.findall(r"<h2\b", self.html)), 5)
        self.assertGreaterEqual(len(re.findall(r"<h3\b", self.html)), 12)
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('aria-busy="true"', self.html)
        self.assertIn(":focus-visible", self.css)

    def test_approved_original_tokens_grid_and_reading_measure_are_encoded(self) -> None:
        required_tokens = {
            "--color-canvas": "#f3f4f2",
            "--color-surface-primary": "#ffffff",
            "--color-surface-secondary": "#e8ece9",
            "--color-text-primary": "#1d2522",
            "--color-action-primary": "#8b3a1b",
            "--color-focus": "#006278",
            "--color-status-ready": "#2b6b45",
            "--color-status-error": "#a12f2f",
        }
        for token, value in required_tokens.items():
            self.assertIn(f"{token}: {value};", self.css)
        self.assertIn("grid-template-columns: repeat(12, minmax(0, 1fr))", self.css)
        self.assertIn("grid-template-columns: repeat(6, minmax(0, 1fr))", self.css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", self.css)
        self.assertIn("max-width: 68ch", self.css)
        self.assertNotIn("#0f62fe", self.css.lower())
        self.assertNotIn("#273cff", self.css.lower())
        self.assertNotIn("#ff5a36", self.css.lower())
        self.assertNotIn("--shadow:", self.css)
        self.assertIn("--dialog-shadow:", self.css)

    def test_durable_color_tokens_match_the_site_palette(self) -> None:
        color_pairs = {
            "canvas": "--color-canvas",
            "surface-1": "--color-surface-primary",
            "surface-2": "--color-surface-secondary",
            "ink": "--color-text-primary",
            "muted": "--color-text-muted",
            "border": "--color-border-default",
            "border-strong": "--color-border-strong",
            "action": "--color-action-primary",
            "action-hover": "--color-action-hover",
            "focus": "--color-focus",
            "ready": "--color-status-ready",
            "incomplete": "--color-status-incomplete",
            "unavailable": "--color-status-unavailable",
            "stale": "--color-status-stale",
            "warning": "--color-status-warning",
            "error": "--color-status-error",
            "white": "--color-on-action",
        }
        source_colors = self.tokens["foundation"]["color"]
        for source_name, css_name in color_pairs.items():
            expected = source_colors[source_name]["$value"]["hex"].lower()
            self.assertIn(f"{css_name}: {expected};", self.css)
        self.assertEqual(
            self.tokens["foundation"]["radius"]["pill"]["$value"],
            {"value": 2, "unit": "px"},
        )
        self.assertIn("--radius-status: 2px;", self.css)

    def test_results_form_a_bounded_relational_atlas(self) -> None:
        self.assertIn('class="case-row"', self.app)
        self.assertIn("const INITIAL_CASE_LIMIT = 12", self.app)
        self.assertIn("visible.slice(0, state.visibleLimit)", self.app)
        self.assertIn('id="load-more"', self.html)
        self.assertIn("state.visibleLimit += INITIAL_CASE_LIMIT", self.app)
        self.assertIn('"preview content actions"', self.css)
        self.assertIn("grid-template-columns: minmax(260px, 4fr) minmax(0, 5fr) minmax(150px, 2fr)", self.css)
        self.assertNotRegex(self.css, r"\.results\s*\{[^}]*repeat\(3")

    def test_first_visit_explains_design_for_a_non_designer(self) -> None:
        for phrase in (
            "You do not need to be a designer",
            "Design is how choices shape what people",
            "Start with a problem",
            "What are you trying to make clearer?",
            "Design, made visible",
        ):
            self.assertIn(phrase, self.html)
        self.assertEqual(self.html.count('data-starter-lane="'), 4)
        self.assertIn('aria-label="Start from an everyday design problem"', self.html)
        self.assertIn('id="featured-studies"', self.html)
        self.assertIn('id="hero-study"', self.html)
        self.assertIn("One case from the atlas", self.html)
        self.assertIn("renderFeaturedStudies()", self.app)
        self.assertIn("See the choices before you learn their names", self.html)

    def test_each_case_receives_a_source_safe_original_visual_study(self) -> None:
        for field in (
            "item.preview?.pattern",
            "item.preview?.layout",
            "item.preview?.motion",
            "...(item.platforms ?? [])",
            "...(item.archetypes ?? [])",
            "...(item.journey ?? [])",
            "item.signature_traits?.[0]",
        ):
            self.assertIn(field, self.app)
        for family in ("system", "dashboard", "editorial", "mobile", "commerce", "flow"):
            self.assertIn(f'"{family}"', self.app)
            self.assertIn(f".study-{family}", self.css)
        self.assertIn("Our interpretation, not source UI", self.app)
        self.assertIn("data-study-signature", self.app)
        self.assertIn("function studySeed(item)", self.app)
        self.assertIn("--study-rail", self.app)
        self.assertNotIn("item.preview?.primary", self.app)
        self.assertNotIn("item.preview?.secondary", self.app)

        def seed_for(item: dict) -> int:
            source = "|".join(
                str(value)
                for value in (
                    item["slug"],
                    item["preview"]["pattern"],
                    item["preview"]["layout"],
                    item["preview"]["motion"],
                    *item["platforms"],
                    *item["archetypes"],
                    *item["journey"],
                )
            )
            value = 2166136261
            for character in source:
                value ^= ord(character)
                value = (value * 16777619) & 0xFFFFFFFF
            return value

        signatures = {seed_for(item) for item in self.index["cases"]}
        self.assertEqual(len(signatures), 60)

    def test_case_detail_leads_with_plain_help_before_technical_analysis(self) -> None:
        for phrase in (
            "What this case can help you see",
            "Where this case can help",
            "What to notice",
            "What to try",
            "Where to be careful",
            "Open the full technical analysis",
        ):
            self.assertIn(phrase, f"{self.html}\n{self.app}")
        render_case = self.app.split("function renderCase(model)", 1)[1].split("function validatePublicPackage", 1)[0]
        self.assertIn('decisionBlock("Where this case can help", model.value.best_for)', render_case)
        self.assertLess(render_case.index('decisionBlock("Where this case can help"'), render_case.index('decisionBlock("What to notice"'))
        self.assertLess(render_case.index('decisionBlock("What to notice"'), render_case.index("definitionList(model)"))

    def test_every_case_has_distinct_reviewed_practical_guidance(self) -> None:
        guidance_sets = set()
        for case in self.index["cases"]:
            model = json.loads(
                (SITE / "generated-data/cases" / case["slug"] / "downloads/case.json").read_text(encoding="utf-8")
            )
            guidance = tuple(item.strip() for item in model["value"]["best_for"])
            self.assertGreaterEqual(len(guidance), 2, case["slug"])
            self.assertTrue(all(guidance), case["slug"])
            guidance_sets.add(guidance)
        self.assertEqual(len(guidance_sets), 60)
        self.assertIn('decisionBlock("Where this case can help", model.value.best_for)', self.app)
        self.assertNotIn("function whyItMatters(model)", self.app)
        self.assertNotIn("can guide decisions in", self.app)

    def test_loading_and_error_states_put_named_context_in_the_captured_region(self) -> None:
        self.assertIn('class="catalog-loading-panel" role="listitem"', self.app)
        self.assertIn('role="status" aria-live="polite"', self.app)
        self.assertIn("Public catalog / 60 reviewed cases", self.app)
        self.assertIn('classList.toggle("case-loading-state", TEST_STATE === "case-loading")', self.app)
        self.assertIn(".case-loading-state .detail-preview", self.css)
        self.assertIn(".case-loading-state .local-nav { display: none; }", self.css)

        package_heading = self.html.split('<header class="package-heading grid-12">', 1)[1].split("</header>", 1)[0]
        for element_id in ("package-title", "package-summary", "package-ready", "package-status", "package-recovery-actions", "retry-package", "package-return"):
            self.assertIn(f'id="{element_id}"', package_heading)
        self.assertLess(package_heading.index('id="package-ready"'), package_heading.index('id="package-status"'))
        self.assertLess(package_heading.index('id="package-status"'), package_heading.index('id="retry-package"'))

    def test_wide_results_header_keeps_both_messages_readable(self) -> None:
        media = self.css.split("@media (min-width: 600px)", 1)[1].split("@media (min-width: 960px)", 1)[0]
        self.assertIn("grid-template-columns: minmax(0, 1fr) auto", media)
        self.assertIn(".results-head #status { grid-column: 1; grid-row: 1; max-width: 72ch; }", media)
        self.assertIn(".results-head .preview-boundary { grid-column: 1; grid-row: 2; max-width: 72ch; }", media)
        self.assertIn(".results-head .sort-control { grid-column: 2; grid-row: 1 / span 2; align-self: start; }", media)

    def test_filter_taxonomy_is_explained_at_the_point_of_use(self) -> None:
        for explanation in (
            "Where it is used",
            "What kind of thing it helps make",
            "Whether the case feels expressive, technical, collaborative, or service-focused",
            "How content or imagery carries meaning",
            "How much information shares the view",
            "How much public support the case has",
        ):
            self.assertIn(explanation, self.html)

    def test_package_explains_the_human_and_tool_choice_first(self) -> None:
        for phrase in (
            "For people first",
            "For tools first",
            "Choose Markdown when a person needs to read the case",
            "Choose JSON when a tool needs to work",
            "Technical file details",
        ):
            self.assertIn(phrase, f"{self.html}\n{self.app}")

    def test_responsive_and_mobile_contracts_are_present(self) -> None:
        self.assertIn("@media (min-width: 600px)", self.css)
        self.assertIn("@media (min-width: 960px)", self.css)
        self.assertIn("@media (min-width: 1280px)", self.css)
        self.assertIn("@media (max-width: 599px)", self.css)
        self.assertIn("min-height: 44px", self.css)
        self.assertIn("overflow-x: auto", self.css)
        self.assertIn("overflow-x: hidden", self.css)
        self.assertIn("prefers-reduced-motion: reduce", self.css)

    def test_wave4_catalog_states_and_single_horizontal_region_contract(self) -> None:
        for state_name in ("catalog-loading", "catalog-error"):
            self.assertIn(f'"{state_name}"', self.app)
        for element_id in ("catalog-recovery", "retry-catalog"):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("Retry public catalog", f"{self.html}\n{self.app}")
        self.assertIn('aria-label="Selected case comparison table"', self.html)
        self.assertIn(".compare-table { max-width: 100%; overflow-x: auto", self.css)
        self.assertIn(".file-table-wrap { overflow-x: visible; }", self.css)
        self.assertIn(".comparison { display: flex; flex-wrap: wrap;", self.css)
        self.assertIn(".local-nav {", self.css)
        local_nav_rule = self.css.split(".local-nav {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow: visible", local_nav_rule)
        lane_rule = self.css.split(".lane-filters {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow: visible", lane_rule)

    def test_wave4_primary_controls_have_44_pixel_minimum_targets(self) -> None:
        self.assertRegex(self.css, r"\.wordmark\s*\{[^}]*min-height:\s*44px")
        self.assertRegex(self.css, r"\.comparison button\s*\{[^}]*min-height:\s*44px")
        self.assertRegex(self.css, r"\.case-title-button\s*\{[^}]*min-height:\s*44px")
        self.assertRegex(self.css, r"\.hero-actions \.button\s*\{[^}]*min-height:\s*44px")
        self.assertNotRegex(self.css, r"\.hero-actions \.button\s*\{[^}]*min-height:\s*(?:[0-3]?\d|4[0-3])px")
        self.assertIn("min-height: 44px", self.css)
        self.assertRegex(
            self.css,
            r"\.filter-grid select,\s*\.sort-control select\s*\{[^}]*border:\s*1px solid var\(--color-border-strong\)",
        )

    def test_wave4_async_errors_are_announced(self) -> None:
        self.assertGreaterEqual(self.app.count('class="load-error" role="alert"'), 3)
        self.assertNotIn("error.message", self.app)
        self.assertNotIn("failure?.message", self.app)
        self.assertIn("could not be loaded and checked", self.app)
        self.assertIn("The Site asked your browser to download", self.app)

    def test_wave4_dialog_focus_restoration_is_queued_with_catalog_fallback(self) -> None:
        self.assertIn("storedTarget !== document.body", self.app)
        self.assertIn('const target = storedTarget instanceof HTMLElement', self.app)
        self.assertIn('window.setTimeout(() => {', self.app)
        self.assertIn(': $("search");', self.app)

    def test_wave4_spacing_and_dynamic_control_focus_repairs(self) -> None:
        self.assertRegex(
            self.css,
            r"@media \(max-width: 599px\)[\s\S]*?\.hero-title h1\s*\{[^}]*overflow-wrap:\s*anywhere",
        )
        self.assertIn('candidate.dataset.lane === state.lane', self.app)
        self.assertIn('activeButton?.focus()', self.app)
        self.assertIn('toggleCompare(compareButton.dataset.compare, { restoreCatalogFocus: true })', self.app)
        self.assertIn('restoredToggle?.focus()', self.app)
        self.assertIn('$("download-readable").focus()', self.app)
        self.assertIn('$("retry-package").focus()', self.app)
        self.assertIn('const previousCount = $("results").querySelectorAll(".case-row").length', self.app)
        self.assertIn('firstNewCase?.querySelector("[data-open-case]")?.focus()', self.app)
        self.assertIn('.method-grid .privacy-band > p:last-child { color: var(--color-canvas); }', self.css)

    def test_visual_study_boundary_label_uses_accessible_text_color(self) -> None:
        self.assertRegex(
            self.css,
            r"\.visual-study figcaption small\s*\{[^}]*color:\s*#46524d",
        )

    def test_site_has_no_remote_visual_dependencies_or_source_assets(self) -> None:
        combined = f"{self.html}\n{self.css}\n{self.app}".lower()
        self.assertNotIn("@import", combined)
        self.assertNotIn("<img", combined)
        self.assertNotIn("cdn.", combined)
        self.assertNotIn("fonts.googleapis", combined)
        self.assertNotIn("ibm plex", combined)
        self.assertNotIn("<iframe", combined)

    def test_readme_preserves_context_commands_and_publication_boundary(self) -> None:
        self.assertIn("five task regions", self.readme)
        self.assertIn("python3 corpus/scripts/build_catalog.py --visibility public", self.readme)
        self.assertIn("python3 -m http.server 4173 --directory site", self.readme)
        self.assertIn("python3 -m unittest tests.test_wave11_site tests.test_wave11_evidence_exchange", self.readme)
        self.assertIn("https://israelmusondaayliffe.github.io/design-plugin/", self.readme)
        self.assertIn("A local repair is not production proof", self.readme)
        self.assertIn("const LOCAL_ONLY = true", self.app)
        self.assertNotIn('data-local-only="true"', self.html)

    def test_all_sixty_browser_download_sources_match_their_manifests(self) -> None:
        for case in self.index["cases"]:
            root = SITE / "generated-data" / "cases" / case["slug"] / "downloads"
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["slug"], case["slug"])
            self.assertEqual({item["format"] for item in manifest["files"]}, {"readable", "structured"})
            self.assertEqual(len(manifest["files"]), 2)
            for item in manifest["files"]:
                path = root / item["route"]
                payload = path.read_bytes()
                self.assertEqual(path.parent, root)
                self.assertEqual(len(payload), item["byte_size"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])
                self.assertEqual(item["model_sha256"], manifest["model_sha256"])
                self.assertEqual(item["media_type"], {"readable": "text/markdown; charset=utf-8", "structured": "application/json; charset=utf-8"}[item["format"]])
                self.assertRegex(item["download_filename"], rf'^[a-z0-9][a-z0-9._-]+\.{"md" if item["format"] == "readable" else "json"}$')

    def test_downloads_are_byte_verified_and_use_the_verified_bytes(self) -> None:
        for source in (
            "response.arrayBuffer()",
            "bytes.byteLength !== file.byte_size",
            "await sha256Hex(bytes)",
            "digest !== file.sha256",
            "new Blob([verified.bytes]",
            "URL.createObjectURL(blob)",
            "URL.revokeObjectURL(url)",
            "safeDownloadFilename(link.download, format)",
        ):
            self.assertIn(source, self.app)
        self.assertIn('cache: "no-store"', self.app)
        self.assertIn('aria-disabled="true">Download readable brief', self.html)
        self.assertIn('aria-disabled="true">Download structured JSON', self.html)

    def test_manifest_validation_fails_closed_before_downloads_enable(self) -> None:
        for source in (
            "DOWNLOAD_MEDIA_TYPES",
            "safeDownloadFilename(file.download_filename, file.format)",
            "file.media_type !== DOWNLOAD_MEDIA_TYPES[file.format]",
            "file.byte_size < 1",
            "routes.has(file.route)",
            "filenames.has(file.download_filename)",
            'detail.validationStatus = "ready"',
        ):
            self.assertIn(source, self.app)
        self.assertLess(self.app.index("await verifyPackageFiles(detail)"), self.app.index('renderPackage(detail, "ready")'))

    def test_local_recovery_hooks_and_actions_are_bounded_and_specific(self) -> None:
        for state_name in ("case-loading", "case-error", "package-error", "package-denied", "download-error", "download-failure"):
            self.assertIn(f'"{state_name}"', self.app)
            self.assertIn(f"`test-state={state_name}`", self.readme)
        for host in ("127.0.0.1", "localhost", "::1"):
            self.assertIn(f'"{host}"', self.app)
        for element_id in ("case-loading-message", "case-loading-return", "package-recovery-actions", "retry-package", "package-return"):
            self.assertIn(f'id="{element_id}"', self.html)
        for phrase in (
            "Retry package validation",
            "Return to case",
            "Return to catalog",
            "No download is available",
            "No package or download is exposed",
        ):
            self.assertIn(phrase, f"{self.html}\n{self.app}")
        self.assertIn("LOCAL_TEST_HOSTS.has(window.location.hostname)", self.app)
        self.assertIn("LOCAL_TEST_STATES.has(candidate)", self.app)
        self.assertIn("use public cases, and expose no private fixtures", self.readme)

    def test_approved_quality_target_routes_remain_supported(self) -> None:
        self.assertIn('window.location.hash === "#download-package"', self.app)
        self.assertIn('const PRIVATE_TEST_CASE_SLUG = "private-test-case"', self.app)
        self.assertIn("showLocalPermissionDenied(slug, trigger)", self.app)
        self.assertIn('TEST_STATE === "download-error"', self.app)
        self.assertIn("No private fixture was loaded", self.app)
        for route in (
            "/?case=ibm-carbon#download-package",
            "/?case=ibm-carbon&test-state=download-error#download-package",
            "/?case=private-test-case#download-package",
        ):
            self.assertIn(route, self.readme)


if __name__ == "__main__":
    unittest.main()
