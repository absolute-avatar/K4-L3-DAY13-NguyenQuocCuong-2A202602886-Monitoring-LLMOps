# Alert rules và runbook vận hành

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

<!-- TODO (CP2 - completed): Điền ba alert, bước điều tra và mitigation
thay cho các trường trống của starter template. -->

## Phạm vi triển khai và bằng chứng

[config/alert_rules.yaml](../config/alert_rules.yaml) khai báo ba rule với
condition, duration, severity, owner, Slack channel và runbook tương ứng.
Đây là contract cấu hình, không phải một alert engine hoặc Slack webhook.
Repository chưa có evidence chứng minh condition đã được duy trì đủ
duration và notification đã gửi thành công.

Challenge `rag_slow` được đo trong khoảng 14 giây, xử lý P95 2654 ms: vượt
ngưỡng challenge 2000 ms nhưng dưới ngưỡng alert latency 3000 ms, chưa đáp
ứng duration 5 phút. Không kết luận alert đã fire từ ảnh incident này.
Nếu triển khai alert engine sau lab, cần nối metrics thực tế, kiểm tra
duration và lưu trạng thái firing/delivery riêng; không ghi webhook secret
vào repository hoặc screenshot. Xem [report](../submission/REPORT.md).

<!-- TODO (future operations - optional): Nối alert engine và Slack delivery;
đây là bước triển khai tiếp theo, không được ghi là đã làm trong checkpoint 2. -->

## Alert 1

- **Tên:** HighRequestLatency
- **Severity:** critical
- **Duration:** 5 phút
- **Kênh thông báo:** Slack `#llmops-alerts`
- **SLI/SLO liên quan:** `fast_successful_requests`, latency P95.
- **Điều kiện và thời gian duy trì:** `latency_p95_ms > 3000` liên tục 5 phút.
- **Ảnh hưởng tới người dùng:** phần lớn request ở tail mất hơn 3 giây; phiên hỏi đáp có cảm giác treo hoặc timeout.
- **Ba bước kiểm tra đầu tiên:**
  1. Xác nhận P50/P95/P99 và TTFT trên dashboard trong cùng cửa sổ 60 phút; kiểm tra traffic có tăng đột biến hay không.
  2. Lọc `response_sent` có `latency_ms > 3000` trong `data/logs.jsonl`, lấy một `correlation_id` đại diện.
  3. Mở trace có cùng `correlation_id`; so sánh duration của `retrieval` và `fake-llm-generation` để khoanh vùng bước chậm.
- **Mitigation tạm thời:** giảm concurrency, tắt incident practice nếu đang bật, dùng prompt/version ổn định và chuyển sang fallback an toàn nếu dependency ngoài chậm.
- **Owner:** `ai-platform-oncall`

## Alert 2

- **Tên:** ReliabilityDegraded
- **Severity:** critical
- **Duration:** 5 phút
- **Kênh thông báo:** Slack `#llmops-alerts`
- **SLI/SLO liên quan:** error rate tối đa 2%, retrieval success tối thiểu 90%.
- **Điều kiện và thời gian duy trì:** `error_rate_pct > 2` hoặc `retrieval_success_rate_pct < 90` liên tục 5 phút.
- **Ảnh hưởng tới người dùng:** request trả HTTP 500 hoặc không lấy được context cần thiết để trả lời.
- **Ba bước kiểm tra đầu tiên:**
  1. Xem error rate, error breakdown và retrieval success trên dashboard để xác định loại lỗi chiếm ưu thế.
  2. Lọc `request_failed`, ghi lại `error_type`, feature và `correlation_id`; không sao chép payload có PII thô.
  3. Mở trace tương ứng, xác nhận observation nào có level `ERROR` và kiểm tra các request cùng feature/session có bị ảnh hưởng hay không.
- **Mitigation tạm thời:** tắt nguồn retrieval lỗi, dùng fallback context, giảm tải và rollback thay đổi gần nhất nếu lỗi bắt đầu sau deployment/prompt promotion.
- **Owner:** `ai-platform-oncall`

## Alert 3

- **Tên:** AnswerQualityDegraded
- **Severity:** warning
- **Duration:** 10 phút
- **Kênh thông báo:** Slack `#llmops-alerts`
- **SLI/SLO liên quan:** quality proxy trung bình tối thiểu 0.75.
- **Điều kiện và thời gian duy trì:** `quality_score_avg < 0.75` liên tục 10 phút.
- **Ảnh hưởng tới người dùng:** API vẫn phản hồi nhưng câu trả lời ngắn, thiếu context hoặc không bám câu hỏi.
- **Ba bước kiểm tra đầu tiên:**
  1. So sánh quality theo feature và khoảng thời gian với baseline; đồng thời kiểm tra retrieval success và token output.
  2. Lấy correlation ID của các response có quality thấp và xem trace metadata `prompt_name`, `prompt_label`, `prompt_version`.
  3. So sánh candidate với baseline bằng cùng input; kiểm tra version production có vừa được promote hay không.
- **Mitigation tạm thời:** rollback label `production` về prompt baseline đã biết tốt, sau đó chạy lại cùng sample queries để xác nhận quality phục hồi.
- **Owner:** `llm-quality-oncall`
