/* ─────────────────────────────────────────────────────
   Event Studio — app.js
   ───────────────────────────────────────────────────── */

const form = document.getElementById("analysis-form");
const runButton = document.getElementById("run-button");
const statusTitle = document.getElementById("status-title");
const statusCopy = document.getElementById("status-copy");
const downloadLink = document.getElementById("download-link");
const metricGenerated = document.getElementById("metric-generated");
const metricMatch = document.getElementById("metric-match");
const metricSequence = document.getElementById("metric-sequence");
const metricFrameError = document.getElementById("metric-frame-error");
const typeCounts = document.getElementById("type-counts");
const generatedTableWrap = document.getElementById("generated-table-wrap");
const referenceTableWrap = document.getElementById("reference-table-wrap");
const navStatus = document.getElementById("nav-status");

/* ─── HELP MODAL ─── */
const helpBtn = document.getElementById("help-btn");
const helpModal = document.getElementById("help-modal");
const closeHelp = document.querySelector(".modal-close-btn");

if (helpBtn && helpModal) {
  helpBtn.addEventListener("click", () => helpModal.classList.remove("is-hidden"));
  if (closeHelp) {
    closeHelp.addEventListener("click", () => helpModal.classList.add("is-hidden"));
  }
  helpModal.addEventListener("click", (e) => {
    if (e.target === helpModal) helpModal.classList.add("is-hidden");
  });
}

/* ─── MODE TABS ─── */
let currentMode = "sample";

document.querySelectorAll(".mode-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    currentMode = tab.dataset.mode;

    const isSample = currentMode === "sample";
    document.getElementById("sample-inputs").style.display = isSample ? "block" : "none";
    document.getElementById("upload-inputs").style.display = isSample ? "none" : "block";
    document.getElementById("home-file").disabled = isSample;
    document.getElementById("away-file").disabled = isSample;
    document.getElementById("game-id").disabled = !isSample;
  });
});

/* ─── FORM SUBMIT ─── */
form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const startFrame = document.getElementById("start-frame").value;
  const endFrame = document.getElementById("end-frame").value;

  setLoadingState(true);

  try {
    let response;
    if (currentMode === "sample") {
      const params = new URLSearchParams();
      params.set("gameId", document.getElementById("game-id").value);
      if (startFrame) params.set("startFrame", startFrame);
      if (endFrame) params.set("endFrame", endFrame);
      response = await fetch(`/api/analyze?${params.toString()}`);
    } else {
      const homeFiles = document.getElementById("home-file").files;
      const awayFiles = document.getElementById("away-file").files;
      if (!homeFiles.length || !awayFiles.length) {
        throw new Error("Please select both Home and Away CSV files.");
      }
      const formData = new FormData();
      formData.append("home_file", homeFiles[0]);
      formData.append("away_file", awayFiles[0]);
      if (startFrame) formData.append("start_frame", startFrame);
      if (endFrame) formData.append("end_frame", endFrame);
      response = await fetch("/api/upload", { method: "POST", body: formData });
    }

    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Analysis failed");

    renderResults(payload);
  } catch (error) {
    statusTitle.textContent = "Analysis failed";
    statusCopy.textContent = error.message;
    downloadLink.classList.add("is-hidden");
    navStatus.innerHTML = '<span class="status-dot" style="background:#ef4444;box-shadow:0 0 0 3px rgba(239,68,68,0.15)"></span> Error';
  } finally {
    setLoadingState(false);
  }
});

/* ─── LOADING STATE ─── */
function setLoadingState(isLoading) {
  runButton.disabled = isLoading;
  runButton.classList.toggle("is-loading", isLoading);

  if (isLoading) {
    runButton.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
      Processing...`;
    statusTitle.textContent = "Running analysis";
    statusCopy.textContent = "Generating event feed and validating against reference labels…";
    navStatus.innerHTML = '<span class="status-dot" style="background:#f59e0b;box-shadow:0 0 0 3px rgba(245,158,11,0.15)"></span> Processing';
  } else {
    runButton.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21 5,3"/></svg>
      Run Analysis`;
  }
}

