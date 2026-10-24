[English](README.md) · **Tiếng Việt** · [日本語](README.ja.md)

# device-e2e

Plugin hỗ trợ kiểm thử tự động (End-to-End Test) ứng dụng mobile trên thiết bị thật từ máy Mac: điều khiển iPhone
qua WebDriverAgent và Android qua adb + uiautomator.

## Cấu trúc thành phần

| Thành phần | Chức năng |
|---|---|
| `agents/device-tester.md` | **Agent thực thi chính:** Đảm nhiệm việc lên kịch bản (test case), điều khiển điện thoại, phân loại nguyên nhân lỗi (do tool hay do app), dọn dẹp sau khi test và xuất báo cáo kết quả (PASS/FAIL/BLOCKED) kèm bằng chứng (evidence). *Lưu ý: Chỉ được phép tự sửa code app nếu brief yêu cầu.* |
| `skills/playbook/` | **Bộ quy trình và tài liệu chuẩn:** Hướng dẫn các bước chạy, cách phân loại lỗi, quy tắc tương tác với thiết bị và cách báo cáo. Đi kèm các tài liệu tham khảo (`references/`): cách thiết kế test case chuẩn, từ điển thuật ngữ định nghĩa rõ các trạng thái (PASS/FAIL/...), tài liệu riêng cho iOS/Android và danh sách các lỗi thường gặp (traps). |
| `skills/playbook/e2e_test_plan.template.md` | **Mẫu kế hoạch kiểm thử (Test Plan):** Định dạng chuẩn để xác định đầu vào, đánh giá rủi ro, ma trận trạng thái/sự kiện, các bước thực thi và ngân sách thời gian cho mỗi case. Bao gồm cả mẫu file báo cáo kết quả và định dạng log lỗi (`BUG-n`). |
| `bin/validate_e2e_plan.py` | **Công cụ xác thực Test Plan:** Chạy độc lập không cần AI model để kiểm tra chéo kế hoạch test. Đảm bảo: mọi yêu cầu (spec) đều được cover (hoặc có lý do bỏ qua rõ ràng), không có case thừa, không bị trống trạng thái và tổng thời gian chạy nằm trong giới hạn. Khi dùng thêm cờ `--results`, tool sẽ đối chiếu file kết quả thực tế với plan (kiểm tra bằng chứng có tồn tại thật không, bug log đã đủ thông tin chưa). |
| `skills/playbook/harness/` | **Bộ điều khiển thiết bị:** Gồm `IosDriver` (gọi HTTP tới WebDriverAgent) và `AndroidDriver` (adb + uiautomator) sử dụng chung một cấu trúc hàm. `evidence.py` đặt tên và lưu file bằng chứng (ảnh chụp, UI tree, logcat hoặc crash report của iOS, quay màn hình Android). Cấu hình linh hoạt qua biến môi trường (`WDA` cho IP của iPhone, `E2E_*` cho các cấu hình khác) và chỉ sử dụng thư viện chuẩn của Python 3. |
| `commands/init.md` | Chứa lệnh `/device-e2e:init` để khởi tạo file cấu hình `.claude/device-e2e/project.md` từ template và liệt kê những thông tin bạn cần điền tiếp. |
| `skills/playbook/project.template.md` | **Mẫu cấu hình dự án:** Nơi khai báo các thông tin agent cần để chạy (thông tin thiết bị, app ID, lệnh build, đường dẫn harness, và cơ chế dọn dẹp dữ liệu). |

## Hướng dẫn cài đặt

