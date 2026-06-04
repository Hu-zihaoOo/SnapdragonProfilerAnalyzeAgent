from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import generate_llm_report, load_env_file, read_prompt_text, read_system_prompt_text, render_rule_report
from .analyzer import summarize
from .loader import CsvLoadError, load_csv_files
from .rules import evaluate_rules


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapdragon-profiler-agent",
        description="Analyze Snapdragon Profiler CSV captures with local rules and optional DeepSeek/LangChain.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one or more Snapdragon Profiler CSV files.")
    analyze.add_argument(
        "csv",
        nargs="+",
        help="CSV files, directories containing CSV files, or glob patterns such as *.csv.",
    )
    analyze.add_argument(
        "--prompt",
        default=None,
        help="Path to metric evaluation prompt/rules text. Defaults to ./prompts/EvaluatePrompts when present.",
    )
    analyze.add_argument(
        "--agent-prompt",
        default=None,
        help="Path to LLM system prompt. Defaults to ./prompts/AgentPrompt when present.",
    )
    analyze.add_argument("--output", default="report.md", help="Write Markdown report to this path. Defaults to report.md.")
    analyze.add_argument("--no-llm", action="store_true", help="Skip DeepSeek and output deterministic rule report.")
    analyze.add_argument("--env", default=".env", help="Path to .env file. Defaults to .env.")
    analyze.add_argument("--top", type=int, default=8, help="Number of top bottlenecks to include.")
    return parser


def analyze_command(args: argparse.Namespace) -> int:
    load_env_file(args.env)

    loaded = load_csv_files(args.csv)
    summary = summarize(loaded.rows, source=loaded.source_files)
    issues = evaluate_rules(summary)

    prompt_path = Path(args.prompt) if args.prompt is not None else None
    if args.prompt is not None and prompt_path and not prompt_path.exists():
        raise CsvLoadError(f"提示词文件不存在: {prompt_path}")
    prompt_text = read_prompt_text(prompt_path)

    agent_prompt_path = Path(args.agent_prompt) if args.agent_prompt is not None else None
    if args.agent_prompt is not None and agent_prompt_path and not agent_prompt_path.exists():
        raise CsvLoadError(f"Agent 系统提示词文件不存在: {agent_prompt_path}")
    system_prompt_text = read_system_prompt_text(agent_prompt_path)

    if args.no_llm:
        report = render_rule_report(summary, issues, top_n=args.top)
    else:
        report = generate_llm_report(
            summary,
            issues,
            prompt_text,
            system_prompt_text=system_prompt_text,
            top_n=args.top,
        )

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written: {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            return analyze_command(args)
    except CsvLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
