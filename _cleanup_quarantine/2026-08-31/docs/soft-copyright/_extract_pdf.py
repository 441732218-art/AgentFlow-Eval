import pdfplumber

with pdfplumber.open('727软著源代码.pdf') as pdf:
    print(f"Pages: {len(pdf.pages)}")
    all_lines = []
    for i, page in enumerate(pdf.pages):
        txt = page.extract_text() or ''
        all_lines.append(f"=== PAGE {i+1} ===")
        all_lines.append(txt)

    out = '\n'.join(all_lines)
    with open('_pdf_extracted.txt', 'w', encoding='utf-8') as f:
        f.write(out)
    print(f"Extracted {len(out)} chars, {len(out.splitlines())} lines")


