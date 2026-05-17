"""
将 hai7.json 转为仅含 person_birth_death 与 era_years 的 minify JSON，供应用集成。

可选合并 hai7_extension.csv：全部行均并入 era_years（含年号条目与无年号时代的帝王名条目，
结构同为 raw + label，应用侧一律按「纪年词条」处理）。person_birth_death 仍仅来自 hai7.json。

默认丢弃：source、stats、last_index。
不使用 gzip。

用法：
  python bddate_from_cihai7_compress.py --extension hai7_extension.csv
  python bddate_from_cihai7_compress.py
  python bddate_from_cihai7_compress.py --input hai7.json --output hai7.dist.json
  python bddate_from_cihai7_compress.py --no-extension
  python bddate_from_cihai7_compress.py --scalar-single-raw
  python bddate_from_cihai7_compress.py --short-keys --output hai7.compact.json
  python bddate_from_cihai7_compress.py --scalar-single-raw --short-keys --output hai7.compact.json
  python bddate_from_cihai7_compress.py --check
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

Bucket = Dict[str, Union[str, List[Dict[str, str]]]]


def _script_data_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _minify_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _get_raw_label(rec: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    raw = rec.get("raw") if "raw" in rec else rec.get("r")
    lab = rec.get("label") if "label" in rec else rec.get("l")
    if raw is not None:
        raw = str(raw)
    if lab is not None:
        lab = str(lab)
    return raw, lab if lab else None


def _normalize_record_canonical(rec: Dict[str, Any]) -> Dict[str, str]:
    raw, lab = _get_raw_label(rec)
    out: Dict[str, str] = {}
    if raw:
        out["raw"] = raw
    if lab:
        out["label"] = lab
    return out


def _record_to_dist(rec: Dict[str, Any], short_keys: bool) -> Dict[str, str]:
    raw, lab = _get_raw_label(rec)
    if not raw:
        return {}
    if short_keys:
        d: Dict[str, str] = {"r": raw}
        if lab:
            d["l"] = lab
        return d
    d2: Dict[str, str] = {"raw": raw}
    if lab:
        d2["label"] = lab
    return d2


def _compress_bucket(
    bucket: Dict[str, List[Dict[str, Any]]],
    scalar_single_raw: bool,
    short_keys: bool,
) -> Bucket:
    out: Bucket = {}
    for head, lst in bucket.items():
        if not lst:
            continue
        if scalar_single_raw and len(lst) == 1:
            one = lst[0]
            if isinstance(one, dict):
                raw, lab = _get_raw_label(one)
                if raw and not lab:
                    out[head] = raw
                    continue
        records = [_record_to_dist(x, short_keys) for x in lst]
        records = [r for r in records if r]
        if records:
            out[head] = records
    return out


def _expand_bucket_for_compare(bucket: Bucket) -> Dict[str, List[Dict[str, str]]]:
    """将分发格式还原为 canonical 列表（raw / label），用于与源数据对比。"""
    expanded: Dict[str, List[Dict[str, str]]] = {}
    for head, val in bucket.items():
        if isinstance(val, str):
            expanded[head] = [{"raw": val}]
            continue
        if isinstance(val, list):
            norm: List[Dict[str, str]] = []
            for rec in val:
                if isinstance(rec, dict):
                    n = _normalize_record_canonical(rec)
                    if n.get("raw"):
                        norm.append(n)
            if norm:
                expanded[head] = norm
    return expanded


def _canonical_bucket_from_source(
    bucket: Optional[Dict[str, List[Any]]],
) -> Dict[str, List[Dict[str, str]]]:
    if not bucket:
        return {}
    out: Dict[str, List[Dict[str, str]]] = {}
    for head, lst in bucket.items():
        norm = []
        for x in lst:
            if isinstance(x, dict):
                n = _normalize_record_canonical(x)
                if n.get("raw"):
                    norm.append(n)
        if norm:
            out[head] = norm
    return out


def _record_identity(rec: Dict[str, str]) -> Tuple[str, str]:
    """用于去重：同一 raw + 同说明视为重复。"""
    return (rec.get("raw") or "", rec.get("label") or "")


def parse_hai7_extension_csv(path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    解析扩展 CSV：三列「词头,说明,raw」。
    全部并入 era_years（年号与无年号时代帝王名均视为纪年类词条）。
    """
    era: Dict[str, List[Dict[str, str]]] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            head = row[0].strip()
            label = row[1].strip()
            raw = row[2].strip()
            if not head or not raw:
                continue
            rec: Dict[str, str] = {"raw": raw}
            if label:
                rec["label"] = label
            era.setdefault(head, []).append(rec)
    return era


def merge_extension_into_era(
    base_person: Optional[Dict[str, List[Any]]],
    base_era: Optional[Dict[str, List[Any]]],
    ext_era: Dict[str, List[Dict[str, str]]],
) -> Tuple[Dict[str, List[Any]], Dict[str, List[Any]]]:
    """person 仅cihai拷贝；era 浅拷贝词头列表后追加扩展，按 (raw, label) 去重。"""
    person: Dict[str, List[Any]] = {
        k: list(v) for k, v in (base_person or {}).items() if isinstance(v, list)
    }
    era: Dict[str, List[Any]] = {
        k: list(v) for k, v in (base_era or {}).items() if isinstance(v, list)
    }
    for head, new_items in ext_era.items():
        existing = era.setdefault(head, [])
        seen = {
            _record_identity(_normalize_record_canonical(x))
            for x in existing
            if isinstance(x, dict)
        }
        for item in new_items:
            n = _normalize_record_canonical(item)
            if not n.get("raw"):
                continue
            key = _record_identity(n)
            if key in seen:
                continue
            existing.append(dict(n))
            seen.add(key)
    return person, era


