# Dựng và kiểm tra dashboard

[`../config/dashboard.yaml`](../config/dashboard.yaml) là contract chấm điểm, không phụ thuộc việc bạn dựng dashboard trong Langfuse hay một công cụ local. File này quy định đúng nguồn dữ liệu, phép tổng hợp, đơn vị và threshold cho sáu panel.

Trường `query` trong YAML là pseudocode mô tả phép tính, không phải câu lệnh để copy nguyên vào mọi công cụ. Bạn chuyển cùng logic đó sang cú pháp của công cụ đã chọn.

## Mapping dữ liệu

| Panel | Event/field | Phép tổng hợp |
|---|---|---|
| Latency | `response_sent.latency_ms/ttft_ms` | latency P50/P95/P99 và TTFT P95 |
| Traffic | `request_received` | count, request/phút |
| Errors | `request_received`, `request_failed`, `error_type`, `tool_success` | error rate, breakdown và retrieval success |
| Cost | `response_sent.cost_usd` | tổng theo phút và toàn cửa sổ |
| Tokens | `response_sent.tokens_in/tokens_out` | tổng theo từng field |
| Quality | `response_sent.quality_score` | mean |

Giữ time range mặc định 60 phút, refresh 30 giây và hiển thị threshold/SLO line. Giá trị chính xác nằm trong `config/dashboard.yaml`; không tự đổi contract chỉ để ảnh dashboard đẹp hơn.

## Cách dựng

1. Hoàn thiện logging/PII và chạy API.
2. Chạy `python scripts/load_test.py --concurrency 5` để tạo baseline.
3. Dùng `data/logs.jsonl` làm nguồn chuẩn để tạo đúng sáu panel bằng Streamlit, notebook, Grafana hoặc công cụ tương đương. Langfuse vẫn là nơi mở trace/prompt version để điều tra sâu.
4. Đặt tên panel, đơn vị và threshold giống contract.
5. Chạy validator:

```bash
python scripts/validate_dashboard.py
```

Validator kiểm tra cấu trúc contract; nó không thể chứng minh biểu đồ trong ảnh dùng đúng dữ liệu. Evidence runtime vẫn bắt buộc.

## Dashboard runtime của repository cá nhân

<!-- TODO (CP2 - completed): Bổ sung dashboard runtime có thể chạy lại từ
structured logs thay cho việc chỉ giữ YAML contract. -->

Repository cung cấp dashboard local tại hai endpoint:

- `GET /dashboard`: giao diện sáu panel, time range 60 phút và auto-refresh 30 giây;
- `GET /dashboard/data`: snapshot JSON đã tổng hợp trực tiếp từ `data/logs.jsonl`.

Khởi động và mở dashboard:

```powershell
uvicorn app.main:app --reload --env-file .env
```

Sau đó truy cập `http://127.0.0.1:8000/dashboard`. Không cần cài thêm
Streamlit/Grafana; phần tổng hợp nằm trong `app/dashboard.py` và các threshold
vẫn lấy từ `config/dashboard.yaml`.

## Cách kiểm tra runtime

1. Lưu ảnh baseline và giá trị P95/error/cost hiện tại.
2. Bật một incident practice, ví dụ `python scripts/inject_incident.py --scenario rag_slow`.
3. Chạy lại load test với cùng input và concurrency.
4. Xác nhận panel liên quan thay đổi theo đúng hướng; với `rag_slow`, P95 phải tăng rõ ràng.
5. Lọc log chậm, lấy correlation ID rồi mở trace có cùng ID.
6. Tắt incident bằng `python scripts/inject_incident.py --scenario rag_slow --disable`.

Ảnh dashboard phải nhìn được tên panel, time range, đơn vị và threshold. Báo cáo phải dẫn lại trace ID hoặc log line dùng để giải thích thay đổi.

## Evidence runtime đã lưu

<!-- TODO (CP2 UI - completed): Đã có ảnh dashboard sáu panel với dữ liệu.
Giữ snapshot cũ để đối chiếu; không coi số hiện tại của cửa sổ trượt là hằng số. -->

[Ảnh dashboard 11](../submission/evidence/11-dashboard-overview.png) hiển thị
giờ cập nhật 17:29:11 ngày 29/09/2026, time range 60 phút, refresh 30 giây.
Snapshot có P50 155 ms, P95/P99 2658 ms, TTFT P95 50 ms, 32 requests, error
0%, retrieval success 100%, cost làm tròn $0.0657, 1,120 input/4,159 output
tokens và quality 0.84. 73 records là số dòng log, không phải số requests.

Đây là aggregate nhiều lượt chạy trong cửa sổ trượt; không dùng P95 2658 ms
để thay P95 incident chính thức 2654 ms. Đo incident theo đúng correlation
IDs của baseline/incident/recovery trong [report](../submission/REPORT.md).
`12-incident-metric.png` là ảnh biểu đồ phân tích số đo thật, không gọi là ảnh
dashboard live. Nếu cửa sổ 60 phút không còn dữ liệu, chạy workload mới rồi
chụp snapshot mới; không sửa ảnh hoặc timestamp để giả dữ liệu còn mới.

## Cách diễn giải SLO và các giới hạn

- `latency_ms` đo xử lý tại ứng dụng; client latency còn có queue/network.
  TTFT hiện đo từ đầu fake LLM, không gồm retrieval. CP3 chỉ rõ sự khác nhau.
- SLO chính trong [slo.yaml](../config/slo.yaml) là 99.5% request thành công
  trong 3000 ms, cửa sổ 28 ngày; error budget 0.5% (50 bad events/10,000
  requests). Threshold P95 3000 ms trên panel là tín hiệu tail latency,
  không phải phép tính trực tiếp attainment của SLO request-based.
- Panel cost tổng hợp 60 phút; nhãn daily budget $2.50 là mức tham chiếu,
  chưa chứng minh chi phí cả ngày hoặc một hệ thống cảnh báo ngân sách.
- Quality proxy là heuristic; dữ liệu `No errors in window` vẫn hợp lệ khi
  error rate 0%, không cần tạo lỗi chỉ để có error breakdown trong ảnh.
- [Ba alert](../config/alert_rules.yaml) có condition/duration/owner/channel
  và [runbook](alerts.md), nhưng khai báo YAML không đồng nghĩa đã có alert
  engine hay notification Slack chạy thực tế.
