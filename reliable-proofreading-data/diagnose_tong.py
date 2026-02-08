# -*- coding: utf-8 -*-
"""诊断「不推荐词形_同」统计为 0 的原因：检查「同」条是否被遍历、正文是否被正则匹配。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

try:
    from src.special_checker.variant_forms_from_mdict import VariantFormsExtractor, SOURCE_BUTUIJIAN_TONG
except ImportError:
    from variant_forms_from_mdict import VariantFormsExtractor, SOURCE_BUTUIJIAN_TONG

# 正则与测试用词（现汉7 中典型「同」条；与 variant_forms_from_mdict 一致，含弯引号 ""）
TONG_PATTERN = re.compile(r'同[""\u201c\u201d「](?:<a\s[^>]*>)?([^<"」\u201c\u201d]+)(?:</a>)?["」\u201c\u201d]。')
TEST_ENTRIES = ["词藻", "忽律"]  # 可增补其他已知「同」条

def main():
    ext = VariantFormsExtractor()
    if not ext.mdict_manager:
        print("未配置 MdictManager，无法诊断。")
        return
    mgr = ext.mdict_manager
    dict_name = "现汉7.mdx"
    entries = mgr.entries(dict_name, limit=None)
    entries_set = set(entries)
    print(f"词典词条总数: {len(entries)}")
    for w in TEST_ENTRIES:
        in_list = w in entries_set
        print(f"\n「{w}」: 是否在词条列表中 = {in_list}")
        if not in_list:
            print(f"  → 若「同」条不做成独立词头，则不会被遍历，不推荐词形_同 会为 0。")
            continue
        content = mgr.query(dict_name, w)
        if not content:
            print(f"  → query 返回空，无法提取。")
            continue
        has_tong = '同"' in content or '同「' in content or '同"' in content or '\u201c' in content
        matches = list(TONG_PATTERN.finditer(content))
        triples = ext.extract_from_content(content, dict_name)
        tong_triples = [t for t in triples if t[2] == SOURCE_BUTUIJIAN_TONG]
        print(f"  正文含「同\"」或「同「」: {has_tong}")
        print(f"  正则 同\"X\"。 匹配次数: {len(matches)}")
        print(f"  提取结果中 不推荐词形_同 条数: {len(tong_triples)}")
        if matches and not tong_triples:
            print(f"  → 正则能匹配但未进入结果，可能被 headword/去重等过滤。")
        elif not matches and has_tong:
            print(f"  → 正文有「同」但正则未匹配，可能是格式差异（如无句号、引号不同）。")
    print("\n说明: stats 里「不推荐词形_同」统计的是「匹配到的」条数，不是合并后的表内条数。为 0 表示全词典遍历时没有一条被识别为 同\"X\"。")

if __name__ == "__main__":
    main()
