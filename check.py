"""专项检查用例"""

from src.special_checker import check_to_general_standard_kanji_list

# 测试通用规范汉字表检查
results = check_to_general_standard_kanji_list("""
鼕
""")
for result in results:
    print(f"类型: {result.error_type}")
    print(f"位置: {result.location}")
    print(f"原文: {result.original_text}")
    print(f"提示: {result.suggestion}")
    # print(f"置信度: {result.confidence}")
    print("---")
