/* ═══ Reconnect — Frontend App ═══ */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const el = (tag, attrs = {}, ...children) => {
  const n = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") n.className = v;
    else if (k === "style" && typeof v === "string") n.style.cssText = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  });
  children.flat().forEach(ch => {
    if (ch == null) return;
    n.appendChild(typeof ch === "string" ? document.createTextNode(ch) : ch);
  });
  return n;
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.text();
}

function showModal(title, body) {
  $("#modalTitle").textContent = title;
  $("#modalBody").textContent = typeof body === "string" ? body : JSON.stringify(body, null, 2);
  $("#modal").showModal();
}

// ─── State ───────────────────────────────────────────────────────────────────
let STATE = { cases: [], currentCaseId: null, currentCase: null };

// ─── Encouragement messages based on progress ─────────────────────────────
const ENCOURAGEMENTS = [
  { min: 0, msg: "Every journey starts with a single step. You've begun — that takes courage." },
  { min: 1, msg: "You've started gathering information. That's real progress." },
  { min: 3, msg: "Three pieces of evidence — you're building a solid foundation." },
  { min: 5, msg: "Five items gathered. You're being thorough, and that matters." },
  { min: 10, msg: "Ten pieces of evidence. You're doing meaningful, careful work." },
  { min: 20, msg: "Twenty items. This is a serious, well-documented search. Be proud of your diligence." },
];

function getEncouragement(count) {
  let best = ENCOURAGEMENTS[0];
  for (const e of ENCOURAGEMENTS) {
    if (count >= e.min) best = e;
  }
  return best.msg;
}

// ─── Category labels ──────────────────────────────────────────────────────
const CATEGORY_LABELS = {
  death_records: "🏛️ Death Records & Indexes",
  obituaries: "📰 Obituaries",
  official_records: "⚖️ Official & Government Records",
  people_search: "🔍 People Search & Public Records",
  missing_persons: "🔎 Missing Persons Databases",
  unclaimed_assets: "💰 Unclaimed Property & Assets",
  social_media: "💬 Social Media & Online Presence",
  genealogy: "🌳 Genealogy & Family Connections",
  property: "🏠 Property & Voter Records",
  medical: "🏥 Medical & Benefits",
  news: "📰 News & Media",
  relationship_search: "👥 Relationship Cross-References",
};

const CATEGORY_ORDER = [
  "death_records", "obituaries", "official_records", "people_search",
  "missing_persons", "unclaimed_assets", "social_media", "genealogy",
  "property", "medical", "news", "relationship_search"
];

// ═══════════════════════════════════════════════════════════════════════════
// TABS & NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════
function setActiveTab(tab) {
  $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  ["overview","search","evidence","stateinfo","tasks","documents","graph","audit"].forEach(k => {
    $(`#panel-${k}`).classList.toggle("hidden", k !== tab);
  });
}

function showWelcome() {
  $("#welcomeScreen").classList.remove("hidden");
  $("#caseView").classList.add("hidden");
}

function showCaseView() {
  $("#welcomeScreen").classList.add("hidden");
  $("#caseView").classList.remove("hidden");
}

// ═══════════════════════════════════════════════════════════════════════════
// WIZARD (Guided First Steps)
// ═══════════════════════════════════════════════════════════════════════════
let wizardStep = 1;
const WIZARD_STEPS = 4;

function openWizard() {
  wizardStep = 1;
  // Reset fields
  $("#wiz-name").value = "";
  $("#wiz-title").value = "";
  $("#wiz-dob").value = "";
  $("#wiz-aliases").value = "";
  $("#wiz-location").value = "";
  $("#wiz-relatives").value = "";
  $("#wiz-notes").value = "";
  updateWizard();
  $("#wizardOverlay").classList.remove("hidden");
}

function closeWizard() {
  $("#wizardOverlay").classList.add("hidden");
}

function updateWizard() {
  // Update step visibility
  $$(".wizard-step").forEach(s => s.classList.toggle("active", +s.dataset.step === wizardStep));
  // Update dots
  const dots = $("#wizardDots");
  dots.innerHTML = "";
  for (let i = 1; i <= WIZARD_STEPS; i++) {
    const dot = el("div", { class: `wizard-dot ${i === wizardStep ? "active" : ""} ${i < wizardStep ? "done" : ""}` });
    dots.appendChild(dot);
  }
  // Update buttons
  $("#wizBack").style.visibility = wizardStep === 1 ? "hidden" : "visible";
  $("#wizNext").textContent = wizardStep === WIZARD_STEPS ? "Create case & start searching →" : "Next →";
}

async function wizardFinish() {
  const name = $("#wiz-name").value.trim();
  const title = $("#wiz-title").value.trim() || `Finding ${name}`;
  if (!name) { alert("Please enter a name to search for."); wizardStep = 1; updateWizard(); return; }

  const payload = {
    title,
    subject_name: name,
    dob: $("#wiz-dob").value.trim() || null,
    aliases: $("#wiz-aliases").value.trim() || null,
    last_known_locations: $("#wiz-location").value.trim() || null,
    relatives: $("#wiz-relatives").value.trim() || null,
    notes: $("#wiz-notes").value.trim() || null,
  };

  closeWizard();
  const created = await api("/cases", { method: "POST", body: JSON.stringify(payload) });
  await loadCases();
  await selectCase(created.id);
  // Auto-run search
  await runSearch(created.id);
  setActiveTab("search");
}

// Wizard event handlers
$("#wizNext").addEventListener("click", () => {
  if (wizardStep < WIZARD_STEPS) { wizardStep++; updateWizard(); }
  else wizardFinish();
});
$("#wizBack").addEventListener("click", () => {
  if (wizardStep > 1) { wizardStep--; updateWizard(); }
});

