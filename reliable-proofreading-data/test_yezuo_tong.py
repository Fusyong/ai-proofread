# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.special_checker.variant_forms_from_mdict import (
    VariantFormsExtractor,
    SOURCE_GUIFAN_BUKUIFAN,
    SOURCE_TUIJIAN_YEZUO,
    SOURCE_BUTUIJIAN_TONG,
    SINGLE_CHAR_FANTI,
    SINGLE_CHAR_GUIFAN,
    SINGLE_CHAR_OTHER,
)

ext = VariantFormsExtractor()
# 枝丫（枝桠）→ 仅进 variant_to_standard（异形词_括号）
c0 = '''<entry id="66590"><hwg><hw>枝丫（枝桠）</hw><pinyin>zhīyā</pinyin></hwg><def>枝杈。</def></entry>'''
p0 = ext._extract_variant_forms_xianhan7(c0)
assert any(t[:2] == ("枝丫", "枝桠") and t[2] == SOURCE_GUIFAN_BUKUIFAN for t in p0), p0
print("枝丫（枝桠）->", p0)

# 辞藻：也作词藻。（与现汉7实际返回一致）→ 异形词
c1 = '''<link rel="stylesheet" type="text/css" href="XDHY7.css" />
<entry id="08566"><hwg><hw>辞藻</hw><pinyin>cízǎo</pinyin></hwg><def><ps>名</ps>诗文中工巧的词语，常指运用的典故和古人诗文中现成的词语：<ex>～华丽｜堆砌～。</ex>也作词藻。</def></entry>'''
p1 = ext._extract_variant_forms_xianhan7(c1)
print("辞藻 也作 ->", p1)
assert any(t[:2] == ("辞藻", "词藻") and t[2] == SOURCE_TUIJIAN_YEZUO for t in p1), p1

# 同一条目中多个「也作某某。」→ 每个都提取
c1b = '''<entry id="1"><hwg><hw>某词</hw><pinyin>mǒucí</pinyin></hwg><def>释义一。也作写法A。</def><def>释义二。也作写法B。</def></entry>'''
p1b = ext._extract_variant_forms_xianhan7(c1b)
assert any(t[:2] == ("某词", "写法A") and t[2] == SOURCE_TUIJIAN_YEZUO for t in p1b), p1b
assert any(t[:2] == ("某词", "写法B") and t[2] == SOURCE_TUIJIAN_YEZUO for t in p1b), p1b
print("某词 两处也作 ->", [(t[0], t[1], t[2]) for t in p1b])

# 词藻：同"辞藻"。→ 不推荐词形_同（ASCII 引号，测试用）
c2 = '''<link rel="stylesheet" type="text/css" href="XDHY7.css" />
<entry id="08522"><hwg><hw>词藻</hw><pinyin>cízǎo</pinyin></hwg><def>同"<a href="entry://辞藻">辞藻</a>"。</def></entry>'''
p2 = ext._extract_variant_forms_xianhan7(c2)
print("词藻 同 ->", p2)
assert any(t[:2] == ("辞藻", "词藻") and t[2] == SOURCE_BUTUIJIAN_TONG for t in p2), p2

# 忽律：现汉7 实际格式为弯引号 ""（U+201C/U+201D）
c2b = '''<entry id="21525"><hwg><hw>忽律</hw><pinyin>hūlǜ</pinyin></hwg><def>同\u201c<a href="entry://㺀𤝽">㺀𤝽</a>\u201d。</def></entry>'''
p2b = ext._extract_variant_forms_xianhan7(c2b)
assert any(t[:2] == ("㺀𤝽", "忽律") and t[2] == SOURCE_BUTUIJIAN_TONG for t in p2b), p2b
print("忽律 同（弯引号）->", [(t[0], t[1], t[2]) for t in p2b])

# 吗（嗎）同"嘛③"：词头括注繁体用 headword_key 得「吗」；引号内带圈数字未加标签需剥离得「嘛」
c2c = '''<entry id="34364"><hwg><hw>吗（嗎）</hw><pinyin>·ma</pinyin></hwg><def><num>❸</num> 同\u201c<a href="entry://嘛">嘛③</a>\u201d。</def></entry>'''
p2c = ext._extract_variant_forms_xianhan7(c2c)
assert any(t[:2] == ("嘛", "吗") and t[2] == SOURCE_BUTUIJIAN_TONG for t in p2c), "应得 推荐=嘛 不推荐=吗: " + str(p2c)
print("吗（嗎）同嘛③（键=吗、值=嘛）->", [(t[0], t[1], t[2]) for t in p2c])

# 乌拉：一条查询含两个词条，两组词头-异形词
c3 = '''<link rel="stylesheet" href="XDHY7.css" />
<entry id="1"><hwg><hw>乌拉</hw>（乌喇）<pinyin>wūlā</pinyin></hwg><def>拟声词。</def></entry>
<entry id="2"><hwg><hw>乌拉</hw>（靰鞡）<pinyin>wūla</pinyin></hwg><def>东北地区冬天穿的鞋。</def></entry>'''
p3 = ext._extract_variant_forms_xianhan7(c3)
assert len(p3) >= 2, "乌拉应至少有两组词头-异形词"
assert any(t[:2] == ("乌拉", "乌喇") for t in p3), p3
assert any(t[:2] == ("乌拉", "靰鞡") for t in p3), p3
print("乌拉（两词条）->", p3)

