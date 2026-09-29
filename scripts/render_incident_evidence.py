from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Render a genuine CP3 metric chart from saved runtime measurements")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    summary = json.loads((args.run_dir / "summary.json").read_text(encoding="utf-8"))
    traces = json.loads((args.run_dir / "langfuse-traces.json").read_text(encoding="utf-8"))
    phase_names = {"baseline": "Baseline", "incident": "Incident", "recovery": "Recovery"}
    colors = {"baseline": "#17786f", "incident": "#d14949", "recovery": "#17786f"}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="590" viewBox="0 0 1120 590">',
           '<rect width="1120" height="590" fill="#f7f9fc"/>',
           '<g font-family="Segoe UI,Arial,sans-serif" fill="#203146">',
           '<text x="35" y="42" font-size="24" font-weight="700">CP3: measured request latency before / during / after incident</text>',
           f'<text x="35" y="70" font-size="16">{html.escape(summary["challenge_id"])} | feature: {html.escape(summary["affected_feature"])} | concurrency: {summary["concurrency"]}</text>',
           '<text x="35" y="99" font-size="14">Source: real response_sent logs; 5 requests per phase; unit: milliseconds (ms)</text>']
    chart_bottom = 420
    chart_height = 270
    max_value = max(3500, max(phase["metrics"]["latency_ms"]["p95"] for phase in summary["phases"]) * 1.25)

    def y(value: float) -> float:
        return chart_bottom - value / max_value * chart_height

    for value in (0, 1000, 2000, 3000):
        svg.extend([f'<line x1="90" y1="{y(value):.1f}" x2="1050" y2="{y(value):.1f}" stroke="#d8dfe8"/>',
                    f'<text x="28" y="{y(value) + 5:.1f}" font-size="13">{value}</text>'])
    threshold = summary["latency_threshold_ms"]
    svg.extend([f'<line x1="90" y1="{y(threshold):.1f}" x2="1050" y2="{y(threshold):.1f}" stroke="#b57515" stroke-width="2" stroke-dasharray="7 5"/>',
                f'<text x="730" y="{y(threshold) - 9:.1f}" font-size="14" fill="#925c0d">Challenge threshold: {threshold} ms</text>',
                f'<text x="780" y="{y(3000) - 9:.1f}" font-size="13">SLO boundary: 3000 ms</text>'])
    rows = []
    for index, phase in enumerate(summary["phases"]):
        center = 230 + index * 335
        p95 = phase["metrics"]["latency_ms"]["p95"]
        color = colors[phase["name"]]
        start = datetime.fromisoformat(phase["started_at"]).astimezone(timezone(timedelta(hours=7)))
        end = datetime.fromisoformat(phase["ended_at"]).astimezone(timezone(timedelta(hours=7)))
        svg.extend([f'<rect x="{center - 66}" y="{y(p95):.1f}" width="132" height="{chart_bottom - y(p95):.1f}" fill="{color}" rx="4"/>',
                    f'<text x="{center}" y="{y(p95) - 12:.1f}" text-anchor="middle" font-size="22" font-weight="700">P95 {p95:.0f} ms</text>',
                    f'<text x="{center}" y="454" text-anchor="middle" font-size="20">{phase_names[phase["name"]]}</text>',
                    f'<text x="{center}" y="481" text-anchor="middle" font-size="14">{start:%H:%M:%S}–{end:%H:%M:%S} UTC+07</text>',
                    f'<text x="{center}" y="506" text-anchor="middle" font-size="14">Above threshold: {phase["metrics"]["over_challenge_threshold"]}/5</text>'])
        metrics = phase["metrics"]
        rows.append(f'<tr><td>{phase_names[phase["name"]]}</td><td>{start.isoformat(timespec="seconds")} – {end:%H:%M:%S}</td><td>{metrics["latency_ms"]["p50"]}</td><td>{p95}</td><td>{metrics["client_latency_ms"]["p95"]}</td><td>{metrics["ttft_p95_ms"]}</td><td>{metrics["error_rate_pct"]}%</td></tr>')
    svg.extend(['<text x="35" y="547" font-size="13">P95 uses nearest-rank; with only 5 samples it equals the maximum. Small experiment, not a 28-day SLO measurement.</text>',
                '<text x="35" y="570" font-size="13">Warmup requests excluded. This is an analytical chart from measured data, not a screenshot of a dashboard or Langfuse.</text>', '</g></svg>'])
    chart = "\n".join(svg)
    (args.run_dir / "12-incident-metric.svg").write_text(chart, encoding="utf-8")

    selected = next(trace for trace in traces["traces"] if trace["phase"] == "incident")
    log = next(record for phase in summary["phases"] if phase["name"] == "incident"
               for record in phase["response_logs"] if record["correlation_id"] == selected["correlation_id"])
    durations = {item["name"]: item["duration_ms"] for item in selected["observations"]}
    escaped_log = html.escape(json.dumps(log, ensure_ascii=False, indent=2))
    page = f'''<!doctype html>
<html lang="vi"><meta charset="utf-8"><title>CP3 incident evidence</title>
<style>body{{max-width:1160px;margin:28px auto;font:16px/1.55 Segoe UI,Arial,sans-serif;background:#f7f9fc;color:#203146;padding:0 16px}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:12px;border:1px solid #ccd6e2;text-align:left}}pre{{background:white;padding:18px;border:1px solid #ccd6e2;white-space:pre-wrap;overflow-wrap:anywhere}}a{{color:#125b99}}code{{font-size:14px}}h1{{font-size:28px}}</style>
<h1>CP3 — metric → log → trace</h1>
<p>Ảnh chụp trang này là evidence phân tích số liệu đã lưu. Các số đo đều lấy từ lần chạy thật; các query riêng của challenge không được đưa vào artifact.</p>
<img src="12-incident-metric.svg" alt="Measured P95 for baseline, incident and recovery">
<table><tr><th>Phase</th><th>UTC+07 window</th><th>P50 xử lý (ms)</th><th>P95 xử lý (ms)</th><th>P95 client (ms)</th><th>TTFT P95 (ms)</th><th>Error</th></tr>{''.join(rows)}</table>
<h2>Log thật của request đại diện</h2><pre>{escaped_log}</pre>
<h2>Trace đã xác minh qua Langfuse API</h2>
<p>Correlation ID: <code>{html.escape(selected['correlation_id'])}</code><br>Trace ID: <code>{selected['trace_id']}</code><br>Root: {durations['lab-agent-run']} ms · Retrieval: {durations['retrieval']} ms · Generation: {durations['fake-llm-generation']} ms</p>
<p><a href="{html.escape(selected['trace_url'] or '', quote=True)}" target="_blank" rel="noopener">Mở trace thật trong Langfuse để chụp waterfall (14-incident-trace.png)</a></p>
<p>Raw input/output không capture; user ID đã hash. Các observation cùng parent root. Việc tắt incident đã được kiểm chứng bằng một lượt recovery với cùng input/concurrency.</p>
<p>Dashboard 60 phút chứa cả traffic practice cũ. Bảng trên lọc theo correlation ID từng lượt chạy để tránh gán metric của request khác cho challenge.</p>
</html>'''
    (args.run_dir / "incident-view.html").write_text(page, encoding="utf-8")
    print(f"Chart: {args.run_dir / '12-incident-metric.svg'}")
    print(f"Evidence viewer: {args.run_dir / 'incident-view.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