// ═══════════════════════════════════════════════════════════════════════════
// CASES
// ═══════════════════════════════════════════════════════════════════════════
async function loadCases() {
  STATE.cases = await api("/cases");
  renderCaseList();
  if (!STATE.currentCaseId && STATE.cases.length) {
    await selectCase(STATE.cases[0].id);
  } else if (STATE.currentCaseId) {
    const still = STATE.cases.find(c => c.id === STATE.currentCaseId);
    if (still) await selectCase(STATE.currentCaseId, { skipList: true });
    else if (STATE.cases.length) await selectCase(STATE.cases[0].id);
    else showWelcome();
  } else {
    showWelcome();
  }
}

function renderCaseList() {
  const list = $("#caseList");
  list.innerHTML = "";
  STATE.cases.forEach(c => {
    list.appendChild(el("div", { class: `case-item ${c.id === STATE.currentCaseId ? "active" : ""}`, onclick: () => selectCase(c.id) },
      el("div", { class: "case-title" }, c.title),
      el("div", { class: "case-sub" }, `${c.subject_name}${c.dob ? ` · ${c.dob}` : ""}`)
    ));
  });
}

async function selectCase(caseId, opts = {}) {
  STATE.currentCaseId = caseId;
  STATE.currentCase = await api(`/cases/${caseId}`);
  $("#currentCasePill").textContent = STATE.currentCase.title;
  $("#currentCaseMeta").textContent = `${STATE.currentCase.subject_name} · ${STATE.currentCase.id}`;
  if (!opts.skipList) renderCaseList();
  showCaseView();
  await refreshAllPanels();
}

async function refreshAllPanels() {
  await Promise.allSettled([
    renderOverview(), renderSearch(), renderEvidence(),
    renderStateInfo(), renderTasks(), renderDocuments(),
    renderGraph(), renderAudit(),
  ]);
}

function requireCase() {
  if (!STATE.currentCaseId) throw new Error("Select a case first.");
  return STATE.currentCaseId;
}

// ═══════════════════════════════════════════════════════════════════════════
// OVERVIEW (with progress tracking and encouragement)
// ═══════════════════════════════════════════════════════════════════════════
async function renderOverview() {
  const caseId = requireCase();
  const c = STATE.currentCase || await api(`/cases/${caseId}`);
  const panel = $("#panel-overview");
  panel.innerHTML = "";

  // Fetch counts for progress
  const [evidence, events, searches, tasks] = await Promise.all([
    api(`/cases/${caseId}/evidence`),
    api(`/cases/${caseId}/timeline`),
    api(`/cases/${caseId}/search-runs`),
    api(`/cases/${caseId}/tasks`),
  ]);

  const totalItems = evidence.length + events.length + searches.length;
  const progressPct = Math.min(100, Math.round((totalItems / 15) * 100));

  // Progress card
  const progressCard = el("div", { class: "card card-warm" },
    el("div", { class: "card-title" }, "Your progress"),
    el("div", { class: "row", style: "justify-content:space-between" },
      el("span", { class: "muted" }, `${evidence.length} evidence · ${searches.length} searches · ${events.length} events`),
      el("span", { class: "badge" }, `${progressPct}%`),
    ),
    el("div", { class: "progress-bar" }, el("div", { class: "progress-fill", style: `width:${progressPct}%` })),
    el("div", { class: "encouragement" }, getEncouragement(totalItems)),
  );

  // Case details
  const details = el("div", { class: "card" },
    el("div", { class: "card-title" }, "Who you're looking for"),
    kv("Name", c.subject_name),
    kv("DOB", c.dob || "Unknown"),
    kv("Also known as", c.aliases || "None listed"),
    kv("Last known location", c.last_known_locations || "Unknown"),
    kv("Connected people", c.relatives || "None listed"),
    c.notes ? kv("Your notes", c.notes) : null,
    el("div", { class: "row", style: "margin-top:12px" },
      el("button", { class: "btn secondary", onclick: () => openCaseEditor(c) }, "Edit details"),
      el("button", { class: "btn danger", onclick: () => deleteCase(caseId) }, "Delete case"),
    ),
  );

  // Suggested next steps
  const nextSteps = el("div", { class: "card card-info" },
    el("div", { class: "card-title" }, "💡 Suggested next steps"),
  );
  if (searches.length === 0) {
    nextSteps.appendChild(el("div", { style: "margin-bottom:8px" },
      el("button", { class: "btn warm", onclick: () => { setActiveTab("search"); renderSearch(); } }, "Run your first search →"),
      el("span", { class: "muted", style: "margin-left:10px" }, "This will generate links to 40+ databases tailored to your case."),
    ));
  }
  if (evidence.length === 0) {
    nextSteps.appendChild(el("div", { style: "margin-bottom:8px" },
      el("button", { class: "btn secondary", onclick: () => setActiveTab("evidence") }, "Add evidence →"),
      el("span", { class: "muted", style: "margin-left:10px" }, "Save links, notes, and files as you find them."),
    ));
  }
  if (c.last_known_locations) {
    nextSteps.appendChild(el("div", { style: "margin-bottom:8px" },
      el("button", { class: "btn secondary", onclick: () => setActiveTab("stateinfo") }, "Check state records →"),
      el("span", { class: "muted", style: "margin-left:10px" }, "See exactly how to request official records for their last known state."),
    ));
  }
  // Relationship suggestions
  if (c.relatives) {
    const rels = c.relatives.split(",").map(r => r.trim()).filter(r => r.length > 2);
    if (rels.length > 0) {
      nextSteps.appendChild(el("div", { class: "card-warm", style: "padding:10px 14px; border-radius:6px; margin-top:8px" },
        el("strong", {}, "👥 Relationship tip: "),
        el("span", {}, `You listed ${rels.length} connected people. When you run a search, Reconnect will automatically cross-reference each of them — relatives often appear in shared obituaries, property records, and court documents.`),
      ));
    }
  }

  // Quick actions
  const quickCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, "Quick actions"),
    el("div", { class: "row" },
      el("button", { class: "btn", onclick: () => window.open(`/cases/${caseId}/export`, "_blank") }, "📄 Export PDF"),
      el("button", { class: "btn secondary", onclick: () => runRagSummary(caseId) }, "🤖 AI Summary"),
    ),
  );

  // Tags
  const tagCard = await renderTagsCard(caseId);
  // Timeline
  const timelineCard = await renderTimelineCard(caseId);

  panel.appendChild(progressCard);
  panel.appendChild(el("div", { class: "grid2" },
    el("div", {}, details, quickCard),
    el("div", {}, nextSteps, tagCard, timelineCard),
  ));
}

