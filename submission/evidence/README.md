# Evidence cá nhân

Thư mục evidence của Nguyễn Quốc Cường, MSSV 2A202602886, project Langfuse
`day13-k4-l3a-2A202602886`. Danh sách yêu cầu đầy đủ xem tại
[docs/SUBMISSION.md](../../docs/SUBMISSION.md); trạng thái cá nhân nằm trong
[REPORT.md](../REPORT.md).

## File thực tế và trạng thái

| Nhóm | Evidence | Trạng thái |
|---|---|---|
| 01–03 | [Kiểm tra mới nhất](pre-submission-validation.txt) | 41 passed, log 100/100, dashboard 6/6; worktree chưa commit |
| Lịch sử CP2 | [Tests](01-pytest.txt), [logs](02-log-validator.txt), [dashboard](03-dashboard-validator.txt) | Giữ nguyên kết quả thời điểm CP2 |
| Lịch sử CP3 | [Validation](cp3-20260929T101509Z/validation.txt) | Giữ nguyên kết quả thời điểm CP3 |
| 04 | [Structured log](04-structured-log.png) | Đã có |
| 05 | [Input giả](05a-pii-test-input.png), [log đã che](05b-pii-redacted-log.png) | Đủ email/điện thoại/CCCD/thẻ |
| 06 | [Trace list](06-trace-list.png) | Đã có project và hơn 10 root traces |
| 07 | [Cây observations](07-trace-waterfall.png) | Đã có quan hệ cha–con; Timeline là bổ sung hữu ích |
| 08 | [Metadata](08a-trace-metadata.png), [usage/cost](08b-generation-usage.png) | TODO: che giá trị public key |
| 09 | [Prompt versions](09-prompt-versions.png) | Đã có v1/v2 và labels |
| 10 | [Production v2](10a-production-v2.png), [rollback v1](10b-production-v1-rollback.png) | Đã có ảnh trước/sau |
| 11 | [Dashboard](11-dashboard-overview.png) | Đã có sáu panel runtime |
| 12 | [Incident metric](12-incident-metric.png) | Đã có metric và time window |
| 13 | [Incident log](13-incident-log.png) | Đã có `req-67ed9c57` và latency 2653 ms |
| 14 | [Incident trace hiện tại](14-incident-trace.png) | TODO: Show labels và metadata cùng correlation ID |

<!-- TODO (evidence index - completed): Dẫn file thực tế, thay link 05/09/10/11 cũ.
TODO (UI - pending): Che public key trong 08a/08b; bổ sung thông tin trên ảnh 14.
TODO (Git/LMS - pending): Chốt commit/push, kiểm tra cuối và nộp SHA. -->

Có thể dùng `.txt` cho output của tests/validators. Có thể tách dashboard thành nhiều ảnh nếu một ảnh không đọc rõ.

Ảnh `04`, `05`, `13` lấy từ terminal hoặc `data/logs.jsonl`. Ảnh `06`–`10`, `14` lấy từ project Langfuse cá nhân `day13-k4-l3a-<MSSV>` và nên nhìn thấy tên project. Không mở/chụp trang API Keys.

Từ `submission/REPORT.md`, dẫn ảnh bằng đường dẫn tương đối:

```markdown
![Trace waterfall](evidence/07-trace-waterfall.png)
```

Không commit secret, API key, PII thô hoặc evidence của học viên/lớp khác.
Ảnh input 05a chỉ chứa fixture giả, đánh dấu `FAKE TEST INPUT ONLY`; không dùng
thông tin thật. Có thể crop/che key bằng khối màu đặc nhưng không sửa kết quả,
ID hoặc tên span để làm giả evidence. JSON/SVG/API export chỉ là tài liệu bổ
sung, không thay thế ảnh UI Langfuse bắt buộc.

## CP3 đã chạy

<!-- TODO (CP3 - completed): Lưu số liệu đo thật, recovery và ảnh 12/13.
TODO (CP3 UI - pending): Ảnh 14 đã có file nhưng cần tên span và correlation ID. -->

Lượt chính: [summary.json](cp3-20260929T101509Z/summary.json).
Biểu đồ: [12-incident-metric.svg](cp3-20260929T101509Z/12-incident-metric.svg).
Log gốc: [incident-responses.jsonl](cp3-20260929T101509Z/incident-responses.jsonl).
Traces API: [langfuse-traces.json](cp3-20260929T101509Z/langfuse-traces.json).
Test/validators: [validation.txt](cp3-20260929T101509Z/validation.txt).

Mở [incident-view.html](cp3-20260929T101509Z/incident-view.html) bằng browser để
xem metric và link trace. Hướng dẫn chụp ảnh:
[checklist evidence CP3](../../docs/grading-evidence.md#evidence-cp3-đã-lưu-và-cách-hoàn-thiện-ảnh-14).

Lượt đầu [cp3-20260929T101253Z](cp3-20260929T101253Z/summary.json) được giữ lại
để minh họa cold prompt fetch ảnh hưởng baseline. Dùng lượt chính đã warm
cache để so sánh retrieval. Không export query riêng của coach vào artifact.

## Cách đóng các TODO còn lại

1. Che toàn bộ giá trị `scope.attributes.public_key` trong 08a/08b, giữ các
   metadata và token/cost cần chấm. Public key không phải secret key nhưng
   evidence nộp bài không nên hiện giá trị key.
2. Mở lại trace `4141305c45dfe206c515364337a29a58`, bật **Timeline → Show labels**;
   chụp root/retrieval/generation và thêm metadata `req-67ed9c57`. Có thể dùng
   hai tên file `14a-incident-waterfall.png`/`14b-incident-metadata.png` rồi cập
   nhật link trong report; chưa tạo link tới file chưa tồn tại.
3. Kiểm tra lại ảnh và mọi link, lưu kết quả tests/validators của bản nộp cuối,
   commit/push theo quyền của chủ repo rồi nộp URL/SHA trên LMS.

Không cần bật lại incident hay chạy lại challenge chỉ để chụp ảnh lịch sử.