1. **Cài đặt Plugin:** Chạy lệnh `claude plugin marketplace add nccong85/device-e2e`, sau đó chạy tiếp
   `claude plugin install device-e2e@device-e2e`. *(Khuyên dùng: Nên cài thêm plugin `review-gate` từ
   [escanner-agent-kit](https://github.com/nccong85/escanner-agent-kit) để có hook bảo vệ, ngăn agent chạy các lệnh
   git làm hỏng dữ liệu).*
2. **Khởi tạo dự án:** Chạy lệnh `/device-e2e:init` trong thư mục dự án. Lệnh này sẽ tạo file cấu hình
   `.claude/device-e2e/project.md` (không ghi đè nếu file đã tồn tại) và nhắc bạn điền các thông tin còn thiếu.
3. **Thiết lập thiết bị thật:**
   - **Với iPhone:** Build WebDriverAgent một lần duy nhất lên máy, bật Developer Mode và UI Automation. Đảm bảo màn
     hình iPhone luôn mở khoá và dùng chung mạng Wi-Fi với máy Mac.
   - **Với Android:** Cắm cáp và đảm bảo máy chạy harness (Mac, Linux hoặc Windows; iOS cần Mac) nhận diện được thiết bị (kiểm tra bằng lệnh `adb devices`).

   Chi tiết: [`ios.md`](skills/playbook/references/ios.md), [`android.md`](skills/playbook/references/android.md).
4. **Viết bộ test:** Viết module app-flows và bộ test dựa trên hai driver. Skill có giải thích cấu trúc.

## Cách sử dụng

### Cơ chế hoạt động

Plugin có ba phần, và Claude Code gọi mỗi phần theo một cách khác nhau:

| Phần | Cách được gọi |
|---|---|
| Skill `playbook` | Claude tự nạp khi câu lệnh khớp với mô tả của skill (test trên máy thật, e2e/regression trên thiết bị, verify fix trên phần cứng…). Gọi thẳng bằng `/device-e2e:playbook`. |
| Agent `device-tester` | Phiên chính giao việc cho agent khi yêu cầu khớp mô tả của nó. Gọi rõ bằng lời ("dùng agent device-tester …") hoặc gõ `@agent-device-e2e:device-tester`. Agent nạp sẵn skill `playbook` khi khởi động. |
| Lệnh `/device-e2e:init` | Chỉ chạy khi bạn gõ lệnh. |

Hai điểm quyết định cách viết yêu cầu:

- **Agent không thấy lịch sử hội thoại.** Nó chạy trong một context riêng, chỉ nhận đoạn brief mà phiên chính viết từ
  yêu cầu của bạn. Mọi thông tin agent cần (spec, plan, nền tảng, ngân sách, việc bạn đã duyệt) phải có trong câu bạn gõ.
- **Agent không hỏi lại bạn được.** Thiếu thông tin hoặc thiếu phê duyệt thì nó dừng với `BLOCKED: …`, phiên chính
  báo lại cho bạn, và bạn gửi yêu cầu tiếp theo.

### Brief

Agent nhận các dòng cố định sau:

```
SPEC: <đường dẫn spec>
PLAN: <đường dẫn plan> | write (MODE: feature | release)
PLAN_APPROVED: <người duyệt, YYYY-MM-DD> | none
BUILD: installed | approved <người duyệt, YYYY-MM-DD>
PLATFORMS: ios, android | ios | android
CASES: all | <các ID>
BUDGET: <số phút dùng máy>
RESULTS: <đường dẫn file kết quả> (mặc định: đường dẫn trong project.md)
```

Thiếu `SPEC`, `PLAN`, `PLATFORMS` hoặc `BUDGET` thì agent dừng với `BLOCKED: brief missing <field>`. Phê duyệt chỉ
tính khi nằm trong brief: dòng *Approved by* trong file plan không được tính.

### Quy trình hai lượt

**Lượt 1: viết plan.** Agent viết plan, chạy `validate_e2e_plan.py` đến khi không còn lỗi, rồi dừng với
`BLOCKED: plan <path> needs owner approval` mà chưa chạm vào máy.

> Dùng agent device-tester: SPEC docs/specs/import_pdf.md, PLAN write (MODE: feature), PLAN_APPROVED none,
> BUILD installed, PLATFORMS ios, android, CASES all, BUDGET 60.

**Duyệt.** Đọc plan (các case, số phút máy, mục *Not covered*), sửa nếu cần.

**Lượt 2: chạy.** Agent chạy `READY` → `DRY` → các case theo thứ tự → `EXPLORE` (nếu có trong plan) → `DIAG`, phân loại mọi FAIL (lỗi harness thì tự
sửa và chạy lại, lỗi app thì gom bằng chứng), dọn dẹp và ghi file kết quả: một test completion report theo
ISTQB / ISO/IEC/IEEE 29119-3 (kết luận go/no-go so với exit criteria của plan, số liệu, kết quả, lỗi, sai lệch so
với plan, rủi ro còn lại, bài học).

> Dùng agent device-tester: SPEC docs/specs/import_pdf.md, PLAN test/e2e/import_pdf_plan.md,
> PLAN_APPROVED nccong 2026-10-24, BUILD installed, PLATFORMS ios, android, CASES all, BUDGET 60.

Agent kết thúc bằng năm dòng:

```
E2E: ios pass=<n> fail=<n> blocked=<n> not_run=<n> · android pass=<n> fail=<n> blocked=<n> not_run=<n>
VERDICT: <go | no-go | go with risks>: <lý do>
APP_BUGS: <none | BUG-n mức độ ưu tiên tiêu đề>
BLOCKERS: <none | điều đã chặn case hoặc lượt chạy>
REPORT: <đường dẫn file kết quả>
```

Các yêu cầu thường gặp khác: chỉ chạy lại case lỗi (`CASES: E3, E7`), chỉ một nền tảng (`PLATFORMS: android`), cho
phép build lại (`BUILD: approved nccong 2026-10-24`, dùng lệnh build trong `project.md`).

Có thể nói ngắn, ví dụ "test import PDF trên hai điện thoại thật, spec ở docs/specs/import_pdf.md, 60 phút". Phiên
chính sẽ tự dựng brief, nhưng dòng nào thiếu thì agent sẽ báo `BLOCKED`.

## Những việc nó sẽ không làm

- Build hoặc cài lại app, trừ khi brief ghi rằng chủ dự án đã đồng ý. Gỡ app sẽ xóa sạch dữ liệu app.
- Dùng `xcodebuild test` hoặc `flutter drive` trên điện thoại có dữ liệu quan trọng.
- Báo PASS khi không có bằng chứng đọc từ thiết bị, hoặc cho case mà điều kiện tiên quyết chưa được chứng minh.
- Chạy trên thiết bị khi chủ dự án chưa duyệt test plan, hoặc bỏ một case đã lên plan khỏi kết quả.