function kv(k, v) {
  if (v == null) return null;
  return el("div", { class: "kv" }, el("div", { class: "k" }, k), el("div", { class: "v" }, v || ""));
}

// ═══════════════════════════════════════════════════════════════════════════
// SEARCH HUB (categorized, with guidance and priority)
// ═══════════════════════════════════════════════════════════════════════════
async function renderSearch() {
  const caseId = requireCase();
  const c = STATE.currentCase;
  const panel = $("#panel-search");
  panel.innerHTML = "";

  // Search form
  const form = el("div", { class: "card" },
    el("div", { class: "card-title" }, "🔍 Search Hub"),
    el("div", { class: "muted", style: "margin-bottom:12px" }, "Generate targeted links to 40+ databases. Reconnect doesn't scrape — you click through and search each source yourself, keeping everything legal and safe."),
    el("div", { class: "grid2" },
      el("div", {},
        el("label", { class: "label" }, "Full name"),
        el("input", { class: "input", id: "sqName", value: c?.subject_name || "" }),
        el("label", { class: "label" }, "Date of birth"),
        el("input", { class: "input", id: "sqDob", value: c?.dob || "" }),
        el("label", { class: "label" }, "Last known location"),
        el("input", { class: "input", id: "sqLoc", value: (c?.last_known_locations || "").split(",")[0]?.trim() || "" }),
      ),
      el("div", {},
        el("label", { class: "label" }, "Relatives / connected people"),
        el("input", { class: "input", id: "sqRel", value: c?.relatives || "" }),
        el("label", { class: "label" }, "Aliases"),
        el("input", { class: "input", id: "sqAliases", value: c?.aliases || "" }),
        el("button", { class: "btn warm large block", style: "margin-top:24px", onclick: () => runSearch(caseId) }, "🔍 Generate search links"),
      ),
    ),
  );
  panel.appendChild(form);

  // Previous runs
  const runs = await api(`/cases/${caseId}/search-runs`);
  if (runs.length > 0) {
    const latest = runs[0];
    const results = latest.results || [];
    if (results.length > 0) {
      renderSearchResults(panel, results);
    }
  }
}

function renderSearchResults(container, results) {
  // Group by category
  const grouped = {};
  for (const r of results) {
    const cat = r.category || "other";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(r);
  }

  const wrapper = el("div", {});
  wrapper.appendChild(el("div", { class: "card card-success", style: "margin-top:12px" },
    el("strong", {}, `✅ ${results.length} search links generated across ${Object.keys(grouped).length} categories. `),
    el("span", {}, "Start with the essential (teal) sources, then work through the important (amber) ones. Click each link to search."),
  ));

  for (const cat of CATEGORY_ORDER) {
    if (!grouped[cat]) continue;
    const items = grouped[cat];
    // Sort by priority
    items.sort((a, b) => (a.priority || 3) - (b.priority || 3));

    const section = el("div", { class: "source-category" },
      el("div", { class: "source-category-title" }, CATEGORY_LABELS[cat] || cat),
    );

    for (const item of items) {
      const card = el("div", { class: `source-card priority-${item.priority || 3}` },
        el("div", { class: "source-header" },
          el("span", { class: "source-name" }, item.source),
          el("div", { class: "row" },
            item.priority === 1 ? el("span", { class: "badge" }, "Essential") :
            item.priority === 2 ? el("span", { class: "badge warm" }, "Important") : null,
            el("a", { class: "btn", href: item.url, target: "_blank", style: "font-size:12px; padding:5px 12px;" }, "Open →"),
          ),
        ),
        el("div", { class: "source-notes" }, item.notes || ""),
        item.guidance ? el("div", { class: "source-guidance" }, item.guidance) : null,
      );
      section.appendChild(card);
    }
    wrapper.appendChild(section);
  }
  container.appendChild(wrapper);
}

