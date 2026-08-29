import os
import json
import re
import sys
from bs4 import BeautifulSoup
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

def resource_path(relative_path):
    """ Lấy đường dẫn tuyệt đối tới tài nguyên, hoạt động cho cả lúc code và lúc chạy file EXE """
    try:
        # PyInstaller tạo một thư mục tạm và lưu đường dẫn trong _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class HTMLEditorBackend:
    """Xử lý đọc/ghi file HTML và bóc tách biến const DATA."""

    def __init__(self):
        self.file_path = ""
        self.data = {}
        self.site_title = ""
        self.header_p = ""

    def load_file(self, file_path):
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Bóc tách <title> và <div class="header"><p> bằng BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        title_tag = soup.find('title')
        self.site_title = title_tag.string.strip() if title_tag and title_tag.string else ""
        header_p_tag = soup.select_one('div.header p')
        self.header_p = header_p_tag.string.strip() if header_p_tag and header_p_tag.string else ""    

        match = re.search(
            r"const\s+DATA\s*=\s*(\{[\s\S]*?\});\s*(?:let|var|const|function|\n)",
            content,
        )
        if not match:
            raise ValueError(
                "Không tìm thấy biến `const DATA` trong file HTML!"
            )

        json_str = match.group(1)
        json_str_clean = re.sub(r"//.*$", "", json_str, flags=re.MULTILINE)
        json_str_clean = re.sub(
            r"([{,]\s*)([a-zA-Z0-9_]+)\s*:", r'\1"\2":', json_str_clean
        )
        json_str_clean = re.sub(r",\s*([\]}])", r"\1", json_str_clean)

        self.data = json.loads(json_str_clean)

    def save_file(self, file_path=None):
        target_path = file_path or self.file_path
        if not target_path:
            return False

        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Cập nhật các thẻ HTML bằng BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        if soup.find('title'):
            soup.find('title').string = self.site_title
            
        header_p_tag = soup.select_one('div.header p')
        if header_p_tag:
            header_p_tag.string = self.header_p

        content = str(soup)
        
        formatted_data = json.dumps(self.data, ensure_ascii=False, indent=4)
        new_content = re.sub(
            r"(const\s+DATA\s*=\s*)\{[\s\S]*?\n\s*\};",
            f"\\1{formatted_data};",
            content,
        )

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True


class QuestionDialog(QDialog):
    """Hộp thoại chỉnh sửa câu hỏi thông minh linh hoạt theo loại."""

    def __init__(self, parent=None, question_data=None):
        super().__init__(parent)
        self.setWindowTitle("Chỉnh sửa câu hỏi")
        self.resize(750, 650)
        self.question_data = question_data or {}

        if parent:
            self.setFont(parent.font())

        self.init_ui()
        self.load_question_data()

        self.type_combo.currentIndexChanged.connect(self.on_type_changed)

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        top_form = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(
            [
                "Single Choice (single)",
                "Multiple Choice (multi)",
                "Drag & Drop (drag)",
                "True / False (truefalse)",
                "Fill in the blank (fill)",
            ]
        )

        self.txt_text = QTextEdit()
        self.txt_text.setMaximumHeight(80)
        self.txt_text.setPlaceholderText("Nhập nội dung câu hỏi...")

        top_form.addRow("Loại câu hỏi:", self.type_combo)
        top_form.addRow("Nội dung:", self.txt_text)
        main_layout.addLayout(top_form)

        self.stack = QStackedWidget()

        self.page_single = self.create_single_ui()
        self.page_multi = self.create_multi_ui()
        self.page_drag = self.create_drag_ui()
        self.page_truefalse = self.create_truefalse_ui()
        self.page_fill = self.create_fill_ui()

        self.stack.addWidget(self.page_single)     # Index 0
        self.stack.addWidget(self.page_multi)      # Index 1
        self.stack.addWidget(self.page_drag)       # Index 2
        self.stack.addWidget(self.page_truefalse)  # Index 3
        self.stack.addWidget(self.page_fill)       # Index 4

        main_layout.addWidget(self.stack)

        self.btn_toggle_json = QPushButton("⚙️ Cấu hình JSON nâng cao")
        self.btn_toggle_json.setCheckable(True)
        self.btn_toggle_json.toggled.connect(self.toggle_json_view)
        main_layout.addWidget(self.btn_toggle_json)

        self.txt_raw_json = QTextEdit()
        self.txt_raw_json.setPlaceholderText("JSON tùy biến thêm...")
        self.txt_raw_json.setVisible(False)
        self.txt_raw_json.setMaximumHeight(90)
        main_layout.addWidget(self.txt_raw_json)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    # --- TẠO GIAO DIỆN CHO TỪNG LOẠI ---

    def create_single_ui(self):
        widget = QGroupBox("Cấu hình Lựa chọn Đơn (Single Choice)")
        layout = QVBoxLayout(widget)
        self.single_list_layout = QVBoxLayout()
        self.single_scroll_content = QWidget()
        self.single_scroll_content.setLayout(self.single_list_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.single_scroll_content)
        layout.addWidget(scroll)

        btn_add = QPushButton("+ Thêm đáp án")
        btn_add.clicked.connect(lambda: self.add_single_row())
        layout.addWidget(btn_add)
        return widget

    def create_multi_ui(self):
        widget = QGroupBox("Cấu hình Lựa chọn Nhiều (Multiple Choice)")
        layout = QVBoxLayout(widget)

        req_layout = QHBoxLayout()
        req_layout.addWidget(QLabel("Số lượng đáp án bắt buộc chọn (required):"))
        self.spin_required = QSpinBox()
        self.spin_required.setRange(1, 10)
        self.spin_required.setValue(2)
        req_layout.addWidget(self.spin_required)
        req_layout.addStretch()
        layout.addLayout(req_layout)

        self.multi_list_layout = QVBoxLayout()
        self.multi_scroll_content = QWidget()
        self.multi_scroll_content.setLayout(self.multi_list_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.multi_scroll_content)
        layout.addWidget(scroll)

        btn_add = QPushButton("+ Thêm đáp án")
        btn_add.clicked.connect(lambda: self.add_multi_row())
        layout.addWidget(btn_add)
        return widget

    def create_drag_ui(self):
        widget = QGroupBox("Cấu hình Kéo thả (Drag & Drop)")
        layout = QVBoxLayout(widget)

        lbl_opts = QLabel("<b>1. Các Thẻ kéo (Draggables):</b>")
        self.drag_opts_layout = QVBoxLayout()
        btn_add_opt = QPushButton("+ Thêm thẻ kéo")
        btn_add_opt.clicked.connect(lambda: self.add_drag_opt_row())

        lbl_items = QLabel("<b>2. Các Câu hỏi/Vị trí nhỏ (Items & Matches):</b>")
        self.drag_items_layout = QVBoxLayout()
        btn_add_item = QPushButton("+ Thêm vị trí thả")
        btn_add_item.clicked.connect(lambda: self.add_drag_item_row())

        self.drag_scroll_content = QWidget()
        s_layout = QVBoxLayout(self.drag_scroll_content)
        s_layout.addWidget(lbl_opts)
        s_layout.addLayout(self.drag_opts_layout)
        s_layout.addWidget(btn_add_opt)
        s_layout.addSpacing(15)
        s_layout.addWidget(lbl_items)
        s_layout.addLayout(self.drag_items_layout)
        s_layout.addWidget(btn_add_item)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.drag_scroll_content)
        layout.addWidget(scroll)
        return widget

    def create_truefalse_ui(self):
        widget = QGroupBox("Cấu hình Đúng / Sai (True / False nhiều câu nhỏ)")
        layout = QVBoxLayout(widget)

        self.tf_list_layout = QVBoxLayout()
        self.tf_scroll_content = QWidget()
        self.tf_scroll_content.setLayout(self.tf_list_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.tf_scroll_content)
        layout.addWidget(scroll)

        btn_add = QPushButton("+ Thêm câu hỏi nhỏ")
        btn_add.clicked.connect(lambda: self.add_tf_row())
        layout.addWidget(btn_add)
        return widget

    def create_fill_ui(self):
        widget = QGroupBox("Cấu hình Điền vào chỗ trống (Fill)")
        layout = QVBoxLayout(widget)

        self.fill_list_layout = QVBoxLayout()
        self.fill_scroll_content = QWidget()
        self.fill_scroll_content.setLayout(self.fill_list_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.fill_scroll_content)
        layout.addWidget(scroll)

        btn_add = QPushButton("+ Thêm câu hỏi nhỏ (1 ô trống)")
        btn_add.clicked.connect(lambda: self.add_fill_row())
        layout.addWidget(btn_add)
        return widget

    # --- CÁC HÀM THÊM / XÓA DÒNG ĐỘNG ---

    def add_single_row(self, text="", is_correct=False):
        row_widget = QWidget()
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 2, 0, 2)

        chk = QRadioButton("Đúng")
        chk.setChecked(is_correct)
        if not hasattr(self, "single_group"):
            self.single_group = QButtonGroup(self)
            self.single_group.setExclusive(True)
        self.single_group.addButton(chk)

        txt = QLineEdit(text)
        txt.setPlaceholderText("Nội dung lựa chọn...")

        btn_del = QPushButton("Xóa")
        btn_del.clicked.connect(
            lambda: self.remove_widget(row_widget, self.single_list_layout)
        )

        h_layout.addWidget(chk)
        h_layout.addWidget(txt)
        h_layout.addWidget(btn_del)
        self.single_list_layout.addWidget(row_widget)

    def add_multi_row(self, text="", is_correct=False):
        row_widget = QWidget()
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 2, 0, 2)

        chk = QCheckBox("Đúng")
        chk.setChecked(is_correct)

        txt = QLineEdit(text)
        txt.setPlaceholderText("Nội dung lựa chọn...")

        btn_del = QPushButton("Xóa")
        btn_del.clicked.connect(
            lambda: self.remove_widget(row_widget, self.multi_list_layout)
        )

        h_layout.addWidget(chk)
        h_layout.addWidget(txt)
        h_layout.addWidget(btn_del)
        self.multi_list_layout.addWidget(row_widget)

    def add_drag_opt_row(self, text=""):
        row_widget = QWidget()
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 2, 0, 2)

        txt = QLineEdit(text)
        txt.setPlaceholderText("Tên thẻ kéo (VD: A, B...)")
        btn_del = QPushButton("Xóa")
        btn_del.clicked.connect(
            lambda: self.remove_widget(row_widget, self.drag_opts_layout)
        )

        h_layout.addWidget(txt)
        h_layout.addWidget(btn_del)
        self.drag_opts_layout.addWidget(row_widget)

    def add_drag_item_row(self, item_text="", match_list=None):
        if match_list is None:
            match_list = []
        
        row_widget = QWidget()
        v_layout = QVBoxLayout(row_widget)
        v_layout.setContentsMargins(0, 5, 0, 5)

        top_h_layout = QHBoxLayout()
        txt_item = QLineEdit(item_text)
        txt_item.setPlaceholderText("Nội dung phát biểu/câu hỏi nhỏ (VD: Vị trí 1...)")
        
        btn_del = QPushButton("Xóa vị trí")
        btn_del.clicked.connect(lambda: self.remove_widget(row_widget, self.drag_items_layout))
        
        top_h_layout.addWidget(txt_item)
        top_h_layout.addWidget(btn_del)
        v_layout.addLayout(top_h_layout)

        # Vùng chứa các ô đáp án đúng tường minh
        match_container = QWidget()
        match_layout = QVBoxLayout(match_container)
        match_layout.setContentsMargins(20, 0, 0, 0) # Thụt lề vào trong

        btn_add_match = QPushButton("+ Thêm ô đáp án đúng")
        btn_add_match.setMaximumWidth(180)
        
        def add_match_field(match_text=""):
            m_widget = QWidget()
            m_h = QHBoxLayout(m_widget)
            m_h.setContentsMargins(0, 2, 0, 2)
            txt_m = QLineEdit(match_text)
            txt_m.setPlaceholderText("Nhập thẻ kéo khớp (VD: A)")
            btn_m_del = QPushButton("✕")
            btn_m_del.setFixedWidth(30)
            btn_m_del.clicked.connect(lambda: self.remove_widget(m_widget, match_layout))
            m_h.addWidget(QLabel("   ➜ Ô đáp án:"))
            m_h.addWidget(txt_m)
            m_h.addWidget(btn_m_del)
            match_layout.addWidget(m_widget)

        btn_add_match.clicked.connect(lambda: add_match_field())
        
        # Nạp danh sách đáp án cũ nếu có
        if match_list:
            for m in match_list:
                add_match_field(m)
        else:
            add_match_field("") # Mặc định tạo 1 ô

        v_layout.addWidget(match_container)
        v_layout.addWidget(btn_add_match)
        self.drag_items_layout.addWidget(row_widget)

    def add_tf_row(self, text="", is_correct=True):
        row_widget = QWidget()
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 2, 0, 2)

        txt = QLineEdit(text)
        txt.setPlaceholderText("Nội dung phát biểu nhỏ...")

        combo_tf = QComboBox()
        combo_tf.addItems(["Đúng (True)", "Sai (False)"])
        combo_tf.setCurrentIndex(0 if is_correct else 1)

        btn_del = QPushButton("Xóa")
        btn_del.clicked.connect(
            lambda: self.remove_widget(row_widget, self.tf_list_layout)
        )

        h_layout.addWidget(txt)
        h_layout.addWidget(combo_tf)
        h_layout.addWidget(btn_del)
        self.tf_list_layout.addWidget(row_widget)

    def add_fill_row(self, text="", answers_list=None):
        if answers_list is None:
            answers_list = []
        row_widget = QWidget()
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 2, 0, 2)

        txt_q = QLineEdit(text)
        txt_q.setPlaceholderText("Câu hỏi có chứa ________")

        txt_ans = QLineEdit(", ".join(answers_list))
        txt_ans.setPlaceholderText("Đáp án chấp nhận (cách nhau dấu phẩy)")

        btn_del = QPushButton("Xóa")
        btn_del.clicked.connect(
            lambda: self.remove_widget(row_widget, self.fill_list_layout)
        )

        h_layout.addWidget(txt_q)
        h_layout.addWidget(QLabel("➡️ Đáp án:"))
        h_layout.addWidget(txt_ans)
        h_layout.addWidget(btn_del)
        self.fill_list_layout.addWidget(row_widget)

    def remove_widget(self, widget, layout):
        layout.removeWidget(widget)
        widget.deleteLater()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def toggle_json_view(self, checked):
        self.txt_raw_json.setVisible(checked)
        if checked:
            # Tự động lấy dữ liệu hiện tại từ form UI và convert sang chuỗi JSON định dạng đẹp
            current_data = self.get_data(ignore_raw_json=True)
            formatted_json = json.dumps(current_data, ensure_ascii=False, indent=2)
            self.txt_raw_json.setPlainText(formatted_json)
            
    def get_data(self, ignore_raw_json=False):
        idx = self.type_combo.currentIndex()
        type_codes = ["single", "multi", "drag", "truefalse", "fill"]
        qtype_code = type_codes[idx]

        data = {
            "type": qtype_code,
            "text": self.txt_text.toPlainText().strip()
        }

        if qtype_code == "single":
            opts = []
            correct_idx = 0
            for i in range(self.single_list_layout.count()):
                w = self.single_list_layout.itemAt(i).widget()
                if w:
                    txt = w.findChild(QLineEdit).text().strip()
                    chk = w.findChild(QRadioButton)
                    opts.append(txt)
                    if chk and chk.isChecked():
                        correct_idx = len(opts) - 1
            data["opts"] = opts
            data["correct"] = correct_idx

        elif qtype_code == "multi":
            opts = []
            correct_list = []
            for i in range(self.multi_list_layout.count()):
                w = self.multi_list_layout.itemAt(i).widget()
                if w:
                    txt = w.findChild(QLineEdit).text().strip()
                    chk = w.findChild(QCheckBox)
                    opts.append(txt)
                    if chk and chk.isChecked():
                        correct_list.append(len(opts) - 1)
            data["opts"] = opts
            data["correct"] = correct_list
            data["required"] = self.spin_required.value()

        elif qtype_code == "drag":
            draggables = []
            for i in range(self.drag_opts_layout.count()):
                w = self.drag_opts_layout.itemAt(i).widget()
                if w:
                    txt = w.findChild(QLineEdit).text().strip()
                    if txt:
                        draggables.append(txt)

            items = []
            matches = []
            for i in range(self.drag_items_layout.count()):
                w = self.drag_items_layout.itemAt(i).widget()
                if w:
                    txt_item = w.findChild(QLineEdit)
                    if txt_item and txt_item.text().strip():
                        items.append(txt_item.text().strip())
                        
                        m_list = []
                        for child_line in w.findChildren(QLineEdit):
                            if child_line != txt_item and child_line.text().strip():
                                m_list.append(child_line.text().strip())
                        matches.append(m_list)

            data["draggables"] = draggables
            data["items"] = items
            data["matches"] = matches            

        elif qtype_code == "truefalse":
            items = []
            for i in range(self.tf_list_layout.count()):
                w = self.tf_list_layout.itemAt(i).widget()
                if w:
                    txt = w.findChild(QLineEdit).text().strip()
                    combo = w.findChild(QComboBox)
                    is_correct = (combo.currentIndex() == 0) if combo else True
                    if txt:
                        items.append({"text": txt, "correct": is_correct})
            data["items"] = items

        elif qtype_code == "fill":
            items = []
            for i in range(self.fill_list_layout.count()):
                w = self.fill_list_layout.itemAt(i).widget()
                if w:
                    inputs = w.findChildren(QLineEdit)
                    if len(inputs) >= 2:
                        txt_q = inputs[0].text().strip()
                        txt_ans = inputs[1].text().strip()
                        ans_list = [a.strip() for a in txt_ans.split(",") if a.strip()]
                        if txt_q:
                            items.append({"text": txt_q, "answers": ans_list})
            data["items"] = items

        # Tránh đệ quy/lặp vô tận khi tự đọc lại chuỗi JSON đang tạo
        if not ignore_raw_json:
            raw_json_str = self.txt_raw_json.toPlainText().strip()
            if raw_json_str:
                try:
                    extra_json = json.loads(raw_json_str)
                    data.update(extra_json)
                except Exception:
                    pass

        return data

    def on_type_changed(self, index):
        self.stack.setCurrentIndex(index)

    # --- NẠP DỮ LIỆU CŨ VÀO FORM ---

    def load_question_data(self):
        self.type_combo.blockSignals(True)

        qtype = self.question_data.get("type", "single")
        type_map = {"single": 0, "multi": 1, "drag": 2, "truefalse": 3, "fill": 4}
        idx = type_map.get(qtype, 0)
        self.type_combo.setCurrentIndex(idx)
        self.stack.setCurrentIndex(idx)

        self.txt_text.setPlainText(self.question_data.get("text", ""))

        # Clear layouts
        self.clear_layout(self.single_list_layout)
        self.clear_layout(self.multi_list_layout)
        self.clear_layout(self.drag_opts_layout)
        self.clear_layout(self.drag_items_layout)
        self.clear_layout(self.tf_list_layout)
        self.clear_layout(self.fill_list_layout)

        if hasattr(self, "single_group"):
            self.single_group = QButtonGroup(self)
            self.single_group.setExclusive(True)

        # 1. Single
        if qtype == "single":
            opts = self.question_data.get("opts", [])
            correct = self.question_data.get("correct", 0)
            for i, opt in enumerate(opts):
                self.add_single_row(opt, i == correct)
            if not opts:
                self.add_single_row("Đáp án A", True)
                self.add_single_row("Đáp án B", False)

        # 2. Multi
        elif qtype == "multi":
            opts = self.question_data.get("opts", [])
            correct = self.question_data.get("correct", [])
            required = self.question_data.get("required", len(correct) if correct else 2)
            self.spin_required.setValue(required)

            for i, opt in enumerate(opts):
                self.add_multi_row(opt, i in correct)
            if not opts:
                self.add_multi_row("Đáp án 1", True)
                self.add_multi_row("Đáp án 2", False)

        # 3. Drag
        elif qtype == "drag":
            draggables = self.question_data.get("draggables", [])
            items = self.question_data.get("items", [])
            matches = self.question_data.get("matches", [])

            for d in draggables:
                self.add_drag_opt_row(d)

            for i, item_text in enumerate(items):
                m_list = matches[i] if i < len(matches) else []
                self.add_drag_item_row(item_text, m_list)

            if not draggables:
                self.add_drag_opt_row("A")
                self.add_drag_item_row("1. Phát biểu mẫu", ["A"])

        # 4. True / False
        elif qtype == "truefalse":
            tf_items = self.question_data.get("items", [])
            for it in tf_items:
                self.add_tf_row(it.get("text", ""), it.get("correct", True))
            if not tf_items:
                self.add_tf_row("Phát biểu mẫu đúng/sai", True)

        # 5. Fill
        elif qtype == "fill":
            fill_items = self.question_data.get("items", [])
            for it in fill_items:
                self.add_fill_row(it.get("text", ""), it.get("answers", []))
            if not fill_items:
                self.add_fill_row("Câu hỏi ________", ["đáp án"])

        extra_fields = {
            k: v for k, v in self.question_data.items()
            if k not in ["type", "text", "opts", "correct", "required", "draggables", "items", "matches", "answers"]
        }
        if extra_fields:
            self.txt_raw_json.setPlainText(
                json.dumps(extra_fields, ensure_ascii=False, indent=2)
            )

        self.type_combo.blockSignals(False)