def build_dist_payload(
    data: Dict[str, Any],
    scalar_single_raw: bool,
    short_keys: bool,
) -> Dict[str, Bucket]:
    person = data.get("person_birth_death") or {}
    era = data.get("era_years") or {}
    if not isinstance(person, dict):
        person = {}
    if not isinstance(era, dict):
        era = {}
    return {
        "person_birth_death": _compress_bucket(person, scalar_single_raw, short_keys),
        "era_years": _compress_bucket(era, scalar_single_raw, short_keys),
    }


def verify_against_source(
    source: Dict[str, Any],
    dist_payload: Dict[str, Bucket],
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key in ("person_birth_death", "era_years"):
        src_b = _canonical_bucket_from_source(source.get(key))
        got_b = _expand_bucket_for_compare(dist_payload.get(key) or {})
        if set(src_b.keys()) != set(got_b.keys()):
            missing = set(src_b.keys()) - set(got_b.keys())
            extra = set(got_b.keys()) - set(src_b.keys())
            if missing:
                errors.append(f"{key}: 缺失词头 {len(missing)} 个（示例: {list(missing)[:3]}）")
            if extra:
                errors.append(f"{key}: 多余词头 {len(extra)} 个")
        for hw in src_b:
            if hw not in got_b:
                errors.append(f"{key}: 缺少词头 {hw!r}")
                continue
            if src_b[hw] != got_b[hw]:
                errors.append(f"{key}[{hw!r}]: 记录不一致")
    return len(errors) == 0, errors


def run(
    input_path: str,
    output_path: str,
    scalar_single_raw: bool,
    short_keys: bool,
    do_check: bool,
    extension_path: Optional[str],
) -> int:
    if not os.path.isfile(input_path):
        print(f"找不到输入文件：{input_path}", file=sys.stderr)
        return 1

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ext_era: Dict[str, List[Dict[str, str]]] = {}
    if extension_path:
        ext_era = parse_hai7_extension_csv(extension_path)
        n_ext = sum(len(v) for v in ext_era.values())
        print(f"已读扩展 CSV：{extension_path}（纪年类 {n_ext} 条，并入 era_years）")

    if extension_path:
        merged_person, merged_era = merge_extension_into_era(
            data.get("person_birth_death"),
            data.get("era_years"),
            ext_era,
        )
        payload_source: Dict[str, Any] = {
            "person_birth_death": merged_person,
            "era_years": merged_era,
        }
    else:
        payload_source = data

    payload = build_dist_payload(payload_source, scalar_single_raw, short_keys)
    text = _minify_dumps(payload)

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    in_size = os.path.getsize(input_path)
    out_size = len(text.encode("utf-8"))
    saved = in_size - out_size
    pct = (saved / in_size * 100) if in_size else 0.0
    print(f"已写入：{output_path}")
    print(f"输入文件大小：{in_size} 字节")
    print(f"输出文件大小：{out_size} 字节（相对输入节省 {saved} 字节，约 {pct:.1f}%）")

    if do_check:
        ok, errs = verify_against_source(payload_source, payload)
        if ok:
            hint = "（含扩展 CSV 合并结果）" if extension_path else ""
            print(f"校验：person_birth_death / era_years 与源数据一致（canonical 对比）{hint}")
        else:
            for e in errs:
                print(f"校验失败：{e}", file=sys.stderr)
            return 2

    return 0


def _parse_args() -> argparse.Namespace:
    data_dir = _script_data_dir()
    default_in = os.path.join(data_dir, "hai7.json")
    default_out = os.path.join(data_dir, "hai7.dist.json")
    p = argparse.ArgumentParser(description="由 hai7.json 生成分发用 minify JSON（两键，无 gzip）。")
    p.add_argument("--input", default=default_in, help=f"默认：{default_in}")
    p.add_argument("--output", default=default_out, help=f"默认：{default_out}")
    p.add_argument(
        "--scalar-single-raw",
        action="store_true",
        help="仅一条且仅有 raw 的词头改为字符串",
    )
    p.add_argument(
        "--short-keys",
        action="store_true",
        help="记录内使用 r / l 替代 raw / label",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="写盘后对比源数据中两桶是否与 canonical 形式一致",
    )
    p.add_argument(
        "--extension",
        default=None,
        metavar="PATH",
        help="扩展 CSV（hai7_extension.csv 格式）；省略时若存在脚本目录下 hai7_extension.csv 则自动合并",
    )
    p.add_argument(
        "--no-extension",
        action="store_true",
        help="不合并扩展 CSV（即使默认路径存在）",
    )
    return p.parse_args()


def _resolve_extension_path(
    args: argparse.Namespace, data_dir: str
) -> Tuple[Optional[str], int]:
    if args.no_extension:
        return None, 0
    if args.extension is not None:
        p = os.path.abspath(args.extension)
        if not os.path.isfile(p):
            print(f"找不到扩展文件：{p}", file=sys.stderr)
            return None, 1
        return p, 0
    auto = os.path.join(data_dir, "hai7_extension.csv")
    return (auto if os.path.isfile(auto) else None), 0


def main() -> int:
    args = _parse_args()
    data_dir = _script_data_dir()
    ext, err = _resolve_extension_path(args, data_dir)
    if err:
        return err
    return run(
        args.input,
        args.output,
        args.scalar_single_raw,
        args.short_keys,
        args.check,
        ext,
    )


if __name__ == "__main__":
    sys.exit(main())