async function runSearch(caseId) {
  const payload = {
    full_name: ($("#sqName")?.value || STATE.currentCase?.subject_name || "").trim(),
    dob: ($("#sqDob")?.value || STATE.currentCase?.dob || "").trim() || null,
    location: ($("#sqLoc")?.value || (STATE.currentCase?.last_known_locations || "").split(",")[0] || "").trim() || null,
    relatives: ($("#sqRel")?.value || STATE.currentCase?.relatives || "").trim() || null,
    local_only: false,
  };
  const run = await api(`/cases/${caseId}/search`, { method: "POST", body: JSON.stringify(payload) });
  await renderSearch();
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE-SPECIFIC RECORDS
// ═══════════════════════════════════════════════════════════════════════════
async function renderStateInfo() {
  const caseId = requireCase();
  const c = STATE.currentCase;
  const panel = $("#panel-stateinfo");
  panel.innerHTML = "";

  const loc = c?.last_known_locations || "";
  const stateAbbrev = extractStateAbbrev(loc);

  panel.appendChild(el("div", { class: "card" },
    el("div", { class: "card-title" }, "🏛️ State Vital Records Guide"),
    el("div", { class: "muted" }, "Enter a state to see exactly how to request official death certificates, marriage records, and more."),
    el("div", { class: "row", style: "margin-top:12px" },
      el("input", { class: "input", id: "stateInput", placeholder: "State abbreviation (e.g., AZ, CA, TX)", value: stateAbbrev, style: "max-width:260px" }),
      el("button", { class: "btn warm", onclick: () => loadStateInfo() }, "Look up state records"),
    ),
  ));

  if (stateAbbrev) {
    await loadStateInfo(stateAbbrev);
  }
}

async function loadStateInfo(abbrev) {
  const st = abbrev || ($("#stateInput")?.value || "").trim().toUpperCase();
  if (!st || st.length < 2) return;
  try {
    const info = await api(`/states/${st}`);
    const container = $("#panel-stateinfo");
    // Remove previous state cards
    container.querySelectorAll(".state-card").forEach(c => c.remove());

    if (info.error) {
      container.appendChild(el("div", { class: "state-card" }, el("div", {}, info.error)));
      return;
    }

    const card = el("div", { class: "state-card" },
      el("h3", { style: "margin-bottom:8px; font-family:var(--font-ui);" }, `${info.state} — ${info.office}`),
      el("div", { class: "row", style: "margin-bottom:12px; gap:16px;" },
        el("span", {}, `💵 Fee: ${info.fee}`),
        el("span", {}, `⏱️ Processing: ${info.processing}`),
        el("span", {}, info.online_available ? "✅ Online ordering available" : "📫 Mail-in only"),
      ),
      el("div", { style: "margin-bottom:12px" },
        el("a", { href: info.url, target: "_blank", class: "btn warm" }, "Visit official website →"),
        el("span", { class: "muted", style: "margin-left:10px" }, `Phone: ${info.phone}`),
      ),
      el("div", { style: "margin-bottom:12px; font-size:14px; color:var(--text-light)" }, info.coverage_notes),
    );

    // Steps
    const stepsList = el("ol", { class: "state-steps" });
    (info.steps || []).forEach(s => {
      // Strip the leading "1. " etc from steps since the CSS counter handles it
      const text = s.replace(/^\d+\.\s*/, "");
      stepsList.appendChild(el("li", {}, text));
    });
    card.appendChild(el("h4", { style: "margin: 16px 0 8px; font-family:var(--font-ui);" }, "Steps to request records:"));
    card.appendChild(stepsList);

    // Tips
    if (info.tips && info.tips.length) {
      card.appendChild(el("h4", { style: "margin: 16px 0 8px; font-family:var(--font-ui);" }, "💡 Tips:"));
      const tipsList = el("div", {});
      info.tips.forEach(t => {
        tipsList.appendChild(el("div", { style: "padding:6px 0; font-size:14px; border-bottom:1px solid rgba(212,149,107,0.15);" }, `• ${t}`));
      });
      card.appendChild(tipsList);
    }

    container.appendChild(card);
  } catch (e) {
    console.error("State lookup error:", e);
  }
}

function extractStateAbbrev(loc) {
  if (!loc) return "";
  const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"];
  const parts = loc.replace(/;/g, ",").split(",").map(p => p.trim().toUpperCase());
  for (const p of parts.reverse()) {
    const tokens = p.split(/\s+/);
    const last = tokens[tokens.length - 1];
    if (STATES.includes(last)) return last;
  }
  return "";
}

// ═══════════════════════════════════════════════════════════════════════════
// EVIDENCE
// ═══════════════════════════════════════════════════════════════════════════
async function renderEvidence() {
  const caseId = requireCase();
  const items = await api(`/cases/${caseId}/evidence`);
  const panel = $("#panel-evidence");
  panel.innerHTML = "";

  const addCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, "Add evidence"),
    el("div", { class: "muted", style: "margin-bottom:12px" }, "Save anything you find — links, notes, screenshots, documents. Every piece helps build the picture."),
    el("div", { class: "grid2" },
      el("div", {},
        el("label", { class: "label" }, "Title"),
        el("input", { class: "input", id: "evTitle2", placeholder: "What did you find?" }),
        el("label", { class: "label" }, "URL (if it's a link)"),
        el("input", { class: "input", id: "evUrl2", placeholder: "https://..." }),
        el("label", { class: "label" }, "Date (if known)"),
        el("input", { class: "input", id: "evDate2", placeholder: "YYYY-MM-DD" }),
        el("label", { class: "label" }, "Notes"),
        el("textarea", { class: "textarea", id: "evContent2", rows: "4", placeholder: "What does this tell you? Why is it important?" }),
        el("div", { class: "row", style: "margin-top:8px" },
          el("label", { class: "muted" }, el("input", { type: "checkbox", id: "evSensitive2" }), " Contains sensitive info (auto-redact)"),
        ),
        el("button", { class: "btn warm", style: "margin-top:10px", onclick: () => addEvidence(caseId) }, "💾 Save evidence"),
      ),
      el("div", {},
        el("label", { class: "label" }, "Or upload a file"),
        el("input", { class: "input", id: "fileTitle", placeholder: "File title", value: "Uploaded file" }),
        el("input", { class: "input", id: "fileDate", placeholder: "YYYY-MM-DD", style: "margin-top:8px" }),
        el("input", { type: "file", id: "fileInput", style: "margin-top:8px" }),
        el("button", { class: "btn secondary", style: "margin-top:10px", onclick: () => uploadFile(caseId) }, "📎 Upload"),
      ),
    ),
  );

  const listCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, `Evidence collected (${items.length} items)`),
  );

  if (items.length === 0) {
    listCard.appendChild(el("div", { class: "muted", style: "padding:20px; text-align:center" },
      "No evidence yet. As you search through the databases, save anything relevant here."
    ));
  }

  items.forEach(it => {
    const body = el("div", {},
      el("div", { style: "font-weight:600; margin-bottom:4px" }, `${it.event_date || ""} — ${it.title}`),
      el("div", { class: "small" }, `${it.kind} · ${it.id}`),
    );
    if (it.url) body.appendChild(el("div", { style: "margin-top:4px" }, el("a", { href: it.url, target: "_blank" }, it.url)));
    if (it.content) body.appendChild(el("div", { class: "mono", style: "margin-top:8px" }, it.content));
    if (it.file_path) body.appendChild(el("a", { href: `/evidence/file?path=${encodeURIComponent(it.file_path)}`, target: "_blank", style: "display:block; margin-top:6px" }, "📎 Open file"));
    body.appendChild(el("button", { class: "btn danger", style: "margin-top:8px; font-size:11px; padding:4px 10px;", onclick: () => deleteEvidence(caseId, it.id) }, "Remove"));
    listCard.appendChild(el("div", { class: "result", id: `evidence-${it.id}` }, body));
  });

  panel.appendChild(addCard);
  panel.appendChild(listCard);
}

