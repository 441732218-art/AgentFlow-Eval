软著源程序鉴别材料 — 生成说明
================================
软件名称：AgentFlow-Eval Agent自动化评测工作台
版本号：V1.0
申请人：李凯昕
开发方式：独立开发

有效源代码总行数 T（已剔除空行、纯注释行）= 10831
文件数 = 106
生成模式 = HEAD_TAIL
分页 = 每页 50 行有效代码
head_pages=30, tail_pages=30

筛选规则：
  - 优先：backend/app/core|api|models → frontend/src 核心 → utils/入口
  - 排除：node_modules、__pycache__、.git、dist、build、tests、*.test.*、
          alembic/versions、配置/静态资源/依赖清单等
  - 已剔除空行与纯注释行（# // /* */ 独占行）

输出文件：
  源程序鉴别材料_前30页.txt
  源程序鉴别材料_后30页.txt
  源程序鉴别材料_前30页+后30页_合并.txt
  源程序鉴别材料_前30页+后30页.html   ← 浏览器打开 Ctrl+P 另存 PDF（A4，边距 2.5cm）
  源程序_连续全文.txt
  00-源程序文件清单.txt
  预览_源程序_网页版.html

自查：
  [ ] 页眉软件名与申请表完全一致
  [ ] 版本号 V1.0 一致
  [ ] 每页（末页除外）正文 50 行
  [ ] 无 node_modules / 测试 / 密钥
  [ ] HTML 打印预览分页正常

重新生成：
  python scripts/export_soft_copyright.py
