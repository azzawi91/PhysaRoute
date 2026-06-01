#!/usr/bin/env python3
# =============================================================================
# Copyright (c) 2026 Mustafa Mazzawi.  All rights reserved.
#
# This file is part of the PhysaRoute reference implementation accompanying
# the manuscript "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for
# Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT"
# (IEEE Internet of Things Journal, under review).
#
# All rights reserved.  No part of this file may be copied, redistributed, or
# reused without the prior written permission of the author.  See LICENSE for
# the full terms.  Contact: mazzawi1991@gmail.com
# =============================================================================
"""Final Appendix-F fix: drop the stale 'the abstract's phrasing is imprecise'
sentence now that the abstract has been corrected inline."""
import os
from docx import Document
from docx.oxml.ns import qn

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO = _os.path.dirname(_HERE)
SRC = _os.path.join(_REPO, "manuscript", "output", "PhysaRoute_IEEE_IoTJ_Manuscript_Submission.docx")
doc = Document(SRC)

# Use the *actual* phrasing found in the file (typographic quotes, shorter
# noun "a nomenclature standard").
SRC_FRAG = (
    "IEEE 11073-10101 [29] is a nomenclature standard "
    "(sensor-type and metric labelling) and does not specify a timing "
    "envelope; the abstract’s “compliance with IEEE 11073-10101 "
    "timing requirements” is imprecise."
)
DST_FRAG = (
    "IEEE 11073-10101 [29] is a nomenclature standard "
    "(sensor-type and metric labelling) and does not specify a timing "
    "envelope, so the timing claim in Section IX is framed against IEC "
    "60601-2-27 [40] rather than 11073-10101."
)

# Walk every paragraph and replace
n = 0
for p in doc.element.body.findall('.//' + qn('w:p')):
    ts = p.findall('.//' + qn('w:t'))
    if not ts:
        continue
    joined = ''.join(t.text or '' for t in ts)
    if SRC_FRAG in joined:
        new = joined.replace(SRC_FRAG, DST_FRAG, 1)
        ts[0].text = new
        ts[0].set(qn('xml:space'), 'preserve')
        for t in ts[1:]:
            t.text = ''
        n += 1
        print("  fixed Appendix F paragraph")
        break

print(f"replacements applied: {n}")
doc.save(SRC)
print("saved")
