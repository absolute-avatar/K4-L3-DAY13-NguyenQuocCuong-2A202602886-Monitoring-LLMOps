# Tài liệu Day 13 Monitoring & LLMOps

Thư mục này gom tài liệu hướng dẫn và quy định của bài lab cá nhân.
[README ở root](../README.md) là điểm bắt đầu; kết quả và trạng thái nộp
thực tế nằm tại [báo cáo cá nhân](../submission/REPORT.md) và
[evidence index](../submission/evidence/README.md).

<!-- TODO (docs navigation - completed): Đồng bộ link tài liệu với file đang
tồn tại; hướng dẫn CP3 được gộp vào grading-evidence.md, không khôi phục file đã xóa. -->

## Đọc nhanh bản đã triển khai

- [Kết quả kiểm tra mới nhất](../submission/evidence/pre-submission-validation.txt):
  41 tests passed, log 100/100, dashboard 6/6 trên worktree hiện tại.
- [Prompt versions/rollback](PROMPT_VERSIONING.md): script tái hiện và ảnh 09/10.
- [Dashboard runtime](DASHBOARD_SETUP.md): sáu panel và cách diễn giải SLO.
- [Incident evidence](grading-evidence.md#evidence-cp3-đã-lưu-và-cách-hoàn-thiện-ảnh-14):
  metric/log đã có; cách bổ sung tên span/correlation ID vào ảnh 14.
- Còn pending: che public key trong ảnh 08, hoàn thiện ảnh 14, chốt commit
  và nộp URL/SHA. Không coi hoàn thiện tài liệu là hoàn tất submission.

## Tiến trình và quy định

- [SETUP.md](SETUP.md): cài đặt, Langfuse và smoke test.
- [CHECKPOINTS.md](CHECKPOINTS.md): timeline 14:00–18:00 (240 phút) và tín hiệu hoàn thành.
- [RUBRIC.md](RUBRIC.md): tiêu chí, điểm và evidence.
- [RULES.md](RULES.md): AI policy, bảo mật, challenge và deadline.
- [SUBMISSION.md](SUBMISSION.md): tên repo, cấu trúc, danh sách evidence, báo cáo và checklist nộp bài.

## Hướng dẫn kỹ thuật

- [GUIDE.md](GUIDE.md): gỡ lỗi theo từng lớp tín hiệu.
- [PROMPT_VERSIONING.md](PROMPT_VERSIONING.md): prompt version, label và rollback.
- [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md): dựng dashboard từ log contract.
- [dashboard-spec.md](dashboard-spec.md): yêu cầu trình bày sáu panel.
- [alerts.md](alerts.md): ba runbook đã điền và giới hạn bằng chứng alert/Slack.
- [blueprint-template.md](blueprint-template.md): khung thiết kế observability.
- [grading-evidence.md](grading-evidence.md): checklist nhanh khi thu thập evidence.
- [mock-debug-qa.md](mock-debug-qa.md): câu hỏi tự kiểm tra trước demo.
