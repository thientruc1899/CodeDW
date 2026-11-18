# Hướng dẫn chạy `run_all.py` — Pipeline Inform → DW

Script chạy lần lượt 10 job đồng bộ Inform (MariaDB) → Data Warehouse (Postgres).

- Job lỗi → ghi log rồi **chạy tiếp** job sau.
- Mỗi job ghi 1 dòng tóm tắt vào bảng `staging.etl_run_log` (dùng dựng dashboard Power BI).
- Luôn gửi bảng tổng hợp lên **Microsoft Teams** sau mỗi lần chạy.
- Exit code `1` nếu có job FAIL → Task Scheduler báo `0x1`.

---

## 1. Cấu trúc thư mục

```
PROJECT_ROOT/
├── .venv/
├── .env
├── requirements.txt
├── helper/
│   └── teams_notify.py      # hàm send_summary()
├── code/
│   ├── run_all.py
│   ├── sync_inform_ecom_order.py
│   ├── ...                  # các job khác
└── logs/                    # tự tạo khi chạy
    └── pipeline_YYYYMMDD_HHMMSS.log
```

---

## 2. Cài đặt lần đầu

### Windows (CMD)
```cmd
cd C:\duong-dan\PROJECT_ROOT
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Ubuntu
```bash
cd /duong-dan/PROJECT_ROOT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Thư viện tối thiểu cho `run_all.py`: `psycopg2-binary`, `python-dotenv` (các job con cần thêm `pymysql`...).

### File `.env` (đặt ở `PROJECT_ROOT`)
```env
DW_HOST=...
DW_PORT=5432
DW_USER=...
DW_PASSWORD=...
DW_DB=...
# + biến webhook Teams mà helper/teams_notify.py dùng
# + biến kết nối Inform mà các job con dùng
```
> Không commit `.env` lên Git.

---

## 3. Cách chạy

**Luôn đứng ở `PROJECT_ROOT`** rồi bật `.venv` trước.

| Mục đích | Lệnh |
|---|---|
| Mặc định (kéo `LOOKBACK_DAYS` ngày gần nhất, đến hôm qua) | `python code/run_all.py` |
| Chạy 1 ngày | `python code/run_all.py 2026-10-15` |
| Backfill khoảng ngày | `python code/run_all.py 2026-10-01 2026-10-20` |

- Ngày định dạng `YYYY-MM-DD`, múi giờ VN (UTC+7).
- Kéo trùng ngày không sao — bước load final đã dedupe + upsert.

---

## 4. Cấu hình (sửa trong `run_all.py`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `JOBS` | 10 file | Danh sách job, chạy **đúng thứ tự** (order trước, detail sau) |
| `WARN_IF_ZERO_ROWS` | ecom, retail, hrv | Job mà 0 dòng là bất thường → `WARN`. B2B không đưa vào vì có ngày không phát sinh |
| `LOOKBACK_DAYS` | `1` | Số ngày kéo lại mỗi lần. Tăng lên 3 nếu máy hay tắt |
| `JOB_TIMEOUT` | 300s | Quá thời gian → dừng job, tính `FAIL` |
| `LOG_KEEP_DAYS` | 30 | Tự xoá file log cũ hơn |
| `ERROR_TAIL_LINES` | 15 | Số dòng lỗi cuối lưu vào DB |
| `TEAMS_TAIL_LINES` | 12 | Số dòng lỗi cuối đưa lên Teams |
| `TEAMS_MAX_DETAIL` | 5 | Tối đa số job hiện chi tiết trên Teams |

### Thêm job mới
1. Đặt file vào `code/`.
2. Job phải in ra `Rows pulled: N` và `Inserted N rows ...` (đầu dòng) để đếm được số dòng.
3. Thêm tên file vào `JOBS` (đúng vị trí thứ tự). Nếu 0 dòng là bất thường → thêm vào `WARN_IF_ZERO_ROWS`.

---

## 5. Trạng thái job

| Status | Khi nào |
|---|---|
| ✅ `OK` | Exit code 0 |
| ⚠️ `WARN` | Chạy OK nhưng kéo về 0 dòng (chỉ job trong `WARN_IF_ZERO_ROWS`) |
| ❌ `FAIL` | Exit code ≠ 0, không tìm thấy file, hoặc timeout |