async function addEvidence(caseId) {
  const title = $("#evTitle2").value.trim();
  if (!title) return;
  const url = $("#evUrl2").value.trim() || null;
  const event_date = $("#evDate2").value.trim() || null;
  const content = $("#evContent2").value.trim() || null;
  const sensitive = $("#evSensitive2").checked;
  const kind = url ? "link" : "note";
  await api(`/cases/${caseId}/evidence`, { method: "POST", body: JSON.stringify({ kind, title, url, content, event_date, sensitive }) });
  await renderEvidence();
  await renderOverview();
}

async function uploadFile(caseId) {
  const f = $("#fileInput").files[0];
  if (!f) return;
  const form = new FormData();
  form.append("file", f);
  form.append("title", $("#fileTitle").value.trim() || f.name);
  const date = $("#fileDate").value.trim();
  if (date) form.append("event_date", date);
  form.append("sensitive", "false");
  await fetch(`/cases/${caseId}/evidence/upload`, { method: "POST", body: form });
  await renderEvidence();
  await renderOverview();
}

async function deleteEvidence(caseId, evidenceId) {
  await api(`/cases/${caseId}/evidence/${evidenceId}`, { method: "DELETE" });
  await renderEvidence();
  await renderOverview();
}

// ═══════════════════════════════════════════════════════════════════════════
// TAGS
// ═══════════════════════════════════════════════════════════════════════════
async function renderTagsCard(caseId) {
  const [allTags, caseTags] = await Promise.all([api("/tags"), api(`/cases/${caseId}/tags`)]);
  const currentIds = new Set(caseTags.map(t => t.id));
  const wrap = el("div", { class: "card" }, el("div", { class: "card-title" }, "Tags"));
  if (caseTags.length) {
    caseTags.forEach(t => {
      wrap.appendChild(el("div", { class: "row", style: "margin-bottom:4px" },
        el("span", { class: "badge" }, t.label),
        el("button", { class: "btn secondary", style: "font-size:10px; padding:2px 6px;", onclick: async () => { await api(`/cases/${caseId}/tags/${t.id}`, { method: "DELETE" }); await renderOverview(); } }, "×"),
      ));
    });
  } else {
    wrap.appendChild(el("div", { class: "muted" }, "No tags yet."));
  }
  const select = el("select", {});
  select.appendChild(el("option", { value: "" }, "Add tag…"));
  allTags.filter(t => !currentIds.has(t.id)).forEach(t => select.appendChild(el("option", { value: t.id }, t.label)));
  wrap.appendChild(el("div", { class: "row", style: "margin-top:8px" },
    select,
    el("button", { class: "btn", style: "font-size:12px; padding:5px 10px;", onclick: async () => { if (select.value) { await api(`/cases/${caseId}/tags/${select.value}`, { method: "POST" }); await renderOverview(); } } }, "Add"),
  ));
  const newLabel = el("input", { class: "input", placeholder: "Create new tag", style: "margin-top:6px" });
  wrap.appendChild(el("div", { class: "row", style: "margin-top:4px" },
    newLabel,
    el("button", { class: "btn secondary", style: "font-size:12px;", onclick: async () => { if (newLabel.value.trim()) { await api("/tags", { method: "POST", body: JSON.stringify({ label: newLabel.value.trim() }) }); await renderOverview(); } } }, "Create"),
  ));
  return wrap;
}

