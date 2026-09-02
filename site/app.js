"use strict";

const LOCAL_ONLY = true;
const INITIAL_CASE_LIMIT = 12;

const LANE_LABELS = {
  "design-systems-data-experimental": "Design systems",
  "saas-dashboard-admin-productivity": "Product UI",
  "brand-editorial-portfolio-marketing": "Brand and editorial",
  "mobile": "Mobile",
  "commerce-media-content-heavy": "Commerce",
  "onboarding-forms-settings-flows": "Flows and forms",
};

const VALUE_LABELS = {
  ios: "iOS",
  saas: "SaaS",
  crm: "CRM",
  ui: "UI",
  "cross-platform": "Cross-platform",
  "responsive-web": "Responsive web",
  "content-heavy": "Content-heavy",
  "data-visualization": "Data visualization",
  "native-app": "Native app",
  "browse-discover": "Browsing and discovery",
  "complete-service": "Service completion",
  "create-manage": "Creation and management",
  "evaluate-convert": "Evaluation and conversion",
  "learn-progress": "Learning and progress",
  "monitor-operate": "Monitoring and operations",
  "onboard-configure": "Onboarding and configuration",
  "transact-checkout": "Transaction and checkout",
  "visualize-explore": "Visualization and exploration",
};

const FACETS = {
  platform: "platforms",
  "product-type": "product_types",
  archetype: "archetypes",
  media: "media_strategy",
  density: "density",
  evidence: "evidence_quality",
};

const ANALYSIS_LABELS = {
  brand_posture: "Brand posture",
  layout: "Layout",
  grid: "Grid",
  container: "Container",
  responsive_behavior: "Responsive behavior",
  typography: "Typography",
  color: "Color",
  spacing: "Spacing",
  surfaces: "Surfaces",
  components: "Components",
  states: "States",
  navigation: "Navigation",
  forms: "Forms",
  flows: "Flows",
  motion: "Motion",
  interaction: "Interaction",
  imagery: "Imagery",
  accessibility: "Accessibility",
};

const BOUNDARY_ORDER = ["observed", "inferred", "recommended", "unknown", "evidence_scope", "date_boundary", "public_projection"];
const DOWNLOAD_MEDIA_TYPES = {
  readable: "text/markdown; charset=utf-8",
  structured: "application/json; charset=utf-8",
};
const LOCAL_TEST_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);
const LOCAL_TEST_STATES = new Set(["catalog-loading", "catalog-error", "case-loading", "case-error", "package-error", "package-denied", "download-error", "download-failure"]);
const IS_LOCAL_TEST_HOST = LOCAL_ONLY && LOCAL_TEST_HOSTS.has(window.location.hostname);
const PRIVATE_TEST_CASE_SLUG = "private-test-case";
const LOCAL_CATALOG_REBUILD_HINT = "Rebuild the public catalog data, then retry.";

function readLocalTestState() {
  if (!IS_LOCAL_TEST_HOST) return "";
  const candidate = new URLSearchParams(window.location.search).get("test-state") ?? "";
  return LOCAL_TEST_STATES.has(candidate) ? candidate : "";
}

function readLocalTestFormat() {
  const candidate = new URLSearchParams(window.location.search).get("test-format") ?? "readable";
  return Object.hasOwn(DOWNLOAD_MEDIA_TYPES, candidate) ? candidate : "readable";
}

const TEST_STATE = readLocalTestState();
const TEST_FORMAT = readLocalTestFormat();

const state = {
  cases: [],
  catalog: null,
  lane: "",
  selected: new Set(),
  activeCase: null,
  activeView: "case",
  activePackage: null,
  packageCache: new Map(),
  downloadUrls: new Map(),
  focusReturn: new Map(),
  visibleLimit: INITIAL_CASE_LIMIT,
};

const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, character => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  "\"": "&quot;",
  "'": "&#39;",
}[character]));

function humanize(value) {
  return VALUE_LABELS[String(value ?? "").toLowerCase()] ?? String(value ?? "")
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .replace(/\b\w/g, character => character.toUpperCase());
}

function formatDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? "")) return String(value ?? "Not recorded");
  return new Intl.DateTimeFormat("en", { dateStyle: "long", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isInteger(bytes) || bytes < 0) return "Unknown";
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function validColor(value, fallback) {
  return /^#[0-9a-f]{3,8}$/i.test(value ?? "") ? value : fallback;
}

function validRadius(value) {
  return /^\d+(?:\.\d+)?(?:px|rem|em|%)$/.test(value ?? "") ? value : "4px";
}

function safeHttpsUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password ? parsed.href : "#";
  } catch {
    return "#";
  }
}

function safeDownloadRoute(value) {
  return /^[a-z0-9][a-z0-9.-]*$/.test(value ?? "") ? value : null;
}

function safeDownloadFilename(value, format) {
  const extension = format === "readable" ? ".md" : format === "structured" ? ".json" : "";
  return typeof value === "string"
    && /^[a-z0-9][a-z0-9._-]+$/.test(value)
    && !value.includes("..")
    && value.endsWith(extension)
    ? value
    : null;
}

class PackageFileError extends Error {
  constructor(message, { code = "validation-error", format = "package" } = {}) {
    super(message);
    this.name = "PackageFileError";
    this.code = code;
    this.format = format;
  }
}

async function sha256Hex(bytes) {
  if (!window.crypto?.subtle) {
    throw new PackageFileError("this browser cannot verify SHA-256", { code: "browser-failure" });
  }
  const digest = await window.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, "0")).join("");
}

function revokeDownloadUrls() {
  for (const url of state.downloadUrls.values()) URL.revokeObjectURL(url);
  state.downloadUrls.clear();
}

function listMarkup(values, className = "") {
  const items = Array.isArray(values) ? values : [];
  return `<ul${className ? ` class="${esc(className)}"` : ""}>${items.map(value => `<li>${esc(value)}</li>`).join("")}</ul>`;
}

function setInitialLoadingRows() {
  const template = $("loading-template");
  $("results").insertAdjacentHTML("beforeend", `
    <article class="catalog-loading-panel" role="listitem">
      <div role="status" aria-live="polite">
        <p class="technical-label">Public catalog / 60 reviewed cases</p>
        <h3>Loading the reference library</h3>
        <p>Checking the public case index before any case or download becomes available.</p>
      </div>
    </article>`);
  for (let index = 0; index < 4; index += 1) {
    $("results").append(template.content.cloneNode(true));
  }
}

function fillSelect(id, values) {
  const select = $(id);
  for (const value of values ?? []) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = humanize(value);
    select.appendChild(option);
  }
}

function countByLane() {
  return state.cases.reduce((counts, item) => {
    counts[item.corpus_lane] = (counts[item.corpus_lane] ?? 0) + 1;
    return counts;
  }, {});
}

function renderLaneFilters() {
  const counts = countByLane();
  const lanes = Object.keys(LANE_LABELS).filter(lane => counts[lane]);
  $("lane-filters").innerHTML = [
    `<button type="button" data-lane="" aria-pressed="${state.lane === ""}"><span>All cases</span><small>${state.cases.length}</small></button>`,
    ...lanes.map(lane => `<button type="button" data-lane="${esc(lane)}" aria-pressed="${state.lane === lane}"><span>${esc(LANE_LABELS[lane])}</span><small>${counts[lane]}</small></button>`),
  ].join("");
}

