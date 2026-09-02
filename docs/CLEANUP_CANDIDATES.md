# 项目清理候选清单（CLEANUP CANDIDATES）

> 生成日期：2026-08
> 性质：仅列出疑似废弃/临时文件候选，不删除
> 原则：宁可保留，也不破坏软著冻结版本

---

## 1. 临时 / 调试文件（下划线前缀）

| 文件 | 原因 | 风险 | 建议 |
|------|------|------|------|
| _backend_err.txt / _backend_out.txt / _code_err.txt / _gen_err.txt | 疑似调试日志/输出 | 无 | 人工确认后删除 |
| _check2.py / _check_deps.py / _check_output.py / _diag_html.py / _search_ver.py / _run_backend.py | 疑似临时检查脚本 | 可能被手动引用 | 人工确认后删除 |
| _check_playwright.js | 疑似临时检查脚本 | 可能被手动引用 | 人工确认后删除 |
| _fix_version.py / _run_code_doc.bat | 疑似临时脚本 | 可能被手动引用 | 人工确认后删除 |
| _done_flag.txt / _out.txt / _probe_result.md | 疑似临时标记/输出 | 无 | 人工确认后删除 |
| _install_log.txt / _screenshot_err.txt / _screenshot_out.txt / _screenshot_report.txt | 疑似临时日志 | 无 | 人工确认后删除 |
| .txt（0 字节） | 空文件 | 无 | 人工确认后删除 |

## 2. 一次性文档生成脚本（软著整理过程产物）

| 文件 | 原因 | 风险 | 建议 |
|------|------|------|------|
| add_screenshots.py / add_screenshots2.py | 疑似软著截图嵌入脚本 | 可能被引用 | 人工确认后删除 |
| build_copyright_60pages.py / build_source.py / build.py.txt | 疑似软著文档构建脚本 | 可能被引用 | 人工确认后删除 |
| gen_copyright_docx.py / gen_manual_docx.py / gen_output.py / md_to_docx.py | 疑似文档转换脚本 | 可能被引用 | 人工确认后删除 |
| fix_header.py / fix_manual.py / fix_output.py / fix_ruff.py / fix_versions.py | 疑似修复脚本 | 可能被引用 | 人工确认后删除 |
| clean_html.py / embed_screenshots.py / extract_copyright.py / prepare_copyright.py | 疑似软著处理脚本 | 可能被引用 | 人工确认后删除 |
| rebuild_clean.py / rebuild_html.py / trim_to_60.py / update_manual.py / check_pdf.py | 疑似软著处理脚本 | 可能被引用 | 人工确认后删除 |

## 3. 大文件 / 生成产物

| 文件 | 原因 | 风险 | 建议 |
|------|------|------|------|
| raw_source.txt（约 844KB） | 疑似源码导出中间产物 | 软著材料可能引用 | 人工确认后删除 |
| source_code_60pages.txt（约 570KB） | 疑似 60 页源码中间产物 | 软著材料可能引用 | 人工确认后删除 |
| trimmed_source.txt / copyright_raw.txt | 疑似中间产物 | 软著材料可能引用 | 人工确认后删除 |
| architecture-diagram.png / architecture-diagram.md | 疑似架构图 | 文档可能引用 | 人工确认后删除 |

## 4. 其他

| 文件 | 原因 | 风险 | 建议 |
|------|------|------|------|
| start_backend.bat / start_frontend.bat | 疑似启动脚本 | 可能有用 | 保留（待确认） |
| githubworkflows | 疑似 CI 配置草稿 | 可能有用 | 保留（待确认） |

---

> 说明：以上文件均「不删除」，仅列入候选，待人工确认后再决定是否清理。