// ═══════════════════════════════════════════════════════════════════════════
// TIMELINE
// ═══════════════════════════════════════════════════════════════════════════
async function renderTimelineCard(caseId) {
  const events = await api(`/cases/${caseId}/timeline`);
  const wrap = el("div", { class: "card" }, el("div", { class: "card-title" }, "Timeline"));
  if (!events.length) wrap.appendChild(el("div", { class: "muted" }, "No events yet. Add milestones as you go."));
  events.slice(0, 10).forEach(ev => {
    wrap.appendChild(el("div", { class: "result" },
      el("div", {}, `${ev.event_date || "?"} — ${ev.event_type}: ${ev.title}`),
      el("button", { class: "btn secondary", style: "font-size:10px; padding:2px 8px; margin-top:4px", onclick: async () => { await api(`/cases/${caseId}/timeline/${ev.id}`, { method: "DELETE" }); await renderOverview(); } }, "Remove"),
    ));
  });
  wrap.appendChild(el("div", { class: "row", style: "margin-top:10px" },
    el("input", { class: "input", id: "evDate", placeholder: "YYYY-MM-DD", style: "max-width:140px" }),
    el("input", { class: "input", id: "evType", placeholder: "type", style: "max-width:120px" }),
    el("input", { class: "input", id: "evTitle", placeholder: "Event title", style: "flex:1" }),
    el("button", { class: "btn", style: "font-size:12px;", onclick: async () => {
      const title = $("#evTitle").value.trim(); if (!title) return;
      await api(`/cases/${caseId}/timeline`, { method: "POST", body: JSON.stringify({ event_type: $("#evType").value.trim() || "note", title, event_date: $("#evDate").value.trim() || null, data: {} }) });
      await renderOverview();
    }}, "+ Add"),
  ));
  return wrap;
}

// ═══════════════════════════════════════════════════════════════════════════
// TASKS
// ═══════════════════════════════════════════════════════════════════════════
async function renderTasks() {
  const caseId = requireCase();
  const tasks = await api(`/cases/${caseId}/tasks`);
  const panel = $("#panel-tasks");
  panel.innerHTML = "";

  panel.appendChild(el("div", { class: "card" },
    el("div", { class: "card-title" }, "Add task"),
    el("div", { class: "row" },
      el("input", { class: "input", id: "taskTitle", placeholder: "What needs to be done?" }),
      el("input", { class: "input", id: "taskDue", placeholder: "YYYY-MM-DD", style: "max-width:150px" }),
      el("select", { id: "taskPri", style: "max-width:120px" },
        el("option", { value: "1" }, "P1 high"), el("option", { value: "2", selected: "selected" }, "P2 med"), el("option", { value: "3" }, "P3 low")),
      el("button", { class: "btn warm", onclick: async () => {
        const title = $("#taskTitle").value.trim(); if (!title) return;
        await api(`/cases/${caseId}/tasks`, { method: "POST", body: JSON.stringify({ title, due_date: $("#taskDue").value.trim() || null, priority: +$("#taskPri").value, notes: null }) });
        await renderTasks();
      }}, "Add"),
    ),
  ));

  const list = el("div", { class: "card" }, el("div", { class: "card-title" }, `Tasks (${tasks.length})`));
  tasks.forEach(t => {
    const statusSel = el("select", { style: "max-width:140px", onchange: async (e) => { await api(`/cases/${caseId}/tasks/${t.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); await renderTasks(); } },
      ...["open","in_progress","blocked","done"].map(s => el("option", { value: s, ...(t.status === s ? { selected: "selected" } : {}) }, s)),
    );
    list.appendChild(el("div", { class: "result" },
      el("div", { class: "row" },
        el("div", { style: "flex:1; font-weight:500" }, t.title),
        statusSel,
        el("button", { class: "btn danger", style: "font-size:11px; padding:4px 8px;", onclick: async () => { await api(`/cases/${caseId}/tasks/${t.id}`, { method: "DELETE" }); await renderTasks(); } }, "×"),
      ),
      t.notes ? el("div", { class: "mono", style: "margin-top:6px" }, t.notes) : null,
    ));
  });
  panel.appendChild(list);
}

// ═══════════════════════════════════════════════════════════════════════════
// DOCUMENTS
// ═══════════════════════════════════════════════════════════════════════════
async function renderDocuments() {
  const caseId = requireCase();
  const docs = await api(`/cases/${caseId}/documents`);
  const panel = $("#panel-documents");
  panel.innerHTML = "";

  panel.appendChild(el("div", { class: "card" },
    el("div", { class: "card-title" }, "Generate a document"),
    el("div", { class: "muted", style: "margin-bottom:10px" }, "These are draft templates to help you take action — welfare check scripts, agency letters, and more."),
    el("div", { class: "grid2" },
      el("div", {},
        el("label", { class: "label" }, "Document type"),
        el("select", { id: "docType" },
          el("option", { value: "welfare_check_script" }, "Welfare Check Call Script"),
          el("option", { value: "agency_letter" }, "Agency Letter (Status Inquiry)"),
          el("option", { value: "dps_history_request" }, "DPS History Request"),
          el("option", { value: "timeline_affidavit" }, "Timeline Affidavit"),
          el("option", { value: "presumed_death_petition" }, "Presumed Death Petition (Draft)"),
        ),
        el("label", { class: "label" }, "Your name"),
        el("input", { class: "input", id: "reqName" }),
        el("label", { class: "label" }, "Your relationship"),
        el("input", { class: "input", id: "reqRel", placeholder: "e.g., daughter, son, sibling" }),
      ),
      el("div", {},
        el("label", { class: "label" }, "Phone"),
        el("input", { class: "input", id: "reqPhone" }),
        el("label", { class: "label" }, "Email"),
        el("input", { class: "input", id: "reqEmail" }),
        el("label", { class: "label" }, "Last contact year"),
        el("input", { class: "input", id: "reqYear", placeholder: "e.g., 2013" }),
        el("button", { class: "btn warm", style: "margin-top:16px", onclick: async () => {
          const payload = {
            doc_type: $("#docType").value, requester_name: $("#reqName").value.trim() || null,
            requester_relation: $("#reqRel").value.trim() || null, requester_phone: $("#reqPhone").value.trim() || null,
            requester_email: $("#reqEmail").value.trim() || null, last_contact_year: $("#reqYear").value.trim() || null,
          };
          const doc = await api(`/cases/${caseId}/documents/render`, { method: "POST", body: JSON.stringify(payload) });
          showModal("Document generated", doc.content);
          await renderDocuments();
        }}, "📝 Generate document"),
      ),
    ),
  ));

  const list = el("div", { class: "card" }, el("div", { class: "card-title" }, `Saved documents (${docs.length})`));
  docs.forEach(d => {
    list.appendChild(el("div", { class: "result" },
      el("div", {}, `${d.created_at} — ${d.doc_type}: ${d.title}`),
      el("div", { class: "row", style: "margin-top:6px" },
        el("button", { class: "btn secondary", style: "font-size:12px;", onclick: () => showModal(d.title, d.content) }, "View"),
        el("a", { class: "btn secondary", href: `/cases/${caseId}/documents/${d.id}.pdf`, target: "_blank", style: "font-size:12px;" }, "PDF"),
        el("button", { class: "btn danger", style: "font-size:11px;", onclick: async () => { await api(`/cases/${caseId}/documents/${d.id}`, { method: "DELETE" }); await renderDocuments(); } }, "×"),
      ),
    ));
  });
  panel.appendChild(list);
}

// ═══════════════════════════════════════════════════════════════════════════
// GRAPH (with relationship suggestions)
// ═══════════════════════════════════════════════════════════════════════════
async function renderGraph() {
  const caseId = requireCase();
  const data = await api(`/cases/${caseId}/graph`);
  const panel = $("#panel-graph");
  panel.innerHTML = "";

  // Relationship suggestions
  const c = STATE.currentCase;
  const relNodes = data.nodes.filter(n => n.type === "person" && n.meta?.role === "relative");
  if (relNodes.length > 0) {
    const suggestCard = el("div", { class: "card card-info" },
      el("div", { class: "card-title" }, "👥 Relationship multiplier — search connected people"),
      el("div", { class: "muted", style: "margin-bottom:10px" }, "People connected to the person you're looking for often appear in shared records. Searching for them can reveal information about your subject."),
    );
    relNodes.forEach(n => {
      suggestCard.appendChild(el("div", { class: "row", style: "margin-bottom:6px" },
        el("span", { style: "flex:1" }, `🔗 ${n.label}`),
        el("a", { class: "btn secondary", style: "font-size:11px;", href: `https://www.google.com/search?q=${encodeURIComponent('"' + n.label + '" "' + c.subject_name + '"')}`, target: "_blank" }, "Search together"),
        el("a", { class: "btn secondary", style: "font-size:11px;", href: `https://www.google.com/search?q=${encodeURIComponent('"' + n.label + '" obituary')}`, target: "_blank" }, "Check obituary"),
      ));
    });
    panel.appendChild(suggestCard);
  }

  const graphCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, `Connection map (${data.nodes.length} nodes · ${data.edges.length} connections)`),
    el("canvas", { class: "canvas", width: "1200", height: "500", id: "graphCanvas" }),
  );
  panel.appendChild(graphCard);
  drawGraph($("#graphCanvas"), data);
}

