# -*- coding: utf-8 -*-
"""临时脚本：查询并打印现汉7中「枝丫」词条的原始数据。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from src.special_checker.mdict import MdictManager

def main():
    m = MdictManager()
    content = m.query("现汉7.mdx", "枝丫")
    if content is None:
        print("未查到词条「枝丫」（可能词典未配置或词条不存在）")
    else:
        print("=== 现汉7 词条「枝丫」 原始数据 ===")
        print(content)
        print("=== 以上为原始数据 ===")

if __name__ == "__main__":
    main()
