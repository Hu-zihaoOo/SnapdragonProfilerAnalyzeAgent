from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from snapdragon_profiler_agent.analyzer import normalize_metric_name, summarize
from snapdragon_profiler_agent.loader import CsvLoadError, ProfileRow, load_csv, load_csv_files
from snapdragon_profiler_agent.rules import evaluate_rules


class CoreTests(unittest.TestCase):
    def _write_valid_csv(self, path: Path, metric: str = "FPS[1]", value: float = 30.0) -> None:
        path.write_text(
            "Process,Category,Metric,Timestamp,TimestampRaw,Value\n"
            f"p,EGL,{metric},0,0,{value}\n",
            encoding="utf-8",
        )

    def test_normalize_metric_name_strips_instance_suffix(self) -> None:
        self.assertEqual(normalize_metric_name("% Linear Filtered[123]"), "% Linear Filtered")

    def test_load_csv_rejects_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("Metric,Value\nFPS,30\n", encoding="utf-8")
            with self.assertRaises(CsvLoadError):
                load_csv(path)

    def test_load_csv_rejects_non_numeric_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text(
                "Process,Category,Metric,Timestamp,TimestampRaw,Value\n"
                "p,EGL,FPS[1],0,0,not-a-number\n",
                encoding="utf-8",
            )
            with self.assertRaises(CsvLoadError):
                load_csv(path)

    def test_load_csv_files_merges_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.csv"
            second = root / "second.csv"
            self._write_valid_csv(first, "FPS[1]", 29.0)
            self._write_valid_csv(second, "% Linear Filtered[1]", 98.0)

            loaded = load_csv_files([first, second])

            self.assertEqual(len(loaded.rows), 2)
            self.assertEqual(loaded.source_files, (str(first), str(second)))

    def test_load_csv_files_accepts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_valid_csv(root / "capture.csv")

            loaded = load_csv_files([root])

            self.assertEqual(len(loaded.rows), 1)
            self.assertEqual(loaded.source_files, (str(root / "capture.csv"),))

    def test_load_csv_files_accepts_glob(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "a.csv"
            second = root / "b.csv"
            self._write_valid_csv(first)
            self._write_valid_csv(second)

            loaded = load_csv_files([str(root / "*.csv")])

            self.assertEqual(len(loaded.rows), 2)
            self.assertEqual(loaded.source_files, (str(first), str(second)))

    def test_load_csv_files_wraps_bad_file_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("Metric,Value\nFPS,30\n", encoding="utf-8")

            with self.assertRaisesRegex(CsvLoadError, "bad.csv"):
                load_csv_files([path])

    def test_rules_detect_expected_bottlenecks(self) -> None:
        rows = [
            ProfileRow("p", "EGL", "FPS[1]", 0, 0, 29.9),
            ProfileRow("p", "GPU Shader Processing", "% Linear Filtered[1]", 1, 1, 97.9),
            ProfileRow("p", "GPU Shader Processing", "% Shaders Stalled[1]", 2, 2, 15.4),
            ProfileRow("p", "GPU Shader Processing", "% Texture Pipes Busy[1]", 3, 3, 66.8),
            ProfileRow("p", "GPU Primitive Processing", "% Prims Trivially Rejected[1]", 4, 4, 86.7),
            ProfileRow("p", "GPU Primitive Processing", "Reused Vertices / Second[1]", 5, 5, 0),
            ProfileRow("p", "GPU General", "GPU % Utilization[1]", 6, 6, 24.3),
        ]
        issues = evaluate_rules(summarize(rows))
        titles = {issue.title for issue in issues}
        self.assertIn("线性纹理过滤占比过高", titles)
        self.assertIn("Shader stall 超过建议阈值", titles)
        self.assertIn("Texture pipe 压力偏高", titles)
        self.assertIn("图元 trivially rejected 比例异常高", titles)
        self.assertIn("顶点复用计数为 0", titles)


if __name__ == "__main__":
    unittest.main()