class MainWindow(QMainWindow):
    """Cửa sổ chính quản lý bài trắc nghiệm."""

    def __init__(self):
        super().__init__()
        self.backend = HTMLEditorBackend()
        self.current_sub_key = None
        self.current_topic_id = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("K._n? HTML Test Bank Manager")
        self.resize(1100, 700)
        
        icon_path = resource_path("image.ico")
        self.setWindowIcon(QIcon(icon_path))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        top_bar = QHBoxLayout()
        btn_new = QPushButton("✨ Tạo Mới File HTML Test")
        btn_new.clicked.connect(self.create_new_file)
        btn_open = QPushButton("📂 Mở File HTML Test")
        btn_open.clicked.connect(self.open_file)
        btn_save = QPushButton("💾 Lưu File HTML Test")
        btn_save.clicked.connect(self.save_file)

        self.txt_site_title = QLineEdit()
        self.txt_site_title.setPlaceholderText("<title>")
        self.txt_header_p = QLineEdit()
        self.txt_header_p.setPlaceholderText("<div class='header'><p>")

        lbl_font = QLabel("🔤 Cỡ chữ:")
        self.spin_font = QSpinBox()
        self.spin_font.setRange(10,30)
        self.spin_font.setValue(10)
        self.spin_font.valueChanged.connect(self.change_font_size)

        top_bar.addWidget(btn_new)
        top_bar.addWidget(btn_open)
        top_bar.addWidget(btn_save)
        
        top_bar.addSpacing(65)
        top_bar.addWidget(QLabel("Tiêu đề HTML:"))
        top_bar.addWidget(self.txt_site_title)
        top_bar.addSpacing(30)
        top_bar.addWidget(QLabel("Tên môn học:"))
        top_bar.addWidget(self.txt_header_p)
        
        top_bar.addStretch() # Đẩy tất cả các phần tử phía sau sang sát lề phải
        top_bar.addWidget(lbl_font)
        top_bar.addWidget(self.spin_font)
        main_layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Trái: TreeWidget
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        lbl_tree = QLabel("<b>Cấu trúc Học phần / Bài học</b>")
        self.tree = QTreeWidget()
        
        # 1. Đảo vị trí cột: Mã / ID đặt trước, Danh mục đặt sau
        self.tree.setHeaderLabels(["Mã / ID", "Danh mục"])
        
        # 2. Cấu hình tỉ lệ chiều rộng:
        # Cột 0 (Mã / ID): Tự căn chỉnh theo độ dài nội dung (chiếm diện tích nhỏ)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # Cột 1 (Danh mục): Tự giãn rộng chiếm tối đa phần diện tích còn lại
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.tree.itemSelectionChanged.connect(self.on_tree_selection_changed)

        tree_btn_layout = QHBoxLayout()
        btn_add_sub = QPushButton("+ Học Phần")
        btn_add_sub.clicked.connect(self.add_subject)
        btn_add_top = QPushButton("+ Bài Học")
        btn_add_top.clicked.connect(self.add_topic)
        btn_del_item = QPushButton("- Xóa")
        btn_del_item.clicked.connect(self.delete_tree_item)

        tree_btn_layout.addWidget(btn_add_sub)
        tree_btn_layout.addWidget(btn_add_top)
        tree_btn_layout.addWidget(btn_del_item)

        left_layout.addWidget(lbl_tree)
        left_layout.addWidget(self.tree)
        left_layout.addLayout(tree_btn_layout)

        # Phải: Bảng câu hỏi
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        lbl_q = QLabel("<b>Danh sách câu hỏi</b>")
        self.table_q = QTableWidget()
        self.table_q.setColumnCount(3)
        self.table_q.setHorizontalHeaderLabels(["STT", "Loại", "Nội dung"])
        self.table_q.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table_q.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        q_btn_layout = QHBoxLayout()
        btn_add_q = QPushButton("Thêm câu hỏi")
        btn_add_q.clicked.connect(self.add_question)
        btn_edit_q = QPushButton("Sửa câu hỏi")
        btn_edit_q.clicked.connect(self.edit_question)
        btn_del_q = QPushButton("Xóa câu hỏi")
        btn_del_q.clicked.connect(self.delete_question)

        q_btn_layout.addWidget(btn_add_q)
        q_btn_layout.addWidget(btn_edit_q)
        q_btn_layout.addWidget(btn_del_q)

        right_layout.addWidget(lbl_q)
        right_layout.addWidget(self.table_q)
        right_layout.addLayout(q_btn_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([380, 620])
        main_layout.addWidget(splitter)

    def change_font_size(self, size):
        font = QApplication.font()
        font.setPointSize(size)
        QApplication.setFont(font)

    def create_new_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Tạo file HTML trắc nghiệm mới", "", "HTML Files (*.html *.htm)"
        )
        if file_path:
            # Template HTML cơ bản tích hợp sẵn cấu trúc dữ liệu trắng
            template_content = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>CHỦ NGHĨA XÃ HỘI KHOA HỌC</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            background: linear-gradient(135deg, grey, black);
            min-height: 100vh;
            padding: 16px;
            font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 28px;
            overflow: hidden;
            margin-bottom: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        .header {
            background: linear-gradient(135deg, #1e3c2c, #2a5a3a);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 1.5rem; }
        .header p { font-size: 0.8rem; opacity: 0.9; }
        
        .mode-bar {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 12px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        }
        .mode-badge {
            background: #16a34a;
            color: white;
            padding: 6px 20px;
            border-radius: 40px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 40px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
			transition: transform 0.25s ease;
        }
		.btn:hover {
			transform: scale(1.15);
		}
        .btn-primary { background: #3b82f6; color: white; }
        .btn-success { background: #22c55e; color: white; }
        .btn-warning { background: #f59e0b; color: white; }
        .btn-outline { background: transparent; border: 2px solid #3b82f6; color: #3b82f6; }
        
        .home-content { padding: 20px; }
        .subject-grid, .topic-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
            margin-top: 16px;
        }
        .subject-card, .topic-card {
            background: #f8fafc;
            padding: 16px;
            border-radius: 20px;
            border-left: 5px solid #3b82f6;
            cursor: pointer;
        }
        .subject-card:active, .topic-card:active { background: #f1f5f9; transform: scale(0.98); }
        .subject-card h3, .topic-card h3 { font-size: 1rem; color: #1e293b; }
        
		/* CSS CHO THANH TÌM KIẾM VÀ KẾT QUẢ TÌM KIẾM */
        .search-container {
            margin-bottom: 20px;
            position: relative;
        }
        .search-box-wrapper {
            display: flex;
            align-items: center;
            background: #f1f5f9;
            border: 2px solid #cbd5e1;
            border-radius: 40px;
            padding: 4px 16px;
            transition: all 0.3s ease;
        }
        .search-box-wrapper:focus-within {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
            background: #ffffff;
        }
        .search-icon {
            font-size: 16px;
            color: #64748b;
            margin-right: 8px;
        }
        .search-input {
            flex: 1;
            border: none;
            outline: none;
            background: transparent;
            padding: 8px 0;
            font-size: 14px;
            color: #1e293b;
        }
        .clear-search-btn {
            background: #e2e8f0;
            border: none;
            color: #64748b;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 12px;
            transition: 0.2s;
        }
        .clear-search-btn:hover {
            background: #cbd5e1;
            color: #0f172a;
        }
        .search-results-area {
            margin-top: 16px;
        }
        .search-results-count {
            font-size: 14px;
            font-weight: 600;
            color: #3b82f6;
            margin-bottom: 12px;
        }
        .search-item-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            text-align: left;
            transition: 0.2s;
        }
        .search-item-card:hover {
            border-color: #93c5fd;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        .search-item-meta {
            font-size: 12px;
            font-weight: 600;
            color: #64748b;
            margin-bottom: 8px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .search-meta-tag {
            background: #e2e8f0;
            padding: 2px 8px;
            border-radius: 12px;
        }
        .search-item-qtext {
            font-size: 15px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 10px;
            line-height: 1.4;
        }
        .search-item-opts {
            margin-bottom: 12px;
            font-size: 13px;
        }
        .search-opt-line {
            padding: 6px 10px;
            border-radius: 8px;
            margin-bottom: 4px;
            background: #ffffff;
            border: 1px solid #f1f5f9;
        }
        .search-opt-line.is-correct {
            background: #dcfce7;
            border-color: #86efac;
            color: #166534;
            font-weight: 600;
        }
        .highlight-keyword {
            background-color: #fef08a;
            color: #854d0e;
            padding: 0 1px;
            border-radius: 1px;
        }
        .no-results {
            text-align: center;
            padding: 24px;
            color: #64748b;
            font-style: italic;
        }
		
        .quiz-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            flex-wrap: wrap;
            gap: 8px;
        }
        .timer {
            background: #1e293b;
            color: white;
            padding: 6px 14px;
            border-radius: 40px;
            font-family: monospace;
            font-weight: bold;
        }
        .question-area { padding: 20px; }
        .list-toggle {
            width: 100%;
            background: #f1f5f9;
            padding: 10px;
            border-radius: 40px;
            display: flex;
            justify-content: space-between;
            cursor: pointer;
            border: none;
            margin-bottom: 16px;
            font-weight: 600;
        }
        .numbers-container {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            padding: 12px;
            background: #f8fafc;
            border-radius: 20px;
            margin-bottom: 20px;
            max-height: 0;
            overflow: hidden;
            transition: 0.3s;
        }
        .numbers-container.show { max-height: 250px; overflow-y: auto; }
        .q-num {
            width: 42px;
            height: 42px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 14px;
            font-weight: 700;
            cursor: pointer;
            margin: 0 auto;
        }
        .q-num.active { background: #3b82f6; color: white; border-color: #3b82f6; }
        .q-num.answered { background: #22c55e; color: white; border-color: #22c55e; }
        .q-num.current { border: 3px solid #f59e0b; }
        
        .question-text {
            font-size: 1rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 20px;
            line-height: 1.4;
        }
        .option-item {
            padding: 12px 16px;
            margin: 8px 0;
            background: #f8fafc;
            border-radius: 16px;
            border: 2px solid #e2e8f0;
            cursor: pointer;
            transition: 0.1s;
        }
        .option-item.correct { background: #dcfce7; border-color: #22c55e; }
        .option-item.wrong { background: #fee2e2; border-color: #ef4444; }
        .option-item.selected { border-color: #3b82f6; background: #eff6ff; }
        
        .multi-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            margin: 8px 0;
            background: #f8fafc;
            border-radius: 16px;
            border: 2px solid #e2e8f0;
        }
        .multi-item input { width: 20px; height: 20px; cursor: pointer; }
        .multi-item.correct { background: #dcfce7; border-color: #22c55e; }
        .multi-item.wrong { background: #fee2e2; border-color: #ef4444; }
        .multi-item.selected { border-color: #3b82f6; background: #eff6ff; }
        
        .tf-item {
            padding: 12px;
            margin: 8px 0;
            background: #f8fafc;
            border-radius: 16px;
            border: 2px solid #e2e8f0;
        }
        .tf-item.correct { background: #dcfce7; border-color: #22c55e; }
        .tf-item.wrong { background: #fee2e2; border-color: #ef4444; }
        .tf-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .tf-text { flex: 1; font-weight: 500; }
        .tf-buttons { display: flex; gap: 12px; }
        .tf-buttons button {
            padding: 6px 20px;
            border: 2px solid #cbd5e1;
            background: white;
            border-radius: 40px;
            font-weight: 600;
            cursor: pointer;
        }
        .tf-buttons button.true-active { background: #22c55e; color: white; border-color: #22c55e; }
        .tf-buttons button.false-active { background: #ef4444; color: white; border-color: #ef4444; }
        
        .drag-pool {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            padding: 16px;
            background: #eff6ff;
            border-radius: 20px;
            margin: 16px 0;
            border: 2px dashed #3b82f6;
            min-height: 80px;
        }
        .drag-item {
            padding: 8px 16px;
            background: white;
            border: 2px solid #3b82f6;
            border-radius: 40px;
            cursor: grab;
            user-select: none;
        }
        .drag-item.correct { background: #dcfce7; border-color: #22c55e; }
        .drag-item.wrong { background: #fee2e2; border-color: #ef4444; }
        .drop-zones { display: grid; gap: 16px; margin-top: 16px; }
        .drop-zone {
            padding: 12px;
            border: 2px dashed #94a3b8;
            border-radius: 16px;
            background: #fafafa;
            min-height: 80px;
        }
        .drop-title { font-weight: 600; margin-bottom: 8px; color: #334155; }
        .drop-placeholder { color: #999; font-style: italic; text-align: center; padding: 8px; }
        
        .fill-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 16px;
            margin: 8px 0;
            font-size: 14px;
        }
        .fill-input.correct { background: #dcfce7; border-color: #22c55e; }
        .fill-input.wrong { background: #fee2e2; border-color: #ef4444; }
        .correct-answer-hint {
            font-size: 13px;
            margin-top: 4px;
            padding: 8px 12px;
            background: #f1f5f9;
            border-radius: 12px;
            color: #16a34a;
        }
        
        .instruction {
            background: #fef9c3;
            padding: 8px 12px;
            border-radius: 14px;
            font-size: 12px;
            margin-bottom: 16px;
            border-left: 4px solid #f59e0b;
        }
        .quiz-footer {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: space-between;
            padding: 12px 16px;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
        }
        
        .result-screen { text-align: center; padding: 30px 20px; }
        .score-big { font-size: 2.5rem; font-weight: 800; margin: 16px 0; }
        .score-detail { display: flex; justify-content: center; gap: 20px; margin: 20px 0; flex-wrap: wrap; }
        .score-box { background: #f8fafc; padding: 16px 24px; border-radius: 20px; }
        .score-box .num { font-size: 1.8rem; font-weight: 800; }
        .review-area {
            margin-top: 20px;
            padding: 16px;
            background: #f8fafc;
            border-radius: 20px;
            text-align: left;
            max-height: 350px;
            overflow-y: auto;
        }
        .review-item {
            padding: 12px;
            margin: 8px 0;
            border-radius: 14px;
        }
        .review-item.correct { background: #dcfce7; border-left: 5px solid #22c55e; }
        .review-item.wrong { background: #fee2e2; border-left: 5px solid #ef4444; }
        .footer {
            text-align: center;
            padding: 12px;
            color: rgba(255,255,255,0.6);
            font-size: 10px;
        }
        
        @media (min-width: 640px) {
            .subject-grid, .topic-grid { grid-template-columns: repeat(2, 1fr); }
            .numbers-container { grid-template-columns: repeat(10, 1fr); } /* Hiển thị 10 câu hỏi trong 1 hàng của danh sách câu hỏi */
            .drop-zones { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
<div class="container">
    <div id="homeScreen" class="card">
        <div class="header">
            <h1>📚 ÔN TẬP 📚</h1>
			<p>CHỦ NGHĨA XÃ HỘI KHOA HỌC</p>
        </div>
        <div class="home-content">
			<!-- THANH TÌM KIẾM CÂU HỎI VÀ ĐÁP ÁN -->
            <div class="search-container">
                <div class="search-box-wrapper">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="searchInput" class="search-input" placeholder="Nhập từ khóa tìm kiếm câu hỏi hoặc đáp án..." oninput="handleSearch()">
                    <button id="clearSearchBtn" class="clear-search-btn" onclick="clearSearch()" style="display:none;">✖</button>
                </div>
            </div>

            <!-- KHU VỰC HIỂN THỊ KẾT QUẢ TÌM KIẾM -->
            <div id="searchResultsArea" class="search-results-area" style="display:none;">
                <div id="searchResultsCount" class="search-results-count"></div>
                <div id="searchResultsList"></div>
            </div>
			
			<!-- DANH SÁCH MÔN HỌC / BÀI HỌC BAN ĐẦU -->
            <div id="defaultHomeContent">
                <div style="font-weight:600; margin-bottom:12px;">📖 Chọn môn học phần</div>
                <button id="backBtn" onclick="backToSubjects()" style="display:none; margin-bottom:12px;" class="btn btn-outline">← Danh sách học phần</button>
                <h3 id="subjectName" style="margin-bottom:12px;"></h3>
                <div id="subjectsList" class="subject-grid"></div>
                <div id="topicsList" class="topic-grid" style="display:none;"></div>
            </div>
        </div>
    </div>

    <div id="quizScreen" class="card" style="display:none">
        <div class="mode-bar">
            <span class="mode-badge">🎯 Học tập 🎯</span>
        </div>
        <div class="quiz-header">
            <button class="btn btn-outline" onclick="goHome()" style="padding:5px 12px;">🏠 Trang chủ</button>
            <div class="timer" id="timer">00:00</div>
            <div id="topicName" style="font-size:0.7rem; max-width:180px;"></div>
        </div>
        <div class="question-area">
            <button class="list-toggle" onclick="toggleList()"><span>📋 Danh sách câu hỏi</span><span id="listArrow">▼</span></button>
            <div id="numbersContainer" class="numbers-container"><div id="questionNumbers" style="display:contents;"></div></div>
            <div id="questionContent"></div>
        </div>
        <div class="quiz-footer">
            <button class="btn btn-primary" id="prevBtn" onclick="prev()">← Câu trước</button>
            <button class="btn btn-warning" onclick="shuffleAll()">🔄 Đảo câu</button>
            <button class="btn btn-warning" onclick="resetCurrent()">Làm lại</button>
            <button class="btn btn-success" id="nextBtn" onclick="next()">Câu tiếp →</button>
            <button class="btn btn-success" id="submitBtn" onclick="submitQuiz()" style="display:none">📤 Nộp bài</button>
        </div>
    </div>

    <div id="resultScreen" class="card" style="display:none">
        <div class="header"><h1>🏆 KẾT QUẢ</h1></div>
        <div class="result-screen">
            <div class="score-big" id="finalScore">0/0</div>
            <div>⏱️ Thời gian: <span id="finalTime">00:00</span></div>
            <div>⭐ Thang 10: <span id="scale10">0.0</span></div>
            <div class="score-detail">
                <div class="score-box"><h4>✅ Đúng</h4><div class="num" id="correctCount">0</div></div>
                <div class="score-box"><h4>❌ Sai</h4><div class="num" id="wrongCount">0</div></div>
            </div>
            <button class="btn btn-primary" onclick="showDetail()">📋 Xem chi tiết</button>
            <div id="detailArea" class="review-area" style="display:none;"></div>
            <div style="margin-top:20px"><button class="btn btn-success" onclick="retry()">Làm lại</button><button class="btn btn-outline" onclick="goHome()" style="margin-left:12px;">Về trang chủ</button></div>
        </div>
    </div>
</div>
<div class="footer">© Hệ thống ôn luyện</div>

<script>
// DỮ LIỆU CHỦ ĐỀ 1
const DATA = {
    "tenMonHoc": {
        "name": "CHỦ NGHĨA XÃ HỘI KHOA HỌC",
        "topics": {
            "1": {
                "name": "BÀI 1: TỔNG QUAN VỀ CHỦ NGHĨA XÃ HỘI KHOA HỌC",
                "questions": [
                    {
                        "type": "single",
                        "text": "Những nhà tư tưởng tiêu biểu của chủ nghĩa xã hội không tưởng phê quán đầu thế kỷ XIX là ai?",
                        "opts": [
                            "A. Xanh Ximông, Sáclơ Phuriê, G. Mably",
                            "B. Xanh Ximông, Sáclơ Phuriê, Rôbớt Ôoen",
                            "C. Grắccơ Babớp, Xanh Ximông, Sáclơ Phuriê",
                            "D. Xanh Ximông, Giăng Mêliê, Rôbớt Ôoen"
                        ],
                        "correct": 1
                    },
                    {
                        "type": "single",
                        "text": "Tác phẩm nào đánh dấu sự ra đời của chủ nghĩa xã hội khoa học?",
                        "opts": [
                            "A. Tuyên ngôn của Đảng Cộng sản",
                            "B. Bộ tư bản",
                            "C. Góp phần phê phán triết học pháp quyền của Hêghen – Lời nói đầu",
                            "D. Tình cảnh nước Anh"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Phát kiến nào của C.Mác và Ph.Ăngghen chỉ ra sự diệt vong về kinh tế của chủ nghĩa tư bản?",
                        "opts": [
                            "A. Chủ nghĩa duy vật biện chứng",
                            "B. Học thuyết về giá trị thặng dư",
                            "C. Học thuyết về sứ mệnh lịch sử toàn thế giới của giai cấp công nhân",
                            "D. Chủ nghĩa duy vật lịch sử"
                        ],
                        "correct": 1
                    },
                    {
                        "type": "single",
                        "text": "Phát kiến nào của C.Mác và Ph.Ăngghen chỉ ra những hạn chế có tính lịch sử của chủ nghĩa xã hội không tưởng?",
                        "opts": [
                            "A. Học thuyết về sứ mệnh lịch sử toàn thế giới của giai cấp công nhân",
                            "B. Học thuyết về giá trị thặng dư",
                            "C. Chủ nghĩa duy vật lịch sử",
                            "D. Chủ nghĩa duy vật biện chứng"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Ph.Ăngghen đã đánh giá: “Hai phát hiện vĩ đại này đã đưa chủ nghĩa xã hội trở thành một khoa học”. Hai phát kiến đó là gì?",
                        "opts": [
                            "A. Học thuyết giá trị thặng dư – Chủ nghĩa duy vật lịch sử",
                            "B. Chủ nghĩa duy vật biện chứng và chủ nghĩa duy vật lịch sử",
                            "C. Sứ mệnh lịch sử của giai cấp công nhân – Học thuyết giá trị thặng dư",
                            "D. Sứ mệnh lịch sử của giai cấp công nhân – Chủ nghĩa duy vật lịch sử"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Đâu là nhân tố chủ quan quan trọng nhất để giai cấp công nhân thực hiện thắng lợi sứ mệnh lịch sử của mình?",
                        "opts": [
                            "A. Đảng Cộng sản",
                            "B. Sự phát triển của giai cấp công nhân về chất lượng",
                            "C. Liên minh giai cấp công nhân với giai cấp nông dân",
                            "D. Sự phát triển của giai cấp công nhân về số lượng"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Xét trong quan hệ sản xuất tư bản chủ nghĩa giai cấp công nhân là:",
                        "opts": [
                            "A. Giai cấp không có tư liệu sản xuất, đi làm thuê cho nhà tư bản, bị nhà tư bản bóc lột giá trị thặng dư",
                            "B. Giai cấp nghèo khổ nhất",
                            "C. Giai cấp có số lượng đông trong dân cư",
                            "D. Giai cấp tạo ra của cải cho xã hội"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Tìm ý đúng để hoàn thiện luận điểm sau: Cùng với sự phát triển của khoa học và công nghệ ngày càng hiện đại, giai cấp công nhân:",
                        "opts": [
                            "A. Tăng về số lượng và nâng cao về chất lượng",
                            "B. Tăng về số lượng và giảm về chất lượng",
                            "C. Giảm về số lượng và có trình độ sản xuất ngày càng cao",
                            "D. Giảm về số lượng và nâng cao về chất lượng"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Dấu hiệu đánh dấu sự trưởng thành vượt bậc của giai cấp công nhân với tư cách là giai cấp cách mạng là:",
                        "opts": [
                            "A. Sự ra đời của Đảng Cộng sản",
                            "B. Sự trưởng thành về trình độ nhận thức",
                            "C. Sự trưởng thành về trình độ kỹ thuật",
                            "D. Sự trưởng thành về ý thức chính trị"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Giai cấp công nhân Việt Nam ra đời vào thời gian nào?",
                        "opts": [
                            "A. Trong cuộc khai thác thuộc địa lần thứ nhất của thực dân Pháp",
                            "B. Những năm đầu thế kỷ 19",
                            "C. Trong cuộc khai thác thuộc địa lần thứ hai của thực dân Pháp",
                            "D. Trước khi thực dân Pháp xâm lược Việt Nam"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Nội dung trực tiếp về văn hoá tư tưởng thể hiện sứ mệnh lịch sử của giai cấp công nhân Việt Nam là:",
                        "opts": [
                            "A. Xây dựng nền văn hoá Việt Nam tiên tiến, đậm đà bản sắc dân tộc",
                            "B. Xây dựng hệ giá trị và con người Việt Nam",
                            "C. Xây dựng con người mới xã hội chủ nghĩa",
                            "D. Xây dựng nền giáo dục hiện đại"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Hạn chế cơ bản lớn nhất mà giai cấp công nhân Việt Nam hiện nay cần khắc phục là gì?",
                        "opts": [
                            "A. Trình độ khoa học kỹ thuật chưa cao",
                            "B. Số lượng còn ít",
                            "C. Tâm lý tiểu nông",
                            "D. Hiệu quả lao động thấp"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Trong các nội dung sau đây thì nội dung nào thuộc về giải pháp xây dựng giai cấp công nhân Việt Nam hiện nay?",
                        "opts": [
                            "A. Nâng cao nhận thức, kiên định quan điểm giai cấp công nhân là giai cấp lãnh đạo cách mạng thông qua đội tiền phong là Đảng Cộng sản Việt Nam",
                            "B. Coi trọng và giữ vững bản chất giai cấp công nhân và nguyên tắc sinh hoạt Đảng",
                            "C. Xây dựng giai cấp công nhân lớn mạnh, có giác ngộ giai cấp và chính trị vững vàng",
                            "D. Xây dựng giai cấp công nhân tăng về số lượng và chất lượng"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "multi",
                        "text": "Điều kiện chủ quan để giai cấp công nhân thực hiện được sứ mệnh lịch sử của mình là: (Chọn 2 đáp án đúng)",
                        "opts": [
                            "A. Đảng Cộng sản",
                            "B. Sự phát triển của bản thân giai cấp công nhân cả về số lượng và chất lượng",
                            "C. Sở hữu toàn bộ tư liệu sản xuất trong xã hội",
                            "D. Không cần liên minh với các giai cấp, tầng lớp khác"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    },
                    {
                        "type": "multi",
                        "text": "Giai cấp công nhân Việt Nam có đặc điểm gì khác với giai cấp công nhân ở các nước tư bản? (Chọn 2 đáp án đúng)",
                        "opts": [
                            "A. Chịu sự bóc lột của thực dân và phong kiến",
                            "B. Xuất thân từ nông dân là chủ yếu",
                            "C. Không có sự gắn kết với các giai cấp, tầng lớp khác",
                            "D. Sở hữu tư liệu sản xuất trong xã hội"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    },
                    {
                        "type": "single",
                        "text": "Phạm trù nào được coi là cơ bản nhất và là xuất phát điểm của chủ nghĩa xã hội khoa học?",
                        "opts": [
                            "A. Sứ mệnh lịch sử của giai cấp công nhân",
                            "B. Cách mạng xã hội chủ nghĩa",
                            "C. Giai cấp công nhân",
                            "D. Chuyên chính vô sản"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Đặc điểm sứ mệnh lịch sử của giai cấp công nhân là:",
                        "opts": [
                            "A. Xóa bỏ triệt để chế độ tư hữu về tư liệu sản xuất",
                            "B. Thay thế chế độ chiếm hữu nô lệ bằng chế độ xã hội chủ nghĩa",
                            "C. Thay thế chế độ công hữu này bằng một chế độ công hữu khác",
                            "D. Thay thế chế độ sở hữu tư nhân này bằng một chế độ sở hữu tư nhân khác"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Điền từ còn thiếu vào chỗ trống: Giai cấp công nhân và nhân dân lao động là cơ sở..., cơ sở... của Đảng cộng sản, là nguồn bổ sung lực lượng phong phú cho Đảng.",
                        "opts": [
                            "A. Chính trị - xã hội",
                            "B. Giai cấp – xã hội",
                            "C. Văn hoá - xã hội",
                            "D. Kinh tế - xã hội"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Điểm then chốt để giúp giai cấp công nhân Việt Nam hiện nay thực hiện thành công sứ mệnh lịch sử của mình là:",
                        "opts": [
                            "A. Coi trọng công tác xây dựng, chỉnh đốn Đảng",
                            "B. Xây dựng khối liên minh công – nông",
                            "C. Trí thức hoá giai cấp công nhân",
                            "D. Phát triển giai cấp công nhân cả về số lượng và chất lượng"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "multi",
                        "text": "Theo C.Mác và Ph.Ăngghen thì đặc điểm nổi bật của giai cấp công nhân là: (Chọn 2 đáp án đúng)",
                        "opts": [
                            "A. Giai cấp cách mạng và có tinh thần cách mạng triệt để",
                            "B. Lao động bằng phương thức công nghiệp",
                            "C. Có quyền sở hữu toàn bộ tư liệu sản xuất",
                            "D. Làm việc trong nông nghiệp, sử dụng công cụ thủ công"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    },
                    {
                        "type": "multi",
                        "text": "Trong thời kỳ thuộc địa, giai cấp công nhân Việt Nam chủ yếu làm việc trong: (Chọn 2 đáp án đúng)",
                        "opts": [
                            "A. Nhà máy, hầm mỏ do thực dân Pháp xây dựng",
                            "B. Đồn điền cao su",
                            "C. Xí nghiệp thủ công truyền thống",
                            "D. Hợp tác xã nông nghiệp"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    },
                    {
                        "type": "multi",
                        "text": "Giai cấp công nhân Việt Nam chủ yếu xuất thân từ tầng lớp nào? (Chọn 2 đáp án đúng)",
                        "opts": [
                            "A. Thợ thủ công bị phá sản",
                            "B. Giai cấp nông dân bị tước đoạt hết ruộng đất",
                            "C. Tầng lớp địa chủ phong kiến",
                            "D. Tầng lớp tư sản dân tộc"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    },
                    {
                        "type": "single",
                        "text": "Đối tượng nghiên cứu của chủ nghĩa xã hội khoa học là gì?",
                        "opts": [
                            "A. Là những quy luật và tính quy luật chính trị – xã hội của quá trình phát sinh, hình thành và phát triển của hình thái kinh tế - xã hội cộng sản chủ nghĩa",
                            "B. Là những quy luật văn hoá - xã hội",
                            "C. Là những quy luật hình thành, phát triển và hoàn thiện của các hình thái kinh tế - xã hội",
                            "D. Là những quy luật kinh tế"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Xét về phương thức lao động, phương thức sản xuất, giai cấp công nhân mang thuộc tính cơ bản nào?",
                        "opts": [
                            "A. Là giai cấp trực tiếp hay gián tiếp vận hành máy móc có tính chất công nghiệp ngày càng hiện đại",
                            "B. Có số lượng đông nhất trong dân cư",
                            "C. Là giai cấp tạo ra của cải vật chất làm giàu cho xã hội",
                            "D. Giai cấp có tư liệu sản xuất nhiều nhất"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Trong các nội dung sau đây thì nội dung nào thuộc về giải pháp xây dựng giai cấp công nhân Việt Nam hiện nay?",
                        "opts": [
                            "A. Thực hiện chiến lược xây dựng giai cấp công nhân lớn mạnh, gắn kết chặt chẽ với chiến lược phát triển kinh tế - xã hội, công nghiệp hoá, hiện đại hoá đất nước, hội nhập quốc tế",
                            "B. Coi trọng và giữ vững bản chất giai cấp công nhân và nguyên tắc sinh hoạt Đảng",
                            "C. Thực hiện tốt chính sách và pháp luật đối với công nhân và người lao động",
                            "D. Xây dựng giai cấp công nhân lớn mạnh, có giác ngộ giai cấp và chính trị vững vàng"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "multi",
                        "text": "Đặc điểm nào sau đây thể hiện đúng bản chất của giai cấp công nhân? (Chọn 2 đáp án đúng)",
                        "opts": [
                            "A. Có tính tổ chức và kỷ luật cao trong lao động sản xuất",
                            "B. Không sở hữu tư liệu sản xuất, sống bằng lao động làm thuê",
                            "C. Luôn gắn bó với giai cấp địa chủ và tiểu thương",
                            "D. Có trình độ học vấn thấp, chủ yếu làm việc tay chân"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    },
                    {
                        "type": "single",
                        "text": "Theo Ph. Ăngghen: “Thực hiện nhiệm vụ giải phóng thế giới ấy, đó là sứ mệnh lịch sử của.........”. Hãy chọn đáp án đúng điền vào chỗ trống?",
                        "opts": [
                            "A. Giai cấp vô sản",
                            "B. Giai cấp tư sản",
                            "C. Giai cấp tiểu tư sản",
                            "D. Giai cấp nông dân"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Điền từ còn thiếu vào chỗ trống: “Giai cấp công nhân Việt Nam thực hiện lãnh đạo cách mạng thông qua đội tiên phong của nó là (...)”",
                        "opts": [
                            "A. Đảng Cộng sản Việt Nam",
                            "B. Mặt trận tổ quốc Việt Nam",
                            "C. Tổng liên đoàn lao động Việt Nam",
                            "D. Tổ chức công đoàn"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Vấn đề nổi bật nhất đối với việc thực hiện sứ mệnh lịch sử của giai cấp công nhân Việt Nam hiện nay là gì?",
                        "opts": [
                            "A. Phát huy vai trò và trách nhiệm của lực lượng đi đầu trong sự nghiệp đẩy mạnh công nghiệp hoá, hiện đại hoá đất nước",
                            "B. Tham gia xây dựng nền kinh tế thị trường định hướng xã hội chủ nghĩa",
                            "C. Lực lượng chủ đạo trong lao động",
                            "D. Nắm vững khoa học và công nghệ"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "So với các giai cấp khác thì sứ mệnh lịch sử của giai cấp công nhân có gì khác biệt?",
                        "opts": [
                            "Xóa bỏ triệt để chế độ tư hữu về tư liệu sản xuất",
                            "Duy trì chế độ tư hữu về tư liệu sản xuất",
                            "Thay thế chế độ sở hữu này bằng một chế độ sở hữu khác",
                            "Không có gì khác biệt"
                        ],
                        "correct": 0
                    }
                ]
            }
        }
    },
    "boSung": {
        "name": "CHỦ NGHĨA XÃ HỘI KHOA HỌC (BỔ SUNG)",
        "topics": {
            "1": {
                "name": "BÀI 1: TỔNG QUAN VỀ CHỦ NGHĨA XÃ HỘI KHOA HỌC",
                "questions": [
                    {
                        "type": "single",
                        "text": "C. Mác và Ph. Ăngghen đã dựa vào những phát kiến nào để xây dựng luận chứng về sứ mệnh lịch sử của giai cấp công nhân?",
                        "opts": [
                            "Chủ nghĩa duy vật lịch sử và Học thuyết giá trị thặng dư",
                            "Triết học cổ điển Đức và Kinh tế chính trị học cổ điển Anh",
                            "Chủ nghĩa xã hội không tưởng – phê phán",
                            "Tất cả các phương án trên"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Định nghĩa đúng nhất về giai cấp công nhân:",
                        "opts": [
                            "Giai cấp lao động trong nền sản xuất công nghiệp có trình độ kỹ thuật và công nghệ hiện đại của xã hội",
                            "Giai cấp chiếm số lượng đông đảo nhất",
                            "Giai cấp bị áp bức, bóc lột nặng nề nhất",
                            "Giai cấp bị thống trị"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Điều kiện khách quan quy định sứ mệnh lịch sử của giai cấp công nhân:",
                        "opts": [
                            "Giai cấp công nhân gắn liền với lực lượng sản xuất tiên tiến",
                            "Giai cấp công nhân là giai cấp tạo ra của cải làm giàu cho xã hội",
                            "Giai cấp công nhân đông về số lượng",
                            "Giai cấp công nhân bị bóc lột nặng nề nhất"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Tác phẩm nào được coi là cương lĩnh chính trị của phong trào cộng sản và công nhân quốc tế?",
                        "opts": [
                            "Tuyên ngôn của Đảng Cộng sản",
                            "Góp phần phê phán triết học pháp quyền của Hêghen – Lời nói đầu",
                            "Tình cảnh nước Anh",
                            "Bộ tư bản"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Ai là người viết ra tác phẩm “Tuyên ngôn của Đảng cộng sản”?",
                        "opts": [
                            "C. Mác và Ph. Ăngghen",
                            "C. Mác",
                            "Ph. Ăngghen",
                            "V. I . Lênin"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Tác phẩm “Tuyên ngôn của Đảng cộng sản” được viết vào năm nào?",
                        "opts": [
                            "1848",
                            "1838",
                            "1858",
                            "1828"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Chủ nghĩa Mác - Lênin bao gồm những bộ phận nào hợp thành?",
                        "opts": [
                            "Triết học Mác - Lênin, Kinh tế chính trị Mác – Lênin và Chủ nghĩa xã hội khoa học",
                            "Chủ nghĩa Mác và Chủ nghĩa xã hội khoa học",
                            "Kinh tế chính trị và Chủ nghĩa xã hội khoa học",
                            "Triết học và kinh tế chính trị"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Đâu là những phát kiến vĩ đại của C. Mác và Ph. Ăngghen?",
                        "opts": [
                            "Chủ nghĩa duy vật lịch sử",
                            "Học thuyết về giá trị thặng dư",
                            "Học thuyết về sứ mệnh lịch sử toàn thế giới của giai cấp công nhân",
                            "Cả ba phương án trên"
                        ],
                        "correct": 3
                    },
                    {
                        "type": "single",
                        "text": "Câu nói sau đây được viết trong tác phẩm nào: “Giai cấp tư sản, trong quá trình thống trị giai cấp chưa đầy một thế kỷ, đã tạo ra những lực lượng sản xuất nhiều hơn và đồ sộ hơn lực lượng sản xuất của tất cả các thế hệ trước gộp lại”",
                        "opts": [
                            "Tuyên ngôn của Đảng Cộng sản",
                            "Chống Đuy-rinh",
                            "Bộ Tư bản",
                            "Ba nguồn gốc và ba bộ phận cấu thành của chủ nghĩa Mác"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "drag",
                        "text": "Kéo thả các đáp án khớp với các phát biểu từ 1 – 4 vế trái dưới đây:",
                        "draggables": [
                            "phương thức sản xuất",
                            "lực lượng sản xuất",
                            "chủ thể",
                            "nhân tố chủ quan"
                        ],
                        "items": [
                            "Giai cấp công nhân đại diện cho ________ tiên tiến",
                            "Đảng Cộng sản là ________ quan trọng nhất để giai cấp công nhân thực hiện thắng lợi sứ mệnh lịch sử của mình",
                            "Giai cấp công nhân đại diện cho ________ hiện đại",
                            "Giai cấp công nhân là ________ của quá trình sản xuất vật chất hiện đại"
                        ],
                        "matches": [
                            [
                                "phương thức sản xuất"
                            ],
                            [
                                "nhân tố chủ quan"
                            ],
                            [
                                "lực lượng sản xuất"
                            ],
                            [
                                "chủ thể"
                            ]
                        ]
                    },
                    {
                        "type": "truefalse",
                        "text": "Chọn đáp án (Đúng hoặc Sai) với từng phát biểu sau:",
                        "items": [
                            {
                                "text": "Giai cấp công nhân là những người lao động trực tiếp hay gián tiếp vận hành các công cụ sản xuất có tính chất công nghiệp ngày càng hiện đại và xã hội hóa cao",
                                "correct": true
                            },
                            {
                                "text": "Đặc điểm nổi bật của giai cấp công nhân là lao động bằng phương thức nông nghiệp",
                                "correct": false
                            },
                            {
                                "text": "Giai cấp công nhân là chủ thể của quá trình sản xuất vật chất hiện đại",
                                "correct": true
                            },
                            {
                                "text": "Giai cấp công nhân là giai cấp cách mạng và có tinh thần cách mạng triệt để",
                                "correct": true
                            }
                        ]
                    },
                    {
                        "type": "multi",
                        "text": "Nội dung sứ mệnh lịch sử của giai cấp công nhân Việt Nam hiện nay bao gồm: (Chọn 3 đáp án đúng)",
                        "opts": [
                            "Nội dung chính trị - xã hội",
                            "Nội dung kinh tế",
                            "Nội dung văn hóa, tư tưởng",
                            "Nội dung lý luận"
                        ],
                        "correct": [
                            0,
                            1,
                            2
                        ],
                        "required": 3
                    },
                    {
                        "type": "truefalse",
                        "text": "Chọn đáp án (Đúng hoặc Sai) với từng phát biểu sau:",
                        "items": [
                            {
                                "text": "Giai cấp công nhân Việt Nam là lực lượng nòng cốt của Đảng Cộng sản Việt Nam",
                                "correct": true
                            },
                            {
                                "text": "Giai cấp công nhân phát huy vai trò và trách nhiệm của lực lượng đi đầu trong sự nghiệp đẩy mạnh công nghiệp hóa, hiện đại hóa đất nước",
                                "correct": true
                            },
                            {
                                "text": "Giai cấp công nhân Việt Nam hiện nay đã tăng nhanh về số lượng và giảm về chất lượng",
                                "correct": false
                            },
                            {
                                "text": "Giai cấp công nhân Việt Nam gắn bó mật thiết với các tầng lớp nhân dân trong xã hội",
                                "correct": true
                            }
                        ]
                    },
                    {
                        "type": "drag",
                        "text": "Kéo thả các đáp án khớp với các phát biểu từ 1 – 3 vế trái dưới đây:",
                        "draggables": [
                            "giai cấp cách mạng",
                            "giai cấp vô sản",
                            "giải phóng con người",
                            "giai cấp công nhân"
                        ],
                        "items": [
                            "Giai cấp công nhân là ________ và có tinh thần cách mạng triệt để",
                            "Thực hiện sự nghiệp giải phóng thế giới ấy, đó là sứ mệnh lịch sử của ________ hiện đại",
                            "Sứ mệnh lịch sử của giai cấp công nhân là ________ khỏi áp bức, bất công, bóc lột"
                        ],
                        "matches": [
                            [
                                "giai cấp cách mạng"
                            ],
                            [
                                "giai cấp vô sản"
                            ],
                            [
                                "giải phóng con người"
                            ]
                        ]
                    },
                    {
                        "type": "truefalse",
                        "text": "Chọn đáp án (Đúng hoặc Sai) với từng phát biểu sau:",
                        "items": [
                            {
                                "text": "Giai cấp công nhân Việt Nam là tầng lớp giàu có, ít chịu áp bức bóc lột",
                                "correct": false
                            },
                            {
                                "text": "Giai cấp công nhân Việt Nam hiện nay đa dạng về cơ cấu nghề nghiệp, có mặt trong mọi thành phần kinh tế",
                                "correct": true
                            },
                            {
                                "text": "Giai cấp công nhân Việt Nam không có sự liên kết với các lực lượng cách mạng khác",
                                "correct": false
                            },
                            {
                                "text": "Giai cấp công nhân Việt Nam hiện nay đã tăng nhanh về số lượng và chất lượng",
                                "correct": true
                            }
                        ]
                    },
                    {
                        "type": "truefalse",
                        "text": "Chọn đáp án (Đúng hoặc Sai) với từng phát biểu sau:",
                        "items": [
                            {
                                "text": "Giai cấp công nhân đại diện cho phương thức sản xuất tiên tiến và lực lượng sản xuất hiện đại",
                                "correct": true
                            },
                            {
                                "text": "Sự trưởng thành của Đảng Cộng sản – Hạt nhân chính trị quan trọng của giai cấp công nhân",
                                "correct": true
                            },
                            {
                                "text": "Đảng Cộng sản là nhân tố khách quan quan trọng nhất để giai cấp công nhân thực hiện thắng lợi sứ mệnh lịch sử của mình",
                                "correct": false
                            },
                            {
                                "text": "Giai cấp công nhân Việt Nam hiện nay đã tăng cả về số lượng và chất lượng",
                                "correct": true
                            }
                        ]
                    },
                    {
                        "type": "drag",
                        "text": "Kéo thả các yếu tố sau đây vào cột tương ứng:",
                        "draggables": [
                            "Địa vị chính trị - xã hội của giai cấp công nhân",
                            "Đảng Cộng sản",
                            "Địa vị kinh tế của giai cấp công nhân",
                            "Sự phát triển của bản thân giai cấp công nhân cả về số lượng và chất lượng"
                        ],
                        "items": [
                            "Điều kiện khách quan quy định sứ mệnh lịch sử của giai cấp công nhân",
                            "Điều kiện chủ quan để giai cấp công nhân thực hiện được sứ mệnh lịch sử"
                        ],
                        "matches": [
                            [
                                "Địa vị kinh tế của giai cấp công nhân",
                                "Địa vị chính trị - xã hội của giai cấp công nhân"
                            ],
                            [
                                "Đảng Cộng sản",
                                "Sự phát triển của bản thân giai cấp công nhân cả về số lượng và chất lượng"
                            ]
                        ]
                    },
                    {
                        "type": "multi",
                        "text": "Chủ nghĩa xã hội khoa học ra đời dựa trên cơ sở của những tiền đề nào? (Chọn nhiều đáp án)",
                        "opts": [
                            "Tiền đề tư tưởng lý luận",
                            "Tiền đề khoa lịch sử",
                            "Tiền đề khoa học xã hội",
                            "Tiền đề khoa học tự nhiên"
                        ],
                        "correct": [
                            0,
                            3
                        ],
                        "required": 2
                    },
                    {
                        "type": "drag",
                        "text": "Kéo thả các đáp án khớp với các phát biểu từ 1 – 3 vế trái dưới đây:",
                        "draggables": [
                            "tầng lớp nhân dân",
                            "giai cấp, tầng lớp",
                            "Đảng Cộng sản",
                            "tầng lớp trí thức"
                        ],
                        "items": [
                            "Giai cấp công nhân Việt Nam gắn bó mật thiết với các ________ trong xã hội",
                            "Giai cấp công nhân Việt Nam là lực lượng nòng cốt của ________ Việt Nam",
                            "Giai cấp công nhân Việt Nam có mối quan hệ mật thiết với giai cấp nông dân và ________ trong xã hội"
                        ],
                        "matches": [
                            [
                                "giai cấp, tầng lớp"
                            ],
                            [
                                "Đảng Cộng sản"
                            ],
                            [
                                "tầng lớp trí thức"
                            ]
                        ]
                    },
                    {
                        "type": "single",
                        "text": "Tổ chức nào sau đây là đội tiên phong của giai cấp công nhân Việt Nam?",
                        "opts": [
                            "Đảng Cộng sản Việt Nam",
                            "Nhà nước Cộng hòa xã hội chủ nghĩa Việt Nam",
                            "Mặt trận tổ quốc Việt Nam",
                            "Hội Liên hiệp Thanh niên Việt Nam"
                        ],
                        "correct": 0
                    },
                    {
                        "type": "single",
                        "text": "Nội dung cơ bản nhất mà nhờ đó chủ nghĩa xã hội từ không tưởng trở thành khoa học?",
                        "opts": [
                            "Phát hiện ra giai cấp công nhân là lực lượng xã hội có thể thủ tiêu chủ nghĩa tư bản, xây dựng chủ nghĩa xã hội",
                            "Phản ánh đúng khát vọng của nhân dân lao động bị áp bức.",
                            "Chỉ ra sự cần thiết phải thay thế chủ nghĩa tư bản bằng chủ nghĩa xã hội.",
                            "Lên án mạnh mẽ chủ nghĩa tư bản."
                        ],
                        "correct": 0
                    },
                    {
                        "type": "multi",
                        "text": "Những điều kiện khách quan quy định sứ mệnh lịch sử của giai cấp công nhân bao gồm: (Chọn 2 đáp án)",
                        "opts": [
                            "Địa vị kinh tế - xã hội",
                            "Đặc điểm chính trị - xã hội",
                            "Do sự phát triển của lực lượng sản xuất hiện đại",
                            "Giai cấp có lực lượng đông đảo"
                        ],
                        "correct": [
                            0,
                            1
                        ],
                        "required": 2
                    }
                ]
            }
        }
    }
};

let currentSubject = "tenMonHoc";
let currentTopic = "1";
let curQ = 0, answers = {}, results = {}, submitted = false, seconds = 0, timerId = null, totalScore = 0;
function getQ() { return DATA[currentSubject].topics[currentTopic].questions || []; }

function initHome() {
    let subjectsDiv = document.getElementById('subjectsList');
    subjectsDiv.innerHTML = '';
    for (let key in DATA) {
        let card = document.createElement('div');
        card.className = 'subject-card';
        card.innerHTML = `<h3>${DATA[key].name}</h3>`;
        card.onclick = () => loadSubject(key);
        subjectsDiv.appendChild(card);
    }
}

function loadSubject(key) {
    currentSubject = key;
    document.getElementById('subjectName').textContent = DATA[key].name;
    document.getElementById('subjectName').style.display = 'block';
    document.getElementById('backBtn').style.display = 'inline-block';
    document.getElementById('subjectsList').style.display = 'none';
    document.getElementById('topicsList').style.display = 'grid';
    let topicsDiv = document.getElementById('topicsList');
    topicsDiv.innerHTML = '';
    for (let id in DATA[key].topics) {
        let card = document.createElement('div');
        card.className = 'topic-card';
        card.innerHTML = `<h3>${DATA[key].topics[id].name}</h3>`;
        card.onclick = () => loadTopic(id);
        topicsDiv.appendChild(card);
    }
}

function loadTopic(tid) {
    currentTopic = tid;
    curQ = 0; answers = {}; results = {}; submitted = false; totalScore = 0; seconds = 0;
    if (timerId) clearInterval(timerId);
    document.getElementById('homeScreen').style.display = 'none';
    document.getElementById('quizScreen').style.display = 'block';
    document.getElementById('resultScreen').style.display = 'none';
    document.getElementById('topicName').textContent = DATA[currentSubject].topics[tid].name;
    let qs = getQ();
    if (qs.length === 0) {
        document.getElementById('questionContent').innerHTML = '<div style="text-align:center; padding:40px;">📝 Chưa có câu hỏi cho chủ đề này.<br>Hãy thêm câu hỏi sau.</div>';
        document.getElementById('questionNumbers').innerHTML = '';
        return;
    }
    initNumbers(); renderQ(0); startTimer();
}

function backToSubjects() {
    document.getElementById('subjectName').style.display = 'none';
    document.getElementById('backBtn').style.display = 'none';
    document.getElementById('subjectsList').style.display = 'grid';
    document.getElementById('topicsList').style.display = 'none';
}

function initNumbers() {
    let c = document.getElementById('questionNumbers');
    c.innerHTML = '';
    let qs = getQ();
    for (let i = 0; i < qs.length; i++) {
        let d = document.createElement('div');
        d.className = 'q-num';
        if (i === 0) d.classList.add('current');
        d.textContent = i + 1;
        d.onclick = () => { renderQ(i); if (window.innerWidth < 768) toggleList(); };
        c.appendChild(d);
    }
}

function updateNumbers() {
    let nums = document.querySelectorAll('.q-num');
    for (let i = 0; i < nums.length; i++) {
        // Reset lại màu sắc và class cơ bản
        nums[i].classList.remove('current', 'answered');
        nums[i].style.background = '';
        nums[i].style.color = '';

        if (i === curQ) nums[i].classList.add('current');

        // Kiểm tra kết quả câu hỏi nếu đã có đánh giá (results[i])
        if (results[i] !== undefined) {
            nums[i].style.background = results[i] ? '#22c55e' : '#ef4444'; // Đúng: Xanh lá (#22c55e), Sai: Đỏ (#ef4444)
            nums[i].style.color = 'white';
        }
    }
}

function renderQ(idx) {
    let qs = getQ();
    if (qs.length === 0) return;
    curQ = idx;
    updateNumbers();
    let q = qs[idx];
    let c = document.getElementById('questionContent');
    if (q.type === 'single') renderSingle(q, c);
    else if (q.type === 'multi') renderMulti(q, c);
    else if (q.type === 'drag') renderDrag(q, c);
    else if (q.type === 'truefalse') renderTF(q, c);
    else if (q.type === 'fill') renderFill(q, c);
    updateButtons();
}

// ========== SINGLE ==========
function renderSingle(q, c) {
    let saved = answers[curQ] ? answers[curQ][0] : null;
    let locked = submitted || (saved !== null);
    let html = `<div class="question-text">${q.text}</div>`;
    q.opts.forEach((opt, i) => {
        let cls = '';
        if (submitted) {
            if (i === q.correct) cls = 'correct';
            if (saved === i && i !== q.correct) cls = 'wrong';
        } else if (saved !== null) {
            if (i === q.correct) cls = 'correct';
            if (saved === i && i !== q.correct) cls = 'wrong';
        }
        html += `<div class="option-item ${cls}" data-i="${i}">${opt}</div>`;
    });
    if (saved !== null && saved !== q.correct) {
        let correctLetter = String.fromCharCode(65 + q.correct);
        html += `<div class="correct-answer-hint">✅ Đáp án đúng: ${correctLetter}. ${q.opts[q.correct]}</div>`;
    }
    c.innerHTML = html;
    if (!locked) {
        document.querySelectorAll('.option-item').forEach(el => {
            el.onclick = () => {
                let val = parseInt(el.dataset.i);
                answers[curQ] = [val];
                results[curQ] = (val === q.correct);
                updateNumbers();
                renderQ(curQ);
            };
        });
    }
}

// ========== MULTI ==========
function renderMulti(q, c) {
    let saved = answers[curQ] || [];
    let locked = submitted || (saved.length > 0);
    let html = `<div class="question-text">${q.text}</div>`;
    html += `<div class="instruction">✓ Chọn đủ ${q.required} đáp án, sau đó bấm "Xác nhận"</div>`;
    html += `<div id="multiList">`;
    for (let i = 0; i < q.opts.length; i++) {
        let opt = q.opts[i];
        let checked = saved.includes(i) ? 'checked' : '';
        let cls = '';
        if (submitted) {
            if (q.correct.includes(i)) cls = 'correct';
            if (saved.includes(i) && !q.correct.includes(i)) cls = 'wrong';
        } else if (saved.length > 0) {
            if (q.correct.includes(i)) cls = 'correct';
            if (saved.includes(i) && !q.correct.includes(i)) cls = 'wrong';
        }
        html += `<div class="multi-item ${cls}"><input type="checkbox" value="${i}" ${checked} ${locked ? 'disabled' : ''}><span>${opt}</span></div>`;
    }
    html += `</div>`;
    if (!locked && saved.length === 0) {
        html += `<button class="btn btn-primary" style="margin-top:16px;" id="confirmMultiBtn">✅ Xác nhận lựa chọn</button>`;
    }
    c.innerHTML = html;
    
    let tempSelected = [];
    document.querySelectorAll('#multiList input').forEach(cb => {
        cb.onchange = function() {
            if (locked) return;
            let selected = [];
            document.querySelectorAll('#multiList input:checked').forEach(c => selected.push(parseInt(c.value)));
            tempSelected = selected;
        };
    });
    
    let confirmBtn = document.getElementById('confirmMultiBtn');
    if (confirmBtn) {
        confirmBtn.onclick = function() {
            if (tempSelected.length !== q.required) {
                let msg = document.createElement('div');
                msg.style.position = 'fixed';
                msg.style.bottom = '20px';
                msg.style.left = '50%';
                msg.style.transform = 'translateX(-50%)';
                msg.style.background = '#ef4444';
                msg.style.color = 'white';
                msg.style.padding = '8px 16px';
                msg.style.borderRadius = '40px';
                msg.style.fontSize = '12px';
                msg.style.zIndex = '1000';
                msg.innerText = `Vui lòng chọn đúng ${q.required} đáp án!`;
                document.body.appendChild(msg);
                setTimeout(() => msg.remove(), 1500);
                return;
            }
            let correct = JSON.stringify(tempSelected.sort()) === JSON.stringify(q.correct.sort());
            answers[curQ] = tempSelected;
            results[curQ] = correct;
            document.querySelectorAll('#multiList .multi-item').forEach((item, idx) => {
                let cb = item.querySelector('input');
                if (q.correct.includes(idx)) {
                    item.classList.add('correct');
                } else if (cb.checked && !q.correct.includes(idx)) {
                    item.classList.add('wrong');
                }
            });
            if (!correct) {
                let correctLetters = q.correct.map(i => String.fromCharCode(65 + i)).join(', ');
                let hintDiv = document.createElement('div');
                hintDiv.className = 'correct-answer-hint';
                hintDiv.innerHTML = `✅ Đáp án đúng: ${correctLetters}`;
                document.getElementById('multiList').after(hintDiv);
            }
            updateNumbers();
            renderQ(curQ);
        };
    }
}

// ========== TRUE FALSE ==========
function renderTF(q, c) {
    let saved = answers[curQ] || {};
    let locked = submitted;
    let html = `<div class="question-text">${q.text}</div>`;
    html += `<div class="instruction">✓ Chọn đáp án, kết quả hiện ngay</div>`;
    
    for (let idx = 0; idx < q.items.length; idx++) {
        let item = q.items[idx];
        let val = saved[idx];
        let btnTrueClass = (val === true) ? 'true-active' : '';
        let btnFalseClass = (val === false) ? 'false-active' : '';
        let itemClass = '';
        if (submitted || val !== undefined) {
            if (val === item.correct) itemClass = 'correct';
            else if (val !== undefined) itemClass = 'wrong';
        }
        html += `<div class="tf-item ${itemClass}" data-idx="${idx}">
                    <div class="tf-row">
                        <div class="tf-text">${idx+1}. ${item.text}</div>
                        <div class="tf-buttons">
                            <button class="${btnTrueClass}" data-val="true">Đúng</button>
                            <button class="${btnFalseClass}" data-val="false">Sai</button>
                        </div>
                    </div>
                 </div>`;
    }
    c.innerHTML = html;
    
    document.querySelectorAll('.tf-buttons button').forEach(btn => {
        btn.onclick = function(e) {
            e.stopPropagation();
            if (submitted) return;
            let parent = this.closest('.tf-item');
            let idx = parseInt(parent.dataset.idx);
            let value = this.dataset.val === 'true';
            let qq = getQ()[curQ];
            
            let newAnswers = { ...answers[curQ], [idx]: value };
            answers[curQ] = newAnswers;
            
            let isCorrect = (value === qq.items[idx].correct);
            if (isCorrect) {
                parent.classList.add('correct');
                parent.classList.remove('wrong');
            } else {
                parent.classList.add('wrong');
                parent.classList.remove('correct');
            }
            
            parent.querySelectorAll('button').forEach(b => {
                b.classList.remove('true-active', 'false-active');
            });
            this.classList.add(value ? 'true-active' : 'false-active');
            
            let allCorrect = true;
            for (let i = 0; i < qq.items.length; i++) {
                if (newAnswers[i] !== qq.items[i].correct) {
                    allCorrect = false;
                    break;
                }
            }
            results[curQ] = allCorrect;
            updateNumbers();
        };
    });
}


// ========== DRAG - NÚT KIỂM TRA HIỂN NGAY TỪ ĐẦU ==========
let tempDrag = {};
let selectedDragItem = null;

function renderDrag(q, c) {
    let savedData = answers[curQ] || {};
    
    let html = `<div class="question-text">${q.text}</div><div id="dragWrap"></div>`;
    
    if (!submitted) {
        html += `<button class="btn btn-primary" style="margin-top:16px;" id="confirmDragBtn">✅ Kiểm tra</button>`;
    }
    c.innerHTML = html;
    
    let wrap = document.getElementById('dragWrap');
    let pool = document.createElement('div');
    pool.className = 'drag-pool';
    pool.setAttribute('data-pool', 'true');
    
    let style = document.createElement('style');
    style.textContent = `
        .drag-item { cursor: grab; transition: all 0.2s; user-select: none; display: inline-block; margin: 5px; touch-action: manipulation; }
        .drag-item:active { cursor: grabbing; }
        .drag-item.selected-drag { background: #3b82f6; color: white; border-color: #3b82f6; transform: scale(1.02); box-shadow: 0 4px 12px rgba(59,130,246,0.3); }
        .drag-item.dragging { opacity: 0.5; }
        .drag-item.correct { background: #dcfce7; border-color: #22c55e; }
        .drag-item.wrong { background: #fee2e2; border-color: #ef4444; }
        .drop-zone { min-height: 80px; padding: 12px; border: 2px dashed #94a3b8; border-radius: 16px; background: #fafafa; transition: all 0.2s; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; touch-action: manipulation; }
        .drop-zone.drag-over { background: #e3f2fd; border-color: #3b82f6; border-style: solid; }
        .drop-placeholder { color: #999; font-style: italic; font-size: 12px; width: 100%; text-align: center; }
        .drag-pool { display: flex; flex-wrap: wrap; gap: 10px; padding: 16px; background: #eff6ff; border-radius: 20px; margin: 16px 0; border: 2px dashed #3b82f6; min-height: 80px; }
        .drop-zones { display: grid; gap: 16px; margin-top: 16px; }
        .correct-answer-hint { font-size: 13px; margin-top: 8px; padding: 10px 12px; background: #f1f5f9; border-radius: 12px; color: #16a34a; border-left: 4px solid #22c55e; }
        @media (min-width: 640px) { .drop-zones { grid-template-columns: repeat(2, 1fr); } }
    `;
    document.head.appendChild(style);
    
    let used = [];
    Object.values(savedData).forEach(arr => { if (arr && Array.isArray(arr)) used.push(...arr); });
    
    for (let idx = 0; idx < q.draggables.length; idx++) {
        let text = q.draggables[idx];
        if (!used.includes(text)) {
            let d = document.createElement('div');
            d.className = 'drag-item';
            d.textContent = text;
            d.setAttribute('data-text', text);
            d.setAttribute('data-original-index', idx);
            d.draggable = true;
            
            d.addEventListener('dragstart', (e) => {
                if (submitted) { e.preventDefault(); return false; }
                e.dataTransfer.setData('text/plain', text);
                e.dataTransfer.effectAllowed = 'move';
                d.classList.add('dragging');
            });
            d.addEventListener('dragend', () => d.classList.remove('dragging'));
            
            d.onclick = (e) => {
                e.stopPropagation();
                if (submitted) return;
                if (selectedDragItem) selectedDragItem.classList.remove('selected-drag');
                selectedDragItem = d;
                selectedDragItem.classList.add('selected-drag');
            };
            
            d.ondblclick = (e) => {
                e.stopPropagation();
                if (submitted) return;
                autoMoveToFirstEmptyZone(d, q);
            };
            pool.appendChild(d);
        }
    }
    
    let zones = document.createElement('div');
    zones.className = 'drop-zones';
    
    for (let idx = 0; idx < q.items.length; idx++) {
        let label = q.items[idx];
        let col = document.createElement('div');
        col.className = 'drop-col';
        col.innerHTML = `<div class="drop-title">${label}</div>`;
        
        let zone = document.createElement('div');
        zone.className = 'drop-zone';
        zone.dataset.idx = idx;
        
        if (savedData[idx] && savedData[idx].length > 0) {
            for (let text of savedData[idx]) {
                let d = document.createElement('div');
                d.className = 'drag-item';
                d.textContent = text;
                d.setAttribute('data-text', text);
                d.draggable = true;
                
                d.addEventListener('dragstart', (e) => {
                    if (submitted) { e.preventDefault(); return false; }
                    e.dataTransfer.setData('text/plain', text);
                    e.dataTransfer.effectAllowed = 'move';
                    d.classList.add('dragging');
                });
                d.addEventListener('dragend', () => d.classList.remove('dragging'));
                
                d.onclick = (e) => {
                    e.stopPropagation();
                    if (submitted) return;
                    if (selectedDragItem) selectedDragItem.classList.remove('selected-drag');
                    selectedDragItem = d;
                    selectedDragItem.classList.add('selected-drag');
                };
                
                d.ondblclick = (e) => {
                    e.stopPropagation();
                    if (submitted) return;
                    moveToPool(d, q, idx);
                };
                zone.appendChild(d);
            }
        } else {
            zone.innerHTML = '<div class="drop-placeholder">🔽 Kéo thả hoặc chạm chọn thẻ rồi chạm vào đây</div>';
        }
        
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            zone.classList.add('drag-over');
        });
        
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            if (submitted) return;
            
            let text = e.dataTransfer.getData('text/plain');
            if (!text) return;
            
            let sourceItem = null, sourceZone = null, sourceIdx = null;
            let poolItems = pool.querySelectorAll('.drag-item');
            for (let item of poolItems) {
                if (item.textContent === text) { sourceItem = item; break; }
            }
            
            if (!sourceItem) {
                for (let i = 0; i < q.items.length; i++) {
                    let otherZone = document.querySelector(`.drop-zone[data-idx="${i}"]`);
                    if (otherZone) {
                        let items = otherZone.querySelectorAll('.drag-item');
                        for (let item of items) {
                            if (item.textContent === text) {
                                sourceItem = item; sourceZone = otherZone; sourceIdx = i; break;
                            }
                        }
                    }
                    if (sourceItem) break;
                }
            }
            if (!sourceItem) return;
            
            let newData = JSON.parse(JSON.stringify(savedData));
            if (sourceZone) {
                if (newData[sourceIdx]) {
                    newData[sourceIdx] = newData[sourceIdx].filter(t => t !== text);
                    if (newData[sourceIdx].length === 0) {
                        sourceZone.innerHTML = '<div class="drop-placeholder">🔽 Kéo thả hoặc chạm chọn thẻ rồi chạm vào đây</div>';
                    } else {
                        sourceZone.innerHTML = '';
                        newData[sourceIdx].forEach(t => sourceZone.appendChild(createDragItem(t)));
                    }
                }
                sourceItem.remove();
            } else {
                sourceItem.remove();
            }
            
            let placeholder = zone.querySelector('.drop-placeholder');
            if (placeholder) placeholder.remove();
            
            zone.appendChild(createDragItem(text));
            if (!newData[zone.dataset.idx]) newData[zone.dataset.idx] = [];
            newData[zone.dataset.idx].push(text);
            savedData = newData;
            answers[curQ] = savedData;
            
            if (selectedDragItem) {
                selectedDragItem.classList.remove('selected-drag');
                selectedDragItem = null;
            }
            renderQ(curQ);
        });
        
        zone.onclick = (e) => {
            e.stopPropagation();
            if (submitted) return;
            if (!selectedDragItem) return;
            
            let text = selectedDragItem.getAttribute('data-text') || selectedDragItem.textContent;
            let targetIdx = parseInt(zone.dataset.idx);
            let sourceZone = selectedDragItem.parentElement;
            let sourceIdx = sourceZone.classList.contains('drop-zone') ? parseInt(sourceZone.dataset.idx) : null;
            let newData = JSON.parse(JSON.stringify(savedData));
            
            if (sourceZone && sourceZone.classList.contains('drop-zone')) {
                if (newData[sourceIdx]) {
                    newData[sourceIdx] = newData[sourceIdx].filter(t => t !== text);
                    if (newData[sourceIdx].length === 0) {
                        sourceZone.innerHTML = '<div class="drop-placeholder">🔽 Kéo thả hoặc chạm chọn thẻ rồi chạm vào đây</div>';
                    } else {
                        sourceZone.innerHTML = '';
                        newData[sourceIdx].forEach(t => sourceZone.appendChild(createDragItem(t)));
                    }
                }
                selectedDragItem.remove();
            } else if (sourceZone && sourceZone.classList.contains('drag-pool')) {
                selectedDragItem.remove();
            }
            
            let placeholder = zone.querySelector('.drop-placeholder');
            if (placeholder) placeholder.remove();
            
            zone.appendChild(createDragItem(text));
            if (!newData[targetIdx]) newData[targetIdx] = [];
            newData[targetIdx].push(text);
            savedData = newData;
            answers[curQ] = savedData;
            
            selectedDragItem.classList.remove('selected-drag');
            selectedDragItem = null;
            renderQ(curQ);
        };
        
        col.appendChild(zone);
        zones.appendChild(col);
    }
    
    wrap.appendChild(pool);
    wrap.appendChild(zones);
    
    function createDragItem(text) {
        let d = document.createElement('div');
        d.className = 'drag-item';
        d.textContent = text;
        d.setAttribute('data-text', text);
        d.draggable = true;
        
        d.addEventListener('dragstart', (e) => {
            if (submitted) { e.preventDefault(); return false; }
            e.dataTransfer.setData('text/plain', text);
            e.dataTransfer.effectAllowed = 'move';
            d.classList.add('dragging');
        });
        d.addEventListener('dragend', () => d.classList.remove('dragging'));
        d.onclick = (e) => {
            e.stopPropagation();
            if (submitted) return;
            if (selectedDragItem) selectedDragItem.classList.remove('selected-drag');
            selectedDragItem = d;
            selectedDragItem.classList.add('selected-drag');
        };
        return d;
    }
    
    function moveToPool(item, q, zoneIdx) {
        let text = item.getAttribute('data-text') || item.textContent;
        let newData = JSON.parse(JSON.stringify(savedData));
        if (newData[zoneIdx]) {
            newData[zoneIdx] = newData[zoneIdx].filter(t => t !== text);
            if (newData[zoneIdx].length === 0) {
                let zone = document.querySelector(`.drop-zone[data-idx="${zoneIdx}"]`);
                if (zone) zone.innerHTML = '<div class="drop-placeholder">🔽 Kéo thả hoặc chạm chọn thẻ rồi chạm vào đây</div>';
            }
        }
        savedData = newData;
        item.remove();
        
        let pool = document.querySelector('.drag-pool');
        let newItem = createDragItem(text);
        newItem.ondblclick = (e) => {
            e.stopPropagation();
            if (submitted) return;
            autoMoveToFirstEmptyZone(newItem, q);
        };
        pool.appendChild(newItem);
        answers[curQ] = savedData;
        if (selectedDragItem === item) {
            selectedDragItem.classList.remove('selected-drag');
            selectedDragItem = null;
        }
        renderQ(curQ);
    }
    
    function autoMoveToFirstEmptyZone(item, q) {
        let text = item.getAttribute('data-text') || item.textContent;
        let emptyZoneIdx = -1;
        for (let i = 0; i < q.items.length; i++) {
            if (!savedData[i] || savedData[i].length === 0) {
                emptyZoneIdx = i;
                break;
            }
        }
        if (emptyZoneIdx === -1) return;
        
        let sourceZone = item.parentElement;
        let sourceIdx = sourceZone.classList.contains('drop-zone') ? parseInt(sourceZone.dataset.idx) : null;
        let newData = JSON.parse(JSON.stringify(savedData));
        
        if (sourceZone && sourceZone.classList.contains('drop-zone')) {
            if (newData[sourceIdx]) {
                newData[sourceIdx] = newData[sourceIdx].filter(t => t !== text);
                if (newData[sourceIdx].length === 0) {
                    sourceZone.innerHTML = '<div class="drop-placeholder">🔽 Kéo thả hoặc chạm chọn thẻ rồi chạm vào đây</div>';
                } else {
                    sourceZone.innerHTML = '';
                    newData[sourceIdx].forEach(t => sourceZone.appendChild(createDragItem(t)));
                }
            }
            item.remove();
        } else if (sourceZone && sourceZone.classList.contains('drag-pool')) {
            item.remove();
        }
        
        let targetZone = document.querySelector(`.drop-zone[data-idx="${emptyZoneIdx}"]`);
        if (targetZone) {
            let placeholder = targetZone.querySelector('.drop-placeholder');
            if (placeholder) placeholder.remove();
            targetZone.appendChild(createDragItem(text));
            if (!newData[emptyZoneIdx]) newData[emptyZoneIdx] = [];
            newData[emptyZoneIdx].push(text);
            savedData = newData;
        }
        answers[curQ] = savedData;
        if (selectedDragItem === item) {
            selectedDragItem.classList.remove('selected-drag');
            selectedDragItem = null;
        }
        renderQ(curQ);
    }
    
    // NÚT KIỂM TRA
    let confirmBtn = document.getElementById('confirmDragBtn');
    if (confirmBtn) {
        confirmBtn.onclick = function() {
            let currentData = answers[curQ] || {};
            
            document.querySelectorAll('.correct-answer-hint').forEach(div => div.remove());
            
            let hintDiv = document.createElement('div');
            hintDiv.className = 'correct-answer-hint';
            let correctHtml = '<strong>✅ Đáp án đúng:</strong><br>';
            for (let i = 0; i < q.items.length; i++) {
                let correctAnswers = q.matches[i].join(', ');
                correctHtml += `${q.items[i]} ☑️ <strong>${correctAnswers}</strong><br>`;
            }
            hintDiv.innerHTML = correctHtml;
            document.getElementById('questionContent').appendChild(hintDiv);
            
            for (let i = 0; i < q.items.length; i++) {
                let zone = document.querySelector(`.drop-zone[data-idx="${i}"]`);
                if (zone) {
                    let items = zone.querySelectorAll('.drag-item');
                    let correctList = q.matches[i];
                    items.forEach(item => {
                        let text = item.textContent.trim();
                        if (correctList.includes(text)) {
                            item.classList.add('correct');
                            item.classList.remove('wrong');
                        } else {
                            item.classList.add('wrong');
                            item.classList.remove('correct');
                        }
                    });
                }
            }
            
            // LOGIC TÍNH ĐIỂM CÂU HỎI MỚI (Bỏ qua các thẻ dư trong pool)
            let allCorrect = true;
            for (let i = 0; i < q.items.length; i++) {
                let user = (currentData[i] || []).slice();
                let match = (q.matches[i] || []).slice();
                if (JSON.stringify(user.sort()) !== JSON.stringify(match.sort())) {
                    allCorrect = false;
                    break;
                }
            }
            
            results[curQ] = allCorrect;
            updateNumbers();
        };
    }
}

function renderFill(q, c) {
    let locked = submitted || (answers[curQ] && answers[curQ].locked);
    let saved = answers[curQ] || [];
    let html = `<div class="question-text">${q.text}</div><div id="fillList"></div>`;
    if (!locked) html += `<button class="btn btn-primary" style="margin-top:16px;" id="checkFillBtn">✅ Kiểm tra</button>`;
    c.innerHTML = html;
    
    let fillDiv = document.getElementById('fillList');
    if (!answers[curQ]) answers[curQ] = [];
    
    for (let idx = 0; idx < q.items.length; idx++) {
        let item = q.items[idx];
        let div = document.createElement('div');
        div.style.marginBottom = '16px';
        
        let txt = '<div class="fill-text">';
        
        // Kiểm tra xem văn bản có chứa chỗ trống không
        if (item.text.includes('________')) {
            let parts = item.text.split('________');
            for (let i = 0; i < parts.length; i++) {
                txt += parts[i];
                if (i < parts.length - 1) {
                    let savedVal = saved[idx]?.[i] || '';
                    let isCorrect = (locked && savedVal && item.answers.some(a => a.toLowerCase() === savedVal.toLowerCase()));
                    let inputClass = (locked && savedVal) ? (isCorrect ? 'correct' : 'wrong') : '';
                    txt += `<input type="text" class="fill-input ${inputClass}" data-item="${idx}" data-blank="${i}" value="${savedVal}" ${locked ? 'disabled' : ''}>`;
                }
            }
        } else {
            // Nếu không có '________', hiển thị text + chèn 1 ô input phía dưới/sau câu
            let savedVal = saved[idx]?.[0] || '';
            let isCorrect = (locked && savedVal && item.answers.some(a => a.toLowerCase() === savedVal.toLowerCase()));
            let inputClass = (locked && savedVal) ? (isCorrect ? 'correct' : 'wrong') : '';
            txt += `${item.text} <br><input type="text" class="fill-input ${inputClass}" data-item="${idx}" data-blank="0" placeholder="Nhập đáp án..." value="${savedVal}" ${locked ? 'disabled' : ''}>`;
        }
        
        txt += '</div>';
        div.innerHTML = txt;
        fillDiv.appendChild(div);
        
        // Hiển thị gợi ý đáp án đúng khi sai
        if (locked && (!results[curQ] || !answers[curQ][idx])) {
            let hintDiv = document.createElement('div');
            hintDiv.className = 'correct-answer-hint';
            hintDiv.innerHTML = `✅ Đáp án đúng: ${item.answers.join(' hoặc ')}`;
            div.appendChild(hintDiv);
        }
    }
    
    if (!locked) {
        document.querySelectorAll('.fill-input').forEach(inp => {
            inp.oninput = function() {
                let it = parseInt(this.dataset.item);
                let bl = parseInt(this.dataset.blank);
                if (!answers[curQ][it]) answers[curQ][it] = [];
                answers[curQ][it][bl] = this.value;
            };
        });
    }
    
    let checkBtn = document.getElementById('checkFillBtn');
    if (checkBtn) {
        checkBtn.onclick = function() {
            if (submitted) return;
            let qq = getQ()[curQ];
            let inputs = document.querySelectorAll('.fill-input');
            inputs.forEach(inp => {
                let it = parseInt(inp.dataset.item);
                let bl = parseInt(inp.dataset.blank);
                if (!answers[curQ][it]) answers[curQ][it] = [];
                answers[curQ][it][bl] = inp.value;
            });
            answers[curQ].locked = true;
            let allCorrect = true;
            for (let i = 0; i < qq.items.length; i++) {
                let item = qq.items[i];
                let userVal = answers[curQ][i]?.[0] || '';
                let isCorrect = item.answers.some(a => a.toLowerCase() === userVal.toLowerCase());
                if (!isCorrect) allCorrect = false;
            }
            results[curQ] = allCorrect;
            updateNumbers();
            renderQ(curQ);
        };
    }
}

function toggleList() { let c = document.getElementById('numbersContainer'); let a = document.getElementById('listArrow'); if (c.classList.contains('show')) { c.classList.remove('show'); a.textContent = '▼'; } else { c.classList.add('show'); a.textContent = '▲'; } }
function shuffleAll() { 
    if (submitted) return; 
    let qs = getQ(); 
    if (qs.length === 0) return; 
    
    // 1. Đảo thứ tự câu hỏi
    for (let i = qs.length - 1; i > 0; i--) { 
        let j = Math.floor(Math.random() * (i + 1)); 
        [qs[i], qs[j]] = [qs[j], qs[i]]; 
    } 
    
    // 2. Đảo thứ tự đáp án trong từng câu (nếu có options)
    for (let i = 0; i < qs.length; i++) {
        let q = qs[i];
        
        // Xử lý câu 1 đáp án và nhiều đáp án
        if ((q.type === "single" || q.type === "multi") && q.opts && q.opts.length > 0) {
            // Tạo mảng tạm với đáp án và thông tin đúng/sai
            let temp = q.opts.map((opt, idx) => ({
                text: opt,
                isCorrect: q.type === "single" 
                    ? (idx === q.correct) 
                    : q.correct.includes(idx)
            }));
            
            // Đảo thứ tự
            for (let k = temp.length - 1; k > 0; k--) {
                let r = Math.floor(Math.random() * (k + 1));
                [temp[k], temp[r]] = [temp[r], temp[k]];
            }
            
            // Cập nhật lại options
            q.opts = temp.map(x => x.text);
            
            // Cập nhật lại đáp án đúng
            if (q.type === "single") {
                q.correct = temp.findIndex(x => x.isCorrect);
            } else {
                q.correct = temp.map((x, idx) => x.isCorrect ? idx : -1).filter(i => i !== -1);
            }
        }
        
        // Xử lý câu đúng/sai (truefalse) - đảo thứ tự các phát biểu
        if (q.type === "truefalse" && q.items && q.items.length > 0) {
            for (let k = q.items.length - 1; k > 0; k--) {
                let r = Math.floor(Math.random() * (k + 1));
                [q.items[k], q.items[r]] = [q.items[r], q.items[k]];
            }
        }
        
        // Xử lý câu kéo thả (drag) - đảo thứ tự items và draggables
        if (q.type === "drag") {
            if (q.items && q.items.length > 0) {
                for (let k = q.items.length - 1; k > 0; k--) {
                    let r = Math.floor(Math.random() * (k + 1));
                    [q.items[k], q.items[r]] = [q.items[r], q.items[k]];
                    [q.matches[k], q.matches[r]] = [q.matches[r], q.matches[k]];
                }
            }
            if (q.draggables && q.draggables.length > 0) {
                for (let k = q.draggables.length - 1; k > 0; k--) {
                    let r = Math.floor(Math.random() * (k + 1));
                    [q.draggables[k], q.draggables[r]] = [q.draggables[r], q.draggables[k]];
                }
            }
        }
        
        // Xử lý câu điền từ (fill) - đảo thứ tự items
        if (q.type === "fill" && q.items && q.items.length > 0) {
            for (let k = q.items.length - 1; k > 0; k--) {
                let r = Math.floor(Math.random() * (k + 1));
                [q.items[k], q.items[r]] = [q.items[r], q.items[k]];
            }
        }
    }
    
    // Reset lại dữ liệu đã làm
    answers = {}; 
    results = {}; 
    curQ = 0; 
    initNumbers(); 
    renderQ(0); 
}
function resetCurrent() { if (submitted) return; delete answers[curQ]; delete results[curQ]; renderQ(curQ); updateNumbers(); }
function updateButtons() { let qs = getQ(); if (qs.length === 0) return; let p = document.getElementById('prevBtn'); let n = document.getElementById('nextBtn'); let s = document.getElementById('submitBtn'); p.disabled = curQ === 0; if (curQ === qs.length - 1) { n.style.display = 'none'; s.style.display = 'inline-block'; } else { n.style.display = 'inline-block'; s.style.display = 'none'; } }
function prev() { if (curQ > 0) renderQ(curQ - 1); }
function next() { let qs = getQ(); if (curQ < qs.length - 1) renderQ(curQ + 1); }
function submitQuiz() { if (timerId) clearInterval(timerId); submitted = true; totalScore = 0; let qs = getQ(); qs.forEach((q, idx) => { let ans = answers[idx]; let correct = false; if (ans) { if (q.type === 'single') correct = (ans[0] === q.correct); else if (q.type === 'multi') { correct = JSON.stringify(ans.sort()) === JSON.stringify(q.correct.sort()); } else if (q.type === 'truefalse') { let cnt = 0; q.items.forEach((it, i) => { if (ans[i] === it.correct) cnt++; }); correct = (cnt === q.items.length); } else if (q.type === 'drag') { let ok = true; q.matches.forEach((match, i) => { let u = ans[i] || []; if (JSON.stringify(u.sort()) !== JSON.stringify(match.sort())) ok = false; }); correct = ok; } else if (q.type === 'fill') { let ok = true; q.items.forEach((item, i) => { let userVal = ans[i]?.[0] || ''; if (!item.answers.some(a => a.toLowerCase() === userVal.toLowerCase())) ok = false; }); correct = ok; } } if (correct) { totalScore++; results[idx] = true; } else if (ans) results[idx] = false; }); updateNumbers(); showResult(); }
function showResult() { let total = getQ().length; document.getElementById('quizScreen').style.display = 'none'; document.getElementById('resultScreen').style.display = 'block'; document.getElementById('finalScore').textContent = `${totalScore}/${total}`; document.getElementById('finalTime').textContent = formatTime(seconds); document.getElementById('scale10').textContent = ((totalScore / total) * 10).toFixed(1); document.getElementById('correctCount').textContent = totalScore; document.getElementById('wrongCount').textContent = total - totalScore; document.getElementById('detailArea').style.display = 'none'; }
function showDetail() { let d = document.getElementById('detailArea'); let qs = getQ(); d.innerHTML = '<h4 style="margin-bottom:16px;">📋 Chi tiết từng câu</h4>'; qs.forEach((q, idx) => { let isCorrect = results[idx]; let icon = isCorrect ? '✅' : '❌'; let userText = 'Chưa làm'; if (answers[idx]) { if (q.type === 'single') userText = q.opts[answers[idx][0]]; else if (q.type === 'multi') userText = answers[idx].map(i => q.opts[i]).join(', '); else if (q.type === 'truefalse') { let arr = []; q.items.forEach((it, i) => { if (answers[idx][i] !== undefined) arr.push(`${i+1}. ${answers[idx][i] ? 'Đúng' : 'Sai'}`); }); userText = arr.join('; '); } else if (q.type === 'drag') { let arr = []; q.items.forEach((it, i) => { if (answers[idx][i]) arr.push(`${q.items[i]} ${answers[idx][i].join(', ')}`); }); userText = arr.join('; '); } else if (q.type === 'fill') { let arr = []; q.items.forEach((it, i) => { if (answers[idx][i]) arr.push(`${answers[idx][i].join(', ')}`); }); userText = arr.join('; '); } } let correctText = ''; if (q.type === 'single') correctText = q.opts[q.correct]; else if (q.type === 'multi') correctText = q.correct.map(i => q.opts[i]).join(', '); else if (q.type === 'truefalse') correctText = q.items.map((it, i) => `${i+1}. ${it.correct ? 'Đúng' : 'Sai'}`).join('; '); else if (q.type === 'drag') correctText = q.matches.map((m, i) => `${q.items[i]} ${m.join(', ')}`).join('; '); else if (q.type === 'fill') correctText = q.items.map((it, i) => it.answers.join(' hoặc ')).join('; '); let div = document.createElement('div'); div.className = `review-item ${isCorrect ? 'correct' : 'wrong'}`; div.innerHTML = `<div><strong>${icon} Câu ${idx+1}:</strong> ${q.text.substring(0, 80)}</div><div>📝 Bạn chọn: ${userText || 'Chưa làm'}</div><div>✅ Đáp án đúng: ${correctText}</div>`; d.appendChild(div); }); d.style.display = 'block'; }
function retry() { loadTopic(currentTopic); }
function goHome() { if (timerId) clearInterval(timerId); document.getElementById('homeScreen').style.display = 'block'; document.getElementById('quizScreen').style.display = 'none'; document.getElementById('resultScreen').style.display = 'none'; initHome(); }
function startTimer() { if (timerId) clearInterval(timerId); seconds = 0; updateTimer(); timerId = setInterval(() => { seconds++; updateTimer(); }, 1000); }
function updateTimer() { let m = Math.floor(seconds / 60).toString().padStart(2, '0'); let s = (seconds % 60).toString().padStart(2, '0'); document.getElementById('timer').textContent = `${m}:${s}`; }
// ... các hàm khác ...

function formatTime(sec) {
    let m = Math.floor(sec / 60).toString().padStart(2, '0');
    let s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

// ========== THÊM SỰ KIỆN BẤM ENTER VÀO ĐÂY ==========
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        let qs = getQ();
        if (qs.length === 0) return;
        if (curQ < qs.length - 1) {
            next();
        } else {
            if (document.getElementById('submitBtn').style.display === 'inline-block') {
                submitQuiz();
            } else {
                next();
            }
        }
    }
});

// ==========================================
// THUẬT TOÁN & TÍNH NĂNG TÌM KIẾM CÂU HỎI & ĐÁP ÁN
// ==========================================

// Hàm loại bỏ dấu tiếng Việt để so sánh chuỗi không dấu
function removeVietnameseTones(str) {
    if (!str) return '';
    str = str.toLowerCase();
    str = str.replace(/à|á|ạ|ả|ã|â|ầ|ấ|ậ|ẩ|ẫ|ă|ằ|ắ|ặ|ẳ|ẵ/g, "a");
    str = str.replace(/è|é|ẹ|ẻ|ẽ|ê|ề|ế|ệ|ể|ễ/g, "e");
    str = str.replace(/ì|í|ị|ỉ|ĩ/g, "i");
    str = str.replace(/ò|ó|ọ|ỏ|õ|ô|ồ|ố|ộ|ổ|ỗ|ơ|ờ|ớ|ợ|ở|ỡ/g, "o");
    str = str.replace(/ù|ú|ụ|ủ|ũ|ư|ừ|ứ|ự|ử|ữ/g, "u");
    str = str.replace(/ỳ|ý|ỵ|ỷ|ỹ/g, "y");
    str = str.replace(/đ/g, "d");
    return str;
}

// Hàm Tô sáng từ khóa (Highlight)
function highlightText(text, keyword) {
    if (!keyword || !text) return text;
    let normalizedText = removeVietnameseTones(text);
    let normalizedKw = removeVietnameseTones(keyword);
    let index = normalizedText.indexOf(normalizedKw);
    if (index === -1) return text;
    
    // Cắt từ bản gốc để giữ đúng ký tự hoa/thường/dấu ban đầu
    let matchedText = text.substring(index, index + keyword.length);
    
    // Sửa lỗi escape ký tự đặc biệt Regex tại đây
    let escapedText = matchedText.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
    let regex = new RegExp(escapedText, 'gi');
    
    return text.replace(regex, (match) => `<span class="highlight-keyword">${match}</span>`);
}

// Xử lý khi gõ từ khóa tìm kiếm
function handleSearch() {
    let input = document.getElementById('searchInput');
    let clearBtn = document.getElementById('clearSearchBtn');
    let searchArea = document.getElementById('searchResultsArea');
    let defaultHome = document.getElementById('defaultHomeContent');
    let keyword = input.value.trim();

    if (keyword === '') {
        clearBtn.style.display = 'none';
        searchArea.style.display = 'none';
        defaultHome.style.display = 'block';
        return;
    }

    clearBtn.style.display = 'flex';
    searchArea.style.display = 'block';
    defaultHome.style.display = 'none';

    executeSearch(keyword);
}

// Xóa từ khóa tìm kiếm
function clearSearch() {
    let input = document.getElementById('searchInput');
    input.value = '';
    handleSearch();
}

// Thuật toán duyệt qua cấu trúc DATA để tìm câu hỏi trùng khớp
function executeSearch(keyword) {
    let normalizedKw = removeVietnameseTones(keyword);
    let searchResults = [];

    // Duyệt qua tất cả các Môn học -> Bài học -> Câu hỏi
    for (let sKey in DATA) {
        let subject = DATA[sKey];
        for (let tKey in subject.topics) {
            let topic = subject.topics[tKey];
            let questions = topic.questions || [];

            questions.forEach((q, qIndex) => {
                let matchFound = false;

                // 1. Tìm trong nội dung câu hỏi
                if (removeVietnameseTones(q.text).includes(normalizedKw)) {
                    matchFound = true;
                }

                // 2. Tìm trong danh sách lựa chọn (opts)
                if (!matchFound && q.opts) {
                    q.opts.forEach(opt => {
                        if (removeVietnameseTones(opt).includes(normalizedKw)) matchFound = true;
                    });
                }

                // 3. Tìm trong các loại câu hỏi True/False (items)
                if (!matchFound && q.items) {
                    q.items.forEach(item => {
                        let itemText = typeof item === 'string' ? item : item.text;
                        if (itemText && removeVietnameseTones(itemText).includes(normalizedKw)) matchFound = true;
                    });
                }

                // 4. Tìm trong câu hỏi Kéo thả (draggables)
                if (!matchFound && q.draggables) {
                    q.draggables.forEach(dragText => {
                        if (removeVietnameseTones(dragText).includes(normalizedKw)) matchFound = true;
                    });
                }

                if (matchFound) {
                    searchResults.push({
                        subjectKey: sKey,
                        subjectName: subject.name,
                        topicKey: tKey,
                        topicName: topic.name,
                        questionIndex: qIndex,
                        question: q
                    });
                }
            });
        }
    }

    renderSearchResults(searchResults, keyword);
}

// Hiển thị kết quả tìm kiếm ra giao diện
function renderSearchResults(results, keyword) {
    let countDiv = document.getElementById('searchResultsCount');
    let listDiv = document.getElementById('searchResultsList');

    if (results.length === 0) {
        countDiv.textContent = '';
        listDiv.innerHTML = `<div class="no-results">Không tìm thấy câu hỏi hoặc câu trả lời nào phù hợp với từ khóa "${keyword}".</div>`;
        return;
    }

    countDiv.textContent = `🔍 Tìm thấy ${results.length} câu hỏi phù hợp:`;
    
    let html = '';
    results.forEach(res => {
        let q = res.question;
        let highlightedText = highlightText(q.text, keyword);

        html += `<div class="search-item-card">
            <div class="search-item-meta">
                <span class="search-meta-tag">📖 ${res.subjectName}</span>
                <span class="search-meta-tag">📌 ${res.topicName}</span>
            </div>
            <div class="search-item-qtext">${highlightText(`Câu ${res.questionIndex + 1}: ${q.text}`, keyword)}</div>
            <div class="search-item-opts">`;

        // Render chi tiết các phương án và chỉ rõ đáp án đúng
        if (q.type === 'single') {
            q.opts.forEach((opt, idx) => {
                let isCorrect = idx === q.correct;
                let optClass = isCorrect ? 'search-opt-line is-correct' : 'search-opt-line';
                let mark = isCorrect ? ' ✅ (Đáp án đúng)' : '';
                html += `<div class="${optClass}">${highlightText(opt, keyword)}${mark}</div>`;
            });
        } else if (q.type === 'multi') {
            q.opts.forEach((opt, idx) => {
                let isCorrect = Array.isArray(q.correct) && q.correct.includes(idx);
                let optClass = isCorrect ? 'search-opt-line is-correct' : 'search-opt-line';
                let mark = isCorrect ? ' ✅ (Đáp án đúng)' : '';
                html += `<div class="${optClass}">${highlightText(opt, keyword)}${mark}</div>`;
            });
        } else if (q.type === 'truefalse') {
            q.items.forEach((item, idx) => {
                let correctStr = item.correct ? 'ĐÚNG' : 'SAI';
                html += `<div class="search-opt-line is-correct">${idx + 1}. ${highlightText(item.text, keyword)} ➔ <strong>${correctStr}</strong></div>`;
            });
        } else if (q.type === 'drag') {
            q.items.forEach((item, idx) => {
                let matchAns = q.matches[idx] ? q.matches[idx].join(', ') : '';
                html += `<div class="search-opt-line is-correct">${idx + 1}. ${highlightText(item, keyword)} ➔ <strong>${highlightText(matchAns, keyword)}</strong></div>`;
            });
        }

        html += `</div>
            <button class="btn btn-primary" onclick="jumpToQuestion('${res.subjectKey}', '${res.topicKey}', ${res.questionIndex})">🎯 Luyện tập câu này</button>
        </div>`;
    });

    listDiv.innerHTML = html;
}

// Nhảy trực tiếp đến câu hỏi tìm thấy để người dùng luyện tập
function jumpToQuestion(sKey, tKey, qIndex) {
    currentSubject = sKey;
    currentTopic = tKey;
    curQ = qIndex;
    answers = {};
    results = {};
    submitted = false;
    seconds = 0;

    document.getElementById('homeScreen').style.display = 'none';
    document.getElementById('resultScreen').style.display = 'none';
    document.getElementById('quizScreen').style.display = 'block';
    document.getElementById('topicName').textContent = DATA[currentSubject].topics[currentTopic].name;

    startTimer();
    initNumbers();
    renderQ(curQ);
}

initHome();
</script>
</body>
</html>
"""
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(template_content)
                
                # Tự động nạp luôn file vừa tạo vào backend để chỉnh sửa tiếp
                self.backend.load_file(file_path)
                self.reload_tree()
                QMessageBox.information(
                    self, "Thành công", f"Đã tạo và mở file mới tại:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể tạo file:\n{str(e)}")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Mở file HTML", "", "HTML Files (*.html *.htm)"
        )
        if file_path:
            try:
                self.backend.load_file(file_path)
                self.txt_site_title.setText(self.backend.site_title)
                self.txt_header_p.setText(self.backend.header_p)
                self.reload_tree()
                QMessageBox.information(
                    self, "Thành công", f"Đã tải xong file:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def save_file(self):
        if not self.backend.file_path:
            QMessageBox.warning(self, "Cảnh báo", "Chưa mở file HTML nào!")
            return
            
        self.backend.site_title = self.txt_site_title.text().strip()
        self.backend.header_p = self.txt_header_p.text().strip()
        
        if self.backend.save_file():
            QMessageBox.information(
                self, "Thông báo", "Lưu thay đổi thành công!"
            )
        else:
            QMessageBox.critical(self, "Lỗi", "Lưu file thất bại!")

    def reload_tree(self):
        self.tree.clear()
        for sub_key, sub_val in self.backend.data.items():
            # Đảo dữ liệu nút cha: [Mã / ID, Tên danh mục]
            sub_node = QTreeWidgetItem(
                self.tree, [sub_key, sub_val.get("name", "")]
            )
            sub_node.setData(0, Qt.ItemDataRole.UserRole, ("subject", sub_key))

            topics = sub_val.get("topics", {})
            for top_id, top_val in topics.items():
                # Đảo dữ liệu nút con: [Mã / ID, Tên danh mục]
                top_node = QTreeWidgetItem(
                    sub_node, [str(top_id), top_val.get("name", "")]
                )
                top_node.setData(
                    0, Qt.ItemDataRole.UserRole, ("topic", sub_key, str(top_id))
                )
        self.tree.expandAll()

    def on_tree_selection_changed(self):
        selected = self.tree.selectedItems()
        if not selected:
            self.current_sub_key = None
            self.current_topic_id = None
            self.table_q.setRowCount(0)
            return

        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "topic":
            self.current_sub_key = data[1]
            self.current_topic_id = data[2]
            self.reload_questions()
        else:
            self.current_sub_key = None
            self.current_topic_id = None
            self.table_q.setRowCount(0)

    def reload_questions(self):
        self.table_q.setRowCount(0)
        if not self.current_sub_key or not self.current_topic_id:
            return

        questions = (
            self.backend.data.get(self.current_sub_key, {})
            .get("topics", {})
            .get(self.current_topic_id, {})
            .get("questions", [])
        )

        for idx, q in enumerate(questions):
            row = self.table_q.rowCount()
            self.table_q.insertRow(row)
            self.table_q.setItem(row, 0, QTableWidgetItem(str(idx + 1)))
            self.table_q.setItem(
                row, 1, QTableWidgetItem(q.get("type", "single"))
            )
            self.table_q.setItem(
                row, 2, QTableWidgetItem(q.get("text", "")[:80])
            )

    def add_subject(self):
        if not self.backend.data and not self.backend.file_path:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng mở file HTML trước!")
            return
        key, ok1 = QInputDialog.getText(
            self, "Học phần mới", "Nhập Mã học phần (VD: hocPhan3):"
        )
        if ok1 and key:
            name, ok2 = QInputDialog.getText(
                self, "Học phần mới", "Nhập Tên học phần:"
            )
            if ok2 and name:
                self.backend.data[key] = {"name": name, "topics": {}}
                self.reload_tree()

    def add_topic(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(
                self, "Cảnh báo", "Vui lòng chọn 1 Học phần để thêm Bài học!"
            )
            return

        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        sub_key = data[1] if data else None

        if sub_key in self.backend.data:
            name, ok = QInputDialog.getText(
                self, "Bài học mới", "Nhập tên bài học (VD: BÀI 1):"
            )
            if ok and name:
                topics = self.backend.data[sub_key].setdefault("topics", {})
                new_id = str(len(topics) + 1)
                topics[new_id] = {"name": name, "questions": []}
                self.reload_tree()

    def delete_tree_item(self):
        selected = self.tree.selectedItems()
        if not selected:
            return

        data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data[0] == "subject":
            sub_key = data[1]
            del self.backend.data[sub_key]
        elif data[0] == "topic":
            sub_key, top_id = data[1], data[2]
            del self.backend.data[sub_key]["topics"][top_id]
        self.reload_tree()

    def add_question(self):
        if not self.current_sub_key or not self.current_topic_id:
            QMessageBox.warning(
                self, "Thông báo", "Vui lòng chọn bài học muốn thêm câu hỏi!"
            )
            return

        dlg = QuestionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            q_data = dlg.get_data()
            questions = self.backend.data[self.current_sub_key]["topics"][
                self.current_topic_id
            ].setdefault("questions", [])
            questions.append(q_data)
            self.reload_questions()

    def edit_question(self):
        selected_row = self.table_q.currentRow()
        if selected_row < 0:
            return

        questions = self.backend.data[self.current_sub_key]["topics"][
            self.current_topic_id
        ]["questions"]
        q_data = questions[selected_row]

        dlg = QuestionDialog(self, question_data=q_data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            questions[selected_row] = dlg.get_data()
            self.reload_questions()

    def delete_question(self):
        selected_row = self.table_q.currentRow()
        if selected_row < 0:
            return

        questions = self.backend.data[self.current_sub_key]["topics"][
            self.current_topic_id
        ]["questions"]
        del questions[selected_row]
        self.reload_questions()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())