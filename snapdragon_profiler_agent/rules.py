from __future__ import annotations

from dataclasses import asdict, dataclass

from .analyzer import MetricStats, ProfileSummary


SEVERITY_SCORE = {
    "high": 90,
    "medium": 60,
    "low": 30,
    "info": 10,
}


@dataclass(frozen=True)
class BottleneckIssue:
    title: str
    severity: str
    score: float
    metric: str
    evidence: str
    interpretation: str
    recommendation: str
    confidence: str = "medium"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _fmt(value: float, suffix: str = "") -> str:
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B{suffix}"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M{suffix}"
    if abs(value) >= 1_000:
        return f"{value:,.0f}{suffix}"
    return f"{value:.2f}{suffix}"


def _issue(
    *,
    title: str,
    severity: str,
    metric: MetricStats,
    evidence: str,
    interpretation: str,
    recommendation: str,
    confidence: str = "medium",
    extra_score: float = 0,
) -> BottleneckIssue:
    return BottleneckIssue(
        title=title,
        severity=severity,
        score=SEVERITY_SCORE[severity] + extra_score,
        metric=metric.name,
        evidence=evidence,
        interpretation=interpretation,
        recommendation=recommendation,
        confidence=confidence,
    )


def _metric(summary: ProfileSummary, name: str) -> MetricStats | None:
    return summary.get(name)


