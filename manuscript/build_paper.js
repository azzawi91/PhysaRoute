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
// Top-level assembler.  Concatenates all sections into a single docx and writes
// the file to the workspace folder.

const fs = require("fs");
const H  = require("./build_paper_part1.js");
const M1 = require("./build_paper_main.js");
const M2 = require("./build_paper_part2.js");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat,
  HeadingLevel, PageNumber, Footer,
} = H;

const BODY = [
  // Front matter
  M1.titlePara,
  M1.authorPara,
  M1.affilPara,
  M1.abstractBody,
  M1.indexTerms,

  // Sections
  ...M1.intro,
  ...M1.related,
  ...M1.background,
  ...M1.sysmodel,
  ...M1.protocol,
  M1.tableNotation, M1.captionTable1,
  ...M1.analysis,

  ...M2.simSetup,
  M2.tableSim, M2.captionTable2,
  ...M2.results,
  M2.tableStats, M2.captionTable3,
  ...M2.results_tail,

  ...M2.clinical,
  M2.tableClinical, M2.captionTable4,
  ...M2.clinical_tail,

  ...M2.limits,
  ...M2.conclusion,
  ...M2.refsSection,
];

const doc = new Document({
  creator: "Mustafa Mazzawi",
  title: "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for WBANs",
  styles: {
    default: { document: { run: { font: H.FONT, size: 20 } } },
  },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 270 } } },
      }],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 }, // US Letter
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 },
      },
      column: { count: 2, space: 540, equalWidth: true, separate: false },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Mazzawi — PhysaRoute   |   Page ",
                          font: H.FONT, size: 18 }),
            new TextRun({ children: [PageNumber.CURRENT],
                          font: H.FONT, size: 18 }),
          ],
        })],
      }),
    },
    children: BODY,
  }],
});

const path = require("path");
const OUT_DIR = path.join(__dirname, "output");
const OUT = path.join(OUT_DIR, "PhysaRoute_IEEE_IoTJ_Manuscript.docx");

Packer.toBuffer(doc).then(buffer => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(OUT, buffer);
  console.log("Wrote", OUT, "size", buffer.length, "bytes");
}).catch(err => { console.error(err); process.exit(1); });
