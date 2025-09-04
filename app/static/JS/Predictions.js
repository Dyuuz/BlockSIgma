// ===== Predictions.js (accurate summary wiring) =====

// ---- Table data endpoints & polling ----
const ENDPOINT_12H = "/price/latest-predictions";
const ENDPOINT_4H  = "/price/four-hour-prediction";
const REFRESH_SECONDS = 30;

// ---- Summary endpoints (your spec) ----
const ENDPOINTS = {
  "12hs": "/price/twelve-hours-summary",
  "4hs":  "/price/four-hours-summary",
};

// If API doesn’t supply total, default to 245 (your earlier note)
const TOTAL_COINS_DEFAULT = 245;

// ---- App state ----
const state = {
  "12h": {
    data: [],
    filtered: [],
    sortKey: "asset_name",
    sortDir: "asc",
    countdown: REFRESH_SECONDS,
    ticking: null,
    fetching: false,
    lastUpdated: null,
  },
  "4h": {
    data: [],
    filtered: [],
    sortKey: "asset_name",
    sortDir: "asc",
    countdown: REFRESH_SECONDS,
    ticking: null,
    fetching: false,
    lastUpdated: null,
  },
};

// Default display timezone (user can change)
let DISPLAY_TZ = "Africa/Lagos";

// ---------- Utilities ----------
function safe(v){ return (v===null||v===undefined) ? "—" : String(v).replace(/[&<>"']/g, s=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[s])); }
const fmtNum = (v, d=4) => (isFinite(v) ? Number(v).toLocaleString(undefined,{minimumFractionDigits:d, maximumFractionDigits:d}) : "—");
const fmtPct = (v, d=2) => (isFinite(v) ? Number(v).toFixed(d) + "%" : "—");
const polarityClass = (n)=> (isFinite(n) ? (n<0?"negative":(n>0?"positive":"")) : "");

const fmtBool = (b) => {
  const yes = !!b;
  const icon = yes ? "▲" : "▼";          // or "↑"/"↓" if you prefer
  const cls  = yes ? "up" : "down";
  return `<span class="bool ${cls}" title="${yes ? "True" : "False"}" aria-label="${yes ? "True" : "False"}">${icon}</span>`;
};

// --- Parse API UTC strings like: "July 22 25, 09:19 AM UTC+00"
function parseApiUtc(ts) {
  if (!ts || typeof ts !== "string") return null;
  const re = /^\s*([A-Za-z]+)\s+(\d{1,2})\s+(\d{2,4})?,?\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*UTC(?:[+−-]?\d{2})?\s*$/i;
  const m = ts.match(re);
  if (!m) {
    const d = new Date(ts);
    return isNaN(d) ? null : d;
  }
  const months = {
    january:0,february:1,march:2,april:3,may:4,june:5,
    july:6,august:7,september:8,october:9,november:10,december:11
  };
  const mi = months[m[1].toLowerCase()];
  if (mi == null) return null;

  const day = parseInt(m[2], 10);
  let year = m[3] ? parseInt(m[3], 10) : (new Date()).getUTCFullYear();
  if (year < 100) year += 2000;
  let hour = parseInt(m[4], 10);
  const minute = parseInt(m[5], 10);
  const ampm = m[6].toUpperCase();
  if (ampm === "PM" && hour !== 12) hour += 12;
  if (ampm === "AM" && hour === 12) hour = 0;

  const ms = Date.UTC(year, mi, day, hour, minute, 0);
  return new Date(ms);
}

// Format using the selected IANA timezone
function fmtTimeTZ(ts) {
  if (!ts) return "—";
  const d = parseApiUtc(ts);
  if (!d) return String(ts);
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: DISPLAY_TZ,
      year: "numeric", month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
      hour12: true
    }).format(d);
  } catch (e) {
    return d.toLocaleString();
  }
}
const fmtTime = (t) => fmtTimeTZ(t);

// HTTP helper
async function httpGet(url){
  if (window.axios) {
    const { data } = await axios.get(url, { headers:{ "Accept":"application/json" }});
    return data;
  } else {
    const res = await fetch(url, { headers:{ "Accept":"application/json" }});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }
}

// ---------- Summary (Past/Present) ----------
const toNum = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

function parsePercent(val) {
  if (val == null) return null;
  if (typeof val === "string") {
    // accept "87.0%" or "87.0"
    const m = val.match(/-?\d+(\.\d+)?/);
    if (!m) return null;
    return Math.max(0, Math.min(100, parseFloat(m[0])));
  }
  if (typeof val === "number") {
    // if 0..1, treat as ratio; if >1, treat as %
    return val <= 1 ? val * 100 : val;
  }
  return null;
}

