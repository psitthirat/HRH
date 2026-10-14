(() => {
  "use strict";

  const CAT_LIGHT = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"];
  const CAT_DARK = ["#3987e5", "#008300", "#d55181", "#c98500", "#199e70", "#d95926", "#9085e9", "#e66767"];

  const state = {
    level: "hregion", // "hregion" | "prov"
    hrh: "doctor",
    yearIndex: 9,
    mode: "snapshot", // "snapshot" | "change"
    theme: "auto",
  };

  let data = null;
  let map = null;
  let tileLayer = null;
  let geoLayers = {}; // level -> L.geoJSON layer
  let geoLayer = null; // the currently attached layer

  const $ = (id) => document.getElementById(id);
  const tooltipEl = $("map-tooltip");

  // ---------- color helpers ----------

  function hexToRgb(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgbToHex([r, g, b]) {
    const c = (v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0");
    return `#${c(r)}${c(g)}${c(b)}`;
  }
  function lerpRgb(a, b, t) {
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  }

  function isDark() {
    if (state.theme === "dark") return true;
    if (state.theme === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function statusHexes() {
    const dark = isDark();
    return {
      red: dark ? "#e66767" : "#d03b3b",
      yellow: "#fab219",
      green: "#0ca30c",
    };
  }

  // Red -> yellow -> green (traffic-light convention), reusing the status
  // palette's critical/warning/good hues. The same 3-stop ramp backs both
  // magnitude (snapshot density, low=red/high=green) and direction
  // (10-year change, decrease=red/no change=yellow/increase=green) — the
  // diverging case just remaps its -1..1 input onto the ramp's 0..1 domain.
  function redYellowGreen(t) {
    t = Math.max(0, Math.min(1, t));
    const { red, yellow, green } = statusHexes();
    if (t < 0.5) return rgbToHex(lerpRgb(hexToRgb(red), hexToRgb(yellow), t / 0.5));
    return rgbToHex(lerpRgb(hexToRgb(yellow), hexToRgb(green), (t - 0.5) / 0.5));
  }

  function sequentialColor(t) {
    return redYellowGreen(t);
  }

  function divergingColor(t) {
    t = Math.max(-1, Math.min(1, t));
    return redYellowGreen((t + 1) / 2);
  }

  function seriesColor(index) {
    const arr = isDark() ? CAT_DARK : CAT_LIGHT;
    return arr[index % arr.length];
  }

  function fmt(v, digits = 1) {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    return v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  // ---------- data access ----------

  function years() { return data.years; }
  function currentYear() { return years()[state.yearIndex]; }
  function levelData() { return data.levels[state.level]; }
  function levelLabel() { return i18n.t(`level.${state.level}`, levelData().label); }

  // Thai readers expect the Buddhist Era; the underlying data stays in CE.
  function fmtYear(y) { return i18n.lang === "th" ? String(y + 543) : String(y); }

  // Region names: the data file carries the Thai name as the id and the English
  // name as the label, so the language toggle simply picks the other one.
  function regionLabel(region) {
    return i18n.lang === "th" ? region.id : (region.label || region.id);
  }

  function densityFor(hrh, year, regionId) {
    const byYear = levelData().density[hrh][String(year)];
    return byYear ? (byYear[regionId] ?? 0) : 0;
  }

  function allDensitiesFor(hrh, year) {
    return levelData().regions.map((r) => densityFor(hrh, year, r.id));
  }

  function avgDensity(hrh, year) {
    const vals = allDensitiesFor(hrh, year);
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }

  // Fixed color-scale ceiling per level+cadre: the max region/year value
  // across all 10 years, rounded up to the nearest 10 — so a region's color
  // means the same absolute density no matter which year is selected.
  const domainMaxCache = {};
  function densityDomainMax(hrh) {
    const key = `${state.level}:${hrh}`;
    if (domainMaxCache[key] !== undefined) return domainMaxCache[key];
    const allVals = years().flatMap((yr) => allDensitiesFor(hrh, yr));
    const max = Math.max(...allVals, 1e-6);
    const rounded = Math.ceil(max / 10) * 10;
    domainMaxCache[key] = rounded;
    return rounded;
  }

  // Fixed scatter axis domain per level: min/max across ALL cadres and ALL
  // years, so the axes don't rescale when the year slider moves or the mode
  // toggles — only the points/trails move within a constant frame.
  const scatterDomainCache = {};
  function scatterDomain() {
    const key = state.level;
    if (scatterDomainCache[key]) return scatterDomainCache[key];
    const allGini = [];
    const allDensity = [];
    data.hrh_types.forEach((meta) => {
      years().forEach((yr) => {
        allGini.push(levelData().gini[meta.code][String(yr)]);
        allDensity.push(avgDensity(meta.code, yr));
      });
    });
    const giniMin = Math.min(...allGini), giniMax = Math.max(...allGini);
    const densMin = Math.min(...allDensity), densMax = Math.max(...allDensity);
    const giniPad = (giniMax - giniMin) * 0.18 || 0.02;
    const densPad = (densMax - densMin) * 0.18 || 1;
    scatterDomainCache[key] = {
      giniMin, giniMax, densMin, densMax,
      dx0: densMin - densPad, dx1: densMax + densPad,
      gy0: giniMin - giniPad, gy1: giniMax + giniPad,
    };
    return scatterDomainCache[key];
  }

  // ---------- map setup ----------

  function tileUrl() {
    return isDark()
      ? "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
      : "https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png";
  }

  function initMap(geojsons) {
    map = L.map("map", {
      zoomControl: false,
      attributionControl: false,
      minZoom: 5,
      maxZoom: 10,
    });
    L.control.zoom({ position: "bottomright" }).addTo(map);

    tileLayer = L.tileLayer(tileUrl(), {
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);

    Object.keys(geojsons).forEach((levelKey) => {
      geoLayers[levelKey] = L.geoJSON(geojsons[levelKey], {
        style: featureStyle,
        onEachFeature: (feature, layer) => {
          layer.on({
            mouseover: (e) => onHover(e, feature),
            mousemove: (e) => moveTooltip(e),
            mouseout: () => hideTooltip(),
          });
        },
      });
    });

    geoLayer = geoLayers[state.level];
    geoLayer.addTo(map);
    map.fitBounds(geoLayer.getBounds(), { padding: [60, 60] });
  }

  function switchLevel(newLevel) {
    if (newLevel === state.level || !geoLayers[newLevel]) return;
    map.removeLayer(geoLayer);
    state.level = newLevel;
    geoLayer = geoLayers[newLevel];
    geoLayer.addTo(map);
    render();
  }

  function featureStyle(feature) {
    const regionId = feature.properties[levelData().key];
    const color = colorForRegion(regionId);
    return {
      color: isDark() ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.9)",
      weight: state.level === "prov" ? 0.8 : 1.2,
      fillColor: color,
      fillOpacity: 0.88,
    };
  }

  function colorForRegion(regionId) {
    if (state.mode === "snapshot") {
      const domainMax = densityDomainMax(state.hrh);
      const v = densityFor(state.hrh, currentYear(), regionId);
      return sequentialColor(v / domainMax);
    }
    const changes = levelData().change[state.hrh];
    const domain = Math.max(...Object.values(changes).map((c) => Math.abs(c.abs)), 1e-6);
    const c = changes[regionId];
    return divergingColor(c.abs / domain);
  }

  function onHover(e, feature) {
    const layer = e.target;
    layer.setStyle({ weight: 2.5, color: isDark() ? "#ffffff" : "#0b0b0b" });
    layer.bringToFront();

    const regionId = feature.properties[levelData().key];
    const regionMeta = levelData().regions.find((r) => r.id === regionId);
    const label = regionMeta ? regionLabel(regionMeta) : regionId;
    const hrhName = currentHrhLabel();

    let html;
    if (state.mode === "snapshot") {
      const v = densityFor(state.hrh, currentYear(), regionId);
      html = `<div class="tt-title">${label}</div><div class="tt-value">${hrhName}: ${fmt(v)} / 100,000</div>`;
    } else {
      const c = levelData().change[state.hrh][regionId];
      const signClass = c.abs >= 0 ? "tt-pos" : "tt-neg";
      const sign = c.abs >= 0 ? "+" : "";
      const pct = c.pct === null ? "" : ` (${sign}${fmt(c.pct, 0)}%)`;
      html = `<div class="tt-title">${label}</div><div class="tt-value">${hrhName}: <span class="${signClass}">${sign}${fmt(c.abs)}${pct}</span></div><div class="tt-value">${fmt(c.from)} → ${fmt(c.to)}</div>`;
    }
    tooltipEl.innerHTML = html;
    tooltipEl.classList.add("is-visible");
    moveTooltip(e);
  }

  function positionTooltip(clientX, clientY) {
    const pad = 16;
    tooltipEl.style.left = `${clientX + pad}px`;
    tooltipEl.style.top = `${clientY + pad}px`;
  }

  function moveTooltip(e) {
    positionTooltip(e.originalEvent.clientX, e.originalEvent.clientY);
  }

  function hideTooltip() {
    tooltipEl.classList.remove("is-visible");
    geoLayer.eachLayer((l) => l.setStyle(featureStyle(l.feature)));
  }

  // ---------- rendering ----------

  function currentHrhLabel() { return hrhLabel(state.hrh); }

  function hrhLabel(code) {
    const meta = data.hrh_types.find((h) => h.code === code);
    return i18n.t(`hrh.${code}`, meta ? meta.label : code);
  }

  function render() {
    if (geoLayer) geoLayer.eachLayer((l) => l.setStyle(featureStyle(l.feature)));
    renderLegend();
    renderStats();
    renderScatter();
    $("year-value").textContent = fmtYear(currentYear());
  }

  function renderLegend() {
    const bar = $("legend-bar");
    const title = $("legend-title");
    const min = $("legend-min");
    const mid = $("legend-mid");
    const max = $("legend-max");
    const { red, yellow, green } = statusHexes();

    if (state.mode === "snapshot") {
      title.textContent = i18n.lang === "th"
        ? `${currentHrhLabel()} \n ต่อประชากรแสนคน — \n ${levelLabel()}, พ.ศ. ${fmtYear(currentYear())}`
        : `${currentHrhLabel()} \n density per 100,000 population — \n ${levelLabel()}, ${currentYear()}`;
      bar.style.background = `linear-gradient(to right, ${red}, ${yellow}, ${green})`;
      min.textContent = "0";
      mid.textContent = "";
      max.textContent = fmt(densityDomainMax(state.hrh), 0);
    } else {
      title.textContent = i18n.lang === "th"
        ? `${currentHrhLabel()} \n การเปลี่ยนแปลง — \n ${levelLabel()}, ${fmtYear(years()[0])}–${fmtYear(years()[years().length - 1])}`
        : `${currentHrhLabel()} \n change — \n ${levelLabel()}, ${years()[0]}–${years()[years().length - 1]}`;
      bar.style.background = `linear-gradient(to right, ${red}, ${yellow}, ${green})`;
      const changes = levelData().change[state.hrh];
      const domain = Math.max(...Object.values(changes).map((c) => Math.abs(c.abs)), 1e-6);
      min.textContent = `−${fmt(domain, 0)}`;
      mid.textContent = "0";
      max.textContent = `+${fmt(domain, 0)}`;
    }
  }

  function renderStats() {
    const y = currentYear();
    const prevYear = years()[Math.max(0, state.yearIndex - 1)];
    const levelWord = i18n.lang === "th" ? levelLabel() : levelLabel().toLowerCase();

    // Density stat: national average across regions at the selected level
    const densAvg = avgDensity(state.hrh, y);
    const prevDensAvg = avgDensity(state.hrh, prevYear);

    $("stat-density-label").textContent = i18n.lang === "th"
      ? `ความหนาแน่น${currentHrhLabel()} (เฉลี่ยราย${levelWord})`
      : `${currentHrhLabel()} density (avg. ${levelWord})`;
    $("stat-density-value").textContent = fmt(densAvg);
    setDelta($("stat-density-delta"), densAvg - prevDensAvg, true);
    drawSparkline("spark-density", years().map((yr) => avgDensity(state.hrh, yr)), state.yearIndex);

    // Gini stat
    const giniSeries = levelData().gini[state.hrh];
    const giniVal = giniSeries[String(y)];
    const giniPrev = giniSeries[String(prevYear)];
    $("stat-gini-label").textContent = i18n.lang === "th"
      ? `สัมประสิทธิ์จีนี (ราย${levelWord})`
      : `Gini coefficient (${levelWord})`;
    $("stat-gini-value").textContent = fmt(giniVal, 3);
    setDelta($("stat-gini-delta"), giniVal - giniPrev, false);
    drawSparkline("spark-gini", years().map((yr) => giniSeries[String(yr)]), state.yearIndex);
  }

  function setDelta(el, delta, higherIsBetter) {
    if (Number.isNaN(delta)) { el.textContent = ""; return; }
    const sign = delta >= 0 ? "+" : "−";
    el.textContent = `${sign}${fmt(Math.abs(delta), delta < 1 ? 3 : 1)}`;
    const good = higherIsBetter ? delta >= 0 : delta <= 0;
    el.className = `stat-delta ${good ? "up" : "down"}`;
  }

  function drawSparkline(svgId, values, highlightIndex) {
    const svg = $(svgId);
    const w = 240, h = 48, pad = 4;
    const min = Math.min(...values), max = Math.max(...values);
    const range = max - min || 1;
    const x = (i) => pad + (i / (values.length - 1)) * (w - pad * 2);
    const y = (v) => h - pad - ((v - min) / range) * (h - pad * 2);

    const linePath = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L${x(values.length - 1).toFixed(1)},${h} L${x(0).toFixed(1)},${h} Z`;
    const hx = x(highlightIndex), hy = y(values[highlightIndex]);

    svg.innerHTML = `
      <path d="${areaPath}" fill="var(--seq-mid)" opacity="0.10" stroke="none"></path>
      <path d="${linePath}" fill="none" stroke="var(--seq-mid)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></path>
      <circle cx="${hx.toFixed(1)}" cy="${hy.toFixed(1)}" r="4" fill="var(--seq-mid)" stroke="var(--surface-1)" stroke-width="2"></circle>
    `;
  }

  // ---------- scatter: Gini vs. density across all cadres ----------

  function renderScatter() {
    const svg = $("scatter-svg");
    const W = 252, H = 190;
    const padL = 32, padR = 10, padT = 14, padB = 26;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const yearsToPlot = state.mode === "snapshot"
      ? [currentYear()]
      : [years()[0], years()[years().length - 1]];

    const cadres = data.hrh_types.map((meta, idx) => ({
      code: meta.code,
      label: hrhLabel(meta.code),
      color: seriesColor(idx),
      pts: yearsToPlot.map((yr) => ({
        year: yr,
        gini: levelData().gini[meta.code][String(yr)],
        density: avgDensity(meta.code, yr),
      })),
    }));

    const { giniMin, giniMax, densMin, densMax, dx0, dx1, gy0, gy1 } = scatterDomain();

    const X = (d) => padL + ((d - dx0) / (dx1 - dx0)) * plotW;
    const Y = (g) => padT + plotH - ((g - gy0) / (gy1 - gy0)) * plotH;

    const parts = [];
    parts.push(`<line class="axis-line" x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" />`);
    parts.push(`<line class="axis-line" x1="${padL}" y1="${padT + plotH}" x2="${padL + plotW}" y2="${padT + plotH}" />`);
    parts.push(`<text class="axis-label" x="${padL}" y="${padT + plotH + 13}" text-anchor="start">${Math.round(densMin)}</text>`);
    parts.push(`<text class="axis-label" x="${padL + plotW}" y="${padT + plotH + 13}" text-anchor="end">${Math.round(densMax)}</text>`);
    parts.push(`<text class="axis-title" x="${padL + plotW / 2}" y="${H - 1}" text-anchor="middle">${i18n.lang === "th" ? "ความหนาแน่น →" : "Density →"}</text>`);
    parts.push(`<text class="axis-label" x="${padL - 4}" y="${padT + plotH}" text-anchor="end">${giniMin.toFixed(2)}</text>`);
    parts.push(`<text class="axis-label" x="${padL - 4}" y="${padT + 8}" text-anchor="end">${giniMax.toFixed(2)}</text>`);
    parts.push(`<text class="axis-title" x="${padL}" y="${padT - 4}" text-anchor="start">&#8593; ${i18n.lang === "th" ? "จีนี" : "Gini coefficient"}</text>`);

    cadres.forEach((cadre) => {
      const isSelected = cadre.code === state.hrh;
      if (state.mode === "snapshot") {
        const p = cadre.pts[0];
        const r = isSelected ? 6.5 : 4.5;
        parts.push(`<circle data-code="${cadre.code}" cx="${X(p.density).toFixed(1)}" cy="${Y(p.gini).toFixed(1)}" r="${r}" fill="${cadre.color}" fill-opacity="${isSelected ? 1 : 0.82}" stroke="var(--surface-1)" stroke-width="${isSelected ? 2 : 1.2}" />`);
        if (isSelected) {
          parts.push(`<text class="pt-label" x="${(X(p.density) + 9).toFixed(1)}" y="${(Y(p.gini) + 3).toFixed(1)}">${cadre.label}</text>`);
        }
      } else {
        const p0 = cadre.pts[0], p1 = cadre.pts[1];
        const r1 = isSelected ? 6.5 : 5;
        parts.push(`<line class="trail" x1="${X(p0.density).toFixed(1)}" y1="${Y(p0.gini).toFixed(1)}" x2="${X(p1.density).toFixed(1)}" y2="${Y(p1.gini).toFixed(1)}" stroke="${cadre.color}" stroke-width="2" stroke-opacity="0.55" />`);
        parts.push(`<circle data-code="${cadre.code}" data-year="${p0.year}" cx="${X(p0.density).toFixed(1)}" cy="${Y(p0.gini).toFixed(1)}" r="3.5" fill="var(--surface-1)" stroke="${cadre.color}" stroke-width="1.6" />`);
        parts.push(`<circle data-code="${cadre.code}" data-year="${p1.year}" cx="${X(p1.density).toFixed(1)}" cy="${Y(p1.gini).toFixed(1)}" r="${r1}" fill="${cadre.color}" stroke="var(--surface-1)" stroke-width="${isSelected ? 2 : 1.2}" />`);
        if (isSelected) {
          parts.push(`<text class="pt-label" x="${(X(p1.density) + 9).toFixed(1)}" y="${(Y(p1.gini) + 3).toFixed(1)}">${cadre.label}</text>`);
        }
      }
    });

    svg.innerHTML = parts.join("");
    svg.querySelectorAll("circle").forEach((c) => {
      c.addEventListener("mouseenter", (e) => onScatterHover(e, c));
      c.addEventListener("mousemove", (e) => positionTooltip(e.clientX, e.clientY));
      c.addEventListener("mouseleave", () => tooltipEl.classList.remove("is-visible"));
    });

    const y0 = fmtYear(years()[0]), y1 = fmtYear(years()[years().length - 1]);
    $("scatter-title").textContent = i18n.lang === "th"
      ? (state.mode === "snapshot"
          ? `ความหนาแน่นเทียบความเป็นธรรม — ${levelLabel()}, พ.ศ. ${fmtYear(currentYear())}`
          : `ความหนาแน่นเทียบความเป็นธรรม ${y0}→${y1} — ${levelLabel()}`)
      : (state.mode === "snapshot"
          ? `Density vs. equity, all cadres — ${levelLabel()}, ${currentYear()}`
          : `Density vs. equity, shift ${y0}→${y1} — ${levelLabel()}`);

    const legend = $("scatter-legend");
    legend.innerHTML = cadres.map((c) => `
      <div class="scatter-legend-item${c.code === state.hrh ? " is-active" : ""}" data-code="${c.code}">
        <span class="swatch" style="background:${c.color}"></span>${c.label}
      </div>
    `).join("");
    legend.querySelectorAll(".scatter-legend-item").forEach((item) => {
      item.addEventListener("click", () => {
        state.hrh = item.dataset.code;
        $("hrh-select").value = state.hrh;
        render();
      });
    });
  }

  function onScatterHover(e, circleEl) {
    const code = circleEl.dataset.code;
    const cadre = data.hrh_types.find((h) => h.code === code);
    const year = circleEl.dataset.year ? Number(circleEl.dataset.year) : currentYear();
    const gini = levelData().gini[code][String(year)];
    const density = avgDensity(code, year);
    const densWord = i18n.lang === "th" ? "ความหนาแน่น" : "Density";
    tooltipEl.innerHTML = `<div class="tt-title">${cadre.label} — ${fmtYear(year)}</div><div class="tt-value">Gini: ${fmt(gini, 3)}</div><div class="tt-value">${densWord}: ${fmt(density)} / 100,000</div>`;
    tooltipEl.classList.add("is-visible");
    positionTooltip(e.clientX, e.clientY);
  }

  // ---------- controls ----------

  function buildControls() {
    const select = $("hrh-select");
    rebuildHrhSelect();
    select.value = state.hrh;
    select.addEventListener("change", () => {
      state.hrh = select.value;
      render();
    });

    const slider = $("year-slider");
    slider.min = 0;
    slider.max = years().length - 1;
    slider.value = state.yearIndex;
    slider.addEventListener("input", () => {
      state.yearIndex = Number(slider.value);
      render();
    });

    document.querySelectorAll("#mode-toggle .segmented-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#mode-toggle .segmented-btn").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.mode = btn.dataset.mode;
        $("year-field").classList.toggle("is-disabled", state.mode === "change");
        render();
      });
    });

    document.querySelectorAll("#level-toggle .segmented-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#level-toggle .segmented-btn").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        switchLevel(btn.dataset.level);
      });
    });

    $("theme-toggle").addEventListener("click", () => {
      state.theme = isDark() ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", state.theme);
      tileLayer.setUrl(tileUrl());
      updateThemeIcon();
      render();
    });
    updateThemeIcon();
  }

  function rebuildHrhSelect() {
    const select = $("hrh-select");
    const chosen = select.value || state.hrh;
    select.innerHTML = data.hrh_types
      .map((h) => `<option value="${h.code}">${hrhLabel(h.code)}</option>`)
      .join("");
    select.value = chosen;
  }

  function updateThemeIcon() {
    $("theme-icon").textContent = isDark() ? "\u{1F319}" : "\u{2600}\u{FE0F}";
  }

  // ---------- boot ----------

  async function boot() {
    const [dashData, geoHregion, geoProv] = await Promise.all([
      fetch("data/dashboard_data.json").then((r) => r.json()),
      fetch("data/geo_hregion.geojson").then((r) => r.json()),
      fetch("data/geo_prov.geojson").then((r) => r.json()),
    ]);
    data = dashData;
    state.yearIndex = years().length - 1;

    i18n.apply();
    buildControls();
    initMap({ hregion: geoHregion, prov: geoProv });
    render();
  }

  boot();
})();
