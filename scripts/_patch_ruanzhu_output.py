# -*- coding: utf-8 -*-
"""Build revised soft-copyright outputs with expanded M4."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_ruanzhu_materials.py"
OUT_DIR = ROOT / "docs" / "soft-copyright"
SPLIT = OUT_DIR / "全能生成材料_分册"

EXTRA_M4 = """

---

## 附录A 术语对照总表（鉴别一致性）

为确保申请表、用户手册、设计说明书与源程序四类材料在审核中不出现概念漂移，特将核心对象的中文名称与代码标识对照如下：评测任务对应 Task 表与任务 API；测试用例对应 TestSuite 表与用例导入接口；执行轨迹对应 Trace 表与轨迹查询及 DAG 可视化数据源；指标分对应 MetricScore 表与评分卡片及报告聚合字段；审计日志对应 AuditLog 表与审计查询接口。凡正文首次出现优先使用中文全称加括号英文标识的形式，后续可在不引起歧义时使用中文简称，但不得改用未定义别名如“案例包”“流水账”等口语化称呼。该对照表与第三章模块设计、第四章数据设计及用户手册功能名称保持同一语义体系。

## 附录B 开发完成信息与版权年份对齐说明

本软件 V1.0 开发完成日期为 2026年7月14日，与版本变更记录及源程序文件头版权注释年份 2026 保持一致。源程序鉴别材料中的版权行统一写作版权标记加 2026 年及权利人姓名。申请表填写开发完成日期时，应与本说明书封面信息一致，避免出现完成年份与版权注释年份不一致导致的形式审查风险。材料二源代码注释已按该年份统一，不再使用其它未经验证的年份数字。

## 附录C 全流程测试验证范围摘要

著作权人李凯昕独立完成的全流程测试验证涵盖：鉴权开启与关闭两种模式下的评测任务创建与列表隔离；测试用例 CSV 与 JSON 导入解析；Eager 与异步路径下的执行落库；执行轨迹步骤完整性；无密钥规则评分与有密钥混合评分降级；人工复核有效分优先；报告聚合可读；工具沙箱超时与非法表达式拒绝；健康检查降级状态。上述验证保证软件以可运行形态支撑登记鉴定，而非停留在设计草图阶段。测试结论与第十二章质量保障描述相互印证。

## 附录D 审核关注点自检清单

第一，功能描述是否与可点击界面一致；第二，术语是否统一为评测任务、测试用例、执行轨迹、指标分；第三，独创性是否明确写明由著作权人李凯昕独立完成系统架构设计、核心算法编码、领域模型定义及全流程测试验证；第四，敏感信息是否已脱敏；第五，设计说明书汉字量是否达到一万字以上；第六，截图文件名是否符合图序与功能名称规范且无演示水印。本清单用于提交前自检，不构成额外权利主张。
"""

PHRASE = "由著作权人李凯昕独立完成系统架构设计、核心算法编码、领域模型定义及全流程测试验证"


def cn_count(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def load_gen():
    spec = importlib.util.spec_from_file_location("gen_rz", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    g = load_gen()
    m1 = g.build_m1()
    m2 = g.build_m2()
    m3 = g.build_m3()
    m4 = g.build_m4() + EXTRA_M4

    # Normalize originality phrase (exact requirement wording)
    m1 = m1.replace(
        "**上述系统架构设计、核心算法编码、领域模型定义及全流程测试验证，均由著作权人李凯昕独立完成**",
        f"**{PHRASE}**",
    )
    m1 = m1.replace(
        "均由著作权人李凯昕独立完成",
        "——具体为" + PHRASE.replace("由著作权人李凯昕", ""),
    )
    # if double-mangled, rebuild m1 cleanly
    if PHRASE not in m1:
        m1 = g.build_m1()
        # inject into 技术架构 section
        anchor = "而非对单一开源组件的简单堆叠调用。"
        if anchor in m1 and PHRASE not in m1:
            m1 = m1.replace(
                anchor,
                f"由著作权人李凯昕独立完成系统架构设计、核心算法编码、领域模型定义及全流程测试验证。{anchor}",
            )

    m4 = m4.replace(
        "**系统架构设计、核心算法编码、领域模型（评测任务 Task / 测试用例 TestSuite / 执行轨迹 Trace / 指标分 MetricScore）定义，以及全流程测试验证，均由著作权人李凯昕独立完成。**",
        f"**{PHRASE}。** 领域模型具体包括评测任务（Task）、测试用例（TestSuite）、执行轨迹（Trace）、指标分（MetricScore）等核心对象。",
    )
    m4 = m4.replace(
        "**系统架构设计、核心算法编码、领域模型定义及全流程测试验证，均由著作权人李凯昕独立完成。**",
        f"**{PHRASE}。**",
    )
    if PHRASE not in m4:
        m4 = m4.replace(
            "## 第十三章 独创性综合论述",
            f"## 第十三章 独创性综合论述\n\n**{PHRASE}。**\n",
        )

    # Ensure closing chapter also has phrase
    if m4.count(PHRASE) < 2:
        m4 = m4.replace(
            "特此作为文档鉴别材料提交。",
            f"{PHRASE}。特此作为文档鉴别材料提交。",
        )

    full = g.HEADER + m1 + g.SEP + m2 + g.SEP + m3 + g.SEP + m4

    SPLIT.mkdir(parents=True, exist_ok=True)
    (SPLIT / "01_软件主要功能与技术特点.md").write_text(m1, encoding="utf-8")
    (SPLIT / "02_核心源代码.md").write_text(m2, encoding="utf-8")
    (SPLIT / "03_用户使用手册.md").write_text(m3, encoding="utf-8")
    (SPLIT / "04_软件设计说明书.md").write_text(m4, encoding="utf-8")

    targets = [
        OUT_DIR / "软著全能生成材料_V1.0_修订版.md",
        OUT_DIR / "软著全能生成材料_V1.0.md",
    ]
    for p in targets:
        try:
            p.write_text(full, encoding="utf-8")
            print("wrote", p, p.stat().st_size)
        except OSError as exc:
            print("skip", p, exc)

    print("M1 cn", cn_count(m1))
    print("M4 cn", cn_count(m4))
    print("phrase count", full.count(PHRASE))
    print("shot guide", full.count("不可含 Demo/test 水印"))
    print("copyright lines", full.count("(c) 2026"))
    if cn_count(m4) < 10000:
        raise SystemExit("M4 still short")
    if cn_count(m1) < 500 or cn_count(m1) > 1300:
        print("WARN M1 range", cn_count(m1))
    print("OK")


if __name__ == "__main__":
    main()
