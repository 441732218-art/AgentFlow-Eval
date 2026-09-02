# 项目清理报告（CLEANUP REPORT）

> 清理时间：2026-08
> 清理原则：只删除安全缓存，不删除任何源码、测试、配置与软著材料

---

## 1. 删除文件列表（仅安全缓存）

| 类别 | 内容 | 数量 |
|------|------|------|
| Python 字节码缓存 | `__pycache__/` 目录 | 723 个 |
| 测试缓存 | `.pytest_cache/`（根目录 + backend） | 2 个 |
| Linter 缓存 | `.ruff_cache/` | 1 个 |

## 2. 未删除候选列表

以下文件仅列入候选，未删除，详见 `docs/CLEANUP_CANDIDATES.md`：

- 临时/调试文件（`_*.py`、`_*.txt`、`_*.md`、`_*.bat`、`_*.js` 等下划线前缀文件）
- 一次性文档生成脚本（`add_screenshots*.py`、`build_*.py`、`gen_*.py`、`fix_*.py`、`md_to_docx.py` 等）
- 大文件/生成产物（`raw_source.txt`、`source_code_60pages.txt`、`trimmed_source.txt` 等）

## 3. 保留确认（未删除）

- ✅ `backend/app/**`（业务源码）
- ✅ `frontend/src/**`（前端源码）
- ✅ `tests/**`、`config/**`、`migrations/**`
- ✅ `node_modules/`、`package.json`、`package-lock.json`
- ✅ `docs/software_copyright/**`（软著材料，全部保留）
- ✅ `.venv/`（虚拟环境）

## 4. 软著保护确认

**软著冻结材料未修改。**

**AgentFlow Intelligence V1.0.0 提交版本保持不变。**

冻结文件 SHA256 校验（清理后）：

| 文件 | SHA256 | 状态 |
|------|--------|------|
| source_code.txt | `eb1a447bfce964e1e59fefa6ab4035d32a368d2157b0af714c570fb3d09ceb09` | ✅ 未变 |
| source_code.docx | `3da7c2a6f5e983d68aa4bd7e2628f44e20b0da1a9369fc7074937a72be13fcc9` | ✅ 未变 |
| User_Manual.docx | `69e2cc68e2459efa3a7fdccf3b6930e9f32ced76b6555a5a53687d3ce55f7cee` | ✅ 未变 |
| technical_features.docx | `9a863ac87f2341c5ad699f2e7d85863b10f3300a20e4aa0cb41e484f7b85725e` | ✅ 未变 |
| source_manifest.docx | `6ef5a7606d1fe050e98416ac7312aedc683bcb4453828a3100f116e852ae800b` | ✅ 未变 |

## 5. git 状态变化

- 清理前：440 处变更（298 修改 + 142 未跟踪）
- 清理后：441 处变更（298 修改 + 143 未跟踪）
- 变化说明：+1 为新增 `docs/CLEANUP_CANDIDATES.md`；缓存删除未影响 git 状态（缓存文件均在 `.gitignore` 中）

## 6. 结论

本次仅清理了 723 个 `__pycache__` 目录、`.pytest_cache` 与 `.ruff_cache` 缓存，未删除任何源码、测试、配置或软著材料。所有疑似废弃文件均列入候选清单，待人工确认后再处理。
