#!/usr/bin/env python3
"""Source-code identification document generator (stdlib only)."""
import html as html_mod, os, sys, math
from pathlib import Path

SOFTWARE_NAME = "AgentFlow-Eval"
VERSION = "V1.0"
AUTHOR = "李凯昕"
LINES_PER_PAGE = 50
TARGET_PAGES = 60
SCAN_ROOT = "backend"
FILE_EXT = ".py"
CC = "#"
EXCL = ["tests/","tests\\","test_","_test.py","conftest.py","__pycache__",
        ".venv","venv/","venv\\","migrations/","migrations\\","alembic/",
        "alembic\\","build/","build\\","dist/","dist\\",".egg-info"]
ROOT = None; HL = 0; TL = 0

# --- description mapping ---
_D={"_start_api":"启动脚本便捷入口","main":"应用入口与中间件装配",
"config":"全局配置与环境变量","router":"路由注册与分发逻辑",
"ab":"AB测试分流接口","agents_http":"外部智能体接入探测接口",
"audit":"审计日志查询接口","benchmarks":"基准评测管理接口",
"billing":"计费订阅管理接口","dashboard":"驾驶舱统计数据接口",
"diagnosis":"故障诊断分析接口","experiments":"对比实验管理接口",
"judges":"评分卡与评判接口","logs":"系统日志查询接口",
"me":"当前用户信息接口","media":"多模态媒体上传接口",
"observability":"可观测性指标接口","plugins":"插件管理接口",
"reports":"评测报告查询接口","settings":"系统设置读取接口",
"tasks":"评测任务管理接口","tenants":"多租户管理接口",
"tools":"工具沙箱列表接口","traces":"执行轨迹查询接口",
"ws":"实时活动推送接口","check_prod":"生产环境配置检查",
"middleware":"鉴权与安全中间件定义","rbac":"角色权限访问控制",
"security":"密钥鉴权与身份验证","seed":"演示数据种子脚本逻辑",
"settings_guard":"生产设置校验守卫","events":"事件发布与订阅总线",
"ws_hub":"广播管理中心实现","dependencies":"依赖注入与会话工厂",
"tenancy":"租户隔离过滤查询","tenant_context":"租户上下文管理器",
"assignment":"粘性分流分配算法","service":"核心服务逻辑实现",
"stats":"统计检验与样本估算","inprocess":"进程内事件总线实现",
"redis_pubsub":"事件总线适配实现","memory_only":"纯内存缓存实现",
"redis_l2":"二级缓存适配实现","noop":"空操作计量实现",
"sqlalchemy_meter":"数据库计量适配器","celery_queue":"分布式队列适配",
"eager_queue":"同步队列适配实现","memory_queue":"内存队列适配实现",
"factory":"工厂注册与实例创建","http_runner":"外部服务执行器实现",
"openai_runner":"多轮推理执行器实现","parser":"响应解析与字段提取",
"protocol":"通信协议规范定义","ssrf":"请求安全防护校验",
"tool_sandbox":"工具沙箱安全执行","celery":"任务队列实例配置",
"compare":"评测结果对比分析","pipeline":"评测流水线编排",
"llm_judge":"大模型语义评判实现","metrics":"规则指标计算函数集",
"scorecard":"评分卡维度权重定义","evaluator":"多模态评估核心逻辑",
"image":"图像特征提取处理","pdf":"文档特征提取处理",
"spreadsheet":"表格特征提取处理","text":"文本特征提取处理",
"registry":"注册表管理逻辑实现","storage":"媒体文件存储管理",
"types":"数据类型定义集合","business_kpis":"业务指标统计函数",
"slow_tasks":"慢任务监控检测","timeseries":"时序数据聚合查询",
"tracing":"分布式追踪集成配置","context":"日志上下文管理",
"emit":"日志事件发射函数","logger":"结构化日志记录器",
"redaction":"日志脱敏处理函数","commerce":"商业插件接口规范",
"entitlement":"插件授权校验逻辑","hooks":"生命周期钩子定义",
"loader":"插件动态加载机制","manager":"插件生命周期管理器",
"market":"插件市场注册表管理","sandbox":"插件沙箱执行环境",
"signature":"插件签名验证校验","versioning":"插件版本管理兼容",
"event_bus":"事件总线端口抽象","metering":"计量端口抽象定义",
"task_queue":"任务队列端口抽象","circuit_breaker":"熔断器模式实现",
"policy":"弹性策略组合定义","retry":"重试策略与退避算法",
"timeout":"超时控制策略实现","agent_log":"智能体日志模型",
"audit_log":"审计日志数据模型","benchmark":"基准评测数据模型",
"experiment":"对比实验数据模型","media_asset":"媒体资源数据模型",
"metric_score":"指标评分数据模型","slow_task":"慢任务记录模型",
"task":"评测任务数据模型","tenant":"租户数据模型定义",
"trace":"执行轨迹数据模型","audit_hooks":"审计钩子插件示例",
"echo_runner":"回声执行器插件示例","echo_tool":"回声工具插件示例",
"length_judge":"长度评判插件示例","cost":"成本估算工具函数",
"exceptions":"自定义异常类定义","backfill_created_by":"回填创建者数据脚本",
"export_openapi":"导出接口文档脚本","client":"缓存客户端封装",
"decorators":"缓存装饰器定义","invalidation":"缓存失效策略管理",
"keys":"缓存键生成管理","services":"服务层封装函数集",
"warmup":"缓存预热策略函数","queries":"通用查询辅助函数集",
"engine":"核心引擎逻辑实现","stripe_checkout":"支付结账集成处理",
"base":"抽象基类与接口定义","cache":"缓存端口抽象定义",
"db":"数据库日志输出实现"}
_ID={"app":"后端应用","api":"接口层","v1":"版本一接口","endpoints":"端点模块",
"cli":"命令行工具","core":"核心逻辑","ab":"AB测试","adapters":"适配器层",
"bus":"事件总线适配器","cache":"缓存适配器","metering":"计量适配器",
"queue":"队列适配器","agent_runner":"执行器模块","benchmark":"基准评测",
"billing":"计费模块","celery_app":"异步任务","db":"数据库工具",
"diagnosis":"诊断引擎","evaluation":"评测引擎","judge_engine":"评判引擎",
"multimodal":"多模态评估","extractors":"特征提取器",
"observability":"可观测性","aols":"日志子系统","sinks":"日志输出目标",
"plugins":"插件系统","ports":"端口层","profiles":"部署剖面",
"resilience":"弹性策略","models":"数据模型","examples":"插件示例",
"schemas":"数据结构","utils":"工具函数"}

