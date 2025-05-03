"""
    测试辞海第七版词典
"""
from mdict_utils import MDX, MDD
from mdict_utils import query

mdx_path = 'D:/通用资料/工具书/通用电子词典/1古汉语/辞海第七版/离线版/辞海第七版.mdx'
mdd_path = 'D:/通用资料/工具书/通用电子词典/1古汉语/辞海第七版/离线版/辞海第七版.mdd'

# 读取 mdx 文件
mdx = MDX(mdx_path, encoding='utf-8')

# 获取词典信息
print("词典信息：")
for key, value in mdx.header.items():
    print(f"{key.decode('utf-8')}: {value.decode('utf-8')}")

print(f"\n词条总数：{len(mdx)}")

# 获取所有词条
print("\n词条列表：")
for i, key in enumerate(mdx.keys()):
    print(f"{i} {key.decode('utf-8')}")
    if i > 10:
        break

# 读取 mdd 文件（资源文件）
mdd = MDD(mdd_path)

# 查询特定词条
content = query(mdx_path, '毛泽东')
print(content)
