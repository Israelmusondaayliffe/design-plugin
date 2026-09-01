"use strict";

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

const state = {
  cases: [],
  catalog: null,
  lane: "",
  selected: new Set(),
  activeCase: null,
  detailCache: new Map(),
};

const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, character => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  "\"": "&quot;",
  "'": "&#39;",
}[character]));

const humanize = value => VALUE_LABELS[String(value ?? "").toLowerCase()] ?? String(value ?? "")
  .replaceAll("-", " ")
  .replace(/\b\w/g, character => character.toUpperCase());

function formatDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? "")) return String(value ?? "Unknown");
  return new Intl.DateTimeFormat("en", { dateStyle: "long", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function validColor(value, fallback) {
  return /^#[0-9a-f]{3,8}$/i.test(value ?? "") ? value : fallback;
}

function validRadius(value) {
  return /^\d+(?:\.\d+)?(?:px|rem|em|%)$/.test(value ?? "") ? value : "8px";
}

function setInitialLoadingCards() {
  const template = $("loading-template");
  for (let index = 0; index < 6; index += 1) {
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
    `<button type="button" data-lane="" aria-pressed="${state.lane === ""}"><span>All</span><small>${state.cases.length}</small></button>`,
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

function previewMarkup(item, size = "card") {
  const primary = validColor(item.preview?.primary, "#171717");
  const secondary = validColor(item.preview?.secondary, "#ff5a36");
  const radius = validRadius(item.preview?.radius);
  const seed = [...item.slug].reduce((total, character) => total + character.charCodeAt(0), 0);
  const variant = item.corpus_lane === "mobile"
    ? 4
    : item.corpus_lane === "brand-editorial-portfolio-marketing"
      ? [1, 5][seed % 2]
      : item.corpus_lane === "commerce-media-content-heavy"
        ? [2, 3][seed % 2]
        : item.corpus_lane === "onboarding-forms-settings-flows"
          ? 0
          : [0, 2][seed % 2];
  const label = size === "detail" ? `<span>${esc(item.source_name)}</span>` : "";
  return `<div class="abstract-preview preview-${variant} ${size === "detail" ? "preview-detail" : ""}" style="--case-a:${primary};--case-b:${secondary};--case-radius:${radius}">${label}<i></i><i></i><i></i><i></i><i></i></div>`;
}

function caseCard(item, index) {
  const selected = state.selected.has(item.slug);
  return `
    <article class="case-card" style="--card-index:${index}">
      <button class="preview-button" type="button" data-open-case="${esc(item.slug)}" aria-label="Open ${esc(item.name)} case study">
        ${previewMarkup(item)}
      </button>
      <div class="case-meta">
        <span>${esc(LANE_LABELS[item.corpus_lane] ?? humanize(item.corpus_lane))}</span>
        <span>${esc(humanize(item.evidence_quality))} evidence quality</span>
      </div>
      <button class="case-title-button" type="button" data-open-case="${esc(item.slug)}"><h3>${esc(item.name)}</h3></button>
      <p>${esc(item.summary)}</p>
      <ul class="trait-list" aria-label="Signature traits">${item.signature_traits.slice(0, 3).map(trait => `<li>${esc(trait)}</li>`).join("")}</ul>
      <div class="card-actions">
        <button class="open-link" type="button" data-open-case="${esc(item.slug)}">Study case <span aria-hidden="true">↗</span></button>
        <button class="compare-toggle" type="button" data-compare="${esc(item.slug)}" aria-pressed="${selected}" ${!selected && state.selected.size >= 5 ? "disabled" : ""}>
          <span aria-hidden="true">${selected ? "−" : "+"}</span>${selected ? "Selected" : "Compare"}
        </button>
      </div>
    </article>`;
}

function activeFilterCount() {
  return Number(Boolean(state.lane)) + Number(Boolean(readFilter("search").trim())) + Object.keys(FACETS).filter(id => readFilter(id)).length;
}

function updateFilterSummary() {
  const count = activeFilterCount();
  $("active-filter-count").hidden = count === 0;
  $("active-filter-count").textContent = String(count);
  $("clear-search").hidden = readFilter("search").length === 0;
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
  const queryString = params.toString();
  window.history.replaceState({}, "", `${window.location.pathname}${queryString ? `?${queryString}` : ""}${window.location.hash}`);
}

function render() {
  const visible = sorted(state.cases.filter(matches));
  $("results").innerHTML = visible.map(caseCard).join("");
  $("results").setAttribute("aria-busy", "false");
  $("status").textContent = `${visible.length} of ${state.cases.length} reviewed cases`;
  $("empty-state").hidden = visible.length !== 0;
  renderLaneFilters();
  renderCompareTray();
  updateFilterSummary();
  writeUrl();
}

function toggleCompare(slug) {
  if (state.selected.has(slug)) {
    state.selected.delete(slug);
  } else if (state.selected.size<5) {
    state.selected.add(slug);
  }
  render();
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
    ["Platform", item => taxonomyValue(item.platforms)],
    ["Product type", item => taxonomyValue(item.product_types)],
    ["Archetype", item => taxonomyValue(item.archetypes)],
    ["Density", item => taxonomyValue(item.density)],
    ["Media strategy", item => taxonomyValue(item.media_strategy)],
    ["Signature traits", item => proseValue(item.signature_traits)],
    ["Best for", item => proseValue(item.best_for)],
    ["Avoid for", item => proseValue(item.avoid_for)],
  ];
  $("compare-table").innerHTML = `
    <table>
      <thead><tr><th scope="col">Attribute</th>${items.map(item => `<th scope="col">${esc(item.name)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(([label, getter]) => `<tr><th scope="row">${label}</th>${items.map(item => `<td>${esc(getter(item))}</td>`).join("")}</tr>`).join("")}</tbody>
    </table>`;
}

function openCompareDialog() {
  if (state.selected.size < 2) return;
  renderCompareDialog();
  openModal($("compare-dialog"));
}

function openModal(dialog) {
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  document.body.classList.add("modal-open");
}

function closeModal(dialog) {
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
  if (!document.querySelector("dialog[open]")) document.body.classList.remove("modal-open");
}

function updateDialogCompareButton() {
  const selected = state.selected.has(state.activeCase);
  $("dialog-compare").textContent = selected ? "Remove from comparison" : "Add to comparison";
  $("dialog-compare").setAttribute("aria-pressed", String(selected));
  $("dialog-compare").disabled = !selected && state.selected.size >= 5;
}

function definitionList(item) {
  const definitions = [
    ["Platform", taxonomyValue(item.platforms)],
    ["Product type", taxonomyValue(item.product_types)],
    ["Archetype", taxonomyValue(item.archetypes)],
    ["Task stage", taxonomyValue(item.journey)],
    ["Density", taxonomyValue(item.density)],
    ["Interaction", taxonomyValue(item.interaction_complexity)],
    ["Color mode", taxonomyValue(item.color_modes)],
    ["Confidence", taxonomyValue(item.confidence)],
  ];
  return `<dl class="case-definitions">${definitions.map(([term, value]) => `<div><dt>${term}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>`;
}

function listBlock(title, values, tone = "") {
  return `<section class="decision-block ${tone}"><h3>${esc(title)}</h3><ul>${values.map(value => `<li>${esc(value)}</li>`).join("")}</ul></section>`;
}

function inlineMarkdown(value) {
  return esc(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function markdownToHtml(markdown) {
  const lines = String(markdown ?? "").replace(/\r/g, "").split("\n");
  const output = [];
  let list = null;
  const closeList = () => {
    if (list) output.push(`</${list}>`);
    list = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      continue;
    }
    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      closeList();
      const level = Math.min(heading[1].length + 1, 5);
      output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    const unordered = /^[-*]\s+(.+)$/.exec(line);
    if (unordered) {
      if (list !== "ul") {
        closeList();
        list = "ul";
        output.push("<ul>");
      }
      output.push(`<li>${inlineMarkdown(unordered[1])}</li>`);
      continue;
    }
    const ordered = /^\d+[.)]\s+(.+)$/.exec(line);
    if (ordered) {
      if (list !== "ol") {
        closeList();
        list = "ol";
        output.push("<ol>");
      }
      output.push(`<li>${inlineMarkdown(ordered[1])}</li>`);
      continue;
    }
    closeList();
    output.push(`<p>${inlineMarkdown(line)}</p>`);
  }
  closeList();
  return output.join("");
}

function renderEvidence(evidence, source) {
  const items = evidence?.items ?? [];
  const ownerUrl = source?.owner_url ?? state.cases.find(item => item.slug === state.activeCase)?.source_url;
  const retrieved = formatDate(source?.retrieved_at);
  return `
    <div class="evidence-intro">
      <p>${items.length} recorded claims. Source retrieved ${esc(retrieved)}. Observations describe public source material. Inferences and recommendations are corpus analysis or editorial judgment.</p>
      <a class="button" href="${esc(ownerUrl)}" target="_blank" rel="noopener noreferrer">Visit owner source <span aria-hidden="true">↗</span></a>
    </div>
    <ol class="evidence-list">${items.map(item => `
      <li>
        <div><span class="evidence-class ${esc(item.class)}">${esc(humanize(item.class))}</span><span>${esc(humanize(item.confidence))} confidence</span></div>
        <p>${esc(item.claim)}</p>
        <small>${esc(item.locator)}</small>
      </li>`).join("")}</ol>`;
}

async function loadCaseDetail(slug) {
  if (state.detailCache.has(slug)) return state.detailCache.get(slug);
  const root = `generated-data/cases/${encodeURIComponent(slug)}`;
  const requests = ["DESIGN.md", "evidence.json", "source.json"].map(async file => {
    const response = await fetch(`${root}/${file}`);
    if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
    return file.endsWith(".json") ? response.json() : response.text();
  });
  const [analysis, evidence, source] = await Promise.all(requests);
  const detail = { analysis, evidence, source };
  state.detailCache.set(slug, detail);
  return detail;
}

async function openCase(slug) {
  const item = state.cases.find(candidate => candidate.slug === slug);
  if (!item) return;
  state.activeCase = slug;
  $("case-lane").textContent = LANE_LABELS[item.corpus_lane] ?? humanize(item.corpus_lane);
  $("case-title").textContent = item.name;
  $("case-source").textContent = `Source study: ${item.source_name} / Retrieved ${formatDate(item.studied_at)}`;
  $("case-preview").innerHTML = previewMarkup(item, "detail");
  $("panel-overview").innerHTML = `
    <p class="detail-summary">${esc(item.summary)}</p>
    ${definitionList(item)}
    <div class="decision-grid">
      ${listBlock("Signature relationships", item.signature_traits)}
      ${listBlock("Useful when", item.best_for, "positive")}
      ${listBlock("Avoid when", item.avoid_for, "warning")}
    </div>
    ${item.unknowns?.length ? listBlock("Known unknowns", item.unknowns, "unknown") : ""}`;
  $("panel-analysis").innerHTML = `<p class="loading-line">Loading original analysis...</p>`;
  $("panel-evidence").innerHTML = `<p class="loading-line">Loading evidence...</p>`;
  updateDialogCompareButton();
  activateTab("tab-overview", false);
  openModal($("case-dialog"));
  writeUrl();

  try {
    const detail = await loadCaseDetail(slug);
    if (state.activeCase !== slug) return;
    $("case-source").textContent = `Source study: ${item.source_name} / Retrieved ${formatDate(detail.source.retrieved_at)}`;
    $("panel-analysis").innerHTML = markdownToHtml(detail.analysis);
    $("panel-evidence").innerHTML = renderEvidence(detail.evidence, detail.source);
  } catch (error) {
    const message = `<div class="load-error"><h3>Detailed record unavailable</h3><p>${esc(error.message)}</p><p>The catalog summary is still available.</p></div>`;
    $("panel-analysis").innerHTML = message;
    $("panel-evidence").innerHTML = message;
  }
}

function activateTab(tabId, focus = true) {
  const tabs = [...$("case-dialog").querySelectorAll("[role=tab]")];
  for (const tab of tabs) {
    const active = tab.id === tabId;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    $(tab.getAttribute("aria-controls")).hidden = !active;
    if (active && focus) tab.focus();
  }
}

function resetFilters() {
  state.lane = "";
  $("search").value = "";
  for (const id of Object.keys(FACETS)) $(id).value = "";
  $("sort").value = "name";
  render();
  $("search").focus();
}

function hydrateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  $("search").value = params.get("q") ?? "";
  state.lane = params.get("lane") ?? "";
  for (const id of Object.keys(FACETS)) {
    const value = params.get(id) ?? "";
    if ([...$(id).options].some(option => option.value === value)) $(id).value = value;
  }
  const sort = params.get("sort") ?? "name";
  if ([...$("sort").options].some(option => option.value === sort)) $("sort").value = sort;
  for (const slug of (params.get("compare") ?? "").split(",").filter(Boolean).slice(0, 5)) {
    if (state.cases.some(item => item.slug === slug)) state.selected.add(slug);
  }
  const initialCase = params.get("case");
  if (initialCase && state.cases.some(item => item.slug === initialCase)) window.setTimeout(() => openCase(initialCase), 0);
}

function wireEvents() {
  $("search").addEventListener("input", render);
  $("clear-search").addEventListener("click", () => { $("search").value = ""; render(); $("search").focus(); });
  for (const id of [...Object.keys(FACETS), "sort"]) $(id).addEventListener("change", render);
  $("reset-filters").addEventListener("click", resetFilters);
  $("empty-reset").addEventListener("click", resetFilters);
  $("clear-compare").addEventListener("click", () => { state.selected.clear(); render(); });
  $("open-compare").addEventListener("click", openCompareDialog);
  $("dialog-compare").addEventListener("click", () => toggleCompare(state.activeCase));

  $("lane-filters").addEventListener("click", event => {
    const button = event.target.closest("button[data-lane]");
    if (!button) return;
    state.lane = button.dataset.lane;
    render();
  });

  $("results").addEventListener("click", event => {
    const openButton = event.target.closest("[data-open-case]");
    const compareButton = event.target.closest("[data-compare]");
    if (openButton) openCase(openButton.dataset.openCase);
    if (compareButton) toggleCompare(compareButton.dataset.compare);
  });

  $("comparison").addEventListener("click", event => {
    const button = event.target.closest("[data-remove-compare]");
    if (button) toggleCompare(button.dataset.removeCompare);
  });

  for (const button of document.querySelectorAll("[data-close]")) {
    button.addEventListener("click", () => closeModal($(button.dataset.close)));
  }

  for (const dialog of document.querySelectorAll("dialog")) {
    dialog.addEventListener("click", event => {
      if (event.target === dialog) closeModal(dialog);
    });
    dialog.addEventListener("close", () => {
      if (dialog.id === "case-dialog") {
        state.activeCase = null;
        writeUrl();
      }
      if (!document.querySelector("dialog[open]")) document.body.classList.remove("modal-open");
    });
  }

  const tabs = [...$("case-dialog").querySelectorAll("[role=tab]")];
  for (const tab of tabs) {
    tab.addEventListener("click", () => activateTab(tab.id));
    tab.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const current = tabs.indexOf(tab);
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      activateTab(tabs[next].id);
    });
  }
}

async function start() {
  setInitialLoadingCards();
  wireEvents();
  try {
    const response = await fetch("generated-data/catalog/index.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.catalog = await response.json();
    state.cases = state.catalog.cases;
    $("case-count").textContent = String(state.catalog.case_count);
    fillSelect("platform", state.catalog.facets.platforms);
    fillSelect("product-type", state.catalog.facets.product_types);
    fillSelect("archetype", state.catalog.facets.archetypes);
    fillSelect("media", state.catalog.facets.media_strategy);
    fillSelect("density", state.catalog.facets.density);
    fillSelect("evidence", state.catalog.facets.evidence_quality);
    hydrateFromUrl();
    render();
  } catch (error) {
    $("results").innerHTML = "";
    $("results").setAttribute("aria-busy", "false");
    $("status").textContent = `Catalog unavailable: ${error.message}. Rebuild the public catalog data using the command in site/README.md, then reload this page.`;
  }
}

start();
