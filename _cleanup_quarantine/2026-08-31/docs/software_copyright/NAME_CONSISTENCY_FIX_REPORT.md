# 软件名称一致性修正报告（NAME CONSISTENCY FIX REPORT）

> 修正日期：2026-08
> 修正性质：仅修改软著说明材料，未修改任何源码与冻结文件

---

## 1. 修改文件列表

| 文件 | 修改位置 |
|------|----------|
| technical_features.md | 第 11 行（软件简介中的正式名称） |
| AgentFlow-Eval_V1.0.0_User_Manual.md | 第 3 行（软件名称字段）、第 13 行（软件简介） |

---

## 2. 修改前后名称

| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| technical_features.md | AgentFlow-Eval 是一个面向智能体（Agent）工作流的评测平台 | AgentFlow Intelligence 是一个面向智能体（Agent）工作流的评测平台 |
| User_Manual.md（软件名称字段） | 软件名称：AgentFlow-Eval（智能体工作流评测平台） | 软件名称：AgentFlow Intelligence（智能体工作流评测平台） |
| User_Manual.md（软件简介） | AgentFlow-Eval 是一款面向智能体（Agent）工作流的评测平台 | AgentFlow Intelligence 是一款面向智能体（Agent）工作流的评测平台 |

---

## 3. 未修改源码确认

- ✅ 未修改 `backend/app/**`
- ✅ 未修改 `frontend/**`
- ✅ 未修改 `AgentFlow-Eval_V1.0.0_source_code.txt` / `.docx`
- ✅ 未重新生成源码提交文件

---

## 4. 是否影响冻结源码材料

**否。** 本次仅修改 2 份说明材料的正式名称表述，未触及源码提交文件（TXT / DOCX），冻结版本不受影响。

---

## 5. 保留为简称 / 仓库名 / 文件名 / 协议名 / 代码标识的位置（未改动）

| 类别 | 保留值 |
|------|--------|
| 软件简称 | AgentFlow-Eval |
| 仓库名称 | AgentFlow-Eval |
| 文档标题项目标识 | AgentFlow-Eval（如「# AgentFlow-Eval …」） |
| 生成文件名 | AgentFlow-Eval_V1.0.0_* |
| 协议名 | agentflow.http.v1 |
| 源码文件头注释标识 | # AgentFlow-Eval Agent自动化评测工作台 |

---

## 结论

正式软件名称已统一为「AgentFlow Intelligence（智能体工作流评测平台）」，软件简称为「AgentFlow-Eval」，版本 V1.0.0。仅修改软著说明材料，未修改源码和冻结源码提交文件。