// Map your sample shape: { number_of_reached, number_of_predictions, accuracy: "87.0%" }
function extractSummaryItem(item) {
  if (!item || typeof item !== "object") return null;

  const correct = toNum(item.number_of_reached)
               ?? toNum(item.correct)
               ?? toNum(item.hits)
               ?? null;

  let total = toNum(item.number_of_predictions)
           ?? toNum(item.total)
           ?? TOTAL_COINS_DEFAULT;

  let pct = parsePercent(item.accuracy ?? item.percentage ?? item.pct ?? null);
  if (pct == null && correct != null && total != null && total > 0) {
    pct = (correct / total) * 100;
  }
  return (correct == null && pct == null) ? null : { correct, total, pct };
}

// Normalize the full summary payload
function normalizeSummaryPayload(payload) {
  // Expect array where:
  //   index 0 = Present
  //   index 1 = Past (previous)
  const arr = Array.isArray(payload) ? payload
            : Array.isArray(payload?.data) ? payload.data
            : (payload ? [payload] : []);

  const present = arr[0] ? extractSummaryItem(arr[0]) : null;
  const past    = arr[1] ? extractSummaryItem(arr[1]) : null;
  return { present, past };
}

// Render the two lines in the requested order/format
function renderSummaryLines(scope, summary) {
  const host = document.getElementById(`acc-lines-${scope}`);
  if (!host) return;

  const present = summary.present; // first item from API
  const past    = summary.past;    // second item (optional)

  const badgeClass = (pct) => {
    if (pct == null) return "";     // no color if NA
    if (pct >= 70) return "is-good";
    if (pct >= 40) return "is-ok";
    return "is-bad";
  };

  const row = (label, data) => {
    if (!data) {
      return `
        <div class="acc-row">
          <span class="acc-label">${label}</span>
          <span class="acc-right">
            <span class="acc-count">— / —</span>
            <span class="acc-na">NA</span>
          </span>
        </div>`;
    }
    const total = (typeof data.total === "number") ? data.total : (typeof TOTAL_COINS_DEFAULT !== "undefined" ? TOTAL_COINS_DEFAULT : 245);
    const correct = (typeof data.correct === "number") ? data.correct : 0;
    const pct = (typeof data.pct === "number") ? data.pct : (total ? (correct / total * 100) : null);
    const pctTxt = (pct != null) ? `${pct.toFixed(2)}%` : "—";
    return `
      <div class="acc-row">
        <span class="acc-label">${label}</span>
        <span class="acc-right">
          <span class="acc-count">${correct} / ${total}</span>
          <span class="acc-pct ${badgeClass(pct)}">"${pctTxt}"</span>
        </span>
      </div>`;
  };

  // Order on screen: Past first, Present second (your specified format)
  host.innerHTML = row("Previous Accuracy", past) + row("Present Accuracy", present);
}


async function fetchAndRenderSummary(scope) {
  const key = `${scope}s`; // "12h" -> "12hs", "4h" -> "4hs"
  const url = ENDPOINTS[key];
  if (!url) return;
  try {
    const payload = await httpGet(url);
    const summary = normalizeSummaryPayload(payload);
    renderSummaryLines(scope, summary);
  } catch (e) {
    // On error, show NA lines
    renderSummaryLines(scope, { present: null, past: null });
    console.error(`Failed to fetch summary for ${scope}:`, e);
  }
}

// ---------- Times badge ----------
function setTimesBadge(scope){
  const block = document.getElementById(`times-${scope}`);
  if (!block) return;
  const arr = state[scope].filtered.length ? state[scope].filtered : state[scope].data;
  if (!arr || !arr.length) { block.textContent = "Prediction: — • Expiry: —"; return; }
  const item = arr.find(i => i.predicted_time && i.expiry_time) || arr[0];
  block.textContent = `Prediction: ${fmtTime(item.predicted_time)} • Expiry: ${fmtTime(item.expiry_time)}`;
}

