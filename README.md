# 📚 HTML Test Bank Manager

**HTML Test Bank Manager** là ứng dụng desktop viết bằng Python (PyQt6) giúp quản lý, chỉnh sửa và tạo mới các file HTML bài tập trắc nghiệm tương tác độc lập. 

Chương trình cho phép biên tập danh mục môn học, bài học và ngân hàng câu hỏi đa dạng loại hình (trắc nghiệm đơn, trắc nghiệm nhiều đáp án, kéo thả, đúng/sai, điền từ) và xuất trực tiếp ra file HTML có thể chạy ngay trên mọi trình duyệt web/thiết bị mà không cần máy chủ.

Giao diện của file HTML Test Bank được thiết kế theo phong cách hiện đại, trực quan và hỗ trợ tương thích tốt trên cả thiết bị di động lẫn máy tính (Responsive Design). Ngoài ra, chức năng tìm kiếm được tích hợp ngay tại trang chủ giúp hỗ trợ tra cứu nhanh câu hỏi và đáp án.

---

## 🚀 Tính năng chính

- **Quản lý file HTML linh hoạt**: Tải, chỉnh sửa trực tiếp dữ liệu `const DATA` và các thẻ `<title>`, `<div class="header"><p>` trong file HTML mà không làm hỏng cấu trúc giao diện web.
- **Hỗ trợ 5 loại câu hỏi trắc nghiệm**:
  1. **Single Choice (single)**: Lựa chọn 1 đáp án đúng.
  2. **Multiple Choice (multi)**: Chọn nhiều đáp án đúng (tùy chỉnh số lượng đáp án bắt buộc).
  3. **Drag & Drop (drag)**: Kéo thả các thẻ tương ứng vào vị trí đúng.
  4. **True / False (truefalse)**: Câu hỏi Đúng/Sai dạng nhiều phát biểu.
  5. **Fill in the blank (fill)**: Điền vào chỗ trống (hỗ trợ nhiều đáp án chấp nhận cách nhau bằng dấu phẩy).
- **Trình chỉnh sửa JSON nâng cao**: Cho phép xem và can thiệp trực tiếp cấu trúc JSON của từng câu hỏi.
- **Giao diện người dùng trực quan**:
  - Tùy chỉnh kích thước font chữ toàn ứng dụng.
  - Cấu hình danh mục dạng cây (**Học phần / Bài học**).
  - Tìm kiếm câu hỏi/đáp án và xem lại kết quả tức thì trên giao diện web được tạo.

---

## 📁 Cấu trúc dự án

Dưới đây là sơ đồ cấu trúc các thư mục và tập tin chính trong dự án:

```text
HTML-Test-Bank-Manager-VN/
├── image.ico             # Biểu tượng icon ứng dụng
├── main.py               # Mã nguồn ứng dụng 
└── README.md             # Hướng dẫn sử dụng
```

---

## 🛠️ Yêu cầu hệ thống & Cài đặt

### 1. Yêu cầu môi trường

* **Python:** Phiên bản `3.8` trở lên.
* **Hệ điều hành:** Windows, macOS, hoặc Linux.

### 2. Cài đặt các thư viện cần thiết

Cài đặt các gói phụ thuộc qua `pip`:

```bash
pip install PyQt6 beautifulsoup4
```

---

## 📖 Hướng dẫn sử dụng chi tiết

### 0. Chạy ứng dụng từ mã nguồn Python

Mở Terminal / Command Prompt tại thư mục dự án và chạy:

```bash
python main.py
```

### 1. Thao tác File

* **✨ Tạo Mới File HTML Test**: Khởi tạo một file HTML trắc nghiệm hoàn chỉnh mới dựa trên template mẫu có sẵn.
* **📂 Mở File HTML Test**: Chọn và nạp dữ liệu từ một file HTML bài tập đã tồn tại.
* **💾 Lưu File HTML Test**: Cập nhật toàn bộ chỉnh sửa về câu hỏi và tiêu đề vào file HTML.

### 2. Quản lý Cấu trúc Học phần & Bài học

* Ở bảng bên trái (**Cấu trúc Học phần / Bài học**):
* Bấm **+ Học Phần** để thêm môn học/học phần mới (ví dụ: *Triết học Mác-Lênin*).
* Bấm **+ Bài Học** để thêm chương/bài học mới thuộc học phần đang chọn.
* Bấm **- Xóa** để xóa học phần hoặc bài học được chọn.

### 3. Biên tập Câu hỏi

* Chọn bài học tương ứng trên cây cấu trúc, danh sách câu hỏi sẽ hiển thị ở bảng bên phải.
* Bấm **Thêm câu hỏi** hoặc chọn một câu hỏi và bấm **Sửa câu hỏi**:
1. Chọn **Loại câu hỏi** phù hợp.
2. Nhập **Nội dung câu hỏi**.
3. Điền thông tin chi tiết cho từng loại đáp án (thêm/xóa phương án linh hoạt).
4. Bấm **⚙️ Cấu hình JSON nâng cao** để kiểm tra hoặc bổ sung trường dữ liệu tùy biến.
5. Bấm **OK** để lưu câu hỏi.

---

## 📦 Đóng gói ứng dụng thành file thực thi (.EXE)

Bạn có thể đóng gói ứng dụng thành file `.exe` chạy độc lập bằng **PyInstaller**:

1. Cài đặt PyInstaller:
```bash
pip install pyinstaller
```

2. Chạy lệnh đóng gói (kèm file icon `image.ico`):
```bash
pyinstaller --noconsole --onefile --add-data "image.ico;." --icon=image.ico main.py
```

3. File thực thi sẽ nằm trong thư mục `dist/main.exe`.

---

## 📋 Cấu trúc dữ liệu JSON (`const DATA`)

Dữ liệu trắc nghiệm được bóc tách và lưu trữ bên trong thẻ `<script>` của file HTML dưới dạng biến `const DATA`:

```json
{
  "tenMonHoc": {
    "name": "TÊN MÔN HỌC / HỌC PHẦN",
    "topics": {
      "1": {
        "name": "BÀI 1: TÊN BÀI HỌC",
        "questions": [
          {
            "type": "single",
            "text": "Nội dung câu hỏi 1 lựa chọn?",
            "opts": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
            "correct": 0
          },
          {
            "type": "multi",
            "text": "Nội dung câu hỏi chọn nhiều đáp án?",
            "opts": ["Lựa chọn 1", "Lựa chọn 2", "Lựa chọn 3"],
            "correct": [0, 1],
            "required": 2
          }
        ]
      }
    }
  }
}
```

---

## 📝 Giấy phép (License)

Dự án được phát hành dưới mã nguồn tự do, phục vụ mục đích giáo dục và học tập.
