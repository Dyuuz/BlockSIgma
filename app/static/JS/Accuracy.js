// ===== Accuracy.js =====

// ---- Endpoints (edit the *buy* ones if your API uses different paths) ----
const ENDPOINTS = {
  "12hs": "/price/twelve-hours-summary",
  "12hb": "/price/twelve-hours-buy-summary",
  "4hs":  "/price/four-hours-summary",
  "4hb":  "/price/four-hours-buy-summary",
};

// ---- Refresh cadence ----
const REFRESH_SECONDS = 30;

// ---- App state per panel ----
const state = {
    "12hs": { data: [], page: 1, pageSize: 10, fetching: false, pendingRefresh: false, lastUpdated: null, countdown: REFRESH_SECONDS, timer: null },
    "12hb": { data: [], page: 1, pageSize: 10, fetching: false, pendingRefresh: false, lastUpdated: null, countdown: REFRESH_SECONDS, timer: null },
    "4hs":  { data: [], page: 1, pageSize: 10, fetching: false, pendingRefresh: false, lastUpdated: null, countdown: REFRESH_SECONDS, timer: null },
    "4hb":  { data: [], page: 1, pageSize: 10, fetching: false, pendingRefresh: false, lastUpdated: null, countdown: REFRESH_SECONDS, timer: null },
};

// ---- Timezone handling ----
let DISPLAY_TZ = "Africa/Lagos"; // default; overridden by user/system

function populateTimezones() {
  const sel = document.getElementById("tzSelect");
  if (!sel) return;

  let zones = [];
  if (Intl.supportedValuesOf) {
    zones = Intl.supportedValuesOf("timeZone");
  } else {
    zones = [
      "UTC","Africa/Lagos","Europe/London","America/New_York","Asia/Tokyo",
      "Australia/Sydney","America/Sao_Paulo","Asia/Dubai","Asia/Kolkata"
    ];
  }
  zones.sort();

  sel.innerHTML = "";
  zones.forEach(tz => {
    const opt = document.createElement("option");
    opt.value = tz;
    opt.textContent = tz;
    sel.appendChild(opt);
  });

  try {
    const sysTZ = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zones.includes(sysTZ)) {
      sel.value = sysTZ;
      DISPLAY_TZ = sysTZ;
    } else {
      sel.value = DISPLAY_TZ;
    }
  } catch {
    sel.value = DISPLAY_TZ;
  }

  sel.addEventListener("change", () => {
    DISPLAY_TZ = sel.value || "UTC";
    // Re-render all panels (no refetch needed)
    ["12hs","12hb","4hs","4hb"].forEach(renderPanel);
  });
}

