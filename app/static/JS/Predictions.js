// ===== Predictions.js (smooth rendering + controls) =====

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

// ---- Smoothness helpers ----
const aborters = { "12h": null, "4h": null };
const RENDER_Q = { "12h": 0, "4h": 0 };

// Virtualization config/state per scope
const VCFG = {
  "12h": { rowHeight: 36, overscan: 12, mounted: false, count: 0, start: 0, end: 0 },
  "4h":  { rowHeight: 36, overscan: 12, mounted: false, count: 0, start: 0, end: 0 },
};

// Coalesce multiple render() calls into one paint
function scheduleRender(scope, fn){
  if (RENDER_Q[scope]) cancelAnimationFrame(RENDER_Q[scope]);
  RENDER_Q[scope] = requestAnimationFrame(()=> {
    RENDER_Q[scope] = 0;
    fn();
  });
}

// Lightweight debounce
function debounce(fn, wait=150){
  let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), wait); };
}

// ---------- Utilities ----------
function safe(v){ return (v===null||v===undefined) ? "—" : String(v).replace(/[&<>"']/g, s=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[s])); }
const fmtNum = (v, d=4) => (isFinite(v) ? Number(v).toLocaleString(undefined,{minimumFractionDigits:d, maximumFractionDigits:d}) : "—");
const fmtPct = (v, d=2) => (isFinite(v) ? Number(v).toFixed(d) + "%" : "—");
const polarityClass = (n)=> (isFinite(n) ? (n<0?"negative":(n>0?"positive":"")) : "");

const fmtBool = (b) => {
  const yes = !!b;
  const icon = yes ? "▲" : "▼";          // or "↑"/"↓"
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

// ---------- HTTP helper (abortable) ----------
async function httpGet(url, controller){
  if (window.axios) {
    const { data } = await axios.get(url, { signal: controller?.signal, headers:{ "Accept":"application/json" }});
    return data;
  } else {
    const res = await fetch(url, { signal: controller?.signal, headers:{ "Accept":"application/json" }});
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
          <span class="acc-pct ${badgeClass(pct)}">${pctTxt}</span>
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
    // summaries are small – no need to abort these
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

// ---------- Rendering (virtualized tables) ----------
function render(scope){
  const table = document.getElementById(`table-${scope}`);
  const tbody = document.getElementById(`body-${scope}`);
  if (!table || !tbody) return;

  const scroller = table.closest('.table-wrap') || table.parentElement;
  const rows = (state[scope].filtered.length ? state[scope].filtered : state[scope].data) || [];
  VCFG[scope].count = rows.length;

  // Empty state
  if (!rows.length){
    tbody.innerHTML = `<tr><td class="muted" colspan="17">No data</td></tr>`;
    setTimesBadge(scope);
    return;
  }

  // First-time mount: create just two spacer rows (top & bottom). No anchor, no inner table.
  if (!VCFG[scope].mounted){
    tbody.innerHTML = `
      <tr data-pad="top"><td colspan="17" style="padding:0;border:0"><div style="height:0px"></div></td></tr>
      <tr data-pad="bot"><td colspan="17" style="padding:0;border:0"><div style="height:0px"></div></td></tr>
    `;

    // Measure row height using a true row with correct number of cells
    const probe = document.createElement('tr');
    probe.innerHTML = [
      `<td class="id-col">1</td>`,
      `<td><strong>Probe</strong><div class="muted">PRB</div></td>`,
      `<td>PRB</td>`,
      `<td class="right-align">$0.000000</td>`,
      `<td class="right-align">$0.000000</td>`,
      `<td class="right-align">$0.000000</td>`,
      `<td class="right-align">0.00%</td>`,
      `<td class="right-align">0.00%</td>`,
      `<td>${fmtBool(true)}</td>`,
      `<td>—</td>`,
      `<td>—</td>`,
      `<td>${fmtTime(new Date().toISOString())}</td>`,
      `<td class="right-align">0.00%</td>`,
      `<td class="right-align">0.00%</td>`,
      `<td class="right-align">0</td>`,
      `<td>${fmtBool(false)}</td>`,
      `<td>${fmtBool(false)}</td>`
    ].join('');
    // Temporarily insert the probe between the padders
    const botPad = tbody.querySelector('tr[data-pad="bot"]');
    tbody.insertBefore(probe, botPad);

    requestAnimationFrame(()=>{
      VCFG[scope].rowHeight = Math.max(24, Math.round(probe.getBoundingClientRect().height || 36));
      probe.remove(); // clean up
      VCFG[scope].mounted = true;
      scheduleRender(scope, ()=> renderVirtualSlice(scope)); // first paint
    });

    // Scroll listener (passive + rAF)
    const onScroll = ()=> scheduleRender(scope, ()=> renderVirtualSlice(scope));
    scroller.addEventListener('scroll', onScroll, { passive: true });
  } else {
    // Subsequent paints
    scheduleRender(scope, ()=> renderVirtualSlice(scope));
  }

  setTimesBadge(scope);

  function renderVirtualSlice(scope){
    const scroller = table.closest('.table-wrap') || table.parentElement;
    const topPadDiv = tbody.querySelector('tr[data-pad="top"] > td > div');
    const botPadDiv = tbody.querySelector('tr[data-pad="bot"] > td > div');

    const h = scroller.clientHeight || 400;
    const scrollTop = scroller.scrollTop || 0;
    const rh = VCFG[scope].rowHeight;
    const total = VCFG[scope].count;
    const perView = Math.max(1, Math.ceil(h / rh));
    const over = VCFG[scope].overscan;

    const start = Math.max(0, Math.floor(scrollTop / rh) - over);
    const end = Math.min(total, start + perView + over*2);

    if (start === VCFG[scope].start && end === VCFG[scope].end) return;
    VCFG[scope].start = start; VCFG[scope].end = end;

    // Build only visible rows as real <tr> with 17 <td>s (to match 17 <th>s)
    const src = (state[scope].filtered.length ? state[scope].filtered : state[scope].data);
    const visible = src.slice(start, end);

    const frag = document.createDocumentFragment();
    visible.forEach((item, idx) => {
      const displayId = item.id ?? item._id ?? item.asset_id ?? item.rank ?? (start + idx + 1);
      const status = String(item.prediction_status ?? '').trim().toLowerCase().replace(/\s*[-–—]\s*/g, ' - ');
      const tr = document.createElement('tr');
      if (status === 'buy - reached') tr.className = 'reached';
      tr.innerHTML = [
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
        `<td>${safe(item.achievement)}</td>`,
        `<td>${fmtTime(item.time_reached)}</td>`,
        `<td class="right-align"><span class="${polarityClass(item.dynamic_tp)}">${fmtPct(item.dynamic_tp)}</span></td>`,
        `<td class="right-align"><span class="${polarityClass(item.dynamic_sl)}">${fmtPct(item.dynamic_sl)}</span></td>`,
        `<td class="right-align"><span class="${polarityClass(item.rrr)}">${fmtNum(item.rrr, 2)}</span></td>`,
        `<td>${fmtBool(item.sl_status)}</td>`,
        `<td>${fmtBool(item.price_change_status)}</td>`
      ].join('');
      frag.appendChild(tr);
    });

    // Remove any previously rendered visible rows (i.e., everything except the two padders)
    // and re-insert the new slice in between.
    // We do this by clearing between the padders to keep DOM operations minimal.
    let node = tbody.firstChild;
    const keep = new Set(['top', 'bot']);
    while (node) {
      const next = node.nextSibling;
      if (node.nodeType === 1 && node.tagName === 'TR' && !node.dataset.pad) {
        tbody.removeChild(node);
      }
      node = next;
    }
    const botPad = tbody.querySelector('tr[data-pad="bot"]');
    tbody.insertBefore(frag, botPad);

    // Update padders
    const topH = start * rh;
    const botH = Math.max(0, (total - end) * rh);
    topPadDiv.style.height = `${topH}px`;
    botPadDiv.style.height = `${botH}px`;
  }
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

  // 👇 force re-render of the current virtual window
  invalidateVirtual(scope);
  scheduleRender(scope, ()=> render(scope));
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
    invalidateVirtual(scope);           // 👈 important
    scheduleRender(scope, ()=> render(scope));
  });
}


// ---------- Fetch / render (tables) ----------
async function fetchAndRender(scope, url){
  if (state[scope].fetching) {
    // Cancel the in-flight one and continue with the newest
    try { aborters[scope]?.abort(); } catch {}
  }
  const controller = new AbortController();
  aborters[scope] = controller;
  state[scope].fetching = true;
  try{
    const raw = await httpGet(url, controller);
    const list = Array.isArray(raw) ? raw
              : Array.isArray(raw?.data) ? raw.data
              : (raw ? [raw] : []);

    state[scope].data = list;

    // Preserve current search without recomputing thrash
    const q = document.getElementById("searchInput")?.value?.trim().toLowerCase() || "";
    if (q) {
      state[scope].filtered = state[scope].data.filter(it =>
        String(it.asset_name||"").toLowerCase().includes(q) ||
        String(it.symbol||"").toLowerCase().includes(q)
      );
    } else {
      state[scope].filtered = [];
    }

    // Keep current sort across refreshes
    applyCurrentSort(scope);
    invalidateVirtual(scope); 

    // Repaint via scheduler (keeps 60fps)
    scheduleRender(scope, ()=> render(scope));

    state[scope].lastUpdated = new Date();
    updateLastUpdated(scope);
  } catch (err){
    if (err?.name !== 'AbortError') {
      console.error(`Failed to fetch ${scope}:`, err);
      showError(scope, err);
    }
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

// ---------- Polling & countdown (drift-proof, visibility-safe) ----------
const REFRESH_MS = REFRESH_SECONDS * 1000;

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
  fetchAndRenderSummary(scope);

  // schedule state
  state[scope].nextRefreshAt = Date.now() + REFRESH_MS;
  let displayTimer = null;   // updates the "XXs" text
  let fetchTimer   = null;   // schedules the next fetch

  const updateCountdown = ()=>{
    const remaining = Math.max(0, state[scope].nextRefreshAt - Date.now());
    countEl.textContent = `${Math.ceil(remaining / 1000)}s`;
  };

  const scheduleFetchLoop = ()=>{
    clearTimeout(fetchTimer);
    const delay = Math.max(0, state[scope].nextRefreshAt - Date.now());
    fetchTimer = setTimeout(async ()=>{
      // try/catch just to be safe; don't let errors break the loop
      try {
        await fetchAndRender(scope, dataUrl);
        fetchAndRenderSummary(scope);
      } finally {
        // set next target based on the *previous* target, not "now",
        // so the cadence is stable even if a refresh is delayed
        state[scope].nextRefreshAt += REFRESH_MS;

        // If we fell behind (e.g., background throttling), skip forward
        // in REFRESH_MS chunks until nextRefreshAt is in the future.
        while (state[scope].nextRefreshAt <= Date.now()) {
          state[scope].nextRefreshAt += REFRESH_MS;
        }

        scheduleFetchLoop();
        updateCountdown();
      }
    }, delay);
  };

  const startDisplayTimer = ()=>{
    if (displayTimer) return;
    updateCountdown();
    displayTimer = setInterval(updateCountdown, 1000);
  };
  const stopDisplayTimer = ()=>{
    if (displayTimer) { clearInterval(displayTimer); displayTimer = null; }
  };

  // Visibility handler: do NOT reset the countdown.
  const onVis = ()=>{
    const hidden = document.hidden;

    if (hidden) {
      // Save bandwidth and cancel any in-flight request
      try { aborters[scope]?.abort(); } catch {}
      // Optional: stop the UI updater to save CPU
      stopDisplayTimer();
      // We do NOT cancel or change the scheduled fetch target;
      // the loop will catch up when the browser lets timers run again.
    } else {
      // On return: if overdue, fetch immediately; otherwise just resume the UI updater
      if (Date.now() >= state[scope].nextRefreshAt) {
        // Run one fetch now and reschedule from the last target (+REFRESH_MS)
        clearTimeout(fetchTimer);
        (async ()=>{
          try {
            await fetchAndRender(scope, dataUrl);
            fetchAndRenderSummary(scope);
          } finally {
            state[scope].nextRefreshAt += REFRESH_MS;
            while (state[scope].nextRefreshAt <= Date.now()) {
              state[scope].nextRefreshAt += REFRESH_MS;
            }
            scheduleFetchLoop();
            updateCountdown();
          }
        })();
      } else {
        // Not overdue—just ensure the loop is scheduled
        scheduleFetchLoop();
        updateCountdown();
      }
      startDisplayTimer();
    }
  };
  document.addEventListener('visibilitychange', onVis);

  // Kick things off
  startDisplayTimer();
  scheduleFetchLoop();
}


// ---------- Timezone helpers ----------
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

function applyCurrentSort(scope){
  const key = state[scope].sortKey;
  const dir = state[scope].sortDir;
  const type = document
    .querySelector(`#table-${scope} th[data-key="${key}"]`)
    ?.getAttribute("data-type") || "string";

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
}

// ---------- UI wiring ----------
window.addEventListener('DOMContentLoaded', () => {
  // Search (debounced)
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    const onSearch = debounce((val)=> applySearch(val), 180);
    searchInput.addEventListener("input", (e)=> onSearch(e.target.value));
    searchInput.addEventListener("keydown", (e)=> { if (e.key === "Enter") e.currentTarget.blur(); });
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
    scheduleRender("12h", ()=> { render("12h"); updateLastUpdated("12h"); });
    scheduleRender("4h", ()=> { render("4h"); updateLastUpdated("4h"); });
  });
}

function invalidateVirtual(scope){
  // Force next renderVirtualSlice to rebuild even if start/end are the same
  VCFG[scope].start = -1;
  VCFG[scope].end = -1;
}