function readFilter(id) {
  return $(id).value;
}

function matches(item) {
  const query = readFilter("search").trim().toLocaleLowerCase();
  const searchable = [
    item.name,
    item.source_name,
    item.summary,
    item.corpus_lane,
    ...item.platforms,
    ...item.product_types,
    ...item.industries,
    ...item.archetypes,
    ...item.journey,
    ...item.signature_traits,
    ...item.best_for,
    ...item.avoid_for,
  ].join(" ").toLocaleLowerCase();

  if (query && !searchable.includes(query)) return false;
  if (state.lane && item.corpus_lane !== state.lane) return false;

  return Object.entries(FACETS).every(([id, field]) => {
    const filter = readFilter(id);
    if (!filter) return true;
    const value = item[field];
    return Array.isArray(value) ? value.includes(filter) : value === filter;
  });
}

function sorted(items) {
  const mode = readFilter("sort");
  const copy = [...items];
  if (mode === "lane") {
    return copy.sort((a, b) => `${LANE_LABELS[a.corpus_lane]} ${a.name}`.localeCompare(`${LANE_LABELS[b.corpus_lane]} ${b.name}`));
  }
  if (mode === "evidence") {
    const order = { high: 0, medium: 1, low: 2 };
    return copy.sort((a, b) => (order[a.evidence_quality] ?? 9) - (order[b.evidence_quality] ?? 9) || a.name.localeCompare(b.name));
  }
  return copy.sort((a, b) => a.name.localeCompare(b.name));
}

function studyFamily(item) {
  return {
    "design-systems-data-experimental": "system",
    "saas-dashboard-admin-productivity": "dashboard",
    "brand-editorial-portfolio-marketing": "editorial",
    mobile: "mobile",
    "commerce-media-content-heavy": "commerce",
    "onboarding-forms-settings-flows": "flow",
  }[item.corpus_lane] ?? "system";
}

function studyDensity(item) {
  const density = String(item.density ?? "balanced").toLowerCase();
  if (density.includes("high") || density.includes("dense")) return "dense";
  if (density.includes("low") || density.includes("minimal")) return "open";
  return "balanced";
}

