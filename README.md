# K4-L3A — Lab Day 13: Monitoring & LLMOps

> - **Loại repository:** bài nộp cá nhân dựa trên starter của lớp K4-L3A
> - **Hình thức làm bài:** cá nhân
> - **Thời gian trên lớp:** 14:00–18:00 (240 phút)
> - **Deadline mặc định:** 23:59:59 trong ngày học, múi giờ Asia/Ho_Chi_Minh

Bạn sẽ biến một AI API “hộp đen” thành hệ thống có thể trả lời ba câu hỏi: **hệ thống có vấn đề gì, request nào bị ảnh hưởng và bước nào là nguyên nhân**. Quy trình điều tra đúng theo slide là **Metrics → Logs → Traces**:

1. Metrics cho biết triệu chứng và khoảng thời gian.
2. Logs giúp tìm request cụ thể qua `correlation_id`.
3. Trace của request đó cho biết span nào chậm hoặc lỗi.

Repo dùng fake LLM nên không cần API key mô hình trả phí. Mỗi học viên tự tạo một project Langfuse riêng để quan sát trace và quản lý prompt version; không dùng project/key dùng chung.

## Trạng thái bài làm cá nhân

<!-- TODO (documentation - completed): Đồng bộ báo cáo, evidence index và
hướng dẫn chạy lại. Không đánh dấu submission hoàn thành khi UI/Git còn pending. -->

Nguyễn Quốc Cường — MSSV **2A202602886**, project Langfuse
`day13-k4-l3a-2A202602886`. CP1 đã hoàn thiện logging/PII; CP2 có child
observations, managed prompt v1/v2, dashboard runtime, SLO và alert/runbook;
CP3 đã đo baseline/incident/recovery trên challenge gốc và nối metric → log
→ trace. Kiểm tra mới nhất: **41 tests passed, log 100/100, dashboard 6/6**.

- [Báo cáo và trạng thái nộp](submission/REPORT.md).
- [Evidence index](submission/evidence/README.md) và
  [output kiểm tra worktree mới nhất](submission/evidence/pre-submission-validation.txt).
- [Dashboard runtime và giới hạn số đo](docs/DASHBOARD_SETUP.md).
- [Prompt versioning và rollback](docs/PROMPT_VERSIONING.md).
- [Checklist evidence, hướng dẫn hoàn thiện ảnh incident](docs/grading-evidence.md).

Còn phải che public key trong ảnh 08a/08b, hoàn thiện tên span/correlation ID
trong ảnh 14, chốt commit/push và nộp URL/SHA. Hướng dẫn checkpoint bên dưới
giữ lại để tái hiện, không có nghĩa source vẫn là starter chưa hoàn thiện.

## Kết quả cần đạt

Sau lab, bạn có thể:

- tạo structured log dạng JSON, truyền correlation ID và che PII trước khi ghi log;
- đo latency P50/P95/P99, TTFT, traffic, error, token, cost, retrieval success và quality proxy;
- tạo ít nhất 10 traces trên Langfuse, có span tree đọc được và metadata không chứa PII;
- liên kết trace với prompt name/label/version và chứng minh được một lần rollback;
- dựng dashboard 6 panel, định nghĩa một SLO cùng error budget và ba alert có runbook;
- viết incident note có chuỗi bằng chứng metric → log → trace.

## Sản phẩm phải nộp

- Source đã hoàn thiện các `TODO` bắt buộc.
- `submission/REPORT.md` đã điền và evidence đặt trong `submission/evidence/`.
- Kết quả tests, log validator và dashboard validator trên commit cuối.
- Ảnh dashboard có dữ liệu; ít nhất 10 trace IDs; một trace waterfall; prompt v1/v2 và evidence rollback.
- Một SLO/error budget, ba alert symptom-based có `duration`, kênh Slack và runbook.

