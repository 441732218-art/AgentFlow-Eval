"""Add remaining screenshot specs to manual"""
fpath = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"
with open(fpath, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# 图3: Dashboard detail - insert after the second command_center reference
# Find second occurrence of command_center
first = text.find("![驾驶舱看板图](command_center.png)")
second = text.find("![驾驶舱看板图](command_center.png)", first + 1)
if second > 0:
    # Find end of that image section
    end_of_second = text.find("\n\n", second + 50)
    # Replace the duplicate image ref (line 348 area) with dashboard detail spec
    old_block = text[second:second+100]
    new_block = ('![驾驶舱详情](command_center.png)\n\n'
                 '【⚠️ 截图待嵌入 — 图3：驾驶舱详情】\n'
                 '├ 截图内容：驾驶舱中某一具体指标或模块的展开详情\n'
                 '├ 必须可见元素：具体数据、图表（如Token消耗折线图/状态分布饼图/Agent拓扑流程图的节点详情）\n'
                 '├ 最低分辨率：1920×1080\n'
                 '└ 文件名建议：dashboard_detail.png\n')
    text = text[:second] + new_block + text[second+len(old_block):]
    print("[OK] Added 图3: Dashboard detail")
else:
    print("[MISS] Could not find second dashboard image ref")

# 图5: Task create - find task_create.png
tc_pos = text.find("![创建任务](task_create.png)")
if tc_pos > 0:
    after_img = text.find("\n\n", tc_pos + 30)
    task_create_spec = ('\n\n'
                        '【⚠️ 截图待嵌入 — 图5：创建任务】\n'
                        '├ 截图内容：创建任务的表单/弹窗，已填写完整信息\n'
                        '├ 必须可见元素：表单字段（任务名称、描述、模型选择、Temperature、Max Tokens等）、配置预览面板、提交按钮\n'
                        '├ 最低分辨率：1920×1080\n'
                        '└ 文件名建议：task_create.png\n\n')
    text = text[:after_img] + task_create_spec + text[after_img:]
    print("[OK] Added 图5: Task create")
else:
    print("[MISS] task_create.png")

# 图10: Analytics - find analytics.png
an_pos = text.find("![分析中心](analytics.png)")
if an_pos > 0:
    after_an = text.find("\n\n", an_pos + 30)
    analytics_spec = ('\n\n'
                      '【⚠️ 截图待嵌入 — 图10：分析中心】\n'
                      '├ 截图内容：分析中心主页面，包含完整图表面板\n'
                      '├ 必须可见元素：Agent能力雷达图、模型对比柱状图、运维热力图、Cost双轴图、分数分布直方图、核心指标卡片（SUCCESS/AVG SCORE/TOKENS/AVG LATENCY）\n'
                      '├ 最低分辨率：1920×1080\n'
                      '└ 文件名建议：analytics_center.png\n\n')
    text = text[:after_an] + analytics_spec + text[after_an:]
    print("[OK] Added 图10: Analytics")
else:
    print("[MISS] analytics.png")

# 图11: Reports - find reports.png
rp_pos = text.find("![评测报告](reports.png)")
if rp_pos > 0:
    after_rp = text.find("\n\n", rp_pos + 30)
    reports_spec = ('\n\n'
                    '【⚠️ 截图待嵌入 — 图11：评测报告】\n'
                    '├ 截图内容：评测报告详情页\n'
                    '├ 必须可见元素：报告标题、综合评分、各维度指标分详情（准确率/质量/延迟/成本等）、用例明细列表\n'
                    '├ 最低分辨率：1920×1080\n'
                    '└ 文件名建议：eval_report.png\n\n')
    text = text[:after_rp] + reports_spec + text[after_rp:]
    print("[OK] Added 图11: Eval report")
else:
    print("[MISS] reports.png")

with open(fpath, "w", encoding="utf-8") as f:
    f.write(text)
print("\n[DONE] Remaining screenshot specs added")