function studySeed(item) {
  const source = [
    item.slug,
    item.preview?.pattern,
    item.preview?.layout,
    item.preview?.motion,
    ...(item.platforms ?? []),
    ...(item.archetypes ?? []),
    ...(item.journey ?? []),
  ].join("|");
  let hash = 2166136261;
  for (const character of source) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function previewMarkup(item, size = "row") {
  const seed = studySeed(item);
  const family = studyFamily(item);
  const density = studyDensity(item);
  const variant = seed % 4;
  const caseType = {
    system: "component system",
    dashboard: "working dashboard",
    editorial: "editorial page",
    mobile: "mobile flow",
    commerce: "shopping decision",
    flow: "guided task",
  }[family];
  const focus = item.signature_traits?.[0] ?? item.summary;
  const shortName = String(item.name ?? "Design case").split(/\s+/).slice(0, 5).join(" ");
  const focusExcerpt = String(focus ?? "Study the relationship").split(/\s+/).slice(0, 10).join(" ");
  const description = `Original ${family} study for ${item.name}, derived from the public case fields. It is an interpretation, not the source product or evidence.`;
  const studyStyle = [
    `--study-rail:${13 + (seed & 15)}%`,
    `--study-feature:${34 + ((seed >>> 4) & 31)}%`,
    `--study-toolbar:${22 + ((seed >>> 9) & 15)}%`,
    `--study-action:${18 + ((seed >>> 13) & 15)}%`,
    `--study-gap:${3 + ((seed >>> 17) & 7)}%`,
    `--study-inset:${3 + ((seed >>> 20) & 7)}%`,
    `--study-x:${12 + ((seed >>> 6) & 31)}%`,
    `--study-y:${18 + ((seed >>> 11) & 31)}%`,
    `--study-turn:${-9 + ((seed >>> 16) & 15)}deg`,
  ].join(";");
  return `
    <figure class="visual-study study-${family} density-${density} variant-${variant} ${size === "detail" ? "study-detail" : ""}" data-study-signature="${family}-${density}-${variant}-${seed.toString(36)}" style="${studyStyle}" aria-label="${esc(description)}">
      <div class="study-canvas" aria-hidden="true">
        <div class="study-atmosphere"><i></i><i></i><i></i><i></i></div>
        <div class="study-window-bar"><span></span><span></span><span></span><b>${esc(caseType)}</b></div>
        <div class="study-interface">
          <div class="study-rail"><i></i><i></i><i></i><i></i><i></i></div>
          <div class="study-stage">
            <div class="study-toolbar"><i></i><i></i><b></b></div>
            <div class="study-voice"><small>${esc(caseType)}</small><strong>${esc(shortName)}</strong><span>${esc(focusExcerpt)}</span></div>
            <div class="study-feature"><i></i><div><b></b><span></span><span></span></div></div>
            <div class="study-content-grid">
              <i></i><i></i><i></i><i></i><i></i><i></i>
            </div>
            <div class="study-data"><i></i><i></i><i></i><i></i></div>
            <div class="study-action"><i></i><b></b></div>
          </div>
        </div>
      </div>
      <figcaption><strong>Original ${esc(caseType)} study</strong><span>${esc(focus)}</span><small>Our interpretation, not source UI</small></figcaption>
    </figure>`;
}

function caseRow(item, index) {
  const selected = state.selected.has(item.slug);
  const selectionDisabled = !selected && state.selected.size >= 5;
  return `
    <article class="case-row" role="listitem" data-case-slug="${esc(item.slug)}">
      <div class="row-eyebrow"><p class="row-index technical-label">${String(index + 1).padStart(2, "0")}</p><p>${esc(LANE_LABELS[item.corpus_lane] ?? humanize(item.corpus_lane))}</p></div>
      <button class="preview-button row-preview" type="button" data-open-case="${esc(item.slug)}" aria-label="Open ${esc(item.name)} public case">
        ${previewMarkup(item)}
      </button>
      <div class="row-main">
        <button class="case-title-button" type="button" data-open-case="${esc(item.slug)}"><h3>${esc(item.name)}</h3></button>
        <p>${esc(item.summary)}</p>
        <dl class="case-glance">
          <div><dt>What to notice</dt><dd>${esc(item.signature_traits?.[0] ?? "Open the case for the reviewed relationship.")}</dd></div>
          <div><dt>Useful when</dt><dd>${esc(item.best_for?.[0] ?? "You need a related design reference.")}</dd></div>
          <div><dt>Evidence</dt><dd>${esc(humanize(item.evidence_quality))}</dd></div>
        </dl>
      </div>
      <div class="row-actions">
        <button class="button button-primary" type="button" data-open-case="${esc(item.slug)}">See what to borrow</button>
        <button class="button compare-toggle" type="button" data-compare="${esc(item.slug)}" aria-pressed="${selected}" ${selectionDisabled ? "disabled aria-describedby=\"comparison-limit-note\"" : ""}>${selected ? "Selected" : "Compare"}</button>
      </div>
    </article>`;
}

function renderFeaturedStudies() {
  const lanes = [
    "design-systems-data-experimental",
    "mobile",
    "onboarding-forms-settings-flows",
  ];
  const featured = lanes
    .map(lane => state.cases.find(item => item.corpus_lane === lane))
    .filter(Boolean);
  const heroCase = state.cases.find(item => item.slug === "ibm-carbon") ?? featured[0];
  $("hero-study").innerHTML = heroCase ? `
    <button class="preview-button" type="button" data-open-case="${esc(heroCase.slug)}" aria-label="Open ${esc(heroCase.name)} public case">
      ${previewMarkup(heroCase)}
    </button>
    <p><strong>${esc(heroCase.name)}</strong><span>Notice: ${esc(heroCase.signature_traits?.[0] ?? heroCase.summary)}</span></p>` : "";
  $("featured-studies").innerHTML = featured.map(item => `
    <article>
      <button class="preview-button" type="button" data-open-case="${esc(item.slug)}" aria-label="Open ${esc(item.name)} public case">
        ${previewMarkup(item)}
      </button>
      <div><p class="technical-label">${esc(LANE_LABELS[item.corpus_lane] ?? humanize(item.corpus_lane))}</p><h3>${esc(item.name)}</h3><p><strong>Notice:</strong> ${esc(item.signature_traits?.[0] ?? item.summary)}</p></div>
      <button class="text-button" type="button" data-open-case="${esc(item.slug)}">Open this case</button>
    </article>`).join("");
}

function activeFilterCount() {
  return Number(Boolean(state.lane)) + Number(Boolean(readFilter("search").trim())) + Object.keys(FACETS).filter(id => readFilter(id)).length;
}

function updateFilterSummary() {
  const count = activeFilterCount();
  $("active-filter-count").hidden = count === 0;
  $("active-filter-count").textContent = `${count} active`;
  $("clear-search").hidden = readFilter("search").length === 0;
  if (count > 0 && window.matchMedia("(max-width: 959px)").matches) $("advanced-filters").open = true;
}

function writeUrl() {
  const params = new URLSearchParams();
  const query = readFilter("search").trim();
  if (query) params.set("q", query);
  if (state.lane) params.set("lane", state.lane);
  for (const id of Object.keys(FACETS)) {
    const value = readFilter(id);
    if (value) params.set(id, value);
  }
  if (readFilter("sort") !== "name") params.set("sort", readFilter("sort"));
  if (state.selected.size) params.set("compare", [...state.selected].join(","));
  if (state.activeCase) params.set("case", state.activeCase);
  if (state.activeCase && state.activeView === "package") params.set("view", "package");
  if (TEST_STATE) params.set("test-state", TEST_STATE);
  if (TEST_STATE && TEST_FORMAT) params.set("test-format", TEST_FORMAT);
  const queryString = params.toString();
  window.history.replaceState({}, "", `${window.location.pathname}${queryString ? `?${queryString}` : ""}${window.location.hash}`);
}

function render() {
  const visible = sorted(state.cases.filter(matches));
  const displayed = visible.slice(0, state.visibleLimit);
  $("results").innerHTML = displayed.map(caseRow).join("");
  $("results").setAttribute("aria-busy", "false");
  $("status").textContent = `${visible.length} of ${state.cases.length} reviewed public cases match`;
  $("empty-state").hidden = visible.length !== 0;
  $("catalog-pagination").hidden = visible.length === 0 || displayed.length >= visible.length;
  $("pagination-status").textContent = `Showing ${displayed.length} of ${visible.length} matching cases.`;
  renderLaneFilters();
  renderCompareTray();
  updateFilterSummary();
  writeUrl();
}

function toggleCompare(slug, { restoreCatalogFocus = false } = {}) {
  if (state.selected.has(slug)) {
    state.selected.delete(slug);
  } else if (state.selected.size<5) {
    state.selected.add(slug);
  }
  render();
  if (restoreCatalogFocus) {
    const restoredToggle = [...$("results").querySelectorAll("[data-compare]")]
      .find(candidate => candidate.dataset.compare === slug);
    restoredToggle?.focus();
  }
  if (state.activeCase === slug) updateDialogCompareButton();
}

function selectedCases() {
  return [...state.selected].map(slug => state.cases.find(item => item.slug === slug)).filter(Boolean);
}

function renderCompareTray() {
  const items = selectedCases();
  $("compare-tray").hidden = items.length === 0;
  $("compare-count").textContent = String(items.length);
  $("comparison").innerHTML = items.map(item => `
    <button type="button" data-remove-compare="${esc(item.slug)}" aria-label="Remove ${esc(item.name)} from comparison">
      ${esc(item.name)} <span aria-hidden="true">×</span>
    </button>`).join("");
  $("open-compare").disabled = items.length < 2;
}

function taxonomyValue(value) {
  if (Array.isArray(value)) return value.map(humanize).join(", ");
  return humanize(value);
}

function proseValue(value) {
  return Array.isArray(value) ? value.join(", ") : String(value ?? "");
}

function renderCompareDialog() {
  const items = selectedCases();
  const rows = [
    ["Coverage lane", item => LANE_LABELS[item.corpus_lane] ?? humanize(item.corpus_lane)],
    ["Evidence quality", item => humanize(item.evidence_quality)],
    ["Platform", item => taxonomyValue(item.platforms)],
    ["Product type", item => taxonomyValue(item.product_types)],
    ["Archetype", item => taxonomyValue(item.archetypes)],
    ["Density", item => taxonomyValue(item.density)],
    ["Media strategy", item => taxonomyValue(item.media_strategy)],
    ["Signature relationships", item => proseValue(item.signature_traits)],
    ["Useful when", item => proseValue(item.best_for)],
    ["Avoid when", item => proseValue(item.avoid_for)],
  ];
  $("compare-table").innerHTML = `
    <table>
      <thead><tr><th scope="col">Attribute</th>${items.map(item => `<th scope="col">${esc(item.name)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(([label, getter]) => `<tr><th scope="row">${esc(label)}</th>${items.map(item => `<td>${esc(getter(item))}</td>`).join("")}</tr>`).join("")}</tbody>
    </table>
    <div class="comparison-open-actions">${items.map(item => `<button class="button" type="button" data-open-case="${esc(item.slug)}">Open ${esc(item.name)}</button>`).join("")}</div>`;
}

function openCompareDialog(trigger) {
  if (state.selected.size < 2 || state.selected.size > 5) return;
  renderCompareDialog();
  openModal($("compare-dialog"), trigger);
}

function openModal(dialog, trigger) {
  if (!dialog.open) {
    state.focusReturn.set(dialog.id, trigger ?? document.activeElement);
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }
  document.body.classList.add("modal-open");
}

function closeModal(dialog) {
  if (dialog.open && typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function updateDialogCompareButton() {
  const publicCase = state.cases.some(item => item.slug === state.activeCase && item.publication_status === "public");
  const selected = state.selected.has(state.activeCase);
  $("dialog-compare").textContent = publicCase ? (selected ? "Remove from comparison" : "Add to comparison") : "Comparison unavailable";
  $("dialog-compare").setAttribute("aria-pressed", String(selected));
  $("dialog-compare").disabled = !publicCase || (!selected && state.selected.size >= 5);
}

function definitionList(model) {
  const context = model.context.study_context;
  const definitions = [
    ["Platform", taxonomyValue(context.platforms)],
    ["Product type", taxonomyValue(context.product_types)],
    ["Archetype", taxonomyValue(context.archetypes)],
    ["Task stage", taxonomyValue(model.intent.journeys)],
    ["Density", taxonomyValue(context.density)],
    ["Evidence quality", taxonomyValue(model.quality.evidence_quality)],
    ["Coverage confidence", taxonomyValue(model.quality.coverage_confidence)],
    ["Accessibility maturity", taxonomyValue(model.quality.accessibility_maturity)],
  ];
  return `<dl class="case-definitions">${definitions.map(([term, value]) => `<div><dt>${esc(term)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>`;
}

function decisionBlock(title, values) {
  return `<section class="decision-block"><h4>${esc(title)}</h4>${listMarkup(values)}</section>`;
}

function groupedAnalysis(model) {
  const groups = new Map();
  for (const [key, label] of Object.entries(ANALYSIS_LABELS)) {
    const statement = String(model.analysis[key] ?? "").trim();
    if (!statement) continue;
    if (!groups.has(statement)) groups.set(statement, []);
    groups.get(statement).push(label);
  }
  return `<dl class="analysis-list">${[...groups.entries()].map(([statement, labels]) => `<div><dt>${esc(labels.join(" / "))}</dt><dd>${esc(statement)}</dd></div>`).join("")}</dl>`;
}

function evidenceMarkup(model) {
  const boundary = model.evidence_boundary;
  const ownerUrl = safeHttpsUrl(model.provenance.owner_url);
  return `
    <div class="evidence-boundary">
      <p><strong>What the source says:</strong> ${esc(boundary.observed)}</p>
      <p><strong>Our reading and suggestion:</strong> ${esc(boundary.inferred)} ${esc(boundary.recommended)}</p>
      <p><strong>What we cannot prove:</strong> ${esc(boundary.unknown)}</p>
    </div>
    <ol class="evidence-list">${model.evidence.map(item => `
      <li>
        <div class="evidence-meta"><span>${esc(item.id)}</span><span>${esc(humanize(item.truth_class))}</span><span>${esc(humanize(item.confidence))} confidence</span></div>
        <div><h4>${esc(item.claim)}</h4><p>${esc(item.qualification)}</p></div>
        <div><a href="${esc(safeHttpsUrl(item.source_url))}" target="_blank" rel="noopener noreferrer">Owner source</a><br><code>Retrieved ${esc(item.retrieved_at)}</code></div>
      </li>`).join("")}</ol>
    <div class="limits-grid">
      <section class="limit-block"><h4>Source limitations</h4>${listMarkup(model.limitations.map(item => item.statement))}</section>
      <section class="limit-block"><h4>Known unknowns</h4>${listMarkup(model.unknowns.map(item => item.statement))}</section>
    </div>
    <p class="truth-note">Owner source: <a href="${esc(ownerUrl)}" target="_blank" rel="noopener noreferrer">${esc(model.context.source_identity.source_name)}</a>. Retrieved ${esc(formatDate(model.provenance.retrieved_at))}.</p>`;
}

function renderCase(model) {
  $("case-context-content").innerHTML = `
    <p class="case-start"><span>Start here</span>Begin with your own problem, not the source's look. Read the summary as a pattern, then check where this case can actually help.</p>
    <p class="case-source-summary"><strong>The full case summary:</strong> ${esc(model.context.study_context.summary)}</p>
    <div class="case-quick-read">
      ${decisionBlock("Where this case can help", model.value.best_for)}
      ${decisionBlock("What to notice", model.intent.signature_relationships)}
      ${decisionBlock("What to try", [model.analysis.layout, model.analysis.interaction].filter(Boolean))}
      ${decisionBlock("Where to be careful", [...model.value.avoid_for, ...model.value.failure_modes])}
    </div>`;

  $("case-analysis-content").innerHTML = `
    <details class="technical-details">
      <summary>Open the full technical analysis</summary>
      <p class="truth-note">This section uses design terms for readers who need them. Analysis labels: ${model.analysis.truth_classes.map(humanize).map(esc).join(", ")}.</p>
      ${definitionList(model)}
      ${groupedAnalysis(model)}
    </details>`;

  $("case-evidence-content").innerHTML = evidenceMarkup(model);
  $("case-loading").hidden = true;
  $("case-content").hidden = false;
  $("open-package").disabled = false;
}

function validatePublicPackage(slug, model, manifest) {
  if (model?.slug !== slug || manifest?.slug !== slug) throw new Error("The package identifiers do not match the requested public case");
  if (model.publication_status !== "public" || model.package_type !== "design-reference-public-case") throw new Error("The requested case is not a valid public package");
  if (model.schema_version !== "1.0" || manifest.schema_version !== "1.0") throw new Error("The package schema version is not supported by this Site");
  if (!/^[0-9a-f]{64}$/.test(manifest.model_sha256 ?? "")) throw new Error("The package model hash is invalid");
  if (!Array.isArray(manifest.files) || manifest.files.length !== 2) throw new Error("The package must contain readable and structured formats");
  if (manifest.model_sha256 !== manifest.files[0].model_sha256 || manifest.files.some(file => file.model_sha256 !== manifest.model_sha256)) {
    throw new Error("The package files do not share one model binding");
  }
  const formats = new Set(manifest.files.map(file => file.format));
  if (formats.size !== 2 || !formats.has("readable") || !formats.has("structured")) throw new Error("The package must contain one readable and one structured format");
  const routes = new Set();
  const filenames = new Set();
  for (const file of manifest.files) {
    if (!safeDownloadRoute(file.route)) throw new PackageFileError("its route is unsafe", { format: file.format });
    if (!safeDownloadFilename(file.download_filename, file.format)) throw new PackageFileError("its filename is unsafe", { format: file.format });
    if (file.media_type !== DOWNLOAD_MEDIA_TYPES[file.format]) throw new PackageFileError("its media type does not match the approved format", { format: file.format });
    if (!Number.isInteger(file.byte_size) || file.byte_size < 1) throw new PackageFileError("its byte count is invalid", { format: file.format });
    if (!/^[0-9a-f]{64}$/.test(file.sha256 ?? "")) throw new PackageFileError("its SHA-256 is invalid", { format: file.format });
    if (routes.has(file.route) || filenames.has(file.download_filename)) throw new PackageFileError("its route or filename is duplicated", { format: file.format });
    routes.add(file.route);
    filenames.add(file.download_filename);
  }
}

async function loadPublicPackageMetadata(slug) {
  if (state.packageCache.has(slug)) return state.packageCache.get(slug);
  if (TEST_STATE === "case-loading") await new Promise(() => {});
  const root = `generated-data/cases/${encodeURIComponent(slug)}/downloads`;
  const [modelResponse, manifestResponse] = await Promise.all([
    fetch(`${root}/case.json`),
    fetch(`${root}/manifest.json`),
  ]);
  if (TEST_STATE === "case-error") throw new Error("the public model and manifest failed the local validation test");
  if (!modelResponse.ok) throw new Error(`structured package returned HTTP ${modelResponse.status}`);
  if (!manifestResponse.ok) throw new Error(`package manifest returned HTTP ${manifestResponse.status}`);
  const [model, manifest] = await Promise.all([modelResponse.json(), manifestResponse.json()]);
  validatePublicPackage(slug, model, manifest);
  const detail = { model, manifest, root, verifiedFiles: new Map(), validationStatus: "metadata-ready", validationError: null };
  state.packageCache.set(slug, detail);
  return detail;
}

async function verifyPackageFiles(detail) {
  detail.verifiedFiles.clear();
  detail.validationStatus = "validating";
  detail.validationError = null;
  try {
    for (const file of detail.manifest.files) {
      const route = safeDownloadRoute(file.route);
      const response = await fetch(`${detail.root}/${route}`, { cache: "no-store" });
      if (!response.ok) {
        throw new PackageFileError(`the generated route returned HTTP ${response.status}`, { code: "missing-file", format: file.format });
      }
      const bytes = await response.arrayBuffer();
      if ((TEST_STATE === "package-error" || TEST_STATE === "download-error") && file.format === TEST_FORMAT) {
        throw new PackageFileError("its downloaded SHA-256 does not match the manifest", { format: file.format });
      }
      if (bytes.byteLength !== file.byte_size) {
        throw new PackageFileError(`its downloaded byte count is ${bytes.byteLength}, not the manifest value ${file.byte_size}`, { format: file.format });
      }
      const digest = await sha256Hex(bytes);
      if (digest !== file.sha256) {
        throw new PackageFileError("its downloaded SHA-256 does not match the manifest", { format: file.format });
      }
      detail.verifiedFiles.set(file.format, { bytes, file });
    }
    if (TEST_STATE === "package-denied") {
      throw new PackageFileError("the browser blocked local file preparation", { code: "permission-denied", format: TEST_FORMAT });
    }
    detail.validationStatus = "ready";
    return detail;
  } catch (error) {
    detail.verifiedFiles.clear();
    detail.validationStatus = "error";
    detail.validationError = error;
    throw error;
  }
}

function packageContextMarkup(model) {
  return `
    <p class="case-start"><span>Use this package for</span>${esc(model.value.best_for.slice(0, 3).join(", "))}.</p>
    <p class="case-source-summary"><strong>The full case summary:</strong> ${esc(model.context.study_context.summary)}</p>
    <div class="decision-grid">
      ${decisionBlock("Use this package when", model.value.best_for)}
      ${decisionBlock("This package does not prove", ["Accessibility conformance", "Fitness for a specific product", "The source owner's private intent", "Guaranteed design outcomes"])}
    </div>
    <details class="technical-details"><summary>Show the case classification</summary>${definitionList(model)}</details>`;
}

function formatSpecificationsMarkup(manifest) {
  const descriptions = {
    readable: ["Choose this if a person will read, discuss, teach, or hand off the case", "Plain headings, context, what to notice, evidence, limits, and unknowns", "Markdown that also remains easy for many tools to parse"],
    structured: ["Choose this if software will sort, compare, transform, or store the case", "JSON fields from the same approved public record", "Stable labels for tools that need exact structure"],
  };
  return manifest.files.map(file => `
    <section class="format-specification">
      <p class="technical-label">${file.format === "readable" ? "For people first" : "For tools first"}</p>
      <h4>${esc(humanize(file.format))} ${file.format === "readable" ? "brief" : "data"}</h4>
      ${listMarkup(descriptions[file.format] ?? [])}
      <details class="file-technical"><summary>Technical file details</summary><p><code>${esc(file.media_type)}</code><br><code>${esc(file.download_filename)}</code><br>${esc(formatBytes(file.byte_size))}</p></details>
    </section>`).join("");
}

function boundaryMarkup(model) {
  return `<ul class="boundary-list">${BOUNDARY_ORDER.map(key => `<li><strong>${esc(humanize(key))}</strong><span>${esc(model.evidence_boundary[key])}</span></li>`).join("")}</ul>`;
}

function provenanceMarkup(model) {
  const provenance = model.provenance;
  const rows = [
    ["Owner source", `<a href="${esc(safeHttpsUrl(provenance.owner_url))}" target="_blank" rel="noopener noreferrer">${esc(provenance.owner_url)}</a>`],
    ["Retrieved", esc(formatDate(provenance.retrieved_at))],
    ["Rights basis", `<code>${esc(provenance.rights_basis)}</code>`],
    ["Permitted use basis", `<code>${esc(provenance.permitted_use_basis)}</code>`],
    ["Terms or license URL", provenance.terms_or_license_url ? `<a href="${esc(safeHttpsUrl(provenance.terms_or_license_url))}" target="_blank" rel="noopener noreferrer">Open terms</a>` : "Not recorded in the public package"],
    ["Third-party assets stored", provenance.third_party_assets_stored ? "Yes" : "No"],
  ];
  return `<dl class="provenance-grid">${rows.map(([term, value]) => `<div><dt>${esc(term)}</dt><dd>${value}</dd></div>`).join("")}</dl>`;
}

function limitsMarkup(model) {
  return `<div class="limits-grid">
    <section class="limit-block"><h4>Source limitations</h4>${listMarkup(model.limitations.map(item => item.statement))}</section>
    <section class="limit-block"><h4>Known unknowns</h4>${listMarkup(model.unknowns.map(item => item.statement))}</section>
  </div>`;
}

function fileTableMarkup(manifest, stage, failure = null) {
  const verificationLabel = file => {
    if (stage === "ready") return "SHA-256 matched";
    if (stage === "error" && failure?.format === file.format) return "Blocked";
    if (stage === "error") return "Not enabled";
    return "Checking";
  };
  return `<table>
    <thead><tr><th scope="col">Format</th><th scope="col">Download filename</th><th scope="col">Media type</th><th scope="col">Size</th><th scope="col">SHA-256</th><th scope="col">Verification</th></tr></thead>
    <tbody>${manifest.files.map(file => `<tr><th scope="row" data-label="Format">${esc(humanize(file.format))}</th><td data-label="Download filename">${esc(file.download_filename)}</td><td data-label="Media type">${esc(file.media_type)}</td><td data-label="Size">${esc(formatBytes(file.byte_size))}</td><td data-label="SHA-256">${esc(file.sha256)}</td><td data-label="Verification">${esc(verificationLabel(file))}</td></tr>`).join("")}</tbody>
  </table>`;
}

function disableDownloadActions() {
  revokeDownloadUrls();
  for (const id of ["download-readable", "download-structured"]) {
    const link = $(id);
    link.href = "#";
    link.setAttribute("aria-disabled", "true");
    link.removeAttribute("download");
    delete link.dataset.format;
  }
}

function configureVerifiedDownloads(detail) {
  disableDownloadActions();
  for (const [id, format] of [["download-readable", "readable"], ["download-structured", "structured"]]) {
    const verified = detail.verifiedFiles.get(format);
    if (!verified) throw new PackageFileError("its verified bytes are unavailable", { format });
    const blob = new Blob([verified.bytes], { type: verified.file.media_type });
    const url = URL.createObjectURL(blob);
    state.downloadUrls.set(id, url);
    const link = $(id);
    link.href = url;
    link.download = verified.file.download_filename;
    link.dataset.format = format;
    link.removeAttribute("aria-disabled");
  }
}

function packageFailureMessage(detail, failure) {
  const format = failure?.format === "package" ? "package" : `${humanize(failure?.format ?? "package").toLowerCase()} file`;
  const problem = {
    "permission-denied": "this browser blocked local file preparation",
    "missing-file": "a required generated file could not be loaded",
    "validation-incomplete": "file validation has not completed",
    "browser-failure": "the browser could not prepare or start the local file transfer",
  }[failure?.code] ?? "the file did not match its public manifest";
  const recovery = failure?.code === "permission-denied"
    ? "Allow downloads for this local Site, then choose Retry package validation, or return to the case."
    : "Choose Retry package validation, or return to the case.";
  return `The ${format} for ${detail.model.name} is unavailable because ${problem}. ${recovery} No download is available while this problem remains.`;
}

function renderPackage(detail, stage = "loading", failure = null) {
  const { model, manifest } = detail;
  $("package-back").textContent = "Back to case";
  $("retry-package").hidden = false;
  $("package-return").textContent = "Return to case";
  $("package-title").textContent = model.name;
  $("package-summary").textContent = "Choose Markdown when a person needs to read the case. Choose JSON when a tool needs to work with the same approved public record. Both files carry the same supported claims and limits.";
  $("package-context-content").innerHTML = packageContextMarkup(model);
  $("format-specifications").innerHTML = formatSpecificationsMarkup(manifest);
  $("package-boundary-content").innerHTML = boundaryMarkup(model);
  $("package-provenance-content").innerHTML = provenanceMarkup(model);
  $("package-limits-content").innerHTML = limitsMarkup(model);
  $("package-files-content").innerHTML = fileTableMarkup(manifest, stage, failure);
  $("package-recovery-actions").hidden = true;

  if (stage === "ready") {
    configureVerifiedDownloads(detail);
    $("package-ready").textContent = "Validated package files";
    $("package-ready").className = "status-label status-ready";
    $("package-status").textContent = `The readable and structured files for ${model.name} match their manifest filenames, byte counts, and SHA-256 values. Choose either verified file.`;
    return;
  }

  disableDownloadActions();
  if (stage === "error") {
    $("package-ready").textContent = failure?.code === "permission-denied" ? "Download permission blocked" : "Package validation blocked";
    $("package-ready").className = "status-label status-error";
    $("package-status").textContent = packageFailureMessage(detail, failure);
    $("package-recovery-actions").hidden = false;
    return;
  }

  $("package-ready").textContent = "Checking package files";
  $("package-ready").className = "status-label status-incomplete";
  $("package-status").textContent = `Validating the readable and structured files for ${model.name}. Downloads remain unavailable until both filenames, byte counts, and SHA-256 values match the manifest.`;
}

function showCaseError(item) {
  $("case-loading").hidden = true;
  $("case-content").hidden = false;
  $("open-package").disabled = true;
  $("case-context-content").innerHTML = `
    <p class="detail-summary">${esc(item.summary)}</p>
    <div class="load-error" role="alert">
      <h3>${esc(item.name)} package is unavailable</h3>
      <p><strong>Problem:</strong> The public package could not be loaded and checked.</p>
      <p><strong>Next:</strong> Choose Retry ${esc(item.name)} to run the public package validation again, or return to the catalog. No download is available while validation is unresolved.</p>
      <div class="recovery-actions"><button class="button" type="button" data-retry-case>Retry ${esc(item.name)}</button><button class="text-button" type="button" data-return-catalog>Return to catalog</button></div>
    </div>`;
  $("case-analysis-content").innerHTML = "";
  $("case-evidence-content").innerHTML = "";
}

function showUnavailableCase(slug, trigger) {
  const requested = /^[a-z0-9-]{1,120}$/.test(slug ?? "") ? slug : "unknown-case";
  state.activeCase = requested;
  state.activePackage = null;
  $("case-lane").textContent = "Unavailable";
  $("case-title").textContent = "Unavailable public case";
  $("case-source").textContent = `Requested case / ${requested}`;
  $("case-preview").innerHTML = "";
  $("case-loading").hidden = true;
  $("case-content").hidden = false;
  $("open-package").disabled = true;
  $("case-context-content").innerHTML = `
    <div class="load-error" role="alert">
      <h3>${esc(requested)} is not in the reviewed public catalog</h3>
      <p><strong>Problem:</strong> This case is missing, non-public, invalid, or no longer available.</p>
      <p><strong>Next:</strong> Choose Retry ${esc(requested)} to check the public catalog again, or return to the catalog. No package or download is exposed.</p>
      <div class="recovery-actions"><button class="button" type="button" data-retry-case>Retry ${esc(requested)}</button><button class="text-button" type="button" data-return-catalog>Return to catalog</button></div>
    </div>`;
  $("case-analysis-content").innerHTML = "";
  $("case-evidence-content").innerHTML = "";
  updateDialogCompareButton();
  setCaseView("case", false);
  openModal($("case-dialog"), trigger);
  writeUrl();
}

function showLocalPermissionDenied(slug, trigger) {
  revokeDownloadUrls();
  state.activeCase = slug;
  state.activePackage = null;
  $("package-back").textContent = "Back to catalog";
  $("package-title").textContent = "Private test case";
  $("package-summary").textContent = "This loopback-only route verifies that a non-public request exposes no package data or file.";
  $("package-context-content").innerHTML = `
    <div class="load-error" role="alert">
      <p><strong>Case:</strong> ${esc(slug)}</p>
      <p><strong>Problem:</strong> Access to non-public package data is denied.</p>
      <p><strong>Next:</strong> Return to the catalog. No private fixture was loaded.</p>
    </div>`;
  $("format-specifications").innerHTML = "<p>No readable or structured format is available because no public package was loaded.</p>";
  $("package-boundary-content").innerHTML = "<ul class=\"boundary-list\"><li><strong>Public boundary</strong><span>No public package data is exposed for this local sentinel.</span></li></ul>";
  $("package-provenance-content").innerHTML = "<p>Not available. No owner source was loaded.</p>";
  $("package-limits-content").innerHTML = "<p>This route proves the denial state only. It is not a real case or a source record.</p>";
  $("package-files-content").innerHTML = "<p>No files are available for this route.</p>";
  $("package-ready").textContent = "Download permission blocked";
  $("package-ready").className = "status-label status-error";
  $("package-status").textContent = `The package for ${slug} is unavailable because access to non-public package data is denied. Choose Return to catalog. No download is available and no private fixture was loaded.`;
  disableDownloadActions();
  $("retry-package").hidden = true;
  $("package-return").textContent = "Return to catalog";
  $("package-recovery-actions").hidden = false;
  setCaseView("package", false);
  $("dialog-context").textContent = "Permission boundary / Download package";
  openModal($("case-dialog"), trigger);
  writeUrl();
}

async function retryPackageValidation() {
  const detail = state.activePackage;
  if (!detail || detail.model.slug !== state.activeCase) return;
  renderPackage(detail, "loading");
  try {
    await verifyPackageFiles(detail);
    if (state.activePackage !== detail) return;
    renderPackage(detail, "ready");
    window.setTimeout(() => $("download-readable").focus(), 0);
  } catch (error) {
    if (state.activePackage !== detail) return;
    renderPackage(detail, "error", error);
    window.setTimeout(() => $("retry-package").focus(), 0);
  }
}

function returnToCatalog() {
  closeModal($("case-dialog"));
  window.setTimeout(() => $("search").focus(), 0);
}

function retryCatalog() {
  const next = new URL(window.location.href);
  next.searchParams.delete("test-state");
  next.searchParams.delete("test-format");
  window.location.assign(`${next.pathname}${next.search}${next.hash}`);
}

function setCaseView(view, focus = true) {
  const packageView = view === "package";
  state.activeView = packageView ? "package" : "case";
  $("case-screen").hidden = packageView;
  $("package-screen").hidden = !packageView;
  $("case-dialog").setAttribute("aria-labelledby", packageView ? "package-title" : "case-title");
  $("dialog-context").textContent = packageView ? "Public case / Download package" : "Public case / Case detail";
  writeUrl();
  if (focus) (packageView ? $("package-back") : $("open-package")).focus();
}

async function openCase(slug, trigger, requestedView = "case") {
  if (IS_LOCAL_TEST_HOST && slug === PRIVATE_TEST_CASE_SLUG && requestedView === "package") {
    showLocalPermissionDenied(slug, trigger);
    return;
  }
  const item = state.cases.find(candidate => candidate.slug === slug && candidate.publication_status === "public");
  if (!item) {
    showUnavailableCase(slug, trigger);
    return;
  }

  revokeDownloadUrls();
  state.activeCase = slug;
  state.activePackage = null;
  $("case-lane").textContent = LANE_LABELS[item.corpus_lane] ?? humanize(item.corpus_lane);
  $("case-title").textContent = item.name;
  $("case-source").textContent = `Public source study / ${item.source_name} / Studied ${formatDate(item.studied_at)}`;
  $("case-preview").innerHTML = previewMarkup(item, "detail");
  $("case-screen").classList.toggle("case-loading-state", TEST_STATE === "case-loading");
  $("case-loading").hidden = false;
  $("case-loading-message").textContent = `Loading the validated public package for ${item.name}. Downloads remain unavailable until validation finishes.`;
  $("case-content").hidden = true;
  $("open-package").disabled = true;
  updateDialogCompareButton();
  setCaseView("case", false);
  openModal($("case-dialog"), trigger);
  writeUrl();

  try {
    const detail = await loadPublicPackageMetadata(slug);
    if (state.activeCase !== slug) return;
    state.activePackage = detail;
    renderCase(detail.model);
    renderPackage(detail, "loading");
    if (requestedView === "package") setCaseView("package", false);
    try {
      await verifyPackageFiles(detail);
      if (state.activeCase !== slug || state.activePackage !== detail) return;
      renderPackage(detail, "ready");
    } catch (error) {
      if (state.activeCase !== slug || state.activePackage !== detail) return;
      renderPackage(detail, "error", error);
    }
  } catch (error) {
    if (state.activeCase !== slug) return;
    state.activePackage = null;
    showCaseError(item, error);
  }
}

function resetFilters() {
  state.lane = "";
  state.visibleLimit = INITIAL_CASE_LIMIT;
  $("search").value = "";
  for (const id of Object.keys(FACETS)) $(id).value = "";
  $("sort").value = "name";
  $("advanced-filters").open = false;
  render();
  $("search").focus();
}

function hydrateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  $("search").value = params.get("q") ?? "";
  const requestedLane = params.get("lane") ?? "";
  state.lane = Object.hasOwn(LANE_LABELS, requestedLane) ? requestedLane : "";
  for (const id of Object.keys(FACETS)) {
    const value = params.get(id) ?? "";
    if ([...$(id).options].some(option => option.value === value)) $(id).value = value;
  }
  const sort = params.get("sort") ?? "name";
  if ([...$("sort").options].some(option => option.value === sort)) $("sort").value = sort;
  for (const slug of (params.get("compare") ?? "").split(",").filter(Boolean).slice(0, 5)) {
    if (state.cases.some(item => item.slug === slug && item.publication_status === "public")) state.selected.add(slug);
  }
  const initialCase = params.get("case");
  const requestedView = params.get("view") === "package" || window.location.hash === "#download-package" ? "package" : "case";
  if (initialCase) {
    window.setTimeout(() => openCase(initialCase, null, requestedView), 0);
  } else if (state.selected.size >= 2) {
    window.setTimeout(() => openCompareDialog(null), 0);
  }
}

function restoreMethodRouteAfterCatalogRender() {
  if (window.location.hash !== "#method") return;
  const align = () => {
    if (window.location.hash === "#method") {
      const previousScrollBehavior = document.documentElement.style.scrollBehavior;
      document.documentElement.style.scrollBehavior = "auto";
      $("method").scrollIntoView({ behavior: "auto", block: "start" });
      document.documentElement.style.scrollBehavior = previousScrollBehavior;
    }
  };
  const alignAfterLayout = () => window.requestAnimationFrame(() => window.requestAnimationFrame(align));
  align();
  alignAfterLayout();
  if (document.readyState !== "complete") window.addEventListener("load", alignAfterLayout, { once: true });
  if (document.fonts?.ready) document.fonts.ready.then(alignAfterLayout);
}

function wireEvents() {
  $("search").addEventListener("input", () => { state.visibleLimit = INITIAL_CASE_LIMIT; render(); });
  $("clear-search").addEventListener("click", () => { $("search").value = ""; state.visibleLimit = INITIAL_CASE_LIMIT; render(); $("search").focus(); });
  for (const id of [...Object.keys(FACETS), "sort"]) $(id).addEventListener("change", () => { state.visibleLimit = INITIAL_CASE_LIMIT; render(); });
  $("reset-filters").addEventListener("click", resetFilters);
  $("empty-reset").addEventListener("click", resetFilters);
  $("retry-catalog").addEventListener("click", retryCatalog);
  $("load-more").addEventListener("click", () => {
    const previousCount = $("results").querySelectorAll(".case-row").length;
    state.visibleLimit += INITIAL_CASE_LIMIT;
    render();
    const firstNewCase = $("results").querySelectorAll(".case-row")[previousCount];
    firstNewCase?.querySelector("[data-open-case]")?.focus();
  });
  for (const button of document.querySelectorAll("[data-starter-lane]")) {
    button.addEventListener("click", () => {
      state.lane = button.dataset.starterLane;
      state.visibleLimit = INITIAL_CASE_LIMIT;
      $("search").value = "";
      for (const id of Object.keys(FACETS)) $(id).value = "";
      render();
      $("catalog-screen").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
      window.setTimeout(() => $("status").focus?.(), 0);
    });
  }
  $("clear-compare").addEventListener("click", () => { state.selected.clear(); render(); });
  $("open-compare").addEventListener("click", event => openCompareDialog(event.currentTarget));
  $("dialog-compare").addEventListener("click", () => toggleCompare(state.activeCase));
  $("open-package").addEventListener("click", () => setCaseView("package"));
  $("package-back").addEventListener("click", () => state.activePackage ? setCaseView("case") : returnToCatalog());
  $("retry-package").addEventListener("click", retryPackageValidation);
  $("package-return").addEventListener("click", () => state.activePackage ? setCaseView("case") : returnToCatalog());
  $("case-loading-return").addEventListener("click", returnToCatalog);
  $("case-context-content").addEventListener("click", event => {
    const retry = event.target.closest("[data-retry-case]");
    if (retry) {
      const slug = state.activeCase;
      state.packageCache.delete(slug);
      openCase(slug, retry, "case");
      return;
    }
    if (event.target.closest("[data-return-catalog]")) returnToCatalog();
  });

  $("lane-filters").addEventListener("click", event => {
    const button = event.target.closest("button[data-lane]");
    if (!button) return;
    state.lane = button.dataset.lane;
    state.visibleLimit = INITIAL_CASE_LIMIT;
    render();
    const activeButton = [...$("lane-filters").querySelectorAll("button[data-lane]")]
      .find(candidate => candidate.dataset.lane === state.lane);
    activeButton?.focus();
  });

  $("results").addEventListener("click", event => {
    const compareButton = event.target.closest("[data-compare]");
    if (compareButton) {
      toggleCompare(compareButton.dataset.compare, { restoreCatalogFocus: true });
      return;
    }
    const openButton = event.target.closest("[data-open-case]");
    if (openButton) openCase(openButton.dataset.openCase, openButton);
  });

  $("featured-studies").addEventListener("click", event => {
    const openButton = event.target.closest("[data-open-case]");
    if (openButton) openCase(openButton.dataset.openCase, openButton);
  });

  $("hero-study").addEventListener("click", event => {
    const openButton = event.target.closest("[data-open-case]");
    if (openButton) openCase(openButton.dataset.openCase, openButton);
  });

  $("comparison").addEventListener("click", event => {
    const button = event.target.closest("[data-remove-compare]");
    if (button) toggleCompare(button.dataset.removeCompare);
  });

  $("compare-table").addEventListener("click", event => {
    const button = event.target.closest("[data-open-case]");
    if (!button) return;
    closeModal($("compare-dialog"));
    window.setTimeout(() => openCase(button.dataset.openCase, null), 0);
  });

  for (const id of ["download-readable", "download-structured"]) {
    $(id).addEventListener("click", event => {
      const link = event.currentTarget;
      const format = id === "download-readable" ? "readable" : "structured";
      const detail = state.activePackage;
      if (link.getAttribute("aria-disabled") === "true") {
        event.preventDefault();
        if (detail) {
          const failure = new PackageFileError("validation has not completed", { code: "validation-incomplete", format });
          $("package-status").textContent = packageFailureMessage(detail, failure);
          $("package-recovery-actions").hidden = false;
        }
        return;
      }
      if (!detail || !link.href.startsWith("blob:") || !safeDownloadFilename(link.download, format)) {
        event.preventDefault();
        if (detail) renderPackage(detail, "error", new PackageFileError("the verified browser file is unavailable", { code: "browser-failure", format }));
        return;
      }
      if (TEST_STATE === "download-failure" && TEST_FORMAT === format) {
        event.preventDefault();
        renderPackage(detail, "error", new PackageFileError("the browser could not start the local file transfer", { code: "browser-failure", format }));
        return;
      }
      $("package-ready").textContent = "Download requested";
      $("package-ready").className = "status-label status-ready";
      $("package-status").textContent = `The Site asked your browser to download the verified ${format} file ${link.download} for ${detail.model.name}. If the file does not appear, retry this ${format} download or return to the case.`;
    });
  }

  for (const button of document.querySelectorAll("[data-close]")) {
    button.addEventListener("click", () => closeModal($(button.dataset.close)));
  }

  for (const dialog of document.querySelectorAll("dialog")) {
    dialog.addEventListener("click", event => {
      if (event.target === dialog) closeModal(dialog);
    });
    dialog.addEventListener("close", () => {
      if (dialog.id === "case-dialog") {
        revokeDownloadUrls();
        state.activeCase = null;
        state.activeView = "case";
        state.activePackage = null;
        $("case-screen").classList.remove("case-loading-state");
        $("case-screen").hidden = false;
        $("package-screen").hidden = true;
        writeUrl();
      }
      if (!document.querySelector("dialog[open]")) document.body.classList.remove("modal-open");
      const storedTarget = state.focusReturn.get(dialog.id);
      state.focusReturn.delete(dialog.id);
      const target = storedTarget instanceof HTMLElement && storedTarget !== document.body
        ? storedTarget
        : $("search");
      window.setTimeout(() => {
        if (target instanceof HTMLElement && document.contains(target) && !target.disabled) target.focus();
      }, 0);
    });
  }
}

async function start() {
  setInitialLoadingRows();
  wireEvents();
  try {
    if (TEST_STATE === "catalog-loading") await new Promise(() => {});
    if (TEST_STATE === "catalog-error") throw new Error("the catalog request failed the local validation test");
    const response = await fetch("generated-data/catalog/index.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.catalog = await response.json();
    if (state.catalog.visibility !== "public" || state.catalog.case_count !== 60) throw new Error("expected exactly 60 reviewed public cases");
    state.cases = state.catalog.cases.filter(item => item.publication_status === "public");
    if (state.cases.length !== 60) throw new Error("the public catalog count does not match its case records");
    $("case-count").textContent = String(state.catalog.case_count);
    $("public-count").textContent = String(state.catalog.case_count);
    fillSelect("platform", state.catalog.facets.platforms);
    fillSelect("product-type", state.catalog.facets.product_types);
    fillSelect("archetype", state.catalog.facets.archetypes);
    fillSelect("media", state.catalog.facets.media_strategy);
    fillSelect("density", state.catalog.facets.density);
    fillSelect("evidence", state.catalog.facets.evidence_quality);
    renderFeaturedStudies();
    hydrateFromUrl();
    render();
    restoreMethodRouteAfterCatalogRender();
  } catch (error) {
    $("results").innerHTML = "";
    $("results").setAttribute("aria-busy", "false");
    const localHint = IS_LOCAL_TEST_HOST ? ` ${LOCAL_CATALOG_REBUILD_HINT}` : "";
    $("status").textContent = `The public catalog is unavailable because the catalog request could not be loaded and checked. Choose Retry public catalog.${localHint} No case or download is available while the catalog is unavailable.`;
    $("catalog-recovery").hidden = false;
  }
}

start();
