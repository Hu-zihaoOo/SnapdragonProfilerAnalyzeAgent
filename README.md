# Snapdragon Profiler Analyze Agent

用于分析 Snapdragon Profiler 导出的 CSV 数据，支持本地规则诊断，也可以接入 DeepSeek 兼容的 OpenAI API 生成 LLM 分析报告。

## 功能

- 读取单个或多个 Snapdragon Profiler CSV 文件。
- 支持文件、目录和 glob 通配符输入。
- 统计指标的平均值、p50、p95、最小值、最大值等信息。
- 使用本地规则识别常见 GPU 性能瓶颈。
- 可选通过 LangChain 调用 DeepSeek 兼容接口。
- 输出 Markdown 格式性能分析报告。

## 环境要求

- Python 3.11+
- Snapdragon Profiler CSV 需要包含以下列：
  - `Process`
  - `Category`
  - `Metric`
  - `Timestamp`
  - `TimestampRaw`
  - `Value`

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 使用方法

只使用本地规则分析，不调用 LLM：

```bash
python main.py analyze path\to\capture.csv --no-llm --output report.md
```

分析目录下的所有 CSV 文件：

```bash
python main.py analyze path\to\captures --no-llm --output report.md
```

使用 glob 通配符分析：

```bash
python main.py analyze "path\to\captures\*.csv" --no-llm --output report.md
```

也可以用模块方式运行：

```bash
python -m snapdragon_profiler_agent analyze path\to\capture.csv --no-llm
```

## LLM 配置

在本地创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

然后去掉 `--no-llm` 运行：

```bash
python main.py analyze path\to\capture.csv --output report.md
```

## 提示词

默认提示词文件：

- `prompts/AgentPrompt`
- `prompts/EvaluatePrompts`

也可以通过参数指定：

```bash
python main.py analyze capture.csv --agent-prompt prompts/AgentPrompt --prompt prompts/EvaluatePrompts
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## 项目结构

```text
snapdragon_profiler_agent/
  agent.py      LLM 调用与报告渲染
  analyzer.py   指标聚合统计
  cli.py        命令行入口
  loader.py     CSV 加载与校验
  rules.py      本地瓶颈规则
prompts/        默认提示词文件
tests/          单元测试
main.py         CLI 启动文件
```

