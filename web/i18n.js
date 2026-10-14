/* Shared bilingual strings for the dashboard.
 *
 * Thai is the default; the header toggle switches to English and remembers the
 * choice in localStorage so the whole site stays in one language between visits.
 *
 * To change a label, edit the matching string below — nothing else needs touching.
 * Keys are used by both index.html (the map) and report.html (the chapter).
 */
(function (global) {
  "use strict";

  const STRINGS = {
    th: {
      "site.title": "โครงการกำลังคนด้านสุขภาพประเทศไทย",
      "site.subtitle": "ความหนาแน่นและความเป็นธรรมของการกระจาย<br>พ.ศ. 2558–2567",
      "nav.map": "แผนที่",
      "nav.report": "รายงาน",
      "nav.toMap": "กลับสู่แผนที่",
      "lang.toggleTitle": "สลับภาษา / Switch language",
      "theme.toggleTitle": "สลับธีมสว่าง–มืด",

      "field.level": "ระดับพื้นที่",
      "level.hregion": "เขตสุขภาพ",
      "level.prov": "จังหวัด",
      "field.hrh": "วิชาชีพ",
      "field.view": "มุมมอง",
      "mode.snapshot": "รายปี",
      "mode.change": "การเปลี่ยนแปลง 10 ปี",
      "field.year": "ปี พ.ศ.",

      "scatter.title": "ความหนาแน่นเทียบความเป็นธรรม ทุกวิชาชีพ",
      "legend.density": "ความหนาแน่นต่อประชากรแสนคน",
      "legend.change": "การเปลี่ยนแปลง (%)",
      "stat.densityLabel": "ความหนาแน่น",
      "stat.giniLabel": "สัมประสิทธิ์จีนี",
      "source": "ข้อมูล: GIS Health Map (gishealth.moph.go.th) · สำนักบริหารการทะเบียน กรมการปกครอง",

      "report.eyebrow": "บทที่ 4",
      "report.kicker": "รายงานฉบับเต็ม",
      "report.contents": "สารบัญ",
      "report.backToTop": "กลับขึ้นบน",
      "report.downloads": "ดาวน์โหลด",
      "report.docx": "รายงานฉบับ Word",
      "report.notebook": "สมุดบันทึกการวิเคราะห์",
      "report.repo": "คลังโค้ดและข้อมูล",
      "report.figureMissing": "ไม่พบไฟล์รูปนี้ — รัน scripts/build_report_assets.py เพื่อสร้างใหม่",
      "report.loading": "กำลังโหลดเนื้อหา…",
      "report.loadError": "โหลดเนื้อหาไม่สำเร็จ",
      "report.finding": "ข้อค้นพบที่",
      "report.updated": "ปรับปรุงล่าสุด",

      "hrh.doctor": "แพทย์",
      "hrh.nurse-prof": "พยาบาลวิชาชีพ",
      "hrh.dentist": "ทันตแพทย์",
      "hrh.pharmacist": "เภสัชกร",
      "hrh.pt": "นักกายภาพบำบัด",
      "hrh.rt": "นักรังสีการแพทย์",
      "hrh.ph-practictioner": "นักวิชาการสาธารณสุข",
      "hrh.psychologist-clinic": "นักจิตวิทยาคลินิก",
      "region.prefix": "เขต",
    },

    en: {
      "site.title": "Thailand Health Workforce Project",
      "site.subtitle": "Density &amp; distributional equity,<br>2015–2024",
      "nav.map": "Map",
      "nav.report": "Report",
      "nav.toMap": "Back to map",
      "lang.toggleTitle": "Switch language / สลับภาษา",
      "theme.toggleTitle": "Toggle light and dark theme",

      "field.level": "Level",
      "level.hregion": "Health Region",
      "level.prov": "Province",
      "field.hrh": "Workforce type",
      "field.view": "View",
      "mode.snapshot": "Year snapshot",
      "mode.change": "10-year change",
      "field.year": "Year",

      "scatter.title": "Density vs. equity, all cadres",
      "legend.density": "Density per 100,000 population",
      "legend.change": "Change (%)",
      "stat.densityLabel": "density",
      "stat.giniLabel": "Gini coefficient",
      "source": "Data: GIS Health Map (gishealth.moph.go.th) · Bureau of Registration Administration, MOI, Thailand",

      "report.eyebrow": "Chapter 4",
      "report.kicker": "Full report",
      "report.contents": "Contents",
      "report.backToTop": "Back to top",
      "report.downloads": "Downloads",
      "report.docx": "Word report",
      "report.notebook": "Analysis notebook",
      "report.repo": "Code and data repository",
      "report.figureMissing": "Figure file not found — run scripts/build_report_assets.py to regenerate it",
      "report.loading": "Loading…",
      "report.loadError": "Could not load the content",
      "report.finding": "Finding",
      "report.updated": "Last updated",

      "hrh.doctor": "Physician",
      "hrh.nurse-prof": "Professional nurse",
      "hrh.dentist": "Dentist",
      "hrh.pharmacist": "Pharmacist",
      "hrh.pt": "Physiotherapist",
      "hrh.rt": "Radiological technologist",
      "hrh.ph-practictioner": "Public health practitioner",
      "hrh.psychologist-clinic": "Clinical psychologist",
      "region.prefix": "Region",
    },
  };

  const KEY = "hrh-lang";
  let current = "th";
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "th" || saved === "en") current = saved;
  } catch (e) {
    /* private browsing — fall back to the default */
  }

  const listeners = [];

  const i18n = {
    get lang() { return current; },
    other() { return current === "th" ? "en" : "th"; },
    t(key, fallback) {
      const table = STRINGS[current] || STRINGS.th;
      if (key in table) return table[key];
      if (key in STRINGS.th) return STRINGS.th[key];
      return fallback !== undefined ? fallback : key;
    },
    set(lang) {
      if (lang !== "th" && lang !== "en") return;
      current = lang;
      try { localStorage.setItem(KEY, lang); } catch (e) { /* ignore */ }
      document.documentElement.setAttribute("lang", lang);
      document.documentElement.setAttribute("data-lang", lang);
      listeners.forEach((fn) => fn(lang));
    },
    toggle() { i18n.set(i18n.other()); },
    onChange(fn) { listeners.push(fn); },

    /* Rewrite every element carrying data-i18n / data-i18n-html / data-i18n-title. */
    apply(root) {
      const scope = root || document;
      scope.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = i18n.t(el.getAttribute("data-i18n"), el.textContent);
      });
      scope.querySelectorAll("[data-i18n-html]").forEach((el) => {
        el.innerHTML = i18n.t(el.getAttribute("data-i18n-html"), el.innerHTML);
      });
      scope.querySelectorAll("[data-i18n-title]").forEach((el) => {
        const v = i18n.t(el.getAttribute("data-i18n-title"));
        el.setAttribute("title", v);
        el.setAttribute("aria-label", v);
      });
      const btn = scope.querySelector("#lang-toggle .lang-label");
      if (btn) btn.textContent = i18n.other().toUpperCase();
    },
  };

  document.documentElement.setAttribute("lang", current);
  document.documentElement.setAttribute("data-lang", current);
  global.i18n = i18n;
})(window);
