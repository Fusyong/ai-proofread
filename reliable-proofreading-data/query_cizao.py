# -*- coding: utf-8 -*-
"""查询现汉7「辞藻」「词藻」条目以确认也作/同 格式。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.special_checker.mdict import MdictManager
m = MdictManager()
for w in ["辞藻", "词藻"]:
    c = m.query("现汉7.mdx", w)
    print("===", w, "===")
    print(c)
    print()
