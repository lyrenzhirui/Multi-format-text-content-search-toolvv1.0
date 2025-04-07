import os
import time
import chardet
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QLineEdit, QComboBox, QListWidget,
                             QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
                             QHBoxLayout, QHeaderView, QProgressBar, QFrame, QCheckBox)
from PyQt5.QtCore import Qt, QSettings, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QPainter, QPen, QBrush


# 业务逻辑部分 - 搜索线程
class SearchThread(QThread):
    # 定义信号
    update_progress = pyqtSignal(int, str)  # 进度更新信号
    found_match = pyqtSignal(str, str, str, str, str)  # 找到匹配文件的信号
    search_completed = pyqtSignal(int, int)  # 搜索完成信号(total_files, matched_count)
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, folder, keyword, formats, encoding):
        super().__init__()
        self.folder = folder
        self.keyword = keyword
        self.formats = formats  # {'sql': True, 'txt': True, 'xml': True}
        self.encoding = encoding
        self._is_running = True

    def run(self):
        try:
            supported_files = []
            for root, _, files in os.walk(self.folder):
                for file in files:
                    if not self._is_running:
                        return

                    file_lower = file.lower()
                    if (self.formats['sql'] and file_lower.endswith('.sql')) or \
                            (self.formats['txt'] and file_lower.endswith('.txt')) or \
                            (self.formats['xml'] and file_lower.endswith('.xml')):
                        supported_files.append(os.path.join(root, file))

            if not supported_files:
                self.error_occurred.emit("在指定文件夹中未找到符合条件的文件!")
                return

            total_files = len(supported_files)
            matched_count = 0

            for i, file_path in enumerate(supported_files):
                if not self._is_running:
                    return

                self.update_progress.emit(i + 1, os.path.basename(file_path))

                try:
                    # 获取文件信息
                    file_size = os.path.getsize(file_path)
                    mod_time = os.path.getmtime(file_path)
                    mod_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
                    size_str = f"{file_size / 1024:.2f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.2f} MB"

                    # 确定文件类型
                    file_ext = os.path.splitext(file_path)[1].lower()
                    file_type = {
                        '.sql': 'SQL',
                        '.txt': 'TXT',
                        '.xml': 'XML'
                    }.get(file_ext, '未知')

                    # 读取文件内容
                    content = ""
                    if self.encoding == "自动检测":
                        with open(file_path, 'rb') as f:
                            raw_data = f.read()
                            detected = chardet.detect(raw_data)
                            try:
                                content = raw_data.decode(
                                    detected['encoding'] if detected['encoding'] else 'utf-8')
                            except:
                                try:
                                    content = raw_data.decode('utf-8')
                                except:
                                    content = raw_data.decode('gbk', errors='ignore')
                    else:
                        with open(file_path, 'r', encoding=self.encoding, errors='ignore') as f:
                            content = f.read()

                    # 搜索关键词
                    if self.keyword.lower() in content.lower():
                        matched_count += 1
                        self.found_match.emit(file_path, file_type, mod_date, size_str,
                                              os.path.relpath(file_path, self.folder))

                except Exception as e:
                    self.error_occurred.emit(f"读取文件 {os.path.basename(file_path)} 出错: {str(e)}")
                    continue

            self.search_completed.emit(total_files, matched_count)

        except Exception as e:
            self.error_occurred.emit(f"搜索过程中发生错误: {str(e)}")

    def stop(self):
        self._is_running = False