def get_desc(rel):
    p = Path(rel); s = p.stem
    if s == "__init__":
        d = _ID.get(p.parent.name, p.parent.name)
        return f"{d}包初始化"
    return _D.get(s, f"{s}模块功能实现")

def _excl(rel):
    r = rel.replace("\\","/")
    return any(p.replace("\\","/") in r for p in EXCL)

def scan(root):
    res = []
    for dp,_,fns in os.walk(root):
        for fn in fns:
            if not fn.endswith(FILE_EXT): continue
            fp = Path(dp)/fn
            rel = fp.relative_to(ROOT).as_posix()
            if not _excl(rel): res.append(rel)
    res.sort(); return res

def read_lines(rel):
    with open(ROOT/rel,"r",encoding="utf-8",errors="replace") as f: raw=f.readlines()
    while raw and raw[-1].strip()=="": raw.pop()
    return [l.rstrip("\n").rstrip("\r") for l in raw]

def mk_header(rel,desc,clen):
    s=f"{CC} {'='*77}"
    return [s,f"{CC} 软件名称：{SOFTWARE_NAME}",f"{CC} 版本号：{VERSION}",
            f"{CC} 著作权人：{AUTHOR}",f"{CC} 文件路径：{rel}",
            f"{CC} 功能描述：{desc}",
            f"{CC} 本文件代码行数：{clen} 行（不含本文件头注释块）",s]

def build_seq(files):
    S,ents=[],[]
    for f in files:
        lns=read_lines(f); cl=len(lns); desc=get_desc(f)
        h=mk_header(f,desc,cl); st=len(S)
        S.extend(h); S.extend(lns)
        ents.append({"p":f,"d":desc,"cl":cl,"s":st,"e":len(S)-1})
    return S,ents