/* ─── RENDER RESULTS ─── */
function renderResults(payload) {
  const gameLabel = payload.game.id === "uploaded" ? "Uploaded Data" : `Sample Game ${payload.game.id}`;

  statusTitle.textContent = `Analysis complete — ${gameLabel}`;
  statusCopy.textContent = `${payload.summary.eventCount} events generated, showing ${payload.summary.previewCount} preview rows.`;
  navStatus.innerHTML = '<span class="status-dot"></span> Complete';

  // Metrics
  if (payload.validation) {
    metricGenerated.textContent = payload.validation.generatedEventCount.toLocaleString();
    metricMatch.textContent = fmtPct(payload.validation.matchedRatio);
    metricSequence.textContent = fmtPct(payload.validation.sequenceAgreement);
    metricFrameError.textContent = payload.validation.meanStartFrameError == null
      ? "—" : payload.validation.meanStartFrameError.toFixed(2);
  } else {
    metricGenerated.textContent = payload.summary.eventCount.toLocaleString();
    metricMatch.textContent = "—";
    metricSequence.textContent = "—";
    metricFrameError.textContent = "—";
  }

  // Download
  if (payload.csvData) {
    const blob = new Blob([payload.csvData], { type: "text/csv" });
    downloadLink.href = URL.createObjectURL(blob);
    downloadLink.download = "events.csv";
  } else {
    downloadLink.href = payload.downloadUrl;
    downloadLink.download = "";
  }
  downloadLink.classList.remove("is-hidden");

  // Tables
  typeCounts.innerHTML = buildTypeCountsTable(payload.validation?.typeCounts || []);
  typeCounts.classList.remove("empty-msg");
  generatedTableWrap.innerHTML = buildDataTable(payload.events);
  generatedTableWrap.classList.remove("empty-msg");
  referenceTableWrap.innerHTML = buildDataTable(payload.referencePreview);
  referenceTableWrap.classList.remove("empty-msg");

  // Pitch
  drawPitch(payload.events);

  // Key Moments
  buildKeyMoments(payload.events);

  // Store all events for replay linking
  window.__allEvents = payload.events;
}

/* ─── TABLE BUILDERS ─── */
function buildTypeCountsTable(rows) {
  if (!rows || !rows.length) return '<div class="empty-msg">No type counts available.</div>';

  const body = rows.map(r => {
    const cls = r.Delta === 0 ? "pill-neutral" : (r.Delta > 0 ? "pill-positive" : "pill-negative");
    const lbl = r.Delta > 0 ? `+${r.Delta}` : `${r.Delta}`;
    return `<tr><td>${esc(r.Type)}</td><td>${r.Generated}</td><td>${r.Reference}</td><td><span class="${cls}">${lbl}</span></td></tr>`;
  }).join("");

  return `<table class="type-counts-table"><thead><tr><th>Type</th><th>Generated</th><th>Reference</th><th>Delta</th></tr></thead><tbody>${body}</tbody></table>`;
}