# 阀阅：释义中「"阀"也作"伐"」为单字异体说明，不应匹配为词条异形
c4 = '''<entry id="13924"><hwg><hw>阀阅</hw><pinyin>fáyuè</pinyin></hwg><def>〈书〉<ps>名</ps></def><def><num>❶</num> 功勋（"阀"也作"伐"，指功劳，"阅"指经历）。</def><def><num>❷</num> 指有功勋的世家。</def></entry>'''
p4 = ext._extract_variant_forms_xianhan7(c4)
assert not any(t[0] == "阀阅" and t[2] == SOURCE_TUIJIAN_YEZUO for t in p4), "阀阅不应被也作匹配为词条异形: " + str(p4)
print("阀阅（排除也作）->", p4)

# 保姆：括号内有 <sup>①</sup> 等注释，应保存原始匹配文本备查
c5 = '''<entry id="01733"><hwg><hw>保姆（<sup>①</sup>保母、<sup>①</sup>褓姆）</hw><pinyin>bǎomǔ</pinyin></hwg><def><ps>名</ps></def><def><num>❶</num> 受雇为人照料儿童、老人、病人或为人从事家务劳动的妇女。</def><def><num>❷</num> 保育员的旧称。</def></entry>'''
p5 = ext._extract_variant_forms_xianhan7(c5)
assert any(t[:2] == ("保姆", "保母") and t[2] == SOURCE_GUIFAN_BUKUIFAN for t in p5), p5
assert any(t[:2] == ("保姆", "褓姆") for t in p5), p5
raw_expected = "（<sup>①</sup>保母、<sup>①</sup>褓姆）"
assert any(len(t) >= 4 and t[3] == raw_expected for t in p5), "应有原始匹配文本备查: " + str(p5)
print("保姆（带注释原始文本）->", [(t[0], t[1], t[2], (t[3][:20] + "…") if t[3] and len(t[3]) > 20 else t[3]) for t in p5])

# 单字词条：辉（輝、<sup>*</sup>煇）→ 輝=繁体字，煇=规范异体字
c6 = '''<entry id="1"><hwg><hw>辉</hw>（輝、<sup>*</sup>煇）<pinyin>huī</pinyin></hwg><def>光辉。</def></entry>'''
p6 = ext._extract_variant_forms_xianhan7(c6)
assert any(t[:3] == ("辉", "輝", SINGLE_CHAR_FANTI) for t in p6), p6
assert any(t[:3] == ("辉", "煇", SINGLE_CHAR_GUIFAN) for t in p6), p6
assert any(len(t) >= 4 and t[3] and "⁑" not in (t[3] or "") for t in p6)
print("单字 辉（輝、*煇）->", p6)

# 单字词条：为（爲、<sup>⁑</sup>為）→ 爲=繁体字，為=其他异体字
c7 = '''<entry id="2"><hwg><hw>为</hw>（爲、<sup>⁑</sup>為）<pinyin>wéi</pinyin></hwg><def>做。</def></entry>'''
p7 = ext._extract_variant_forms_xianhan7(c7)
assert any(t[:3] == ("为", "爲", SINGLE_CHAR_FANTI) for t in p7), p7
assert any(t[:3] == ("为", "為", SINGLE_CHAR_OTHER) for t in p7), p7
print("单字 为（爲、⁑為）->", p7)

# 单字词条：彩（<sup>②*</sup>綵）义项号→ 綵=规范异体字；咤（<sup>△*</sup>吒）另出字头→ 吒=规范异体字
c8 = '''<entry id="3"><hwg><hw>彩</hw>（<sup>②*</sup>綵）<pinyin>cǎi</pinyin></hwg><def>颜色。</def></entry>'''
p8 = ext._extract_variant_forms_xianhan7(c8)
assert any(t[:3] == ("彩", "綵", SINGLE_CHAR_GUIFAN) for t in p8), p8
c9 = '''<entry id="4"><hwg><hw>咤</hw>（<sup>△*</sup>吒）<pinyin>zhà</pinyin></hwg><def>叱咤。</def></entry>'''
p9 = ext._extract_variant_forms_xianhan7(c9)
assert any(t[:3] == ("咤", "吒", SINGLE_CHAR_GUIFAN) for t in p9), p9
# 现汉7 实际用 ⁎（U+204E）表示规范异体
c10 = '''<entry id="5"><hwg><hw>举</hw>（<sup>⁎</sup>擧）<pinyin>jǔ</pinyin></hwg><def>举起。</def></entry>'''
p10 = ext._extract_variant_forms_xianhan7(c10)
assert any(t[:3] == ("举", "擧", SINGLE_CHAR_GUIFAN) for t in p10), "⁎ 应为规范异体: " + str(p10)
print("单字 彩（②*綵）、咤（△*吒）、举（⁎擧）-> OK")

# 用法提示：<column><note>注意</note>...</column>，按 entry 切分后提取
c_usage = '''<entry id="10880"><hwg><hw>得</hw><pinyin>·de</pinyin></hwg><def><num>❶</num> 用在动词后面。</def><column><note>注意</note>否定式是"不得"：哭不得，笑不得。</column><def><num>❷</num> 用在动词和补语中间。</def><column><note>注意</note>否定式是把"得"换成"不"：拿不动｜办不到。</column></entry>'''
notes = ext._extract_usage_notes_from_content(c_usage)
assert "得" in notes, notes
assert len(notes["得"]) >= 2, notes["得"]
assert any("不得" in n for n in notes["得"]), notes["得"]
print("用法提示 得 ->", len(notes["得"]), "条")

print("OK")
