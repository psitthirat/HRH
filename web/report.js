/* Renders the chapter from web/content/report.<lang>.md.
 *
 * A deliberately small Markdown subset — headings, paragraphs, lists, tables,
 * blockquotes, bold/emphasis/code/links — plus four directives that give the
 * report its structure without asking the author to write HTML:
 *
 *   {{figure:9 | caption}}   a figure with a caption
 *   :::finding 3 … :::       a numbered finding box
 *   :::note label … :::      a boxed aside
 *   :::stats … :::           a row of headline numbers ("- value | label")
 *
 * Writing the renderer rather than pulling in a library keeps the page free of
 * third-party script and keeps the accepted syntax small enough that the
 * comment above is a complete specification of it.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  // ---------- inline ----------

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function inline(text) {
    let s = esc(text);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" rel="noopener">$1</a>');
    // Bracketed citation numerals link to the reference list.
    s = s.replace(/\[(\d+(?:,\s*\d+)*)\]/g, '<span class="cite">[$1]</span>');
    return s;
  }

  // ---------- block ----------

  const FIG_RE = /^\{\{figure:([^\s|}]+)\s*(?:\|\s*([\s\S]*?))?\}\}$/;

  function slugify(text, used) {
    const base = text.trim().replace(/\s+/g, "-").replace(/[^\w฀-๿.-]/g, "").slice(0, 60)
      || "s";
    let slug = base, n = 2;
    while (used.has(slug)) slug = `${base}-${n++}`;
    used.add(slug);
    return slug;
  }

  function renderTable(lines) {
    const cells = (row) => row.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    const header = cells(lines[0]);
    const body = lines.slice(2).map(cells);
    const numeric = (v) => /^[\s\d.,+\-−<>=%/–—]*$/.test(v) && /\d/.test(v);
    let html = '<div class="table-wrap"><table><thead><tr>';
    header.forEach((h) => { html += `<th>${inline(h)}</th>`; });
    html += "</tr></thead><tbody>";
    body.forEach((row) => {
      html += "<tr>";
      row.forEach((c, i) => {
        const cls = i > 0 && numeric(c) ? ' class="num"' : "";
        html += `<td${cls}>${inline(c)}</td>`;
      });
      html += "</tr>";
    });
    return html + "</tbody></table></div>";
  }

  function renderFigure(key, caption, figures) {
    const known = figures.some((f) => f.key === key);
    const src = `figures/fig-${key}.png`;
    const alt = caption ? esc(caption.replace(/\*\*/g, "")) : `Figure ${key}`;
    const label = window.i18n && i18n.lang === "th" ? `รูปที่ ${key}` : `Figure ${key}`;
    if (!known) {
      return `<figure class="fig fig-missing"><p>${label} — ${esc(i18n.t("report.figureMissing"))}</p></figure>`;
    }
    return (
      `<figure class="fig">` +
      `<a href="${src}" target="_blank" rel="noopener">` +
      `<img src="${src}" alt="${alt}" loading="lazy" />` +
      `</a>` +
      (caption
        ? `<figcaption><b>${label}</b> ${inline(caption)}</figcaption>`
        : `<figcaption><b>${label}</b></figcaption>`) +
      `</figure>`
    );
  }

  function renderFence(kind, arg, body, figures) {
    const inner = render(body.join("\n"), figures, null);
    if (kind === "finding") {
      const label = window.i18n ? i18n.t("report.finding") : "Finding";
      return `<aside class="callout finding"><div class="callout-label">${esc(label)} ${esc(arg)}</div>${inner}</aside>`;
    }
    if (kind === "note") {
      return `<aside class="callout note"><div class="callout-label">${esc(arg)}</div>${inner}</aside>`;
    }
    if (kind === "stats") {
      const items = body
        .filter((l) => l.trim().startsWith("- "))
        .map((l) => l.trim().slice(2).split("|"))
        .map(([v, k]) => `<div class="stat"><div class="stat-v">${inline((v || "").trim())}</div>` +
                          `<div class="stat-k">${inline((k || "").trim())}</div></div>`)
        .join("");
      return `<div class="statrow">${items}</div>`;
    }
    return inner;
  }

  function render(md, figures, toc) {
    const lines = md.replace(/\r\n/g, "\n").replace(/<!--[\s\S]*?-->/g, "").split("\n");
    const out = [];
    const usedSlugs = new Set();
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      if (!trimmed) { i++; continue; }

      // fenced directive
      const fence = trimmed.match(/^:::(\w+)\s*(.*)$/);
      if (fence) {
        const body = [];
        i++;
        while (i < lines.length && lines[i].trim() !== ":::") body.push(lines[i++]);
        i++; // closing :::
        out.push(renderFence(fence[1], fence[2], body, figures));
        continue;
      }

      // figure directive (may wrap over lines until the closing braces)
      if (trimmed.startsWith("{{figure:")) {
        let buf = trimmed;
        while (!buf.endsWith("}}") && i + 1 < lines.length) buf += " " + lines[++i].trim();
        i++;
        const m = buf.match(FIG_RE);
        if (m) out.push(renderFigure(m[1], (m[2] || "").trim(), figures));
        continue;
      }

      // heading
      const h = trimmed.match(/^(#{1,4})\s+(.*)$/);
      if (h) {
        const level = h[1].length;
        const text = h[2].trim();
        const slug = slugify(text, usedSlugs);
        out.push(`<h${level} id="${slug}">${inline(text)}</h${level}>`);
        if (toc && (level === 2 || level === 3)) toc.push({ level, text, slug });
        i++;
        continue;
      }

      // table
      if (trimmed.startsWith("|") && i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim())) {
        const block = [];
        while (i < lines.length && lines[i].trim().startsWith("|")) block.push(lines[i++].trim());
        out.push(renderTable(block));
        continue;
      }

      // blockquote (used for the abstract)
      if (trimmed.startsWith(">")) {
        const block = [];
        while (i < lines.length && lines[i].trim().startsWith(">")) {
          block.push(lines[i++].trim().replace(/^>\s?/, ""));
        }
        out.push(`<blockquote>${inline(block.join(" "))}</blockquote>`);
        continue;
      }

      // lists
      if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
        const ordered = /^\d+\.\s+/.test(trimmed);
        const items = [];
        while (i < lines.length) {
          const t = lines[i].trim();
          const m = ordered ? t.match(/^\d+\.\s+(.*)$/) : t.match(/^[-*]\s+(.*)$/);
          if (!m) break;
          let item = m[1];
          i++;
          // continuation lines are indented or simply not a new item
          while (i < lines.length && lines[i].trim() &&
                 !/^[-*]\s+/.test(lines[i].trim()) && !/^\d+\.\s+/.test(lines[i].trim()) &&
                 !lines[i].trim().startsWith("|") && !lines[i].trim().startsWith(":::") &&
                 !lines[i].trim().startsWith("#")) {
            item += " " + lines[i++].trim();
          }
          items.push(`<li>${inline(item)}</li>`);
        }
        out.push(`<${ordered ? "ol" : "ul"}>${items.join("")}</${ordered ? "ol" : "ul"}>`);
        continue;
      }

      // paragraph
      const para = [];
      while (i < lines.length && lines[i].trim() &&
             !lines[i].trim().startsWith("#") && !lines[i].trim().startsWith("|") &&
             !lines[i].trim().startsWith(":::") && !lines[i].trim().startsWith(">") &&
             !lines[i].trim().startsWith("{{figure:") &&
             !/^[-*]\s+/.test(lines[i].trim()) && !/^\d+\.\s+/.test(lines[i].trim())) {
        para.push(lines[i++].trim());
      }
      if (para.length) {
        let text = para.join(" ");
        // A paragraph wrapped entirely in asterisks is a source/footnote line under a
        // table or figure. Strip the markers rather than emitting <em>, whose emphasis
        // wash would otherwise tint the whole line.
        const noteOnly = /^\*[^*][\s\S]*[^*]\*$/.test(text) && !text.slice(1, -1).includes("*");
        if (noteOnly) text = text.slice(1, -1);
        out.push(`<p${noteOnly ? ' class="src-note"' : ""}>${inline(text)}</p>`);
      }
      continue;
    }

    return out.join("\n");
  }

  // ---------- page ----------

  let manifest = { figures: [] };

  function buildToc(toc) {
    const el = $("toc-list");
    el.innerHTML = toc
      .map((h) => `<li class="lvl-${h.level}"><a href="#${h.slug}">${esc(h.text)}</a></li>`)
      .join("");
  }

  async function load() {
    const body = $("report-body");
    body.innerHTML = `<p class="muted">${esc(i18n.t("report.loading"))}</p>`;
    try {
      const res = await fetch(`content/report.${i18n.lang}.md`, { cache: "no-cache" });
      if (!res.ok) throw new Error(res.status);
      const md = await res.text();
      const toc = [];
      body.innerHTML = render(md, manifest.figures, toc);
      buildToc(toc);
      trackActiveSection();
    } catch (err) {
      body.innerHTML =
        `<p class="muted">${esc(i18n.t("report.loadError"))} — <code>content/report.${i18n.lang}.md</code></p>`;
      $("toc-list").innerHTML = "";
    }
  }

  /* Highlight the contents entry for whichever section is on screen. */
  function trackActiveSection() {
    const links = Array.from(document.querySelectorAll("#toc-list a"));
    if (!links.length) return;
    const targets = links
      .map((a) => document.getElementById(a.getAttribute("href").slice(1)))
      .filter(Boolean);
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          links.forEach((a) => a.classList.remove("is-active"));
          const active = links.find((a) => a.getAttribute("href") === `#${e.target.id}`);
          if (active) {
            active.classList.add("is-active");
            active.scrollIntoView({ block: "nearest" });
          }
        });
      },
      { rootMargin: "-10% 0px -80% 0px", threshold: 0 }
    );
    targets.forEach((t) => obs.observe(t));
  }

  // ---------- theme (shared behaviour with the map page) ----------

  function initTheme() {
    const KEY = "hrh-theme";
    let theme = "auto";
    try { theme = localStorage.getItem(KEY) || "auto"; } catch (e) { /* ignore */ }
    const apply = () => {
      if (theme === "auto") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", theme);
      const dark = theme === "dark" ||
        (theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
      $("theme-icon").textContent = dark ? "🌙" : "☀️";
    };
    apply();
    $("theme-toggle").addEventListener("click", () => {
      const dark = theme === "dark" ||
        (theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
      theme = dark ? "light" : "dark";
      try { localStorage.setItem(KEY, theme); } catch (e) { /* ignore */ }
      apply();
    });
  }

  // ---------- boot ----------

  document.addEventListener("DOMContentLoaded", async () => {
    initTheme();
    i18n.apply();
    try {
      const res = await fetch("content/manifest.json", { cache: "no-cache" });
      if (res.ok) manifest = await res.json();
    } catch (e) { /* figures simply render as missing */ }

    await load();

    $("lang-toggle").addEventListener("click", () => {
      i18n.toggle();
      i18n.apply();
      load();
    });

    $("to-top").addEventListener("click", (e) => {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
})();
