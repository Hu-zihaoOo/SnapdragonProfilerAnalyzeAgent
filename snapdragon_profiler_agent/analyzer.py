from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from .loader import ProfileRow


INSTANCE_SUFFIX_RE = re.compile(r"\[\d+\]$")

METRIC_ALIASES = {
    "ALU/Fragment": "ALU / Fragment",
    "ALU/Vertex": "ALU / Vertex",
    "Textures/Fragment": "Textures / Fragment",
    "Textures/Vertex": "Textures / Vertex",
    "Fragment ALU Instructions (Full)": "Fragment ALU Instructions / Sec (Full)",
    "Fragment ALU Instructions (Half)": "Fragment ALU Instructions / Sec (Half)",
    "Texture Memory Read BW": "Texture Memory Read BW (Bytes/Second)",
    "Vertex Memory Read": "Vertex Memory Read (Bytes/Second)",
    "Write Total": "Write Total (Bytes/sec)",
}


@dataclass(frozen=True)
class MetricStats:
    name: str
    category: str
    count: int
    avg: float
    minimum: float
    p50: float
    p95: float
    maximum: float
    raw_names: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["min"] = data.pop("minimum")
        data["max"] = data.pop("maximum")
        return data


@dataclass(frozen=True)
class ProfileSummary:
    source: str
    source_files: tuple[str, ...]
    row_count: int
    process_names: tuple[str, ...]
    categories: tuple[str, ...]
    duration_seconds: float | None
    metrics: dict[str, MetricStats]

    def get(self, metric_name: str) -> MetricStats | None:
        return self.metrics.get(normalize_metric_name(metric_name))

    def to_context_dict(self) -> dict[str, object]:
        fps = self.get("FPS")
        return {
            "source": self.source,
            "source_files": self.source_files,
            "row_count": self.row_count,
            "process_names": self.process_names,
            "categories": self.categories,
            "duration_seconds": self.duration_seconds,
            "fps": fps.to_dict() if fps else None,
            "metrics": [metric.to_dict() for metric in self.metrics.values()],
        }


def normalize_metric_name(metric: str) -> str:
    name = INSTANCE_SUFFIX_RE.sub("", metric).strip()
    name = re.sub(r"\s+", " ", name)
    return METRIC_ALIASES.get(name, name)


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = round((len(sorted_values) - 1) * percentile)
    return sorted_values[max(0, min(len(sorted_values) - 1, index))]


def _normalize_sources(source: str | Path | Sequence[str | Path]) -> tuple[str, tuple[str, ...]]:
    if isinstance(source, (str, Path)):
        source_files = (str(source),)
    else:
        source_files = tuple(str(item) for item in source)

    if not source_files:
        return "<memory>", ()
    if len(source_files) == 1:
        return source_files[0], source_files
    return f"{len(source_files)} CSV files", source_files


def summarize(rows: list[ProfileRow], source: str | Path | Sequence[str | Path] = "<memory>") -> ProfileSummary:
    values_by_metric: dict[str, list[float]] = defaultdict(list)
    raw_names_by_metric: dict[str, set[str]] = defaultdict(set)
    categories_by_metric: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        metric_name = normalize_metric_name(row.metric)
        values_by_metric[metric_name].append(row.value)
        raw_names_by_metric[metric_name].add(row.metric)
        categories_by_metric[metric_name][row.category] += 1

    metrics: dict[str, MetricStats] = {}
    for name, values in values_by_metric.items():
        ordered = sorted(values)
        category = categories_by_metric[name].most_common(1)[0][0]
        metrics[name] = MetricStats(
            name=name,
            category=category,
            count=len(values),
            avg=sum(values) / len(values),
            minimum=ordered[0],
            p50=_percentile(ordered, 0.5),
            p95=_percentile(ordered, 0.95),
            maximum=ordered[-1],
            raw_names=tuple(sorted(raw_names_by_metric[name])),
        )

    timestamps = [row.timestamp for row in rows]
    duration_seconds = None
    if timestamps:
        duration_seconds = (max(timestamps) - min(timestamps)) / 1_000_000

    source_text, source_files = _normalize_sources(source)
    return ProfileSummary(
        source=source_text,
        source_files=source_files,
        row_count=len(rows),
        process_names=tuple(sorted({row.process for row in rows if row.process})),
        categories=tuple(name for name, _ in Counter(row.category for row in rows).most_common()),
        duration_seconds=duration_seconds,
        metrics=dict(sorted(metrics.items())),
    )