function buildDataTable(rows) {
  if (!rows || !rows.length) return '<div class="empty-msg">No rows available.</div>';
  const cols = Object.keys(rows[0]);
  const head = cols.map(c => `<th>${esc(c)}</th>`).join("");
  const body = rows.map(r => `<tr>${cols.map(c => `<td>${esc(norm(r[c]))}</td>`).join("")}</tr>`).join("");
  return `<table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

/* ─── PITCH DRAWING ─── */
function drawPitch(events) {
  const canvas = document.getElementById("pitch-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const pad = 40;
  const pw = W - pad * 2, ph = H - pad * 2;

  // Background
  ctx.fillStyle = "#0c1222";
  ctx.fillRect(0, 0, W, H);

  // Field grass
  ctx.fillStyle = "#132215";
  ctx.fillRect(pad, pad, pw, ph);

  // Helper
  function line(x1, y1, x2, y2) {
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  }
  function rect(x, y, w, h) { ctx.strokeRect(x, y, w, h); }

  ctx.strokeStyle = "rgba(255,255,255,0.25)";
  ctx.lineWidth = 1.5;

  // Outline
  rect(pad, pad, pw, ph);
  // Halfway
  line(W / 2, pad, W / 2, pad + ph);
  // Center circle
  ctx.beginPath(); ctx.arc(W / 2, H / 2, 60, 0, Math.PI * 2); ctx.stroke();
  // Center dot
  ctx.beginPath(); ctx.arc(W / 2, H / 2, 3, 0, Math.PI * 2); ctx.fillStyle = "rgba(255,255,255,0.3)"; ctx.fill();

  // Penalty areas
  const paW = pw * 0.16, paH = ph * 0.44;
  rect(pad, H / 2 - paH / 2, paW, paH);
  rect(pad + pw - paW, H / 2 - paH / 2, paW, paH);

  // Goal areas
  const gaW = pw * 0.055, gaH = ph * 0.2;
  rect(pad, H / 2 - gaH / 2, gaW, gaH);
  rect(pad + pw - gaW, H / 2 - gaH / 2, gaW, gaH);

  // Penalty arcs
  ctx.save();
  ctx.beginPath();
  ctx.rect(pad + paW, pad, pw - paW * 2, ph); ctx.clip();
  ctx.beginPath(); ctx.arc(pad + paW - 10, H / 2, 55, -0.7, 0.7); ctx.stroke();
  ctx.restore();
  ctx.save();
  ctx.beginPath();
  ctx.rect(pad, pad, pw - paW, ph); ctx.clip();
  ctx.beginPath(); ctx.arc(pad + pw - paW + 10, H / 2, 55, Math.PI - 0.7, Math.PI + 0.7); ctx.stroke();
  ctx.restore();

  // Corner arcs
  const cr = 12;
  [[pad, pad, 0, Math.PI/2], [pad+pw, pad, Math.PI/2, Math.PI], [pad+pw, pad+ph, Math.PI, 3*Math.PI/2], [pad, pad+ph, 3*Math.PI/2, 2*Math.PI]].forEach(([cx, cy, s, e]) => {
    ctx.beginPath(); ctx.arc(cx, cy, cr, s, e); ctx.stroke();
  });

  if (!events || !events.length) {
    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.font = "500 16px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Run an analysis to see events on the pitch", W / 2, H / 2);
    return;
  }

  // Plot events
  const homeClr = "#38bdf8";
  const awayClr = "#fb923c";
  const shotClr = "#f43f5e";

  events.forEach(ev => {
    const sx = parseFloat(ev["Start X"]), sy = parseFloat(ev["Start Y"]);
    if (isNaN(sx) || isNaN(sy)) return;
    const px = pad + sx * pw, py = pad + sy * ph;
    const ex = parseFloat(ev["End X"]), ey = parseFloat(ev["End Y"]);
    const clr = ev.Team === "Home" ? homeClr : awayClr;

    if (ev.Type === "PASS" && !isNaN(ex) && !isNaN(ey)) {
      const pex = pad + ex * pw, pey = pad + ey * ph;
      // Line
      ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(pex, pey);
      ctx.strokeStyle = clr + "80"; ctx.lineWidth = 1.2; ctx.stroke();
      // Arrowhead
      const a = Math.atan2(pey - py, pex - px);
      ctx.beginPath();
      ctx.moveTo(pex, pey);
      ctx.lineTo(pex - 6 * Math.cos(a - 0.45), pey - 6 * Math.sin(a - 0.45));
      ctx.lineTo(pex - 6 * Math.cos(a + 0.45), pey - 6 * Math.sin(a + 0.45));
      ctx.closePath(); ctx.fillStyle = clr + "80"; ctx.fill();
    } else if (ev.Type === "SHOT") {
      ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2);
      ctx.fillStyle = shotClr; ctx.fill();
      ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.stroke();
      // Glow
      ctx.beginPath(); ctx.arc(px, py, 12, 0, Math.PI * 2);
      ctx.fillStyle = shotClr + "20"; ctx.fill();
    } else {
      ctx.beginPath(); ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = clr + "b0"; ctx.fill();
    }
  });
}

/* ─── HELPERS ─── */
function norm(v) { return v === null || v === undefined || v === "" ? "—" : String(v); }
function fmtPct(v) { return `${(v * 100).toFixed(1)}%`; }
function esc(v) {
  return String(v).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

/* ─── SPIN ANIMATION (injected) ─── */
const style = document.createElement("style");
style.textContent = `@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin 1s linear infinite}`;
document.head.appendChild(style);

/* ═══════════════════════════════════════════════════════
   MATCH REPLAY SYSTEM
   ═══════════════════════════════════════════════════════ */

const replayCanvas = document.getElementById("replay-canvas");
const replayCtx = replayCanvas ? replayCanvas.getContext("2d") : null;
const replayLoad = document.getElementById("replay-load");
const replayPlay = document.getElementById("replay-play");
const replayScrubber = document.getElementById("replay-scrubber");
const replayTimeEl = document.getElementById("replay-time");
const playIcon = document.getElementById("play-icon");
const pauseIcon = document.getElementById("pause-icon");

let replayFrames = [];
let replayIdx = 0;
let replayPlaying = false;
let replaySpeed = 1;
let replayAnim = null;
let lastGameId = null;

// Enable "Load Frames" after a successful analysis
const origRender = renderResults;
renderResults = function(payload) {
  origRender.call(this, payload);
  if (payload.game.id !== "uploaded") {
    lastGameId = payload.game.id;
    replayLoad.disabled = false;
  }
};

// Load Frames button
if (replayLoad) {
  replayLoad.addEventListener("click", async () => {
    if (!lastGameId) return;
    replayLoad.disabled = true;
    replayLoad.textContent = "Loading…";

    try {
      // Use custom replay range if provided, else fall back to analysis range
      const rStart = document.getElementById("replay-start").value || document.getElementById("start-frame").value;
      const rEnd = document.getElementById("replay-end").value || document.getElementById("end-frame").value;
      let url = `/api/frames?gameId=${lastGameId}&sampleRate=3`;
      if (rStart) url += `&startFrame=${rStart}`;
      if (rEnd) url += `&endFrame=${rEnd}`;

      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");

      replayFrames = data.frames;
      replayIdx = 0;
      replayScrubber.max = replayFrames.length - 1;
      replayScrubber.value = 0;
      replayScrubber.disabled = false;
      replayPlay.disabled = false;
      replayLoad.textContent = `${replayFrames.length} frames loaded`;
      drawReplayFrame(0);
    } catch (e) {
      replayLoad.textContent = "Load failed";
      setTimeout(() => { replayLoad.textContent = "Load Frames"; replayLoad.disabled = false; }, 2000);
    }
  });
}

// Play/Pause
if (replayPlay) {
  replayPlay.addEventListener("click", () => {
    if (!replayFrames.length) return;
    replayPlaying = !replayPlaying;
    playIcon.style.display = replayPlaying ? "none" : "block";
    pauseIcon.style.display = replayPlaying ? "block" : "none";
    if (replayPlaying) tickReplay();
    else cancelAnimationFrame(replayAnim);
  });
}

// Scrubber
if (replayScrubber) {
  replayScrubber.addEventListener("input", () => {
    replayIdx = parseInt(replayScrubber.value);
    drawReplayFrame(replayIdx);
  });
}

// Speed buttons
document.querySelectorAll(".speed-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    replaySpeed = parseInt(btn.dataset.speed);
  });
});

function tickReplay() {
  if (!replayPlaying) return;
  replayIdx += replaySpeed;
  if (replayIdx >= replayFrames.length) { replayIdx = 0; }
  replayScrubber.value = replayIdx;
  drawReplayFrame(replayIdx);
  replayAnim = requestAnimationFrame(tickReplay);
}

function drawReplayFrame(idx) {
  if (!replayCtx || !replayFrames.length) return;
  const fr = replayFrames[idx];
  const W = replayCanvas.width, H = replayCanvas.height;
  const pad = 40, pw = W - pad * 2, ph = H - pad * 2;

  // Clear
  replayCtx.fillStyle = "#0c1222";
  replayCtx.fillRect(0, 0, W, H);

  // Field
  replayCtx.fillStyle = "#132215";
  replayCtx.fillRect(pad, pad, pw, ph);

  // Lines
  replayCtx.strokeStyle = "rgba(255,255,255,0.2)";
  replayCtx.lineWidth = 1.5;
  replayCtx.strokeRect(pad, pad, pw, ph);
  replayCtx.beginPath(); replayCtx.moveTo(W/2, pad); replayCtx.lineTo(W/2, pad+ph); replayCtx.stroke();
  replayCtx.beginPath(); replayCtx.arc(W/2, H/2, 60, 0, Math.PI*2); replayCtx.stroke();

  // Penalty areas
  const paW = pw*0.16, paH = ph*0.44;
  replayCtx.strokeRect(pad, H/2-paH/2, paW, paH);
  replayCtx.strokeRect(pad+pw-paW, H/2-paH/2, paW, paH);

  // Goal areas
  const gaW = pw*0.055, gaH = ph*0.2;
  replayCtx.strokeRect(pad, H/2-gaH/2, gaW, gaH);
  replayCtx.strokeRect(pad+pw-gaW, H/2-gaH/2, gaW, gaH);

  // Draw home players (blue)
  fr.home.forEach(([x, y]) => {
    const px = pad + x * pw, py = pad + y * ph;
    replayCtx.beginPath();
    replayCtx.arc(px, py, 8, 0, Math.PI * 2);
    replayCtx.fillStyle = "#38bdf8";
    replayCtx.fill();
    replayCtx.strokeStyle = "#0c4a6e";
    replayCtx.lineWidth = 2;
    replayCtx.stroke();

    // Hover effect (Home)
    if (__mouseX !== null && __mouseY !== null) {
      const dist = Math.sqrt((px - __mouseX) ** 2 + (py - __mouseY) ** 2);
      if (dist < 10) {
        replayCtx.fillStyle = "white";
        replayCtx.font = "bold 12px Inter, sans-serif";
        replayCtx.textAlign = "center";
        replayCtx.fillText(`Home #${num}`, px, py - 15);
      }
    }
  });

  // Draw away players (orange)
  fr.away.forEach(([x, y]) => {
    const px = pad + x * pw, py = pad + y * ph;
    replayCtx.beginPath();
    replayCtx.arc(px, py, 8, 0, Math.PI * 2);
    replayCtx.fillStyle = "#fb923c";
    replayCtx.fill();
    replayCtx.strokeStyle = "#7c2d12";
    replayCtx.lineWidth = 2;
    replayCtx.stroke();

    // Hover effect (Away)
    if (__mouseX !== null && __mouseY !== null) {
      const dist = Math.sqrt((px - __mouseX) ** 2 + (py - __mouseY) ** 2);
      if (dist < 10) {
        replayCtx.fillStyle = "white";
        replayCtx.font = "bold 12px Inter, sans-serif";
        replayCtx.textAlign = "center";
        replayCtx.fillText(`Away #${num}`, px, py - 15);
      }
    }
  });

  // Draw ball (white with glow)
  if (fr.ball) {
    const bx = pad + fr.ball[0] * pw, by = pad + fr.ball[1] * ph;
    // Glow
    replayCtx.beginPath();
    replayCtx.arc(bx, by, 14, 0, Math.PI * 2);
    replayCtx.fillStyle = "rgba(255,255,255,0.1)";
    replayCtx.fill();
    // Ball
    replayCtx.beginPath();
    replayCtx.arc(bx, by, 5, 0, Math.PI * 2);
    replayCtx.fillStyle = "#fff";
    replayCtx.fill();
    replayCtx.strokeStyle = "rgba(0,0,0,0.3)";
    replayCtx.lineWidth = 1;
    replayCtx.stroke();
  }

  // HUD overlay
  replayCtx.fillStyle = "rgba(255,255,255,0.7)";
  replayCtx.font = "500 12px Inter, sans-serif";
  replayCtx.textAlign = "left";
  replayCtx.fillText(`Frame: ${fr.frame}   Period: ${fr.period}   Time: ${fr.time.toFixed(1)}s`, pad + 8, pad + 18);

  // Update time display
  const total = replayFrames[replayFrames.length - 1].time;
  replayTimeEl.textContent = `${fmtTime(fr.time)} / ${fmtTime(total)}`;
}