def evaluate_rules(summary: ProfileSummary) -> list[BottleneckIssue]:
    issues: list[BottleneckIssue] = []

    fps = _metric(summary, "FPS")
    if fps:
        if fps.avg < 30:
            issues.append(
                _issue(
                    title="FPS 低于 30 帧目标",
                    severity="high",
                    metric=fps,
                    evidence=f"avg={_fmt(fps.avg)} FPS, p50={_fmt(fps.p50)}, min={_fmt(fps.minimum)}",
                    interpretation="帧率已经跌破常见 30 FPS 档位，需要优先缩小 CPU/GPU/同步等待范围。",
                    recommendation="先结合 GPU 利用率和 shader/texture stall 判断是否 GPU 侧饱和；如果 GPU 利用率不高，继续检查 CPU 主线程、VSync、温控或帧率上限。",
                    confidence="high",
                    extra_score=5,
                )
            )
        elif fps.avg < 45:
            issues.append(
                _issue(
                    title="FPS 处在 30 FPS 附近",
                    severity="medium",
                    metric=fps,
                    evidence=f"avg={_fmt(fps.avg)} FPS, p50={_fmt(fps.p50)}, min={_fmt(fps.minimum)}",
                    interpretation="帧率稳定在 30 FPS 附近，可能是性能边界、VSync/目标帧率或设备功耗策略共同作用。",
                    recommendation="确认 Unity `Application.targetFrameRate`、VSync 设置和测试设备功耗模式，再针对高优先级 GPU 指标优化。",
                    confidence="medium",
                    extra_score=4,
                )
            )

    linear = _metric(summary, "% Linear Filtered")
    if linear and linear.avg > 80:
        issues.append(
            _issue(
                title="线性纹理过滤占比过高",
                severity="high",
                metric=linear,
                evidence=f"avg={_fmt(linear.avg, '%')}, p95={_fmt(linear.p95, '%')}",
                interpretation="采样几乎全部走 linear filtering，容易把瓶颈推向 texture pipe 和带宽。",
                recommendation="检查高频采样材质、后处理和全屏 pass；能接受画质差异的纹理改 nearest/降低采样次数/降低分辨率，移动端优先压缩和合并采样。",
                confidence="high",
                extra_score=min(9, (linear.avg - 80) / 2),
            )
        )

    stalled = _metric(summary, "% Shaders Stalled")
    if stalled and stalled.avg > 10:
        issues.append(
            _issue(
                title="Shader stall 超过建议阈值",
                severity="high",
                metric=stalled,
                evidence=f"avg={_fmt(stalled.avg, '%')}, p95={_fmt(stalled.p95, '%')}, max={_fmt(stalled.maximum, '%')}",
                interpretation="shader 等待比例偏高，通常与纹理 fetch、缓存未命中、内存访问或长 shader 路径有关。",
                recommendation="从最贵材质和后处理开始减采样、减分支、减纹理读取；优先查看与 Texture Fetch Stall、Texture L1 Miss、Texture Pipes Busy 的相关性。",
                confidence="high",
                extra_score=min(12, stalled.avg - 10),
            )
        )

    texture_pipes = _metric(summary, "% Texture Pipes Busy")
    if texture_pipes and texture_pipes.avg >= 60:
        issues.append(
            _issue(
                title="Texture pipe 压力偏高",
                severity="medium",
                metric=texture_pipes,
                evidence=f"avg={_fmt(texture_pipes.avg, '%')}, p95={_fmt(texture_pipes.p95, '%')}",
                interpretation="纹理单元持续繁忙，结合高 linear filtering 时更像纹理采样成本主导。",
                recommendation="减少每片元纹理采样、降低 RenderTexture/后处理分辨率、压缩纹理并检查 mipmap；URP 中重点检查 Renderer Feature 和全屏 blit 链。",
                confidence="high",
                extra_score=min(15, (texture_pipes.avg - 60) / 2),
            )
        )

    texture_fetch = _metric(summary, "% Texture Fetch Stall")
    if texture_fetch and texture_fetch.avg > 2:
        severity = "medium" if texture_fetch.avg < 16 else "high"
        issues.append(
            _issue(
                title="Texture fetch stall 高于理想值",
                severity=severity,
                metric=texture_fetch,
                evidence=f"avg={_fmt(texture_fetch.avg, '%')}, p95={_fmt(texture_fetch.p95, '%')}, max={_fmt(texture_fetch.maximum, '%')}",
                interpretation="纹理读取等待超过理想 2%，说明 shader 有一定纹理取数等待。",
                recommendation="检查大纹理、无 mipmap、采样 cache locality 差和过多全屏采样；优先优化被频繁采样的材质和后处理 pass。",
                confidence="medium",
                extra_score=min(10, texture_fetch.avg),
            )
        )

    prim_rejected = _metric(summary, "% Prims Trivially Rejected")
    if prim_rejected and prim_rejected.avg > 2:
        issues.append(
            _issue(
                title="图元 trivially rejected 比例异常高",
                severity="high" if prim_rejected.avg > 30 else "medium",
                metric=prim_rejected,
                evidence=f"avg={_fmt(prim_rejected.avg, '%')}, p95={_fmt(prim_rejected.p95, '%')}",
                interpretation="大量图元被快速剔除，可能存在不可见网格提交、裁剪/遮挡前仍发起 draw 或场景包围盒异常。",
                recommendation="检查摄像机外物体、LOD/occlusion culling、粒子/特效包围盒和批处理后的大包围盒；减少无效 draw 提交。",
                confidence="medium",
                extra_score=min(15, prim_rejected.avg / 8),
            )
        )

    reused = _metric(summary, "Reused Vertices / Second")
    if reused and reused.avg <= 0:
        issues.append(
            _issue(
                title="顶点复用计数为 0",
                severity="medium",
                metric=reused,
                evidence=f"avg={_fmt(reused.avg)}, max={_fmt(reused.maximum)}",
                interpretation="指标显示没有顶点复用，可能是未使用 indexed mesh、动态网格路径不可复用，或该 counter 在当前捕获下不可用。",
                recommendation="确认 Unity Mesh 使用 index buffer，避免逐帧重建无法复用的网格；若项目确实使用索引，标记为数据可用性问题并结合 Vertices Shaded 判断。",
                confidence="medium",
                extra_score=8,
            )
        )

    polygon_area = _metric(summary, "Average Polygon Area")
    if polygon_area and polygon_area.avg > 4096:
        issues.append(
            _issue(
                title="平均多边形面积过大",
                severity="medium",
                metric=polygon_area,
                evidence=f"avg={_fmt(polygon_area.avg)}, p95={_fmt(polygon_area.p95)}",
                interpretation="平均图元面积远大于常规小三角场景，可能由全屏三角形、超大 UI/后处理 pass 或异常网格主导。",
                recommendation="如果是后处理全屏 pass，应继续关注纹理/带宽；如果是场景网格，检查过大三角形、UI overdraw 和不合理 mesh 拆分。",
                confidence="low",
                extra_score=min(10, polygon_area.avg / 20000),
            )
        )

    efu = _metric(summary, "% Time EFUs Working")
    if efu and efu.avg < 20:
        issues.append(
            _issue(
                title="EFU 利用偏低",
                severity="low",
                metric=efu,
                evidence=f"avg={_fmt(efu.avg, '%')}, p95={_fmt(efu.p95, '%')}",
                interpretation="特殊函数单元利用低，不一定是坏事；与 shader busy/stall 组合看，当前更像纹理等待而不是 EFU 饱和。",
                recommendation="不要单独围绕 EFU 优化；先处理 texture filtering、texture pipe 和 shader stall。",
                confidence="medium",
            )
        )

    alu_capacity = _metric(summary, "% Shader ALU Capacity Utilized")
    shader_busy = _metric(summary, "% Shaders Busy")
    if alu_capacity and shader_busy and alu_capacity.avg < 50 and shader_busy.avg > 70:
        issues.append(
            _issue(
                title="Shader 忙但 ALU 利用不高",
                severity="medium",
                metric=alu_capacity,
                evidence=f"ALU capacity avg={_fmt(alu_capacity.avg, '%')}, Shaders Busy avg={_fmt(shader_busy.avg, '%')}",
                interpretation="shader 管线很忙，但 ALU 没被充分吃满，常见原因是纹理、内存或同步等待。",
                recommendation="优先按非 ALU 瓶颈处理：减少纹理读取、改善 mipmap/cache locality、检查 render target 读写和后处理链。",
                confidence="high",
                extra_score=6,
            )
        )

    gpu_util = _metric(summary, "GPU % Utilization")
    if gpu_util and fps and gpu_util.avg < 40 and fps.avg < 45:
        issues.append(
            _issue(
                title="GPU 总利用率不高但 FPS 不高",
                severity="info",
                metric=gpu_util,
                evidence=f"GPU Util avg={_fmt(gpu_util.avg, '%')}, FPS avg={_fmt(fps.avg)}",
                interpretation="整体 GPU 利用率不高，说明瓶颈可能不是简单 GPU 满载；也可能被 30 FPS 上限、VSync、CPU 或功耗策略限制。",
                recommendation="同步检查 Unity Profiler CPU 主线程/RenderThread、目标帧率、设备温控和 Snapdragon Profiler 的 CPU/系统指标。",
                confidence="medium",
            )
        )

    return sorted(issues, key=lambda issue: issue.score, reverse=True)
