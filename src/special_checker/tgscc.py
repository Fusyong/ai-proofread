"""
通用规范汉字表检查
"""
import os
import re
import json
from typing import List
from src.special_checker import CheckResult

class TGSCCChecker:
    """Chechker to the List of Commonly-Used Standardized Chinese Characters
    """
    def __init__(self):
        self.tgscc_list_path = (
            "D:/语文出版社/语文社工具书/通用规范汉字表/通用规范汉字表（维基百科）.csv"
        )
        self.tgscc_to_traditional_kanji_list_path = (
            "D:/语文出版社/语文社工具书/通用规范汉字表/通用规范汉字表繁简对照表-增强（2025-03-04）.csv"
        )
        self.tgscc_to_traditional_kanji_list_notes_path = (
            "D:/语文出版社/语文社工具书/通用规范汉字表/通用规范汉字表规范字与繁体字、异体字对照表注释.md"
        )
        self.tgscc_data_path = "src/resource/tgscc_data.json"

        # 预编译正则表达式
        self.pinzi_pattern = re.compile(r'〖([^〗]+)〗(\d*)')
        self.variant_pattern = re.compile(r'(\D)(\d*)')
        self.ignore_pattern = re.compile(r"""[0-9a-zA-Z，。！？；：“”‘’（）《》,.!?;:"'~\s\(\)\[\]]+""")

        # 初始化数据
        self.tgscc_list = []
        self.simplified_to_traditional = {}  # 简繁映射
        self.simplified_to_variants = {}    # 简异映射
        self.traditional_to_simplified = {} # 繁简映射
        self.variant_to_simplified = {}     # 异简映射
        self.notes = {}  # 字 -> 注释正文（合并原 notes 编号与 notes_content）

        self._load_data()

    def _load_data(self):
        if not os.path.exists(self.tgscc_data_path):
            self._load_from_files()
        else:
            self._load_from_json()

    def _load_from_files(self):
        last_simplified = None
        notes_content = []  # 注释表正文（按编号顺序）
        notes_by_num = {}   # 字 -> 注释编号（处理过程中暂存）

        # 读取规范字表
        with open(self.tgscc_list_path, 'r', encoding='utf-8') as f:
            next(f)
            for line in f:
                parts = line.strip().split(',')
                self.tgscc_list.append(parts[1])

        # 读取注释表
        with open(self.tgscc_to_traditional_kanji_list_notes_path, 'r', encoding='utf-8') as f:
            for line in f:
                notes_content.append(line)

        # 读取并解析繁简异对照表
        with open(self.tgscc_to_traditional_kanji_list_path, 'r', encoding='utf-8') as f:
            next(f)
            for line in f:
                last_simplified = self._process_line(line, last_simplified, notes_by_num) or last_simplified

        # 合并：字 -> 注释正文
        for char, num in notes_by_num.items():
            if num and 1 <= int(num) <= len(notes_content):
                self.notes[char] = notes_content[int(num) - 1].strip()

        self._save_to_json()

    def _process_line(self, line, last_simplified, notes_by_num):
        parts = line.strip().split(',')
        # 本行简体为空时使用上一行的简体，避免记作 null
        simplified = (parts[2].strip() or last_simplified) if len(parts) > 2 else last_simplified
        if not simplified:
            return last_simplified
        traditional = parts[3].strip()

        if not traditional or traditional == '~':
            traditional = simplified
        else:
            traditional = traditional.strip('()')

        note_match = re.search(r'(\d+)$', str(traditional))
        note = note_match.group(1) if note_match else None
        traditional = str(traditional).rstrip('0123456789')

        self.simplified_to_traditional.setdefault(simplified, []).append(traditional)
        self.traditional_to_simplified.setdefault(traditional, []).append(simplified)
        if note:
            notes_by_num[traditional] = note

        variants = parts[4].strip()
        if variants:
            self._process_variants(variants, simplified, notes_by_num)
        return simplified

    def _process_variants(self, variants, simplified, notes_by_num):
        variants = variants.strip('[]')
        pinzi_matches = self.pinzi_pattern.findall(variants)
        for pinzi, note in pinzi_matches:
            self.simplified_to_variants.setdefault(simplified, []).append(pinzi)
            self.variant_to_simplified.setdefault(pinzi, []).append(simplified)
            if note:
                notes_by_num[pinzi] = note

        variants = re.sub(self.pinzi_pattern, '', variants)
        matches = self.variant_pattern.findall(variants)
        for variant, note in matches:
            if variant:
                self.simplified_to_variants.setdefault(simplified, []).append(variant)
                self.variant_to_simplified.setdefault(variant, []).append(simplified)
                if note:
                    notes_by_num[variant] = note

    def _save_to_json(self):
        with open(self.tgscc_data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'simplified_to_traditional': self.simplified_to_traditional,
                'traditional_to_simplified': self.traditional_to_simplified,
                'simplified_to_variants': self.simplified_to_variants,
                'variant_to_simplified': self.variant_to_simplified,
                'tgscc_list': self.tgscc_list,
                'notes': self.notes,
            }, f, ensure_ascii=False)

    def _load_from_json(self):
        with open(self.tgscc_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.simplified_to_traditional = data['simplified_to_traditional']
            self.traditional_to_simplified = data['traditional_to_simplified']
            self.simplified_to_variants = data['simplified_to_variants']
            self.variant_to_simplified = data['variant_to_simplified']
            self.tgscc_list = data['tgscc_list']
            # notes: 字 -> 注释正文；兼容旧格式（notes 为编号 + notes_content 表）时合并
            if 'notes_content' in data:
                notes_content = data['notes_content']
                self.notes = {
                    char: (notes_content[int(num) - 1].strip()
                    if num and 1 <= int(num) <= len(notes_content)
                    else ''
                )
                for char, num in data['notes'].items()
                }
            else:
                self.notes = data['notes']

    def check_text(self, text: str, ignore_list: List[str] | str = "") -> List[CheckResult]:
        """检查文本中的汉字是否符合通用规范汉字表的要求

        Args:
            text: 要检查的文本
            ignore_list: 要忽略的列表，可以是列表或字符串
        Returns:
            List[CheckResult]: 检查结果列表，包含发现的非规范字及其建议
        """
        results = []
        for i, char in enumerate(text):
            if self.ignore_pattern.match(char) or char in ignore_list:
                continue

            is_in_tgscc_appendix = False

            if char in self.traditional_to_simplified and self.traditional_to_simplified[char] != [char]:
                is_in_tgscc_appendix = True
                suggestion = ''.join(s for s in self.traditional_to_simplified[char] if s)
                note_text = self.notes.get(char, '')
                results.append(CheckResult(
                    error_type='traditional_character',
                    location=(i, i + 1),
                    original_text=char,
                    suggestion=f"{suggestion}{f'({note_text})' if note_text else ''}",
                    confidence=1
                ))

            if char in self.variant_to_simplified and self.variant_to_simplified[char] != [char]:
                is_in_tgscc_appendix = True
                suggestion = ''.join(s for s in self.variant_to_simplified[char] if s)
                note_text = self.notes.get(char, '')
                results.append(CheckResult(
                    error_type='variant_character',
                    location=(i, i + 1),
                    original_text=char,
                    suggestion=f"{suggestion}{f'({note_text})' if note_text else ''}",
                    confidence=1
                ))

            if not is_in_tgscc_appendix and char not in self.tgscc_list:
                results.append(CheckResult(
                    error_type='not_general_standard_kanji',
                    location=(i, i + 1),
                    original_text=char,
                    suggestion="不在通用规范汉字表及其附录中",
                    confidence=1
                ))

        return results

def check_to_tgscc(
        text: str,
        ignore_list: List[str] | str = ""
        ) -> List[CheckResult]:
    """通用规范汉字(tgscc)表检查

    Args:
        text: 要检查的文本
        ignore_list: 要忽略的列表，可以是列表或字符串
    Returns:
        List[CheckResult]: 检查结果列表，包含发现的非规范字及其建议
    """
    checker = TGSCCChecker()
    return checker.check_text(text, ignore_list)