// ---------- Rendering (tables) ----------
function render(scope){
  const tbody = document.getElementById(`body-${scope}`);
  if (!tbody) return;
  const rows = (state[scope].filtered.length ? state[scope].filtered : state[scope].data) || [];
  if (!rows.length){
    tbody.innerHTML = `<tr><td class="muted" colspan="99">No data</td></tr>`;
    setTimesBadge(scope);
    return;
  }

  const html = rows.map((item, idx) => {
    // Prefer backend-provided id-like fields; fallback to display index (1-based)
    const displayId = item.id ?? item._id ?? item.asset_id ?? item.rank ?? (idx + 1);

    const cells = [
      `<td class="id-col">${safe(displayId)}</td>`,
      `<td><strong>${safe(item.asset_name)}</strong><div class="muted">${safe(item.symbol)}</div></td>`,
      `<td>${safe(item.symbol)}</td>`,
      `<td class="right-align">$${fmtNum(item.current_price, 6)}</td>`,
      `<td class="right-align">$${fmtNum(item.price_at_predicted_time, 6)}</td>`,
      `<td class="right-align">$${fmtNum(item.predicted_price, 6)}</td>`,
      `<td class="right-align"><span class="value-change ${polarityClass(item.price_difference_currently)}">${fmtPct(item.price_difference_currently)}</span></td>`,
      `<td class="right-align"><span class="value-change ${polarityClass(item.price_difference_at_predicted_time)}">${fmtPct(item.price_difference_at_predicted_time)}</span></td>`,
      `<td>${fmtBool(item.current_status)}</td>`,
      `<td>${safe(item.prediction_status)}</td>`,
      // (NO interval cell)
      `<td>${safe(item.achievement)}</td>`,
      `<td>${fmtTime(item.time_reached)}</td>`,
      `<td class="right-align"><span class="${polarityClass(item.dynamic_tp)}">${fmtPct(item.dynamic_tp)}</span></td>`,
      `<td class="right-align"><span class="${polarityClass(item.dynamic_sl)}">${fmtPct(item.dynamic_sl)}</span></td>`,
      `<td class="right-align"><span class="${polarityClass(item.rrr)}">${fmtNum(item.rrr, 2)}</span></td>`,
      `<td>${fmtBool(item.sl_status)}</td>`,
      `<td>${fmtBool(item.price_change_status)}</td>`,
      // LAST TWO: Predicted & Expiry
      `<td>${fmtTime(item.predicted_time)}</td>`,
      `<td>${fmtTime(item.expiry_time)}</td>`,
    ];

    const status = String(item.prediction_status ?? '')
      .trim()
      .toLowerCase()
      .replace(/\s*[-–—]\s*/g, ' - ');
    const trClass = (status === 'buy - reached') ? 'reached' : '';

    return `<tr class="${trClass}">${cells.join("")}</tr>`;
  }).join("");

  tbody.innerHTML = html;
  setTimesBadge(scope);
}



// ---------- Sorting ----------
function sortData(scope, key, type){
  const dir = (state[scope].sortKey === key && state[scope].sortDir === "asc") ? "desc" : "asc";
  state[scope].sortKey = key; state[scope].sortDir = dir;

  const arr = state[scope].filtered.length ? state[scope].filtered : state[scope].data;
  const val = (o)=> {
    const v = o[key];
    if (type==="time"){
      const d = parseApiUtc(v);
      return d ? d.getTime() : -Infinity;
    }
    if (type==="bool"){ return !!v ? 1 : 0; }
    if (type==="number"){ const n = Number(v); return isFinite(n) ? n : -Infinity; }
    return (v ?? "").toString().toLowerCase();
  };
  arr.sort((a,b)=>{
    const A = val(a), B = val(b);
    if (A<B) return dir==="asc" ? -1 : 1;
    if (A>B) return dir==="asc" ? 1 : -1;
    return 0;
  });
  render(scope);
}

function attachSorting(scope){
  const table = document.getElementById(`table-${scope}`);
  if (!table) { console.warn(`Table element missing for ${scope}`); return; }
  table.querySelectorAll("th.sortable").forEach(th=>{
    th.addEventListener("click", ()=> sortData(scope, th.dataset.key, th.dataset.type));
  });
}

// ---------- Search ----------
function applySearch(q){
  const query = q.trim().toLowerCase();
  ["12h","4h"].forEach(scope=>{
    if (!query){
      state[scope].filtered = [];
    } else {
      state[scope].filtered = state[scope].data.filter(it=>{
        return (String(it.asset_name||"").toLowerCase().includes(query) ||
                String(it.symbol||"").toLowerCase().includes(query));
      });
    }
    render(scope);
  });
}

