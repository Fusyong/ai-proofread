"""
将pdf文件转换为markdown文件

! pip install pymupdf4llm

会丢失加框文字
"""
import pymupdf4llm
md_text = pymupdf4llm.to_markdown("1.pdf")

with open("1.md", "w", encoding="utf-8") as md_file:
    md_file.write(md_text)