Số dòng hiện `?` = output của job không có dòng `Rows pulled` → không đếm được.

---

## 6. Kết quả đầu ra

**File log:** `logs/pipeline_<run_id>.log` — toàn bộ output từng job + bảng SUMMARY.

**Bảng DB `staging.etl_run_log`** (phải tạo sẵn), mỗi job 1 dòng:

| Cột | Nội dung |
|---|---|
| `run_id` | `YYYYMMDD_HHMMSS` — gom các job cùng 1 lần chạy |
| `job`, `status` | Tên file, OK/WARN/FAIL |
| `started_at`, `finished_at`, `duration_s` | Thời gian (giờ VN) |
| `date_from`, `date_to` | Khoảng ngày đã kéo |
| `rows_pulled`, `rows_inserted` | Số dòng (NULL = không biết) |
| `error_tail` | Traceback cuối (FAIL) hoặc ghi chú (WARN) |
| `host` | Tên máy chạy |

Ghi DB lỗi thì pipeline **không dừng**, chỉ in `DB log: failed to write ...`.

**Teams:** bảng tổng hợp + 1 dòng lý do cho mỗi job FAIL/WARN.

---

## 7. Chạy tự động hằng ngày

### Windows — Task Scheduler
**Create Task** →
- **General:** chọn *Run whether user is logged on or not*.
- **Triggers:** Daily, ví dụ 06:00.
- **Actions → Start a program:**
  - Program: `C:\duong-dan\PROJECT_ROOT\.venv\Scripts\python.exe`
  - Arguments: `code\run_all.py`
  - **Start in:** `C:\duong-dan\PROJECT_ROOT` ← bắt buộc, không có thì không đọc được `.env`
- **Settings:** tick *Run task as soon as possible after a scheduled start is missed*.

Kiểm tra: cột **Last Run Result** — `0x0` = OK, `0x1` = có job FAIL.

### Ubuntu — cron
```bash
crontab -e
```
```cron
0 6 * * * cd /duong-dan/PROJECT_ROOT && .venv/bin/python code/run_all.py >> logs/cron.log 2>&1
```
> Cron chạy theo múi giờ server — kiểm tra bằng `timedatectl`, cần `Asia/Ho_Chi_Minh`.

---

## 8. Xử lý lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `ModuleNotFoundError: No module named 'helper'` | Dòng `from helper.teams_notify import ...` đang nằm **trước** đoạn `sys.path.insert(...)`. Chuyển dòng import xuống ngay sau `sys.path.insert` |
| `ModuleNotFoundError: psycopg2 / dotenv` | Chưa bật `.venv` hoặc chưa `pip install -r requirements.txt` |
| `DB log: failed to write` | Sai `DW_*` trong `.env`, hoặc chưa tạo bảng `staging.etl_run_log` |
| `FAIL: file not found` | Tên file trong `JOBS` không khớp thư mục `code/` |
| `TIMEOUT: over 300s` | Khoảng ngày quá dài (backfill) → chia nhỏ khoảng ngày hoặc tăng `JOB_TIMEOUT` |
| Lỗi font/encoding tiếng Việt trên Windows | Script đã ép UTF-8 cho job con; nếu vẫn lỗi ở cửa sổ CMD, chạy `chcp 65001` trước |
| Task Scheduler chạy nhưng không ra gì | Thiếu **Start in** hoặc Program không trỏ vào python trong `.venv` |


## 9.Chạy job riêng lẻ

```
Sync <tên nguồn> từ Inform -> staging.<bảng đích>, rồi nạp sang final.

Run:
    python code/sync_inform_xxx.py                          # hôm qua
    python code/sync_inform_xxx.py 2026-10-15               # 1 ngày
    python code/sync_inform_xxx.py 2026-10-01 2026-10-20    # khoảng ngày


(.venv) C:\Users\PC\Python\Code_Python\200_Data\code> python sync_inform_retail_order.py 2026-10-01 2026-10-20
(.venv) C:\Users\PC\Python\Code_Python\200_Data\code>python sync_inform_retail_detail.py 2026-10-01 2026-10-20


python sync_inform_ecom_order.py 2026-10-01 2026-10-20
python sync_inform_ecom_detail.py 2026-10-06 2026-10-10


```