function fmtTime(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

let __mouseX = null;
let __mouseY = null;
if (replayCanvas) {
  replayCanvas.addEventListener("mousemove", (e) => {
    const rect = replayCanvas.getBoundingClientRect();
    __mouseX = (e.clientX - rect.left) * (replayCanvas.width / rect.width);
    __mouseY = (e.clientY - rect.top) * (replayCanvas.height / rect.height);
  });
  replayCanvas.addEventListener("mouseleave", () => {
    __mouseX = null;
    __mouseY = null;
  });
}

// Draw empty replay pitch on load
if (replayCtx) {
  const W = replayCanvas.width, H = replayCanvas.height;
  replayCtx.fillStyle = "#0c1222";
  replayCtx.fillRect(0, 0, W, H);
  replayCtx.fillStyle = "#132215";
  replayCtx.fillRect(40, 40, W - 80, H - 80);
  replayCtx.strokeStyle = "rgba(255,255,255,0.2)";
  replayCtx.lineWidth = 1.5;
  replayCtx.strokeRect(40, 40, W - 80, H - 80);
  replayCtx.beginPath(); replayCtx.moveTo(W/2, 40); replayCtx.lineTo(W/2, H-40); replayCtx.stroke();
  replayCtx.beginPath(); replayCtx.arc(W/2, H/2, 60, 0, Math.PI*2); replayCtx.stroke();
  replayCtx.fillStyle = "rgba(255,255,255,0.3)";
  replayCtx.font = "500 16px Inter, sans-serif";
  replayCtx.textAlign = "center";
  replayCtx.fillText("Run analysis then click \"Load Frames\" to start replay", W/2, H/2);
}

/* ═══════════════════════════════════════════════════════
   KEY MOMENTS & BUILD-UP ANALYSIS
   ═══════════════════════════════════════════════════════ */

function buildKeyMoments(events) {
  const container = document.getElementById("moments-list");
  if (!container || !events || !events.length) return;

  // Find all SHOT events
  const shots = [];
  events.forEach((ev, idx) => {
    if (ev.Type === "SHOT") {
      shots.push({ event: ev, index: idx });
    }
  });

  if (shots.length === 0) {
    container.innerHTML = '<div class="empty-msg">No shots detected in this analysis. Try running with more frames.</div>';
    return;
  }

  let html = '';
  shots.forEach((shot, si) => {
    const ev = shot.event;
    const shotFrame = parseInt(ev["Start Frame"]) || 0;
    const shotTime = parseFloat(ev["Start Time [s]"]) || 0;

    // Is it a goal? Check if end position is near the goal line (x close to 0 or 1)
    const endX = parseFloat(ev["End X"]);
    const isGoal = !isNaN(endX) && (endX > 0.95 || endX < 0.05);
    const badgeClass = isGoal ? "goal" : "shot";
    const badgeText = isGoal ? "⚽ GOAL" : "🔴 SHOT";

    // Trace backwards to find build-up chain (same team, events leading up to shot)
    const chain = [];
    const shotTeam = ev.Team;
    for (let i = shot.index - 1; i >= 0 && chain.length < 8; i--) {
      const prev = events[i];
      if (prev.Team !== shotTeam) break; // possession changed
      if (prev.Type === "BALL LOST" || prev.Type === "BALL OUT") break;
      chain.unshift(prev);
    }

    // Build chain HTML
    let chainHtml = '';
    if (chain.length > 0) {
      chainHtml = '<div class="chain-title">Build-up sequence</div><div class="chain-events">';
      chain.forEach((c, ci) => {
        const player = c.From || c.To || '—';
        chainHtml += `<div class="chain-event"><span class="chain-type">${esc(c.Type)}</span><span class="chain-player">${esc(player)}</span></div>`;
        if (ci < chain.length - 1) chainHtml += '<span class="chain-arrow">→</span>';
      });
      // Add the shot itself at the end
      chainHtml += `<span class="chain-arrow">→</span><div class="chain-event" style="border-color:var(--red);"><span class="chain-type" style="color:var(--red);">${isGoal ? "GOAL" : "SHOT"}</span><span class="chain-player">${esc(ev.From || '—')}</span></div>`;
      chainHtml += '</div>';
    }

    // Calculate the start frame to watch (beginning of build-up chain)
    const chainStartFrame = chain.length > 0 ? (parseInt(chain[0]["Start Frame"]) || shotFrame - 100) : shotFrame - 100;
    const chainEndFrame = shotFrame + 50;

    html += `
      <div class="moment-card">
        <div class="moment-header">
          <span class="moment-badge ${badgeClass}">${badgeText}</span>
          <span class="moment-team">${esc(ev.Team)} · ${esc(ev.From || 'Unknown')}</span>
          <span class="moment-time">Frame ${shotFrame} · ${fmtTime(shotTime)}</span>
        </div>
        ${chainHtml}
        <div class="moment-actions">
          <button class="btn-ghost" onclick="watchMoment(${chainStartFrame}, ${chainEndFrame})">
            ▶ Watch Build-Up
          </button>
          <button class="btn-ghost" onclick="watchMoment(${shotFrame - 25}, ${shotFrame + 25})">
            🎯 Watch Shot
          </button>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
  container.classList.remove("empty-msg");
}

/**
 * Sets the replay frame range inputs and auto-triggers frame loading
 */
function watchMoment(startFrame, endFrame) {
  const replayStartInput = document.getElementById("replay-start");
  const replayEndInput = document.getElementById("replay-end");
  replayStartInput.value = Math.max(0, startFrame);
  replayEndInput.value = endFrame;

  // Scroll to replay
  document.getElementById("replay-card").scrollIntoView({ behavior: "smooth", block: "start" });

  // Auto-trigger load
  setTimeout(() => {
    document.getElementById("replay-load").click();
  }, 400);
}