function drawGraph(canvas, data) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const pos = new Map();
  const hash = (s) => { let x = 0; for (let i = 0; i < s.length; i++) x = (x * 31 + s.charCodeAt(i)) >>> 0; return x; };
  data.nodes.forEach(n => { const r = hash(n.id); pos.set(n.id, { x: 80 + (r % (w - 160)), y: 80 + ((r >>> 8) % (h - 160)) }); });
  let scale = 1, offsetX = 0, offsetY = 0, dragging = false, lastX = 0, lastY = 0;
  const COLORS = { person: "#E0F2F1", evidence: "rgba(79,209,197,0.9)", alias: "#FFF3E0", place: "#E3F2FD", email: "#FCE4EC", phone: "#F3E5F5", url: "#E8EAF6" };

  function render() {
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, w, h);
    ctx.setTransform(scale, 0, 0, scale, offsetX, offsetY);
    ctx.lineWidth = 1 / Math.max(scale, 0.01); ctx.globalAlpha = 0.5;
    data.edges.forEach(e => { const a = pos.get(e.source), b = pos.get(e.target); if (!a || !b) return; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.strokeStyle = "rgba(26,138,125,0.25)"; ctx.stroke(); });
    ctx.globalAlpha = 1;
    data.nodes.forEach(n => {
      const p = pos.get(n.id); if (!p) return;
      const r = (n.type === "person" ? 9 : 6) / Math.max(scale, 0.01);
      ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = COLORS[n.type] || "#DDD"; ctx.fill();
      if (n.type === "person") { ctx.font = `${11 / Math.max(scale, 0.01)}px sans-serif`; ctx.fillStyle = "#ECF0F1"; ctx.fillText(n.label, p.x + r + 4, p.y + 4); }
    });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = "#95A5A6"; ctx.font = "11px sans-serif";
    ctx.fillText("Drag to pan · Scroll to zoom", 12, h - 10);
  }
  canvas.addEventListener("wheel", (e) => { e.preventDefault(); const z = e.deltaY < 0 ? 1.12 : 0.9; offsetX = e.offsetX - (e.offsetX - offsetX) * z; offsetY = e.offsetY - (e.offsetY - offsetY) * z; scale = Math.min(Math.max(scale * z, 0.2), 6); render(); }, { passive: false });
  canvas.addEventListener("mousedown", (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; });
  window.addEventListener("mousemove", (e) => { if (!dragging) return; offsetX += e.clientX - lastX; offsetY += e.clientY - lastY; lastX = e.clientX; lastY = e.clientY; render(); });
  window.addEventListener("mouseup", () => { dragging = false; });
  render();
}

