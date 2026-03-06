"""专项检查用例"""

from src.special_checker import check_to_tgscc

# # 测试通用规范汉字表检查
# FILE = "E:\\语文出版社\\2025\\走出课本学语文\\汉魏六朝诗歌（下册）\\11.20汉魏六朝诗歌（下册）.proofread.json.md"
# with open(FILE,"r", encoding="utf-8") as f:
#     text = f.read()
#     results = check_to_tgscc(text)
#     with open("special_check_result.csv", "w", encoding="utf-16") as out_f:
#         for result in results:
#             out_f.write(f"{result.original_text},{result.error_type},{result.suggestion}\n")

results = check_to_tgscc("""
鼕
囯
鍾
钟
鈡
锺
鐘
兲
乃,,[廼迺2]
干,~,
,(乾3),[乹亁]
,(幹),[榦]
亏,(虧),
才,~,
,(纔),
与,(與),
万,~,
,(萬),
千,~,
,(韆),
亿,(億),
个,(個),[箇]
么,(麽4),

""")
for result in results:
    print(f"类型: {result.error_type}")
    print(f"位置: {result.location}")
    print(f"原文: {result.original_text}")
    print(f"提示: {result.suggestion}")
    # print(f"置信度: {result.confidence}")
    print("---")