def paginate(S,T):
    global HL,TL
    if T>=LINES_PER_PAGE*TARGET_PAGES:
        HL=LINES_PER_PAGE*(TARGET_PAGES//2); TL=HL
        fr,bk=S[:HL],S[T-TL:]
    else:
        HL=T; TL=0; fr,bk=list(S),[]
    pgs=[]
    for i in range(0,len(fr),LINES_PER_PAGE):
        ch=fr[i:i+LINES_PER_PAGE]
        pgs.append({"n":i//LINES_PER_PAGE+1,"l":[(i+j+1,x) for j,x in enumerate(ch)]})
    for i in range(0,len(bk),LINES_PER_PAGE):
        ch=bk[i:i+LINES_PER_PAGE]
        pn=(len(fr)//LINES_PER_PAGE)+(i//LINES_PER_PAGE)+1
        b=T-TL+i
        pgs.append({"n":pn,"l":[(b+j+1,x) for j,x in enumerate(ch)]})
    return pgs,len(pgs)

# PLACEHOLDER:TOC_CSS_HTML
def build_toc(ents,T,tp):
    nf=HL//LINES_PER_PAGE if HL else 0; rows=[]
    for idx,e in enumerate(ents,1):
        s,en=e["s"],e["e"]; fp,bp=[],[]
        if HL>0:
            fs,fe=max(s,0),min(en,HL-1)
            if fs<=fe:
                p1=fs//LINES_PER_PAGE+1; p2=fe//LINES_PER_PAGE+1
                fp=list(range(p1,p2+1))
        if TL>0:
            bs,be=max(s,T-TL),min(en,T-1)
            if bs<=be:
                o1,o2=bs-(T-TL),be-(T-TL)
                p1=nf+o1//LINES_PER_PAGE+1; p2=nf+o2//LINES_PER_PAGE+1
                bp=list(range(p1,p2+1))
        ap=sorted(set(fp+bp))
        if ap: ps=", ".join(str(p) for p in ap); rng=f"{s+1}–{en+1}"
        else: ps="未收录（位于省略区间）"; rng=f"{s+1}–{en+1}"
        rows.append((idx,e["p"],e["d"],ps,rng))
    return rows

def _e(t): return html_mod.escape(t,quote=False)

CSS=r"""
@page{size:A4 portrait;margin:22mm 18mm 18mm 18mm}
*{margin:0;padding:0;box-sizing:border-box}
html,body{font-family:'Courier New',Courier,monospace;font-size:9pt;color:#000;background:#fff}
.pg{display:flex;flex-direction:column;height:257mm;width:174mm;page-break-after:always;break-after:page;overflow:hidden}
.pg:last-child{page-break-after:auto}
.hd{display:flex;justify-content:space-between;align-items:baseline;padding-bottom:3mm;border-bottom:.5pt solid #333;margin-bottom:2mm;flex-shrink:0;font-size:9pt}
.hd .l{font-weight:bold}
.ca{flex:1 1 auto;margin:0;padding:0;overflow:hidden;font-family:'Courier New',Courier,monospace;font-size:9pt;line-height:1.4;white-space:pre;border:none;background:transparent}
.ft{text-align:center;padding-top:2mm;border-top:.5pt solid #999;margin-top:2mm;flex-shrink:0;font-size:8pt;color:#555}
.tw{padding:0}
.tt{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:6mm}
.tm{font-size:9pt;margin-bottom:5mm;line-height:1.8}
.tm b{display:inline-block;min-width:120pt}
.tb{width:100%;border-collapse:collapse;font-size:7.5pt}
.tb th,.tb td{border:.5pt solid #666;padding:2pt 3pt;text-align:left;vertical-align:top}
.tb th{background:#eee;font-weight:bold}
.tb .c{text-align:center}
.tn{font-size:8pt;margin-top:4mm;color:#333;line-height:1.5}
.wr{color:red;font-weight:bold;font-size:10pt}
@media print{.pg{page-break-after:always;break-after:page}.pg:last-child{page-break-after:auto}}
"""

def gen_html(toc,pgs,tp,T,fc,fb):
    h=[]; hl=_e(f"{SOFTWARE_NAME} 源程序鉴别材料"); hr=_e(VERSION)
    h.append("<!DOCTYPE html>"); h.append('<html lang="zh-CN">')
    h.append(f"<head><meta charset=\"UTF-8\"><title>{SOFTWARE_NAME} 源程序鉴别材料</title>")
    h.append(f"<style>{CSS}</style></head><body>")
    # TOC
    h.append('<div class="pg">')
    h.append(f'<div class="hd"><span class="l">{hl}</span><span class="r">{hr}</span></div>')
    h.append('<div class="tw">')
    h.append(f'<div class="tt">{_e(SOFTWARE_NAME)} 源程序鉴别材料 — 目录</div>')
    h.append('<div class="tm">')
    h.append(f'<b>软件名称：</b>{_e(SOFTWARE_NAME)}<br>')
    h.append(f'<b>版本号：</b>{_e(VERSION)}<br>')
    h.append(f'<b>著作权人：</b>{_e(AUTHOR)}<br>')
    h.append(f'<b>源程序收录文件数：</b>{fc}<br>')
    h.append(f'<b>源程序总行数 T：</b>{T}<br>')
    h.append(f'<b>本文档代码页数：</b>{tp}<br>')
    if fb: h.append(f'<span class="wr">源码总行数不足 {TARGET_PAGES*LINES_PER_PAGE}，无法构成 {TARGET_PAGES} 页，已全文收录、无填充</span><br>')
    h.append('</div>')
    h.append('<table class="tb"><tr><th class="c">序号</th><th>文件相对路径</th><th>功能描述</th><th class="c">收录代码页</th><th class="c">全局行号区间</th></tr>')
    for (i,fp,d,pg,rng) in toc:
        h.append(f'<tr><td class="c">{i}</td><td>{_e(fp)}</td><td>{_e(d)}</td><td class="c">{_e(pg)}</td><td class="c">{_e(rng)}</td></tr>')
    h.append('</table>')
    nf=HL//LINES_PER_PAGE if HL else 0
    if not fb: h.append(f'<div class="tn">本文档依软著规范收录源程序前 {nf} 页与后 {tp-nf} 页，共 {tp} 页代码页；中间部分不予体现，未设省略页。</div>')
    else: h.append(f'<div class="tn">源程序总行数不足，已全文收录共 {tp} 页，无省略。</div>')
    h.append('</div><div class="ft">目录</div></div>')
    # Code pages
    for pg in pgs:
        h.append('<div class="pg">')
        h.append(f'<div class="hd"><span class="l">{hl}</span><span class="r">{hr}</span></div>')
        h.append('<pre class="ca">')
        for (ln,code) in pg["l"]:
            h.append(f"{ln:04d} | {_e(code)}")
        h.append('</pre>')
        h.append(f'<div class="ft">第 {pg["n"]} 页 / 共 {tp} 页</div></div>')
    h.append("</body></html>")
    return "\n".join(h)
def self_check(pgs,tp,T,html_,ents,fb):
    r=[]
    # 1 page count
    exp=math.ceil(T/LINES_PER_PAGE) if fb else TARGET_PAGES
    r.append(("代码页总数",tp==exp,f"期望={exp} 实际={tp}"))
    # 2 lines per page
    bad=[p["n"] for p in pgs if not(fb and p["n"]==tp and len(p["l"])>0) and len(p["l"])!=LINES_PER_PAGE]
    if fb and pgs and len(pgs[-1]["l"])==0: bad.append(pgs[-1]["n"])
    r.append(("每页行数",len(bad)==0,f"异常页={bad}" if bad else "全部通过"))
    # 3 no empty
    emp=[p["n"] for p in pgs if len(p["l"])==0]
    r.append(("空页检测",len(emp)==0,f"空页={emp}" if emp else "无空页"))
    # 4 no placeholder
    phs=["此处省略","省略第","省略 ","……占位"]
    fd=[p for p in phs if p in html_]
    r.append(("占位文检测",len(fd)==0,f"发现={fd}" if fd else "无占位文"))
    # 5 page continuity
    nums=[p["n"] for p in pgs]; exp_n=list(range(1,tp+1))
    r.append(("页码连续性",nums==exp_n,f"1..{tp}连续" if nums==exp_n else f"异常"))
    # 6 TOC
    r.append(("目录页存在","tb" in html_ and "tm" in html_,"存在" if "tb" in html_ else "缺失"))
    # 7 file header in front
    nf=HL//LINES_PER_PAGE if HL else 0
    fps=set()
    for p in pgs:
        if p["n"]<=nf:
            for (_,ln) in p["l"]:
                if "文件路径：" in ln: fps.add(ln.split("文件路径：")[-1].strip())
    fok=all(e["p"] in fps for e in ents if e["s"]<HL)
    r.append(("前段文件头",fok,"全部可见" if fok else "部分缺失"))
    # 8 identifier integrity
    ids=["CORSMiddleware","BaseSettings","add_middleware","latency_ms","execution_id","ensure_ascii","scalar_one_or_none"]
    found=[i for i in ids if i in html_]
    r.append(("标识符完整性",len(found)>=3,f"命中={found}"))
    # 9 line number range
    if not fb and pgs:
        ln1=pgs[0]["l"][0][0]; ln2=pgs[nf-1]["l"][-1][0]
        ln3=pgs[nf]["l"][0][0]; ln4=pgs[-1]["l"][-1][0]
        ok=ln1==1 and ln2==HL and ln3==T-TL+1 and ln4==T
        r.append(("行号范围",ok,f"前段={ln1}..{ln2} 后段={ln3}..{ln4} T={T}"))
    else: r.append(("行号范围",True,"兜底模式跳过"))
    # 10 overflow protection
    r.append(("打印溢出防护","overflow" in html_ and "height" in html_,"已有overflow+height"))
    return r

def gen_report(files,ents,S,T,tp,pgs,toc,cks,fb):
    L=[f"# 源程序鉴别材料 — 生成报告\n\n- **软件名称：** {SOFTWARE_NAME}",
       f"- **版本号：** {VERSION}\n- **著作权人：** {AUTHOR}",
       f"- **收录文件数：** {len(files)}\n- **源程序总行数 T：** {T}",
       f"- **每页行数：** {LINES_PER_PAGE}\n- **代码页总数：** {tp}"]
    if fb: L.append(f"- ⚠️ **源码不足 {TARGET_PAGES*LINES_PER_PAGE} 行，已全文收录**")
    L.append("\n---\n\n## 自检清单\n")
    ap=all(o for _,o,_ in cks)
    for n,o,d in cks: L.append(f"- {'✅' if o else '❌'} **{n}**：{d}")
    L.append(f"\n**{'全部自检通过。' if ap else '存在未通过项！'}**")
    L.append("\n---\n\n## 文件清单\n\n| 序号 | 文件路径 | 描述 | 代码行 | 区间 | 收录页 |")
    L.append("|------|----------|------|--------|------|--------|")
    for (i,fp,d,pg,rng) in toc:
        e=ents[i-1]; L.append(f"| {i} | `{fp}` | {d} | {e['cl']} | {rng} | {pg} |")
    L.append("\n---\n\n## 打印说明\n")
    L.append("1. Chrome/Edge 打开 HTML\n2. Ctrl+P → 另存为 PDF\n3. 边距「默认」→ 勾选「背景图形」")
    L.append("4. 人工检查首页末页各50行无串页\n")
    return "\n".join(L)

def main():
    global ROOT
    sd=Path(__file__).resolve().parent; ROOT=sd.parent.parent
    oh=sd/"源程序鉴别材料.html"; orp=sd/"生成报告.md"
    print(f"[1/5] 扫描 {SCAN_ROOT}/ ...")
    sr=ROOT/SCAN_ROOT
    if not sr.exists(): print(f"ERROR: {sr} 不存在"); sys.exit(1)
    files=scan(sr); print(f"      收录文件: {len(files)}")
    print("[2/5] 构建全局行序列 ...")
    S,ents=build_seq(files); T=len(S); print(f"      总行数 T={T}")
    for e in ents: print(f"        {e['p']:55s} code={e['cl']:4d} [{e['s']+1}..{e['e']+1}] {e['d']}")
    print("[3/5] 分页 ...")
    fb=T<LINES_PER_PAGE*TARGET_PAGES
    pgs,tp=paginate(S,T)
    if fb: print(f"      ⚠️ 源码不足，全文收录 {tp} 页")
    else:
        nf=HL//LINES_PER_PAGE
        print(f"      前段: 行1..{HL} → 页1..{nf}")
        print(f"      后段: 行{T-TL+1}..{T} → 页{nf+1}..{tp}")
        print(f"      中间丢弃: 行{HL+1}..{T-TL}")
    print("[4/5] 生成 HTML ...")
    toc=build_toc(ents,T,tp)
    html_=gen_html(toc,pgs,tp,T,len(files),fb)
    with open(oh,"w",encoding="utf-8") as f: f.write(html_)
    print(f"      → {oh}")
    print("[5/5] 自检 ...")
    cks=self_check(pgs,tp,T,html_,ents,fb)
    for n,o,d in cks: print(f"      [{'PASS' if o else 'FAIL'}] {n}: {d}")
    rpt=gen_report(files,ents,S,T,tp,pgs,toc,cks,fb)
    with open(orp,"w",encoding="utf-8") as f: f.write(rpt)
    print(f"\n      报告 → {orp}")
    print(f"\n{'='*60}\n生成完成!\n  收录文件数: {len(files)}\n  源程序总行数 T: {T}\n  实际代码页数: {tp}")
    if fb: print(f"  ⚠️ 触发不足兜底，建议扩大扫描范围")
    print(f"  HTML: {oh}\n  报告: {orp}\n")
    print("打印 PDF:\n  1. Chrome/Edge 打开 HTML\n  2. Ctrl+P → 另存为 PDF → 默认边距 → 勾选背景图形\n  3. 检查首页末页各50行无串页")
    print(f"{'='*60}")
    if not all(o for _,o,_ in cks): print("\n⚠️ 存在自检未通过项！"); sys.exit(1)

if __name__=="__main__": main()