// ---------- Fetch / render (tables) ----------
async function fetchAndRender(scope, url){
  if (state[scope].fetching) return;
  state[scope].fetching = true;
  try{
    const raw = await httpGet(url);
    const list = Array.isArray(raw) ? raw
              : Array.isArray(raw?.data) ? raw.data
              : (raw ? [raw] : []);

    state[scope].data = list;

    const q = document.getElementById("searchInput")?.value || "";
    if (q) applySearch(q); else state[scope].filtered = [];

    render(scope);
    state[scope].lastUpdated = new Date();
    updateLastUpdated(scope);
  } catch (err){
    console.error(`Failed to fetch ${scope}:`, err);
    showError(scope, err);
  } finally {
    state[scope].fetching = false;
  }
}

function showError(scope, err) {
  const tbody = document.getElementById(`body-${scope}`);
  const msg = err?.message ?? 'Unknown error';
  const hasData = Array.isArray(state[scope]?.data) && state[scope].data.length > 0;

  if (tbody && !hasData) {
    tbody.innerHTML = `<tr><td class="muted" colspan="99">Error loading data (${safe(msg)})</td></tr>`;
  }
}

// ---------- Polling & countdown ----------
function startCountdown(scope, dataUrl){
  const countEl   = document.getElementById(`count-${scope}`);
  const updatedEl = document.getElementById(`updated-${scope}`);
  const bodyEl    = document.getElementById(`body-${scope}`);

  if (!countEl || !updatedEl || !bodyEl) {
    console.warn(`Missing DOM for ${scope}. Check IDs: count-${scope}, updated-${scope}, body-${scope}`);
    return;
  }

  // initial fetches
  fetchAndRender(scope, dataUrl);
  fetchAndRenderSummary(scope); // summary too

  state[scope].countdown = REFRESH_SECONDS;
  countEl.textContent = `${state[scope].countdown}s`;

  if (state[scope].ticking) clearInterval(state[scope].ticking);
  state[scope].ticking = setInterval(() => {
    state[scope].countdown -= 1;
    if (state[scope].countdown <= 0) {
      state[scope].countdown = REFRESH_SECONDS;
      fetchAndRender(scope, dataUrl);
      fetchAndRenderSummary(scope); // refresh summaries on same cadence
    }
    countEl.textContent = `${state[scope].countdown}s`;
  }, 1000);
}

// ---------- Timezone select: populate with ALL IANA zones ----------
function populateTimezones() {
  const tzSelect = document.getElementById("tzSelect");
  if (!tzSelect) return;

  tzSelect.innerHTML = "";

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

  zones.forEach(tz => {
    const opt = document.createElement("option");
    opt.value = tz;
    opt.textContent = tz;
    tzSelect.appendChild(opt);
  });

  try {
    const userTZ = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zones.includes(userTZ)) {
      tzSelect.value = userTZ;
      DISPLAY_TZ = userTZ;
    } else {
      tzSelect.value = "UTC";
      DISPLAY_TZ = "UTC";
    }
  } catch(e) {
    tzSelect.value = "UTC";
    DISPLAY_TZ = "UTC";
  }

  tzSelect.addEventListener("change", () => {
    DISPLAY_TZ = tzSelect.value || "UTC";
    // re-render times immediately (no refetch)
    render("12h");
    render("4h");
    updateLastUpdated("12h");
    updateLastUpdated("4h");
  });
}

// ---------- UI wiring ----------
window.addEventListener('DOMContentLoaded', () => {
  // Search
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e)=> applySearch(e.target.value));
  }

  // Tabs
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

  // Help modal (safe if missing)
  const modal = document.getElementById("modal");
  const helpBtn = document.getElementById("helpBtn");
  const closeModal = document.getElementById("closeModal");
  if (helpBtn && modal) helpBtn.addEventListener("click", () => modal.classList.add("is-open"));
  if (closeModal && modal) closeModal.addEventListener("click", () => modal.classList.remove("is-open"));
  if (modal) modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("is-open"); });

  // Sorting
  attachSorting("12h");
  attachSorting("4h");

  // Timezone dropdown (400+ zones)
  populateTimezones();

  // Start polling
  startCountdown("12h", ENDPOINT_12H);
  startCountdown("4h", ENDPOINT_4H);
});

// time-only, using selected DISPLAY_TZ (e.g., "Africa/Lagos")
function fmtTimeOnlyTZ(date) {
  if (!date) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: DISPLAY_TZ,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true
    }).format(date);
  } catch {
    // fallback
    return date.toLocaleTimeString();
  }
}

function updateLastUpdated(scope) {
  const el = document.getElementById(`updated-${scope}`);
  if (el) el.textContent = fmtTimeOnlyTZ(state[scope].lastUpdated);
}