// ═══════════════════════════════════════════════════════════════════════════
// AUDIT
// ═══════════════════════════════════════════════════════════════════════════
async function renderAudit() {
  const caseId = requireCase();
  const rows = await api(`/audit?case_id=${encodeURIComponent(caseId)}&limit=200`);
  const panel = $("#panel-audit");
  panel.innerHTML = "";
  const card = el("div", { class: "card" },
    el("div", { class: "card-title" }, `Audit log (${rows.length} entries)`),
    el("div", { class: "muted", style: "margin-bottom:10px" }, "Every action is logged for your records. This can be used as evidence of diligent search."),
  );
  rows.forEach(r => {
    card.appendChild(el("div", { class: "result" },
      el("div", {}, `${r.created_at} — ${r.action}`),
      el("div", { class: "small" }, `${r.actor} · ${r.id}`),
    ));
  });
  panel.appendChild(card);
}

// ═══════════════════════════════════════════════════════════════════════════
// GLOBAL SEARCH
// ═══════════════════════════════════════════════════════════════════════════
async function runGlobalSearch() {
  const q = $("#globalSearchInput").value.trim();
  if (!q) return;
  const url = `/search?q=${encodeURIComponent(q)}${STATE.currentCaseId ? `&case_id=${encodeURIComponent(STATE.currentCaseId)}` : ""}`;
  const res = await api(url);
  const box = $("#globalSearchResults");
  box.innerHTML = "";
  res.results.forEach(r => {
    box.appendChild(el("button", { class: "btn secondary", style: "width:100%;text-align:left;margin-bottom:6px;font-size:12px;", onclick: () => { if (r.ref_type === "evidence") setActiveTab("evidence"); else setActiveTab("overview"); } },
      `${r.ref_type}: ${r.title}`));
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// CASE EDITOR
// ═══════════════════════════════════════════════════════════════════════════
function openCaseEditor(c = null) {
  const dlg = $("#caseDialog"); const form = $("#caseForm");
  form.reset(); form.dataset.mode = c ? "edit" : "new"; form.dataset.caseId = c ? c.id : "";
  if (c) { form.title.value = c.title || ""; form.subject_name.value = c.subject_name || ""; form.dob.value = c.dob || ""; form.aliases.value = c.aliases || ""; form.last_known_locations.value = c.last_known_locations || ""; form.relatives.value = c.relatives || ""; form.notes.value = c.notes || ""; }
  dlg.showModal();
}

async function saveCaseFromDialog() {
  const form = $("#caseForm");
  const payload = { title: form.title.value.trim(), subject_name: form.subject_name.value.trim(), dob: form.dob.value.trim() || null, aliases: form.aliases.value.trim() || null, last_known_locations: form.last_known_locations.value.trim() || null, relatives: form.relatives.value.trim() || null, notes: form.notes.value.trim() || null };
  if (!payload.title || !payload.subject_name) return;
  if (form.dataset.mode === "edit") {
    await api(`/cases/${form.dataset.caseId}`, { method: "PATCH", body: JSON.stringify(payload) });
    await loadCases(); await selectCase(form.dataset.caseId);
  } else {
    const created = await api("/cases", { method: "POST", body: JSON.stringify(payload) });
    await loadCases(); await selectCase(created.id);
  }
}

async function deleteCase(caseId) {
  if (!confirm("Delete this case and all related data? This cannot be undone.")) return;
  await api(`/cases/${caseId}`, { method: "DELETE" });
  STATE.currentCaseId = null; STATE.currentCase = null;
  showWelcome(); await loadCases();
}

async function runRagSummary(caseId) {
  try {
    const s = await api(`/cases/${caseId}/rag/summary`, { method: "POST", body: JSON.stringify({}) });
    showModal("AI Summary", s.summary || JSON.stringify(s, null, 2));
  } catch (e) { showModal("AI Summary", "AI summary requires Ollama to be running locally. Set RECONNECT_OLLAMA=1 and restart."); }
}

// ═══════════════════════════════════════════════════════════════════════════
// WIRING
// ═══════════════════════════════════════════════════════════════════════════
document.addEventListener("click", (e) => { const t = e.target.closest(".tab"); if (t) setActiveTab(t.dataset.tab); });

$("#newCaseBtn").addEventListener("click", () => openWizard());
$("#welcomeStartBtn").addEventListener("click", () => openWizard());
$("#refreshBtn").addEventListener("click", () => loadCases());
$("#globalSearchBtn").addEventListener("click", () => runGlobalSearch());
$("#globalSearchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") runGlobalSearch(); });
$("#exportBtn").addEventListener("click", () => { if (STATE.currentCaseId) window.open(`/cases/${STATE.currentCaseId}/export`, "_blank"); });
$("#ragBtn").addEventListener("click", () => { if (STATE.currentCaseId) runRagSummary(STATE.currentCaseId); });
$("#caseForm").addEventListener("submit", async (e) => { e.preventDefault(); await saveCaseFromDialog(); $("#caseDialog").close(); });

loadCases().catch(err => showModal("Startup", String(err)));