// ---- HTTP ----
async function httpGet(url){
  const res = await fetch(url, { headers:{ "Accept":"application/json" }});
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

// ---- Utils ----
function safe(v){ return (v===null||v===undefined) ? "—" : String(v).replace(/[&<>"']/g, s=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[s])); }
const fmtNum = (v, d=2) => (isFinite(v) ? Number(v).toLocaleString(undefined,{minimumFractionDigits:d, maximumFractionDigits:d}) : "—");

function parseApiUtc(ts) {
  if (!ts || typeof ts !== "string") return null;
  const re = /^\s*([A-Za-z]+)\s+(\d{1,2})\s+(\d{2,4})?,?\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*UTC(?:[+−-]?\d{2})?\s*$/i;
  const m = ts.match(re);
  if (!m) { const d = new Date(ts); return isNaN(d) ? null : d; }

  const months = { january:0,february:1,march:2,april:3,may:4,june:5,
                   july:6,august:7,september:8,october:9,november:10,december:11 };
  const mi = months[m[1].toLowerCase()];
  if (mi == null) return null;

  const day = +m[2];
  let year = m[3] ? +m[3] : (new Date()).getUTCFullYear();
  if (year < 100) year += 2000;
  let hour = +m[4];
  const minute = +m[5];
  const ampm = m[6].toUpperCase();
  if (ampm === "PM" && hour !== 12) hour += 12;
  if (ampm === "AM" && hour === 12) hour = 0;

  return new Date(Date.UTC(year, mi, day, hour, minute, 0));
}

function fmtTimeTZ(ts){
  if (!ts) return "—";
  const d = parseApiUtc(ts);
  if (!d) return String(ts);
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: DISPLAY_TZ,
      year: "numeric", month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: true
    }).format(d);
  } catch {
    return d.toLocaleString();
  }
}

function parsePercent(val){
  if (val == null) return null;
  if (typeof val === "number") return val <= 1 ? val * 100 : val;
  const m = String(val).match(/-?\d+(\.\d+)?/);
  return m ? Math.max(0, Math.min(100, parseFloat(m[0]))) : null;
}

// Normalize payload -> array of summary objects
function normalizeSummary(payload){
  const arr = Array.isArray(payload) ? payload
            : Array.isArray(payload?.data) ? payload.data
            : (payload ? [payload] : []);
  // Sort newest first by "from"
  arr.sort((a,b)=>{
    const A = parseApiUtc(a?.from)?.getTime() ?? -Infinity;
    const B = parseApiUtc(b?.from)?.getTime() ?? -Infinity;
    return B - A;
  });
  return arr.map(x => {
    const correct = Number(x.number_of_reached ?? x.correct ?? 0);
    const total   = Number(x.number_of_predictions ?? x.total ?? 0);
    const pct     = parsePercent(x.accuracy ?? x.percentage ?? (total ? (correct/total*100) : null));
    return {
      from: x.from || null,
      to: x.to || null,
      number_of_reached: correct,
      number_of_predictions: total,
      accuracy_pct: pct,
      accuracy_text: (x.accuracy ? String(x.accuracy) : (pct!=null ? `${pct.toFixed(1)}%` : "—")),
    };
  });
}

// ---- Rendering ----
function setWindowChip(scope){
  const chip = document.getElementById(`window-${scope}`);
  if (!chip) return;
  const list = state[scope].data;
  if (!Array.isArray(list) || list.length === 0) {
    chip.textContent = "Latest window: —";
    return;
  }
  const first = list[0];
  chip.textContent = `Latest window: ${fmtTimeTZ(first.from)} → ${fmtTimeTZ(first.to)}`;
}

function renderPanel(scope){
  // body
  const tbody = document.getElementById(`body-${scope}`);
  if (!tbody) return;

  const list = state[scope].data || [];
  const page = state[scope].page || 1;
  const pageSize = state[scope].pageSize || 10;
  const totalRows = list.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const curPage = Math.min(page, totalPages);
  state[scope].page = curPage;

  if (!totalRows){
    tbody.innerHTML = `<tr><td class="muted" colspan="5">No data</td></tr>`;
  } else {
    const start = (curPage - 1) * pageSize;
    const slice = list.slice(start, start + pageSize);

    const rowsHtml = slice.map(it => {
      return `
        <tr>
          <td>${safe(fmtTimeTZ(it.from))}</td>
          <td>${safe(fmtTimeTZ(it.to))}</td>
          <td>${safe(it.number_of_reached)}</td>
          <td class="right-align">${safe(it.number_of_predictions)}</td>
          <td class="right-align">${safe(it.accuracy_text)}</td>
        </tr>`;
    }).join("");

    tbody.innerHTML = rowsHtml;
  }

  // range + page indicators
  const rangeEl = document.getElementById(`range-${scope}`);
  if (rangeEl) {
    if (!totalRows) rangeEl.textContent = "0–0 of 0";
    else {
      const startIdx = (state[scope].page - 1) * state[scope].pageSize + 1;
      const endIdx = Math.min(startIdx + state[scope].pageSize - 1, totalRows);
      rangeEl.textContent = `${startIdx}–${endIdx} of ${totalRows}`;
    }
  }

  const pageEl = document.getElementById(`page-${scope}`);
  if (pageEl) pageEl.textContent = `${state[scope].page} / ${Math.max(1, Math.ceil((state[scope].data.length||0) / state[scope].pageSize))}`;

  // last updated
  const updatedEl = document.getElementById(`updated-${scope}`);
  if (updatedEl && state[scope].lastUpdated) {
    updateLastUpdated(scope);
  }

  // countdown
  const countEl = document.getElementById(`count-${scope}`);
  if (countEl) countEl.textContent = `${state[scope].countdown}s`;

  // window chip
  setWindowChip(scope);
}

async function fetchAndRender(scope){
  if (state[scope].fetching) return;
  state[scope].fetching = true;
  try{
    const url = ENDPOINTS[scope];
    const raw = await httpGet(url);
    state[scope].data = normalizeSummary(raw);
    state[scope].lastUpdated = new Date();
    renderPanel(scope);
  } catch (err){
    console.error(`Failed to fetch ${scope}:`, err);
    const tbody = document.getElementById(`body-${scope}`);
    if (tbody) tbody.innerHTML = `<tr><td class="muted" colspan="5">Error loading data</td></tr>`;
    const chip = document.getElementById(`window-${scope}`);
    if (chip) chip.textContent = "Latest window: —";
  } finally {
    state[scope].fetching = false;
  }
}

function startCountdown(scope){
  // initial fetch
  fetchAndRender(scope);

  // reset countdown
  state[scope].countdown = REFRESH_SECONDS;

  // clear previous
  if (state[scope].timer) clearInterval(state[scope].timer);

  state[scope].timer = setInterval(()=>{
    state[scope].countdown -= 1;
    const countEl = document.getElementById(`count-${scope}`);
    if (countEl) countEl.textContent = `${state[scope].countdown}s`;

    if (state[scope].countdown <= 0){
      state[scope].countdown = REFRESH_SECONDS;
      fetchAndRender(scope);
    }
  }, 1000);
}

// ---- Pagination wiring ----
function wirePagination(scope){
  const psSel = document.getElementById(`ps-${scope}`);
  const prev  = document.getElementById(`prev-${scope}`);
  const next  = document.getElementById(`next-${scope}`);

  if (psSel) {
    // initial value from DOM
    const psDefault = parseInt(psSel.value, 10);
    if (Number.isFinite(psDefault)) state[scope].pageSize = psDefault;

    psSel.addEventListener("change", ()=>{
      const v = parseInt(psSel.value, 10);
      if (Number.isFinite(v)) state[scope].pageSize = v;
      state[scope].page = 1;
      renderPanel(scope);
    });
  }

  if (prev) prev.addEventListener("click", ()=>{
    if (state[scope].page > 1) { state[scope].page -= 1; renderPanel(scope); }
  });

  if (next) next.addEventListener("click", ()=>{
    const totalPages = Math.max(1, Math.ceil((state[scope].data.length||0) / state[scope].pageSize));
    if (state[scope].page < totalPages) { state[scope].page += 1; renderPanel(scope); }
  });
}

// ---- Tabs & modal wiring ----
function wireTabs(){
  document.querySelectorAll(".tab").forEach(tab=>{
    tab.addEventListener("click", ()=>{
      document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.target;
      document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
      const panel = document.getElementById(target);
      if (panel) panel.classList.add("active");
    });
  });
}

function wireModal(){
  const modal = document.getElementById("modal");
  const helpBtn = document.getElementById("helpBtn");
  const closeModal = document.getElementById("closeModal");
  if (helpBtn && modal) helpBtn.addEventListener("click", () => modal.classList.add("is-open"));
  if (closeModal && modal) closeModal.addEventListener("click", () => modal.classList.remove("is-open"));
  if (modal) modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("is-open"); });
}

// ---- Boot ----
window.addEventListener("DOMContentLoaded", ()=>{
  populateTimezones();
  wireTabs();
  wireModal();

  ["12hs","12hb","4hs","4hb"].forEach(scope=>{
    wirePagination(scope);
    startCountdown(scope);
  });
});

function fmtTimeOnlyTZ(dateObj) {
  if (!dateObj) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: DISPLAY_TZ,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true
    }).format(dateObj);
  } catch {
    return dateObj.toLocaleTimeString();
  }
}

function updateLastUpdated(scope) {
  const el = document.getElementById(`updated-${scope}`);
  if (el) el.textContent = fmtTimeOnlyTZ(state[scope].lastUpdated);
}
