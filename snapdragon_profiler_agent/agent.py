from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .analyzer import ProfileSummary
from .rules import BottleneckIssue


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
# DEFAULT_BASE_URL = "https://once.novai.su"
# DEFAULT_MODEL = "gpt-5.5"
DEFAULT_SYSTEM_PROMPT = (
    "你是移动 GPU 性能分析助手，熟悉 Snapdragon Profiler、Unity 和 URP。"
    "只基于输入的统计摘要和规则命中分析，不要编造 CSV 中没有的 counter。"
    "输出中文 Markdown。必须包含瓶颈排序、证据指标、可能原因、优化建议、置信度和数据缺口。"
)


@dataclass(frozen=True)
class AgentConfig:
    api_key: str | None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY") or None,
            base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
            model=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        )


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_prompt_text(path: str | Path | None) -> str:
    if path is None:
        default_path = Path("prompts/EvaluatePrompts")
        if not default_path.exists():
            return ""
        path = default_path
    prompt_path = Path(path)
    return prompt_path.read_text(encoding="utf-8")


def read_system_prompt_text(path: str | Path | None = None) -> str:
    if path is None:
        default_path = Path("prompts/AgentPrompt")
        if not default_path.exists():
            return DEFAULT_SYSTEM_PROMPT
        path = default_path
    prompt_path = Path(path)
    text = prompt_path.read_text(encoding="utf-8").strip()
    return text or DEFAULT_SYSTEM_PROMPT


def build_context(
    summary: ProfileSummary,
    issues: list[BottleneckIssue],
    prompt_text: str,
) -> dict[str, object]:
    metrics = [metric.to_dict() for metric in summary.metrics.values()]
    return {
        "summary": {
            "source": summary.source,
            "source_files": summary.source_files,
            "row_count": summary.row_count,
            "process_names": summary.process_names,
            "categories": summary.categories,
            "duration_seconds": summary.duration_seconds,
            "fps": summary.get("FPS").to_dict() if summary.get("FPS") else None,
        },
        "rule_issues": [issue.to_dict() for issue in issues],
        "metric_stats": metrics,
        "evaluation_prompt_excerpt": prompt_text[:6000],
    }


def render_rule_report(
    summary: ProfileSummary,
    issues: list[BottleneckIssue],
    *,
    note: str | None = None,
    top_n: int = 8,
) -> str:
    lines: list[str] = []
    lines.append("# Snapdragon Profiler 瓶颈分析")
    lines.append("")
    if note:
        lines.append(f"> {note}")
        lines.append("")

    lines.append("## 概览")
    lines.append(f"- 数据源: `{summary.source}`")
    if summary.source_files:
        lines.append(f"- 输入文件数: {len(summary.source_files)}")
        for source_file in summary.source_files:
            lines.append(f"  - `{source_file}`")
    lines.append(f"- 数据行: {summary.row_count}")
    if summary.process_names:
        lines.append(f"- 进程: {', '.join(summary.process_names)}")
    if summary.duration_seconds is not None:
        lines.append(f"- 捕获时长: {summary.duration_seconds:.2f}s")

    fps = summary.get("FPS")
    if fps:
        lines.append(
            f"- FPS: avg={fps.avg:.2f}, p50={fps.p50:.2f}, p95={fps.p95:.2f}, "
            f"min={fps.minimum:.2f}, max={fps.maximum:.2f}"
        )
    lines.append("")

    if issues:
        lines.append("## Top 瓶颈")
        for index, issue in enumerate(issues[:top_n], start=1):
            lines.append(f"{index}. **{issue.title}** ({issue.severity}, confidence={issue.confidence})")
            lines.append(f"   - 指标: `{issue.metric}`")
            lines.append(f"   - 证据: {issue.evidence}")
            lines.append(f"   - 判断: {issue.interpretation}")
            lines.append(f"   - 建议: {issue.recommendation}")
        lines.append("")
    else:
        lines.append("## Top 瓶颈")
        lines.append("- 未命中内置阈值规则；建议补充更多 counter 或扩大采样窗口。")
        lines.append("")

    lines.append("## 关键指标快照")
    key_metrics = [
        "GPU % Utilization",
        "% Shaders Busy",
        "% Shader ALU Capacity Utilized",
        "% Shaders Stalled",
        "% Texture Pipes Busy",
        "% Linear Filtered",
        "% Texture Fetch Stall",
        "% Prims Trivially Rejected",
        "Reused Vertices / Second",
        "Texture Memory Read BW (Bytes/Second)",
        "Write Total (Bytes/sec)",
    ]
    for name in key_metrics:
        metric = summary.get(name)
        if metric:
            lines.append(
                f"- `{metric.name}`: avg={metric.avg:.2f}, p95={metric.p95:.2f}, "
                f"min={metric.minimum:.2f}, max={metric.maximum:.2f}, n={metric.count}"
            )
    lines.append("")

    lines.append("## 数据缺口")
    lines.append("- 当前 CSV 是 counter 聚合数据，不能直接定位到具体材质、Renderer Feature、drawcall 或 GameObject。")
    lines.append("- 下一步应结合 Unity Profiler、Frame Debugger、RenderDoc 或 Snapdragon Profiler 的 per-draw 数据验证。")
    lines.append("- 如果 GPU 利用率不高但 FPS 仍低，需要补充 CPU、VSync、温控、目标帧率相关数据。")
    return "\n".join(lines).rstrip() + "\n"


def generate_llm_report(
    summary: ProfileSummary,
    issues: list[BottleneckIssue],
    prompt_text: str,
    *,
    system_prompt_text: str | None = None,
    config: AgentConfig | None = None,
    top_n: int = 8,
) -> str:
    config = config or AgentConfig.from_env()
    if not config.api_key:
        return render_rule_report(
            summary,
            issues,
            note="未设置 DEEPSEEK_API_KEY，已输出本地规则分析报告。",
            top_n=top_n,
        )

    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        return render_rule_report(
            summary,
            issues,
            note=f"LangChain 依赖不可用，已输出本地规则分析报告: {exc}",
            top_n=top_n,
        )

    context = json.dumps(
        build_context(summary, issues, prompt_text),
        ensure_ascii=False,
        indent=2,
    )
    system_prompt = (system_prompt_text or read_system_prompt_text()).strip() or DEFAULT_SYSTEM_PROMPT

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "请分析下面的 Snapdragon Profiler 聚合数据。不要要求用户重新提供完整 CSV。\n\n{context}",
            ),
        ]
    )
    llm = ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=config.temperature,
    )

    try:
        response = (prompt | llm).invoke({"context": context})
    except Exception as exc:  # pragma: no cover - depends on network/API.
        return render_rule_report(
            summary,
            issues,
            note=f"DeepSeek 调用失败，已输出本地规则分析报告: {exc}",
            top_n=top_n,
        )

    content = getattr(response, "content", str(response))
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    return str(content).strip() + "\n"
