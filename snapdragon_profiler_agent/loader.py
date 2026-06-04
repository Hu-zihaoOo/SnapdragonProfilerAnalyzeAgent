from __future__ import annotations

import csv
import glob
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REQUIRED_COLUMNS = {
    "Process",
    "Category",
    "Metric",
    "Timestamp",
    "TimestampRaw",
    "Value",
}


class CsvLoadError(ValueError):
    """Raised when a Snapdragon Profiler CSV cannot be loaded."""


@dataclass(frozen=True)
class ProfileRow:
    process: str
    category: str
    metric: str
    timestamp: int
    timestamp_raw: int
    value: float


@dataclass(frozen=True)
class CsvLoadResult:
    rows: list[ProfileRow]
    source_files: tuple[str, ...]


def _parse_int(text: str, *, row_number: int, column: str) -> int:
    try:
        return int(float(text))
    except ValueError as exc:
        raise CsvLoadError(f"第 {row_number} 行 `{column}` 不是有效数字: {text!r}") from exc


def _parse_float(text: str, *, row_number: int, column: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise CsvLoadError(f"第 {row_number} 行 `{column}` 不是有效数字: {text!r}") from exc


def load_csv(path: str | Path) -> list[ProfileRow]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise CsvLoadError(f"CSV 文件不存在: {csv_path}")
    if not csv_path.is_file():
        raise CsvLoadError(f"路径不是文件: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CsvLoadError("CSV 为空或缺少表头")

        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise CsvLoadError(f"CSV 缺少必要列: {missing_text}")

        rows: list[ProfileRow] = []
        for index, raw in enumerate(reader, start=2):
            rows.append(
                ProfileRow(
                    process=(raw.get("Process") or "").strip(),
                    category=(raw.get("Category") or "").strip(),
                    metric=(raw.get("Metric") or "").strip(),
                    timestamp=_parse_int(raw.get("Timestamp") or "", row_number=index, column="Timestamp"),
                    timestamp_raw=_parse_int(
                        raw.get("TimestampRaw") or "",
                        row_number=index,
                        column="TimestampRaw",
                    ),
                    value=_parse_float(raw.get("Value") or "", row_number=index, column="Value"),
                )
            )

    if not rows:
        raise CsvLoadError("CSV 没有数据行")
    return rows


def resolve_csv_inputs(inputs: Sequence[str | Path]) -> list[Path]:
    if not inputs:
        raise CsvLoadError("未提供 CSV 输入")

    resolved: list[Path] = []
    for raw_input in inputs:
        text = str(raw_input)
        path = Path(text)

        if path.exists():
            if path.is_dir():
                csv_files = sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".csv")
                if not csv_files:
                    raise CsvLoadError(f"目录中没有 CSV 文件: {path}")
                resolved.extend(csv_files)
            elif path.is_file():
                resolved.append(path)
            else:
                raise CsvLoadError(f"路径不是文件或目录: {path}")
            continue

        if glob.has_magic(text):
            matches = sorted(
                Path(match)
                for match in glob.glob(text, recursive=True)
                if Path(match).is_file() and Path(match).suffix.lower() == ".csv"
            )
            if not matches:
                raise CsvLoadError(f"glob 没有匹配到 CSV 文件: {text}")
            resolved.extend(matches)
            continue

        raise CsvLoadError(f"CSV 文件不存在: {path}")

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in resolved:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)

    if not deduped:
        raise CsvLoadError("没有可读取的 CSV 文件")
    return deduped


def load_csv_files(inputs: Sequence[str | Path]) -> CsvLoadResult:
    source_paths = resolve_csv_inputs(inputs)
    rows: list[ProfileRow] = []

    for path in source_paths:
        try:
            rows.extend(load_csv(path))
        except CsvLoadError as exc:
            raise CsvLoadError(f"读取 CSV 失败 ({path}): {exc}") from exc

    if not rows:
        raise CsvLoadError("CSV 输入没有数据行")

    return CsvLoadResult(
        rows=rows,
        source_files=tuple(str(path) for path in source_paths),
    )