## Bắt đầu nhanh

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Chỉ copy `.env.example` khi chưa có `.env`; không ghi đè file đang chứa cấu
hình cá nhân. Với workspace đã có venv, có thể chạy API bằng
`.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file .env`.

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Tự đăng ký/đăng nhập [Langfuse Cloud](https://cloud.langfuse.com), tạo project riêng tên `day13-k4-l3a-<MSSV>`, rồi vào **Project Settings → API Keys** để tạo key pair. Điền key của chính project đó vào `.env`:

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_PROMPT_NAME=day13-chat
LANGFUSE_PROMPT_LABEL=production
```

Không chia sẻ key và không chụp màn hình trang hiển thị secret. Xem các bước chi tiết tại [docs/SETUP.md](docs/SETUP.md).

> **Phân biệt evidence:** structured logs nằm ở terminal/`data/logs.jsonl`; Langfuse hiển thị traces/observations và prompt versions. Học viên phải tự chạy workload, tự tạo cả log lẫn trace rồi chụp evidence của mình.

Chạy API ở terminal thứ nhất:

```bash
uvicorn app.main:app --reload --env-file .env
```

Chạy baseline ở terminal thứ hai:

```bash
python scripts/load_test.py
python scripts/validate_logs.py
python scripts/validate_dashboard.py
python -m pytest -q
```

Với starter chưa sửa, baseline có thể chưa đạt vì các TODO CP1 còn trống.
Trong bản cá nhân hiện tại CP1 đã hoàn thiện; output cũ vẫn được giữ riêng
để đối chiếu, không ghi đè hoặc gán thành kết quả trên commit nộp mới.

Dashboard runtime: mở `http://127.0.0.1:8000/dashboard`; snapshot JSON tại
`http://127.0.0.1:8000/dashboard/data`. Time range 60 phút và refresh 30 giây.
Traces và prompt versions xem trên Langfuse, không gọi trace UI là log JSONL.

## Lộ trình 14:00–18:00 (240 phút)

| Mốc | Thời gian | Việc chính | Hoàn thành khi |
|---|---:|---|---|
| CP0 | 14:00–14:30 (0–30 phút) | Setup, chạy API và baseline | `/health` trả `ok: true`, log được tạo |
| CP1 | 14:30–15:20 (30–80 phút) | Correlation ID, structured log, PII | `validate_logs.py` đạt ít nhất 80/100 |
| CP2 | 15:20–16:40 (80–160 phút) | Trace, prompt, dashboard, SLO/alert | có span tree; dashboard validator đạt 6/6 |
| CP3 | 16:40–17:30 (160–210 phút) | Điều tra challenge K4-L3A | có metric, log và trace cùng một request |
| CP4 | 17:30–18:00 (210–240 phút) | Report, evidence và kiểm tra cuối | tests/validators chạy xong trên commit nộp |

Chi tiết từng checkpoint nằm trong [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md).

## Các phần cần làm

### CP1 — Logging và PII

- `app/middleware.py`: xóa context cũ; nhận `x-request-id` hoặc sinh `req-<8-hex>`; bind ID; trả ID và response time trong header.
- `app/main.py`: bind `user_id_hash`, `session_id`, `feature`, `model`, `env` trước log `request_received`.
- `app/logging_config.py`: chạy PII scrubber trước bước ghi file/render JSON.
- `app/pii.py`: hoàn thiện pattern và tests cho email, điện thoại Việt Nam, CCCD và thẻ thanh toán.

`validate_logs.py` đọc toàn bộ `data/logs.jsonl`. Sau khi lưu baseline, hãy xóa hoặc đổi tên log cũ, khởi động lại API rồi đo lại để không bị tính các dòng chưa scrub.

### CP2 — Tracing, prompt và dashboard

Starter dùng Langfuse Python SDK v4 và mới tạo root observation cho `LabAgent.run`. Bạn cần thêm child observation cho:

- retrieval: loại `retriever` hoặc `span`;
- LLM call: loại `generation`, có model, prompt, `input_tokens`, `output_tokens` và cost.

Không capture raw prompt/output chứa PII. Correlation ID phải xuất hiện trong trace metadata để nối trace với log.

Dashboard dùng `data/logs.jsonl` làm nguồn chuẩn và giữ đúng 6 panel trong `config/dashboard.yaml`. Panel latency phải có P50/P95/P99 và TTFT; panel errors phải thể hiện cả retrieval success. Sau đó hoàn thiện:

- `config/slo.yaml`: giải thích hoặc điều chỉnh SLO, tính error budget;
- `config/alert_rules.yaml`: ba alert symptom-based, có duration, severity, owner, Slack channel và runbook;
- `docs/alerts.md`: cách kiểm tra và mitigation cho từng alert.

### CP3 — Challenge chính thức

Chỉ chạy khi Lab Coach thông báo mở challenge của K4-L3A. Tại CP3, Lab Coach gửi riêng file đúng lớp; lưu file đó tại `config/challenge.json`. File này đã được `.gitignore` và **không được** force-add/commit/push:

```bash
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
```

Điều tra theo thứ tự:

1. Xem dashboard để xác định metric xấu và khoảng thời gian.
2. Lọc `data/logs.jsonl`, lấy một `correlation_id` của request bất thường.
3. Tìm trace có cùng `correlation_id`, rồi so sánh các span.
4. Ghi root cause, fix action và preventive measure vào `submission/REPORT.md`.

Không tự tạo, sửa, chia sẻ hoặc lấy `config/challenge.json` từ lớp khác. Nếu chưa nhận file riêng, tiếp tục practice bằng tham số `--scenario`; không chạy challenge chính thức.

## Kiểm tra trước khi nộp

```bash
python -m pytest -q
python scripts/validate_logs.py
python scripts/validate_dashboard.py
git status --short
git log -1 --oneline
```

- [ ] Không có `.env`, secret, `.venv/`, PII thô hoặc evidence của học viên/lớp khác.
- [ ] `submission/REPORT.md` đã đủ; mọi ảnh dùng đường dẫn tương đối và mở được.
- [ ] Bạn demo và giải thích được luồng Metrics → Logs → Traces → Root cause.

## Tên repo bài nộp

Starter gốc là `K4-L3A-Day13-Monitoring-LLMOps`; repository hiện tại là bài
nộp cá nhân, dùng mẫu:

```text
K4-L3-DAY13-HoVaTen-MSSV-Monitoring-LLMOps
```

Ví dụ: `K4-L3-DAY13-NguyenVanAn-123456-Monitoring-LLMOps`. Mỗi học viên nộp URL repo cá nhân và commit SHA cuối trên VLearn LMS/Codelabs. Xem đầy đủ tại [docs/SUBMISSION.md](docs/SUBMISSION.md).

Không push bài làm trực tiếp lên repo đề bài và không dùng chung repo bài nộp với học viên khác.

## Tài liệu trong repo

- [SETUP.md](docs/SETUP.md): cài đặt và xử lý lỗi môi trường.
- [CHECKPOINTS.md](docs/CHECKPOINTS.md): đầu ra và cách tự kiểm tra từng mốc.
- [GUIDE.md](docs/GUIDE.md): gợi ý kỹ thuật khi bị kẹt.
- [PROMPT_VERSIONING.md](docs/PROMPT_VERSIONING.md): prompt v1/v2, label và rollback.
- [DASHBOARD_SETUP.md](docs/DASHBOARD_SETUP.md): mapping dữ liệu cho 6 panel.
- [RUBRIC.md](docs/RUBRIC.md), [RULES.md](docs/RULES.md), [SUBMISSION.md](docs/SUBMISSION.md): cách chấm, quy định và cách nộp.
- [grading-evidence.md](docs/grading-evidence.md): checklist nhanh các ảnh/output cần thu thập.
- [REPORT.md](submission/REPORT.md): báo cáo cá nhân duy nhất cần hoàn thiện.
