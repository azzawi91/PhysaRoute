// =============================================================================
// Copyright (c) 2026 Mustafa Mazzawi.  All rights reserved.
//
// This file is part of the PhysaRoute reference implementation accompanying
// the manuscript "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for
// Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT"
// (IEEE Internet of Things Journal, under review).
//
// All rights reserved.  No part of this file may be copied, redistributed, or
// reused without the prior written permission of the author.  See LICENSE for
// the full terms.  Contact: mazzawi1991@gmail.com
// =============================================================================
// Builds Part 1 of the PhysaRoute manuscript helpers + content arrays.
// We generate a single .docx file by combining content arrays from
// build_paper_part1.js (front matter + intro + related work + background)
// and additional sections defined in build_paper_main.js.
//
// This file ONLY exports the helpers and the front-matter / first sections.

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, Footer, Header,
} = require("docx");

const FIG_DIR = path.join(__dirname, "..", "figures");

// ---------- Style helpers ---------------------------------------------------
const FONT = "Times New Roman";

function run(text, opts = {}) {
  return new TextRun({ text, font: FONT, size: 20, ...opts });
}
function it(text)  { return run(text, { italics: true }); }
function bd(text)  { return run(text, { bold: true });   }
function sub(text) { return run(text, { subScript: true }); }
function sup(text) { return run(text, { superScript: true }); }

// Body paragraph with first-line indent (IEEE style)
function p(...children) {
  // accept either string or TextRun children
  const kids = children.map(c => (typeof c === "string" ? run(c) : c));
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 100, line: 260 },
    indent: { firstLine: 240 },
    children: kids,
  });
}
// Body paragraph WITHOUT indent (after a heading)
function pf(...children) {
  const kids = children.map(c => (typeof c === "string" ? run(c) : c));
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 100, line: 260 },
    children: kids,
  });
}
function h1(text, num) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.CENTER,
    spacing: { before: 240, after: 120 },
    children: [
      new TextRun({ text: (num ? num + ". " : "") + text.toUpperCase(),
                    font: FONT, size: 22, bold: false, smallCaps: true }),
    ],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 180, after: 80 },
    children: [
      new TextRun({ text, font: FONT, size: 21, italics: true, bold: false }),
    ],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 120, after: 60 },
    children: [
      new TextRun({ text, font: FONT, size: 20, italics: true }),
    ],
  });
}
function eq(text, num) {
  // Centered "equation" line with right-justified equation number using tabs.
  // We use a simple paragraph with center alignment + tab to right.
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 80 },
    children: [
      new TextRun({ text, font: FONT, size: 20, italics: true }),
      new TextRun({ text: "        (" + num + ")", font: FONT, size: 20 }),
    ],
  });
}
function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60, line: 260 },
    children: [run(text)],
  });
}
function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 200 },
    children: [
      new TextRun({ text, font: FONT, size: 18 }),
    ],
  });
}
function tableCell(text, opts = {}) {
  const isHeader = opts.header === true;
  return new TableCell({
    width: { size: opts.width || 1872, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: isHeader ? { fill: "DCE6F1", type: ShadingType.CLEAR } : undefined,
    borders: {
      top:    { style: BorderStyle.SINGLE, size: 4, color: "000000" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
      left:   { style: BorderStyle.NONE,   size: 0, color: "FFFFFF" },
      right:  { style: BorderStyle.NONE,   size: 0, color: "FFFFFF" },
    },
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      children: [
        new TextRun({ text, font: FONT, size: 18,
                      bold: isHeader || opts.bold === true,
                      italics: opts.italics === true }),
      ],
    })],
  });
}
function image(filename, w, h) {
  const data = fs.readFileSync(path.join(FIG_DIR, filename));
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 60 },
    children: [new ImageRun({
      type: "png",
      data,
      transformation: { width: w || 320, height: h || 200 },
      altText: { title: filename, description: filename, name: filename },
    })],
  });
}

module.exports = {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, Footer, Header,
  FONT, run, it, bd, sub, sup, p, pf, h1, h2, h3, eq, bullet, caption,
  tableCell, image, FIG_DIR,
};
