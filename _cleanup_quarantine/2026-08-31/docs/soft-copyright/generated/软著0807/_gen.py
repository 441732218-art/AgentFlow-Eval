#!/usr/bin/env python3
"""V2.0: natural order, 60 continuous pages, no omission marker."""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

PROJECT = Path(r'D:\AgentFlow-Eval\backend')
OUTPUT = Path(r'D:\AgentFlow-Eval\docs\soft-copyright\generated\软著0807\AgentFlow-Eval 源程序鉴别材料 V2.0.pdf')
LPP = 70  # lines per page

p = PROJECT
order = [
    'app/main.py','app/config.py','app/core/dependencies.py',
]
for f in sorted((p/'app'/'models').glob('*.py')):
    order.append(str(f.relative_to(p)).replace('\\','/'))
order += [
    'app/core/agent_runner/base.py','app/core/agent_runner/protocol.py',
    'app/core/ab/service.py','app/core/benchmark/service.py',
]
for f in sorted((p/'app'/'api'/'v1'/'endpoints').glob('*.py')):
    order.append(str(f.relative_to(p)).replace('\\','/'))
for f in sorted((p/'app'/'utils').glob('*.py')):
    order.append(str(f.relative_to(p)).replace('\\','/'))
for f in sorted((p/'app'/'plugins').rglob('*.py')):
    order.append(str(f.relative_to(p)).replace('\\','/'))
for f in sorted((p/'scripts').glob('*.py')):
    order.append(str(f.relative_to(p)).replace('\\','/'))
order += ['_start_api.py','scripts_local_api_test.py']

all_lines = []
for rel in order:
    fp = p / rel
    if not fp.exists(): continue
    all_lines.append(f'# === File: {rel} ===')
    ct = fp.read_text(encoding='utf-8').rstrip('\n')
    if ct: all_lines.extend(ct.split('\n'))

TOTAL = len(all_lines)
front_n = 30 * LPP
back_start = TOTAL - 30 * LPP
print(f'Lines:{TOTAL} Front30:{front_n} BackStart:{back_start}')
print(f'Front:{all_lines[0][:70]}')
print(f'Back:{all_lines[back_start][:70]}')

# Font
for fp in [r'C:\Windows\Fonts\simsun.ttc', r'C:\Windows\Fonts\msyh.ttc']:
    if Path(fp).exists():
        pdfmetrics.registerFont(TTFont('CJK', str(fp)))
        CF='CJK'; HF='CJK'; break
else: CF='Courier'; HF='Courier'

# PDF
W,H = A4; c = canvas.Canvas(str(OUTPUT), pagesize=A4)
LM = 1.5*cm; RM = 1.5*cm; TM = 1.5*cm; BM = 1.5*cm
CH = H - TM - BM; LH = CH / LPP
LY = BM * 0.6; HS=9; CS=7; FS=8

# Build page list: front 30 + back 30, continuous numbering 1-60
page_lines = []
for i in range(30):  # front 30
    s = i * LPP; e = min(s + LPP, TOTAL)
    page_lines.append(all_lines[s:e])
for i in range(30):  # back 30
    s = back_start + i * LPP; e = min(s + LPP, TOTAL)
    page_lines.append(all_lines[s:e])

# Pad last page if needed
for idx in range(len(page_lines)):
    if len(page_lines[idx]) < LPP:
        page_lines[idx] = page_lines[idx] + [''] * (LPP - len(page_lines[idx]))

for pg_num, pc in enumerate(page_lines, 1):
    # Header: top-right
    c.setFont(HF, HS)
    c.setFillColor(colors.black)
    hdr = "AgentFlow-Eval V1.0"
    tw = c.stringWidth(hdr, HF, HS)
    c.drawString(W - RM - tw, H - TM + 0.5*cm, hdr)
    
    # Code
    c.setFont(CF, CS)
    y = H - TM - LH
    for line in pc:
        dl = line.rstrip().replace('\t','    ')
        if len(dl) > 120: dl = dl[:118] + '..'
        c.drawString(LM, y, dl)
        y -= LH
    
    # Bottom line + page number
    c.setStrokeColor(colors.black); c.setLineWidth(0.5)
    c.line(LM, LY, W - RM, LY)
    c.setFont(HF, FS)
    ft = f"第 {pg_num} 页 / 共 60 页"
    tw = c.stringWidth(ft, HF, FS)
    c.setFillColor(colors.white); c.setStrokeColor(colors.white)
    c.rect(W/2 - tw/2 - 3, LY - 5, tw + 6, 10, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.drawCentredString(W/2, LY - 3, ft)
    c.showPage()

c.save()
print(f'PDF: {OUTPUT.name} | Pages: 60 | Size: {OUTPUT.stat().st_size/1024:.0f} KB')
print(f'Left: 1.5cm | Lines/page: {LPP} | Font: 7pt code')

