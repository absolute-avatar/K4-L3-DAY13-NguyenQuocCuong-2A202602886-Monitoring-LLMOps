# Evidence dùng để chấm bài

Danh sách chính thức, quy tắc chụp và cách nộp nằm tại [SUBMISSION.md](SUBMISSION.md). File này là checklist nhanh khi bạn thu thập evidence cá nhân.

## Evidence runtime bắt buộc

- [ ] Kết quả cuối của `python -m pytest -q`.
- [ ] `validate_logs.py` đạt tối thiểu 80/100.
- [ ] `validate_dashboard.py` đạt 6/6.
- [ ] Structured log có `correlation_id` và metadata.
- [ ] PII giả đã được redact trong output thực tế.
- [ ] Tên project Langfuse cá nhân và danh sách tối thiểu 10 traces do học viên tự tạo.
- [ ] Một trace waterfall có root, retrieval và generation.
- [ ] Trace metadata có correlation ID, prompt version/label, token và cost.
- [ ] Prompt v1/v2 và bằng chứng promote/rollback.
- [ ] Dashboard runtime đủ 6 panel, time range, đơn vị và threshold.
- [ ] Incident metric, incident log và incident trace nối được bằng cùng correlation ID/khoảng sự cố.

## Artifact kiểm tra trực tiếp trên repo

Không cần chụp toàn bộ code. Dẫn link tới:

- `config/slo.yaml` và phần giải thích error budget trong `submission/REPORT.md`;
- `config/alert_rules.yaml` và `docs/alerts.md`;
- source, tests và commit history;
- `submission/REPORT.md`.

## Chất lượng evidence

- Evidence phải thuộc commit SHA được nộp và đúng challenge của lớp.
- Ảnh phải đọc được thông tin dùng để chấm, không phải ảnh trang trống.
- Che secret và PII; không dùng dữ liệu thật.
- Trace/prompt phải thuộc project cá nhân `day13-k4-l3a-<MSSV>`; không chụp trang API Keys.
- Đặt file trong `submission/evidence/`.
- Dẫn đường dẫn tương đối từ report, ví dụ `evidence/07-trace-waterfall.png`.
- Metric, log và trace của incident phải cùng chỉ về một nguyên nhân.

## Evidence CP3 đã lưu và cách hoàn thiện ảnh 14

<!-- TODO (CP3 evidence - completed): Đã có measured artifacts, recovery,
ảnh metric 12 và log 13. Gộp hướng dẫn vào tài liệu hiện có.
TODO (CP3 UI - pending): Ảnh 14 cần tên span và correlation ID. -->

Lượt chính nằm trong `submission/evidence/cp3-20260929T101509Z/`:
[summary](../submission/evidence/cp3-20260929T101509Z/summary.json),
[log incident](../submission/evidence/cp3-20260929T101509Z/incident-responses.jsonl)
và [trace API export](../submission/evidence/cp3-20260929T101509Z/langfuse-traces.json).
Incident đã tắt và recovery đã đo; không cần bật lại để chụp evidence lịch sử.
Không chụp nội dung challenge riêng hoặc trang API Keys.

### 12 — Metric đã có

[Ảnh metric](../submission/evidence/12-incident-metric.png) thể hiện P95
**154 → 2654 → 154 ms**, threshold challenge 2000 ms và ngày 29/09/2026,
múi giờ UTC+07. Phase incident là **17:15:14.662–17:15:28.487**.
Ảnh được chụp từ biểu đồ phân tích số đo thật trong
[incident-view.html](../submission/evidence/cp3-20260929T101509Z/incident-view.html),
không phải ảnh dashboard live. Snapshot dashboard ảnh 11 tổng hợp 60 phút,
không thay thế metrics lọc riêng từng phase.

### 13 — Log đã có

[Ảnh log](../submission/evidence/13-incident-log.png) có
`ts=2026-09-29T10:15:25.797315Z`, `correlation_id=req-67ed9c57`,
`feature=monitoring`, `latency_ms=2653`, `tool_success=true` và user hash.
Để đọc lại dòng gốc từ root repo:

```powershell
Get-Content -Encoding UTF8 submission\evidence\cp3-20260929T101509Z\incident-responses.jsonl |
    Select-String 'req-67ed9c57'
```

### 14 — Trace cần chụp bổ sung

[Ảnh hiện tại](../submission/evidence/14-incident-trace.png) đúng trace nhưng
chưa hiện tên span/correlation ID. Mở
[trace đã xác minh](https://cloud.langfuse.com/project/cmumcz16o205xad0d3qepok9w/traces/4141305c45dfe206c515364337a29a58)
trong project `day13-k4-l3a-2A202602886`; chọn ngày 29/09/2026 nếu cần.

1. Chọn **Timeline → Show labels**; mở rộng vùng hiển thị để thấy đủ tên
   root/retrieval/generation và duration.
2. Chụp waterfall với tên project và trace ID. Giá trị thực tế là:

   ```text
   lab-agent-run             2659 ms
   ├── retrieval             2501 ms
   └── fake-llm-generation    152 ms
   ```

3. Chọn root `lab-agent-run`, mở **Attributes/Metadata**; chụp
   `correlation_id=req-67ed9c57`, feature, model và env, giữ trace ID.
4. Tránh hiện giá trị public key. Có thể lưu hai ảnh
   `14a-incident-waterfall.png` và `14b-incident-metadata.png`, rồi cập nhật
   link trong report sau khi file thực sự tồn tại.

`input=null`/`output=undefined` là chủ ý không capture payload thô, không cần
sửa. JSON/API export chỉ bổ sung, không thay ảnh UI bắt buộc. Không sửa tên
span hoặc ID bằng trình chỉnh ảnh; chỉ crop/che key và thông tin nhạy cảm.

### Giới hạn kết luận

Retrieval mất khoảng 2.5 giây, generation khoảng 0.15 giây. Sau khi tắt
`rag_slow`, processing P95 về 154 ms. Threshold challenge 2000 ms khác SLO
3000 ms; 5 mẫu không đủ để kết luận SLO 28 ngày hoặc alert duration 5 phút
đã fire. Chi tiết và lệnh tái hiện nằm trong [REPORT](../submission/REPORT.md).

## Việc còn lại trước khi nộp bản cá nhân

- [ ] Che giá trị public key trong hai ảnh 08a/08b; giữ metadata cần chấm.
- [ ] Hoàn thiện ảnh 14 như trên; ảnh 05, 09, 10, 11, 12 và 13 đã có.
- [ ] Chốt commit/push chứa toàn bộ source, tài liệu và evidence; kiểm tra
  lại tests/validators, các link và ảnh trên remote, rồi nộp URL/SHA.

[Output kiểm tra mới nhất](../submission/evidence/pre-submission-validation.txt)
có 41 tests passed, log 100/100, dashboard 6/6. Đây là kiểm tra worktree
hiện tại, chưa phải xác nhận trên commit nộp cuối.
