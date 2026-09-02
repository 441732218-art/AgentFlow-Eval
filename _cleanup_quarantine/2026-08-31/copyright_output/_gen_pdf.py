import os
import math
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. 文件路径配置
INPUT_TXT = r"D:\AgentFlow-Eval\copyright_output\source_code_60pages_CLEANED.txt"
OUTPUT_PDF = r"D:\AgentFlow-Eval\copyright_output\AgentFlow-Eval_源程序鉴别材料_60页.pdf"

# 2. 软著申请元信息
SOFTWARE_NAME = "AgentFlow-Eval源程序鉴别材料 V1.0"
COPYRIGHT_HOLDER = "著作权人：李凯昕"

# 3. 注册 Windows 系统自带中文字体 (优先使用微软雅黑，次选宋体)
FONT_NAME = "SystemChineseFont"
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"  # 微软雅黑

if not os.path.exists(FONT_PATH):
    FONT_PATH = r"C:\Windows\Fonts\simsun.ttc"  # 宋体

try:
    # 注册中文字体 (TTC 索引 0)
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH, subfontIndex=0))
    print(f"✅ 成功加载系统中文字体: {FONT_PATH}")
except Exception as e:
    print(f"⚠️ 加载系统字体失败: {e}，将尝试常规方式加载。")

class CopyrightCanvas(canvas.Canvas):
    """自定义 Canvas：自动计算总页数并绘制双线页眉与页脚"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont(FONT_NAME, 9)
        
        # A4 尺寸 595.27 x 841.89 点
        page_width, page_height = A4
        margin_left = 40
        margin_right = page_width - 40
        header_y = page_height - 40
        footer_y = 40

        # --- 页眉绘制 ---
        self.setLineWidth(0.5)
        self.line(margin_left, header_y - 5, margin_right, header_y - 5)
        self.drawString(margin_left, header_y, SOFTWARE_NAME)
        self.drawRightString(margin_right, header_y, f"第 {self._pageNumber} 页 共 {page_count} 页")

        # --- 页脚绘制 ---
        self.line(margin_left, footer_y + 15, margin_right, footer_y + 15)
        self.drawString(margin_left, footer_y, COPYRIGHT_HOLDER)
        
        self.restoreState()


def generate_pdf():
    if not os.path.exists(INPUT_TXT):
        print(f"❌ 找不到输入文件: {INPUT_TXT}")
        return

    with open(INPUT_TXT, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f.readlines()]

    print(f"📄 读取源码行数: {len(lines)} 行")

    # 创建 PDF 画布
    c = CopyrightCanvas(OUTPUT_PDF, pagesize=A4)
    page_width, page_height = A4
    
    # 排版参数（保证每页 55-60 行代码）
    margin_left = 40
    start_y = page_height - 60
    line_height = 11.8  # 行高
    lines_per_page = 59 # 每页固定 56 行
    font_size = 8.5     # 代码字号

    total_lines = len(lines)
    total_pages = math.ceil(total_lines / lines_per_page)

    for page_idx in range(total_pages):
        c.setFont(FONT_NAME, font_size)
        y = start_y
        
        chunk = lines[page_idx * lines_per_page : (page_idx + 1) * lines_per_page]
        for line in chunk:
            # 替换 Tab 为空格防止缩进错位
            line_str = line.replace("\t", "    ")
            c.drawString(margin_left, y, line_str)
            y -= line_height
            
        c.showPage()

    c.save()
    print(f"🎉 PDF 生成成功！路径: {OUTPUT_PDF}")
    print(f"📊 最终 PDF 页数: {total_pages} 页")

if __name__ == "__main__":
    generate_pdf()
