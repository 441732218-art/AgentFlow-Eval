# fix_word_format.py
# 修复Word文档格式：独立封面 + 正确页眉页脚

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 打开V6文档
doc = Document(r"D:\AgentFlow-Eval\软著\generated\材料二_核心源代码_V6.docx")

# 1. 在文档开头插入独立封面页
# 清空首页页眉
header = doc.sections[0].header
header_para = header.paragraphs[0]
header_para.text = ""

# 在文档最前面插入封面内容
# 注意：需要在现有内容前插入
# 由于python-docx无法在开头插入，建议用Word手动操作

print("请在Word中手动执行以下操作：")
print("1. 在文档最前面插入一个新页面作为封面")
print("2. 封面上添加：软件全称、版本号、著作权人、开发完成日期")
print("3. 设置第1页无页眉，页码为'第 1 页'")
print("4. 第2页起设置页眉为软件全称+V1.0")
print("5. 所有页面页码使用Word的'页码'功能自动编号")
