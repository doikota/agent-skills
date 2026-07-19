#!/usr/bin/env node
/*
 * Generate a themed 5-slide Japanese business deck (title / issue-cards /
 * trend-rows / usecase-cards / summary) from a JSON content file.
 *
 * Usage:
 *   node generate_deck.js <content.json> <output.pptx>
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Fi = require("react-icons/fi");

// ---- palette (navy/indigo tech theme — see SKILL.md) ----
const PRIMARY = "141B4D";    // deep indigo navy (dominant)
const PRIMARY_LT = "232C68"; // lighter navy for card fills on dark bg
const SECONDARY = "E7EAF8";  // pale ice-lavender (light bg card tint)
const ACCENT = "4C63FF";     // electric indigo-blue (sharp accent)
const WHITE = "FFFFFF";
const TEXT_MUTED = "6B7280";
const TEXT_MUTED_LT = "AEB6E8";

const FONT_HEAD = "Cambria";
const FONT_BODY = "Calibri";

// Logical icon names available to content JSON -> react-icons/fi components.
const ICON_MAP = {
  cpu: Fi.FiCpu,
  "alert-triangle": Fi.FiAlertTriangle,
  shield: Fi.FiShield,
  eye: Fi.FiEye,
  "dollar-sign": Fi.FiDollarSign,
  users: Fi.FiUsers,
  tool: Fi.FiTool,
  database: Fi.FiDatabase,
  target: Fi.FiTarget,
  headphones: Fi.FiHeadphones,
  code: Fi.FiCode,
  settings: Fi.FiSettings,
  search: Fi.FiSearch,
  "check-circle": Fi.FiCheckCircle,
  "arrow-up-right": Fi.FiArrowUpRight,
  zap: Fi.FiZap,
  "trending-up": Fi.FiTrendingUp,
  globe: Fi.FiGlobe,
  layers: Fi.FiLayers,
  clock: Fi.FiClock,
};

async function iconPng(Icon, colorHex, sizePx = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { size: sizePx, color: colorHex })
  );
  const fullSvg = svg.includes("xmlns")
    ? svg
    : svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
  const buf = await sharp(Buffer.from(fullSvg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

function resolveIcon(key) {
  const Icon = ICON_MAP[key];
  if (!Icon) {
    throw new Error(
      `Unknown icon "${key}". Available icons: ${Object.keys(ICON_MAP).join(", ")}`
    );
  }
  return Icon;
}

function iconCircle(slide, { x, y, d, circleFill, icon, iconInset = 0.22 }) {
  slide.addShape("ellipse", { x, y, w: d, h: d, fill: { color: circleFill }, line: { type: "none" } });
  slide.addImage({ data: icon, x: x + iconInset, y: y + iconInset, w: d - iconInset * 2, h: d - iconInset * 2 });
}

async function buildTitleSlide(pres, content, icons) {
  const s = pres.addSlide();
  s.background = { color: PRIMARY };

  const dotSpecs = [
    [11.6, 0.9, 0.06], [12.2, 1.5, 0.09], [11.3, 1.9, 0.05],
    [12.6, 0.8, 0.05], [11.9, 2.4, 0.07], [12.7, 1.9, 0.05],
    [0.8, 6.6, 0.06], [1.3, 6.9, 0.09], [0.5, 7.1, 0.05],
  ];
  dotSpecs.forEach(([x, y, r]) => {
    s.addShape("ellipse", { x, y, w: r * 2, h: r * 2, fill: { color: ACCENT }, line: { type: "none" } });
  });

  iconCircle(s, { x: 0.9, y: 0.9, d: 1.0, circleFill: PRIMARY_LT, icon: icons.title, iconInset: 0.24 });

  if (content.titleEn) {
    s.addText(content.titleEn, {
      x: 0.9, y: 2.35, w: 10, h: 0.4, fontFace: FONT_BODY, fontSize: 13, color: ACCENT,
      charSpacing: 3, bold: true, margin: 0,
    });
  }

  s.addText(content.title, {
    x: 0.9, y: 2.75, w: 11.2, h: 1.5, fontFace: FONT_HEAD, fontSize: 46, bold: true,
    color: WHITE, margin: 0,
  });

  if (content.subtitle) {
    s.addText(content.subtitle, {
      x: 0.9, y: 4.05, w: 10, h: 0.6, fontFace: FONT_HEAD, fontSize: 19, italic: true,
      color: "CADCFC", margin: 0,
    });
  }

  if (content.date) {
    s.addText(content.date, {
      x: 0.9, y: 6.75, w: 4, h: 0.4, fontFace: FONT_BODY, fontSize: 12,
      color: TEXT_MUTED_LT, margin: 0,
    });
  }
}

async function buildCardsSlide(pres, section, iconsForItems, dark) {
  const s = pres.addSlide();
  s.background = { color: WHITE };

  s.addText(section.heading, {
    x: 0.7, y: 0.55, w: 8, h: 0.7, fontFace: FONT_HEAD, fontSize: 34, bold: true, color: PRIMARY, margin: 0,
  });
  if (section.subheading) {
    s.addText(section.subheading, {
      x: 0.7, y: 1.15, w: 9, h: 0.4, fontFace: FONT_BODY, fontSize: 14, color: TEXT_MUTED, margin: 0,
    });
  }

  const cardW = 5.65, cardH = 2.15, gapX = 0.5, gapY = 0.4;
  const startX = 0.7, startY = 2.0;
  const cardFill = dark ? PRIMARY : SECONDARY;
  const circleFill = dark ? ACCENT : PRIMARY;
  const titleColor = dark ? WHITE : PRIMARY;
  const bodyColor = dark ? "CADCFC" : "3B3F5C";

  section.items.slice(0, 4).forEach((item, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = startX + col * (cardW + gapX);
    const y = startY + row * (cardH + gapY);
    s.addShape("roundRect", {
      x, y, w: cardW, h: cardH, rectRadius: 0.1,
      fill: { color: cardFill }, line: { type: "none" },
      shadow: { type: "outer", color: "141B4D", opacity: dark ? 0.18 : 0.12, blur: 6, offset: 2, angle: 90 },
    });
    iconCircle(s, { x: x + 0.3, y: y + 0.3, d: 0.7, circleFill, icon: iconsForItems[i], iconInset: 0.16 });
    s.addText(item.title, {
      x: x + 1.2, y: y + 0.28, w: cardW - 1.5, h: 0.6, fontFace: FONT_HEAD, fontSize: 16, bold: true,
      color: titleColor, margin: 0, valign: "top",
    });
    s.addText(item.body, {
      x: x + 0.3, y: y + 1.1, w: cardW - 0.6, h: 0.9, fontFace: FONT_BODY, fontSize: 12.5,
      color: bodyColor, margin: 0, valign: "top", lineSpacingMultiple: 1.25,
    });
  });
}

async function buildRowsSlide(pres, section, iconsForItems) {
  const s = pres.addSlide();
  s.background = { color: WHITE };

  s.addText(section.heading, {
    x: 0.7, y: 0.55, w: 8, h: 0.7, fontFace: FONT_HEAD, fontSize: 34, bold: true, color: PRIMARY, margin: 0,
  });
  if (section.subheading) {
    s.addText(section.subheading, {
      x: 0.7, y: 1.15, w: 9, h: 0.4, fontFace: FONT_BODY, fontSize: 14, color: TEXT_MUTED, margin: 0,
    });
  }

  const rows = section.items.slice(0, 4);
  const rowH = 1.15, startY = 2.05, x = 0.7, w = 11.9;
  rows.forEach((r, i) => {
    const y = startY + i * (rowH + 0.12);
    iconCircle(s, { x, y: y + 0.1, d: 0.9, circleFill: SECONDARY, icon: iconsForItems[i], iconInset: 0.2 });
    s.addText(r.title, {
      x: x + 1.15, y: y, w: w - 1.15, h: 0.45, fontFace: FONT_HEAD, fontSize: 17, bold: true,
      color: PRIMARY, margin: 0, valign: "top",
    });
    s.addText(r.body, {
      x: x + 1.15, y: y + 0.48, w: w - 1.15, h: 0.55, fontFace: FONT_BODY, fontSize: 13,
      color: "3B3F5C", margin: 0, valign: "top",
    });
    if (i < rows.length - 1) {
      s.addShape("line", {
        x: x + 1.15, y: y + rowH + 0.02, w: w - 1.15, h: 0,
        line: { color: "E2E5F5", width: 1 },
      });
    }
  });
}

async function buildSummarySlide(pres, summary, checkIcon, arrowIcon) {
  const s = pres.addSlide();
  s.background = { color: PRIMARY };

  s.addText(summary.heading, {
    x: 0.9, y: 0.7, w: 8, h: 0.7, fontFace: FONT_HEAD, fontSize: 34, bold: true, color: WHITE, margin: 0,
  });
  if (summary.subheading) {
    s.addText(summary.subheading, {
      x: 0.9, y: 1.3, w: 10, h: 0.4, fontFace: FONT_BODY, fontSize: 14, color: TEXT_MUTED_LT, margin: 0,
    });
  }

  const points = summary.points.slice(0, 3);
  const startY = 2.35, rowH = 1.0;
  points.forEach((p, i) => {
    const y = startY + i * (rowH + 0.15);
    iconCircle(s, { x: 0.9, y, d: 0.6, circleFill: PRIMARY_LT, icon: checkIcon, iconInset: 0.13 });
    s.addText(p.title, {
      x: 1.75, y: y - 0.05, w: 10.4, h: 0.4, fontFace: FONT_HEAD, fontSize: 16, bold: true,
      color: WHITE, margin: 0, valign: "top",
    });
    s.addText(p.body, {
      x: 1.75, y: y + 0.35, w: 10.4, h: 0.45, fontFace: FONT_BODY, fontSize: 12.5,
      color: "CADCFC", margin: 0, valign: "top",
    });
  });

  if (summary.tagline) {
    const tagY = 5.85, tagH = 1.0;
    s.addShape("roundRect", {
      x: 0.9, y: tagY, w: 11.5, h: tagH, rectRadius: 0.1,
      fill: { color: ACCENT }, line: { type: "none" },
    });
    s.addText(summary.tagline, {
      x: 1.3, y: tagY, w: 9.6, h: tagH, fontFace: FONT_HEAD, fontSize: 19, bold: true, italic: true,
      color: WHITE, margin: 0, valign: "middle",
    });
    s.addImage({ data: arrowIcon, x: 11.55, y: tagY + 0.25, w: 0.5, h: 0.5 });
  }
}

async function main() {
  const [, , contentPath, outputPath] = process.argv;
  if (!contentPath || !outputPath) {
    console.error("Usage: node generate_deck.js <content.json> <output.pptx>");
    process.exit(1);
  }
  const content = JSON.parse(fs.readFileSync(path.resolve(contentPath), "utf8"));
  if (!content.sections || content.sections.length !== 3 || !content.summary) {
    throw new Error("content JSON must have exactly 3 `sections` entries and a `summary` entry (title + 3 sections + summary = 5 slides)");
  }

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5 in

  // Icon color per layout: white icon on a dark (primary/accent) circle,
  // accent-colored icon on a light (secondary) circle.
  const iconCacheWhite = {};
  const iconCacheAccent = {};
  async function whiteIcon(key) {
    if (!iconCacheWhite[key]) iconCacheWhite[key] = await iconPng(resolveIcon(key), WHITE);
    return iconCacheWhite[key];
  }
  async function accentIcon(key) {
    if (!iconCacheAccent[key]) iconCacheAccent[key] = await iconPng(resolveIcon(key), ACCENT);
    return iconCacheAccent[key];
  }

  const titleIcon = await accentIcon(content.titleIcon || "cpu");
  await buildTitleSlide(pres, content, { title: titleIcon });

  for (const section of content.sections) {
    const layout = section.layout || "icon-rows";
    if (layout === "cards-2x2-light" || layout === "cards-2x2-dark") {
      const dark = layout === "cards-2x2-dark";
      const itemIcons = await Promise.all(
        section.items.slice(0, 4).map((it) => (dark ? whiteIcon(it.icon) : whiteIcon(it.icon)))
      );
      await buildCardsSlide(pres, section, itemIcons, dark);
    } else if (layout === "icon-rows") {
      const itemIcons = await Promise.all(section.items.slice(0, 4).map((it) => accentIcon(it.icon)));
      await buildRowsSlide(pres, section, itemIcons);
    } else {
      throw new Error(`Unknown layout "${layout}". Use cards-2x2-light, cards-2x2-dark, or icon-rows.`);
    }
  }

  const checkIcon = await accentIcon(content.summary.pointIcon || "check-circle");
  const arrowIcon = await whiteIcon(content.summary.taglineIcon || "arrow-up-right");
  await buildSummarySlide(pres, content.summary, checkIcon, arrowIcon);

  await pres.writeFile({ fileName: path.resolve(outputPath) });
  console.log(`Wrote ${outputPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