# UI部分
class SQLSearchToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多格式文本内容搜索工具")
        self.setGeometry(100, 100, 800, 600)

        # 初始化UI
        self.init_ui()
        signature = QLabel()
        signature.setText('🧑💻 开发者：<b>赖智锐</b> | 📦 Version <b>1.0</b>')
        signature.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        self.status_bar.addPermanentWidget(signature)

        def create_search_icon():
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # 绘制放大镜圆形
            pen = QPen(QColor(70, 130, 180), 2)
            painter.setPen(pen)
            painter.drawEllipse(8, 8, 16, 16)

            # 绘制放大镜手柄
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawLine(20, 20, 26, 26)

            painter.end()
            return QIcon(pixmap)

        # 设置窗口图标
        try:
            self.setWindowIcon(create_search_icon())
        except:
            pass  # 如果图标不存在则忽略

        # 搜索线程
        self.search_thread = None
        # 当前文件夹路径
        self.current_folder = ""
        # 初始化设置
        self.settings = QSettings("Trae", "TextSearchTool")
        self.current_folder = self.settings.value("last_folder", "", type=str)
        if self.current_folder:
            self.folder_label.setText(self.current_folder)
            self.folder_label.setToolTip(self.current_folder)

    def init_ui(self):
        # 主控件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 添加标题
        title_label = QLabel("多格式文本内容搜索工具")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(separator)

        # 文件夹选择区域
        folder_group = QWidget()
        folder_layout = QHBoxLayout(folder_group)
        folder_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_btn = QPushButton(" 选择文件夹")
        self.folder_btn.setIcon(QIcon.fromTheme("folder-open"))
        self.folder_btn.setIconSize(QSize(20, 20))
        self.folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.folder_btn.clicked.connect(self.select_folder)
        self.folder_btn.setFixedHeight(40)

        self.folder_label = QLabel("未选择文件夹")
        self.folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        self.folder_label.setWordWrap(True)

        folder_layout.addWidget(self.folder_btn)
        folder_layout.addWidget(self.folder_label, 1)
        layout.addWidget(folder_group)

        # 搜索条件区域
        search_group = QWidget()
        search_layout = QVBoxLayout(search_group)
        search_layout.setSpacing(10)

        # 关键词输入
        keyword_layout = QHBoxLayout()
        self.keyword_label = QLabel("搜索关键词:")
        self.keyword_label.setStyleSheet("font-weight: bold; color: #34495e;")
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入要搜索的关键词...")
        self.keyword_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        keyword_layout.addWidget(self.keyword_label)
        keyword_layout.addWidget(self.keyword_input, 1)
        search_layout.addLayout(keyword_layout)

        # 文件格式选择
        format_group = QWidget()
        format_layout = QHBoxLayout(format_group)
        format_layout.setContentsMargins(0, 0, 0, 0)

        self.format_label = QLabel("文件格式:")
        self.format_label.setStyleSheet("font-weight: bold; color: #34495e;")

        # 创建格式选择复选框
        self.sql_check = QCheckBox("SQL")
        self.sql_check.setChecked(True)
        self.txt_check = QCheckBox("TXT")
        self.xml_check = QCheckBox("XML")

        # 设置复选框样式
        checkbox_style = """
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """
        self.sql_check.setStyleSheet(checkbox_style)
        self.txt_check.setStyleSheet(checkbox_style)
        self.xml_check.setStyleSheet(checkbox_style)

        format_layout.addWidget(self.format_label)
        format_layout.addWidget(self.sql_check)
        format_layout.addWidget(self.txt_check)
        format_layout.addWidget(self.xml_check)
        format_layout.addStretch(1)
        search_layout.addWidget(format_group)

        # 编码选择
        encoding_layout = QHBoxLayout()
        self.encoding_label = QLabel("文件编码:")
        self.encoding_label.setStyleSheet("font-weight: bold; color: #34495e;")
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["自动检测", "utf-8", "gbk", "gb18030", "big5"])
        self.encoding_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
        """)
        encoding_layout.addWidget(self.encoding_label)
        encoding_layout.addWidget(self.encoding_combo, 1)
        search_layout.addLayout(encoding_layout)

        layout.addWidget(search_group)

        # 搜索按钮
        self.search_btn = QPushButton(" 开始搜索")
        self.search_btn.setIcon(QIcon.fromTheme("edit-find"))
        self.search_btn.setIconSize(QSize(20, 20))
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.search_btn.clicked.connect(self.start_search)
        self.search_btn.setFixedHeight(45)
        layout.addWidget(self.search_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 结果表格区域
        results_group = QWidget()
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(0, 0, 0, 0)

        self.result_label = QLabel("搜索结果 (0)")
        self.result_label.setStyleSheet("font-weight: bold; color: #34495e; font-size: 14px;")
        results_layout.addWidget(self.result_label)

        # 创建表格控件
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)  # 增加一列显示文件类型
        self.result_table.setHorizontalHeaderLabels(["文件名", "文件类型", "修改日期", "文件大小"])

        # 设置表格样式
        self.result_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                gridline-color: #ecf0f1;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2980b9;
                color: white;
            }
        """)

        # 设置列宽和调整策略
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # 文件名列自动拉伸
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 文件类型列根据内容调整
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 日期列根据内容调整
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 大小列根据内容调整
        self.result_table.setSortingEnabled(True)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.doubleClicked.connect(self.open_file)
        self.result_table.verticalHeader().setVisible(False)

        results_layout.addWidget(self.result_table)
        layout.addWidget(results_group, 1)

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #ecf0f1;
                color: #7f8c8d;
                border-top: 1px solid #bdc3c7;
            }
        """)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            self.current_folder
        )
        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.folder_label.setToolTip(folder)
            self.status_bar.showMessage(f"已选择文件夹: {folder}", 3000)
            self.settings.setValue("last_folder", folder)

    def start_search(self):
        if not self.current_folder:
            self.status_bar.showMessage("请先选择文件夹!", 3000)
            return

        keyword = self.keyword_input.text().strip()
        if not keyword:
            self.status_bar.showMessage("请输入搜索关键词!", 3000)
            return

        # 检查至少选择了一种文件格式
        if not (self.sql_check.isChecked() or self.txt_check.isChecked() or self.xml_check.isChecked()):
            self.status_bar.showMessage("请至少选择一种文件格式!", 3000)
            return

        # 准备搜索
        self.result_table.setRowCount(0)
        self.result_label.setText("搜索结果 (0)")
        encoding = self.encoding_combo.currentText()

        # 获取选择的文件格式
        formats = {
            'sql': self.sql_check.isChecked(),
            'txt': self.txt_check.isChecked(),
            'xml': self.xml_check.isChecked()
        }

        # 禁用搜索按钮并显示进度条
        self.search_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 创建并启动搜索线程
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop()

        self.search_thread = SearchThread(self.current_folder, keyword, formats, encoding)
        self.search_thread.update_progress.connect(self.update_progress)
        self.search_thread.found_match.connect(self.add_match_result)
        self.search_thread.search_completed.connect(self.search_completed)
        self.search_thread.error_occurred.connect(self.show_error)
        self.search_thread.start()

    def update_progress(self, value, filename):
        self.progress_bar.setValue(value)
        self.status_bar.showMessage(f"正在处理: {filename}...")

    def add_match_result(self, file_path, file_type, mod_date, size_str, rel_path):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        # 文件名和相对路径
        item = QTableWidgetItem(rel_path)
        item.setData(Qt.UserRole, file_path)
        self.result_table.setItem(row, 0, item)

        # 文件类型
        type_item = QTableWidgetItem(file_type)
        type_item.setTextAlignment(Qt.AlignCenter)
        self.result_table.setItem(row, 1, type_item)

        # 修改日期
        date_item = QTableWidgetItem(mod_date)
        date_item.setTextAlignment(Qt.AlignCenter)
        self.result_table.setItem(row, 2, date_item)

        # 文件大小
        size_item = QTableWidgetItem(size_str)
        size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.result_table.setItem(row, 3, size_item)

        self.result_label.setText(f"搜索结果 ({self.result_table.rowCount()})")

    def search_completed(self, total_files, matched_count):
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        self.status_bar.showMessage(f"搜索完成，共搜索 {total_files} 个文件，找到 {matched_count} 个匹配文件", 5000)

    def show_error(self, error_msg):
        self.status_bar.showMessage(error_msg, 5000)
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)

    def open_file(self, item):
        try:
            file_path = self.result_table.item(item.row(), 0).data(Qt.UserRole)
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/Mac
                os.system(f'xdg-open "{file_path}"')
        except Exception as e:
            self.status_bar.showMessage(f"无法打开文件: {str(e)}", 3000)

    def closeEvent(self, event):
        # 确保在窗口关闭时停止搜索线程
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop()
            self.search_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    font = QFont()
    font.setFamily("Arial")
    font.setPointSize(10)
    app.setFont(font)
    window = SQLSearchToolUI()
    window.show()
    app.exec_()