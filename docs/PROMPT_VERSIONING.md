# Prompt versioning cơ bản

Mục tiêu của phần này là biết một request đã dùng prompt nào và có thể rollback an toàn. Đây không phải bài tối ưu prompt hoặc A/B testing.

## Prompt contract

Trong project Langfuse cá nhân `day13-k4-l3a-<MSSV>`, tạo text prompt tên `day13-chat`. Prompt phải giữ ba biến:

```text
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

App lấy prompt theo hai biến môi trường:

```dotenv
LANGFUSE_PROMPT_NAME=day13-chat
LANGFUSE_PROMPT_LABEL=production
```

Nếu Langfuse không khả dụng, app dùng template local và trace metadata ghi `prompt_source=local` hoặc `local-fallback` thay vì giả vờ đã lấy được prompt managed.

## Việc cần làm

1. Tạo version 1, gắn labels `baseline` và `production`.
2. Tạo version 2 với một thay đổi nhỏ về format hoặc độ dài câu trả lời, gắn label `candidate`.
3. Chạy cùng một input với `LANGFUSE_PROMPT_LABEL=baseline` và `candidate`.
4. Mở hai trace, kiểm tra `prompt_name`, `prompt_label`, `prompt_version` và prompt link.
5. Chuyển label `production` sang version 2, chạy lại một request.
6. Rollback `production` về version 1 và lưu ảnh evidence.

Không chấm prompt nào “hay hơn”. Điểm nằm ở khả năng truy xuất version, đổi label và rollback có bằng chứng.

## Evidence

- Một ảnh danh sách hai prompt version.
- Hai trace ID chứng minh hai version/label khác nhau.
- Một ảnh trước/sau khi đổi label hoặc rollback `production`.
- Ghi các ID và đường dẫn ảnh vào `submission/REPORT.md`.

## Triển khai trong repository cá nhân

<!-- TODO (CP2 prompt - completed): Đã có v1/v2, workload so sánh,
promote/rollback và ảnh 09/10. Giữ hướng dẫn để có thể tái hiện.
TODO (optional evidence): Nếu tạo trace mới, ghi ID thật; không sửa ID lịch sử. -->

Project cá nhân là `day13-k4-l3a-2A202602886`. V1 giữ template phía trên;
v2 thêm chỉ dẫn `Answer concisely using only the supplied documents.` và
giữ đủ ba biến. Trạng thái cuối đã chụp: v1 có `baseline`/`production`, v2
có `candidate` (có thể hiện thêm label tự động `latest`).

- [Ảnh versions 09](../submission/evidence/09-prompt-versions.png).
- [Ảnh production v2](../submission/evidence/10a-production-v2.png).
- [Ảnh rollback production v1](../submission/evidence/10b-production-v1-rollback.png).
- [Bảng trace IDs/labels/versions đã lưu](../submission/REPORT.md#5-tracing-và-prompt-versioning).

Ảnh UI được chụp bổ sung sau lượt kiểm chứng trace ban đầu; không coi chúng
là cùng một lần chạy nếu chưa có ID/thời gian đối chiếu.

## Lệnh đọc lại và tái hiện

Chạy từ root repo trong PowerShell, dùng `.env` của đúng project cá nhân.
Lệnh status chỉ đọc; không cần chạy lại promote/rollback chỉ để hoàn thiện
tài liệu hoặc chụp trace lịch sử:

```powershell
.\.venv\Scripts\python.exe scripts\manage_prompts.py status
```

Nếu cần tái hiện so sánh, script bên dưới chạy cùng một input giả không chứa
PII cho cả hai labels. Nó warm managed prompt bằng timeout dài hơn rồi flush
trace; không yêu cầu đổi label trong API đang chạy:

```powershell
$baselineId = "req-" + [guid]::NewGuid().ToString("N").Substring(0, 8)
$candidateId = "req-" + [guid]::NewGuid().ToString("N").Substring(0, 8)

.\.venv\Scripts\python.exe scripts\trace_prompt_version.py --label baseline --correlation-id $baselineId
.\.venv\Scripts\python.exe scripts\trace_prompt_version.py --label candidate --correlation-id $candidateId
.\.venv\Scripts\python.exe scripts\verify_langfuse_traces.py --summary-only $baselineId $candidateId
```

Mở từng generation trên UI; kiểm tra tên prompt `day13-chat`,
`prompt_source=langfuse`, label, version, prompt link, model, token và cost.
Copy trace ID thật vào report nếu cần thêm một lượt kiểm chứng mới.

Verifier CP2 hiện chỉ đọc tối đa 100 observations trong 120 phút gần nhất,
không phải phép đếm toàn project. Kiểm tra số `Matching root traces` và
`Valid root/retrieval/generation trees` khớp các request vừa tạo; exit code 0
không tự chứng minh đã tìm đủ traces. Nếu workload nhiều hoặc trace cũ nằm
ngoài cửa sổ, đối chiếu UI/API có phân trang; collector CP3 đã dùng cách này
cho 15 measured traces trong export lịch sử.

Chỉ chạy chu kỳ sau khi chủ repo muốn thay đổi production trong project lab.
Không tạo thêm prompt version để chụp; hoàn thành rollback ngay sau bước
promote và luôn kiểm tra trạng thái cuối:

```powershell
.\.venv\Scripts\python.exe scripts\manage_prompts.py promote
.\.venv\Scripts\python.exe scripts\manage_prompts.py status
# Chụp UI production=v2; có thể tạo một trace --label production để kiểm chứng.

.\.venv\Scripts\python.exe scripts\manage_prompts.py rollback
.\.venv\Scripts\python.exe scripts\manage_prompts.py status
# Chụp UI production=v1; giữ baseline=v1, candidate=v2.
```

Nếu lệnh promote/status lỗi, kiểm tra trạng thái thật trước khi tiếp tục;
không kết luận đã rollback chỉ từ việc đã gõ lệnh.

## Đọc đúng metadata và bảo vệ ảnh

- `prompt_source=local`: chưa bật cấu hình managed prompt/tracing phù hợp.
- `prompt_source=local-fallback`: fetch prompt lỗi; kiểm tra key của đúng
  project, base URL, prompt name/label và khởi động lại API nếu đã đổi `.env`.
- `input=null`/`output=undefined`: chủ ý không capture payload thô. Managed
  prompt được liên kết qua prompt link và metadata thay vì gửi raw prompt.
- 08a/08b hiện có metadata/usage nhưng còn giá trị `scope.attributes.public_key`;
  che toàn bộ giá trị hoặc chụp lại, không che các trường dùng để chấm.
- Model usage/cost trong lab do fake LLM mô phỏng, không phải hóa đơn thực
  của một provider. Không sửa số token/cost trong ảnh để làm khớp report.
