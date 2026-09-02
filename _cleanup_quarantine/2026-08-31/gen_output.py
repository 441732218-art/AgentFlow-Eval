#!/usr/bin/env python3
import os,sys,html as h
BASE_DIR="D:/AgentFlow-Eval"
OUTFILE=r"C:\Users\yunqi\Documents\Codex\2026-07-06\agentflow-eval-agent-agentflow-eval-web-2\材料一_源代码_甄别代码.html"
FILES=["backend/app/main.py","backend/app/config.py","backend/app/core/middleware.py","backend/app/core/agent_runner/openai_runner.py","backend/app/core/judge_engine/llm_judge.py","backend/app/core/judge_engine/scorecard.py","backend/app/core/evaluation/pipeline.py","backend/app/core/evaluation/compare.py","backend/app/core/celery_app/tasks.py"]
L=[];TL=0
for fp in FILES:
 p=os.path.join(BASE_DIR,fp)
 with open(p,encoding="utf-8") as f:
  c=f.read().splitlines()
 L.append(f"--- File: {fp} ---")
 L.extend(c);TL+=len(c)
LN=len(L)
if LN>3000:
 F=L[:1500]
 LS=L[LN-1500:]
 O=LN-3000
 N=f"(第31~{(LN+49)//50-30}页已省略，共省略{O}行)"
else:
 F=list(L);LS=[];O=0;N=""
def E(s): return h.escape(s,quote=True)
def OUT(b,s):
 b.append('<div class="code-page"><pre class="code-listing">')
 cf=""
 for i,ln in enumerate(s,len(L)-len(s)+1 if s is LS else 1):
  if ln.startswith("--- File: "):
   fn=ln.replace("--- File: ","").replace(" ---","")
   if cf!=fn:
    cf=fn
    b.append(f'<span class="file-header">\u25b6 \u6587\u4ef6\uff1a{E(fn)}</span>')
   continue
  b.append(f'<span class="line"><span class="ln">{i:6d}</span>\t{E(ln)}</span>')
 b.append('</pre></div>')
B=[];B.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>AgentFlow-Eval V1.0\u6e90\u4ee3\u7801\u6587\u6863</title><style>')
B.append('@page{size:A4 portrait;margin:2.5cm 2.5cm 3.5cm 2.5cm;')
B.append('@bottom-center{content:"\u7b2c " counter(page) " \u9875 / \u5171 " counter(pages) " \u9875\\A AgentFlow-Eval V1.0 | \u8457\u4f5c\u6743\u4eba\uff1a\u674e\u51ef\u6615";white-space:pre;font-size:9pt;font-family:"Microsoft YaHei",sans-serif;border-top:0.5pt solid #000;padding-top:8pt;}}')
B.append('*{margin:0;padding:0;box-sizing:border-box;}')
B.append('body{font-family:"Microsoft YaHei","SimSun",sans-serif;font-size:10.5pt;line-height:1.5;color:#000;background:#fff;}')
B.append('.cover{page-break-after:always;text-align:center;padding-top:8cm;}')
B.append('.cover h1{font-size:24pt;margin-bottom:1cm;}')
B.append('.cover h2{font-size:18pt;margin-bottom:3cm;}')
B.append('.cover .info{font-size:14pt;line-height:2.5;}')
B.append('.cover .info span{display:block;}')
B.append('.code-page{line-height:14pt;height:23.5cm;overflow:hidden;page-break-after:always;}')
B.append('.code-page:last-child{page-break-after:auto;}')
B.append('.code-listing{font-family:"Consolas","Courier New",monospace;font-size:9pt;line-height:14pt;white-space:pre-wrap;word-break:break-all;tab-size:4;}')
B.append('.line{display:block;width:100%;}')
B.append('.ln{display:inline-block;width:4.5em;text-align:right;margin-right:1.5em;color:#888;user-select:none;}')
B.append('.file-header{font-weight:bold;color:#003366;font-family:"Microsoft YaHei",sans-serif;font-size:10pt;display:block;margin:0.15cm 0;}')
B.append('.omitted-note{page-break-after:always;text-align:center;padding-top:5cm;font-size:14pt;color:#666;}')
B.append('</style></head><body>')
B.append('<div class="cover"><h1>\u8f6f\u4ef6\u8457\u4f5c\u6743\u7533\u8bf7</h1><h2>\u6e90\u4ee3\u7801\u6587\u6863\uff08\u7504\u522b\u4ee3\u7801\uff09</h2><div class="info">')
B.append('<span>\u8f6f\u4ef6\u5168\u79f0\uff1aAgentFlow-Eval</span><span>\u7248\u672c\u53f7\uff1aV1.0</span><span>\u8457\u4f5c\u6743\u4eba\uff1a\u674e\u51ef\u6615</span><span>\u5b8c\u6210\u65e5\u671f\uff1a2026\u5e747\u67087\u65e5</span>')
B.append('</div></div>')
OUT(B,F)
if N: B.append(f'<div class="omitted-note"><p>{E(N)}</p></div>')
if LS: OUT(B,LS)
B.append("</body></html>")
os.makedirs(os.path.dirname(OUTFILE),exist_ok=True)
with open(OUTFILE,"w",encoding="utf-8") as f: f.write("\n".join(B))
fsize=os.path.getsize(OUTFILE)
fsize=os.path.getsize(OUTFILE)
print(f"OK: {OUTFILE}\nTotal:{LN}\nFirst:{len(F)}\nLast:{len(LS)}\nOmit:{O}\nSize:{fsize/1024:.0f}KB")
import sys; sys.stdout.reconfigure(encoding='utf-8')
print("---DATA---")
print("\n".join(B))
print("---END---")
os.makedirs(os.path.dirname(OUTFILE),exist_ok=True)
with open(OUTFILE,"w",encoding="utf-8") as f: f.write("\n".join(B))
fsize=os.path.getsize(OUTFILE)
import sys; sys.stdout.reconfigure(encoding='utf-8')
print("---DATA---")
print("\n".join(B))
print("---END---")
