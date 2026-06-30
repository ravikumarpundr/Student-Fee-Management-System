from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSizePolicy, QHeaderView, QAbstractItemView, QTabWidget, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from database import add_student, get_students, delete_student, generate_certificate_id, update_certificate_id


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #323232;
                color: white;
                padding: 10px 24px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        self.hide()

    def show_message(self, text, duration_ms=2000):
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            x = (parent.width() - self.width()) // 2
            y = parent.height() - self.height() - 24
            self.move(max(x, 0), max(y, 0))
        self.raise_()
        self.show()
        QTimer.singleShot(duration_ms, self.hide)


class StudentManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Student Manager")
        self.setGeometry(200, 200, 800, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2c3e50;
                font-weight: 600;
                font-size: 12px;
                margin: 5px 0px;
            }
            QLineEdit {
                background-color: white;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                color: #495057;
            }
            QLineEdit:focus {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QHeaderView::section:hover {
                background-color: #34495e;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Title section
        title_label = QLabel("👨‍🎓 Student Management")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px 0px 20px 0px;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_listing_tab()
        self.create_add_tab()

        self.setLayout(layout)
        self.toast = Toast(self)
        self.refresh_students()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.toast.isVisible():
            x = (self.width() - self.toast.width()) // 2
            y = self.height() - self.toast.height() - 24
            self.toast.move(max(x, 0), max(y, 0))

    def create_listing_tab(self):
        """Create the listing tab with search and table"""
        listing_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Search/filter bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by student name...")
        self.search_input.textChanged.connect(self.filter_students)
        self.search_input.setFixedHeight(45)
        self.search_input.setStyleSheet("padding-left: 10px; padding-right: 10px;")
        layout.addWidget(self.search_input)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(7)
        self.student_table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Email", "Address", "Certificate ID", "Delete"])
        self.student_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.student_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.student_table.setSelectionMode(QTableWidget.SingleSelection)
        self.student_table.setSortingEnabled(True)
        self.student_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.student_table.verticalHeader().setDefaultSectionSize(35)
        header = self.student_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        # Set fixed width for the certificate ID and delete columns
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.student_table.setColumnWidth(5, 175)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.student_table.setColumnWidth(6, 60)
        self.student_table.itemChanged.connect(self.handle_item_changed)
        self.student_table.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.student_table, stretch=1)

        listing_tab.setLayout(layout)
        self.tab_widget.addTab(listing_tab, "📋 Listing")

    def create_add_tab(self):
        """Create the add new student tab"""
        add_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Form section with better grouping
        form_group = QLabel("Add New Student")
        form_group.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #34495e;
            margin: 15px 0px 10px 0px;
            padding: 8px 0px;
            border-bottom: 2px solid #3498db;
        """)
        layout.addWidget(form_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name (required)")
        self.name_input.setFixedHeight(45)
        self.name_input.setStyleSheet("padding-left: 10px; padding-right: 10px;")
        layout.addWidget(self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone Number (required)")
        self.phone_input.setFixedHeight(45)
        self.phone_input.setStyleSheet("padding-left: 10px; padding-right: 10px;")
        layout.addWidget(self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (optional)")
        self.email_input.setFixedHeight(45)
        self.email_input.setStyleSheet("padding-left: 10px; padding-right: 10px;")
        layout.addWidget(self.email_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address (optional)")
        self.address_input.setFixedHeight(45)
        self.address_input.setStyleSheet("padding-left: 10px; padding-right: 10px;")
        layout.addWidget(self.address_input)

        self.add_button = QPushButton("Add Student")
        self.add_button.clicked.connect(self.handle_add_student)
        self.add_button.setFixedHeight(45)
        layout.addWidget(self.add_button)

        # Add some stretch to center the form
        layout.addStretch()

        add_tab.setLayout(layout)
        self.tab_widget.addTab(add_tab, "➕ Add New")

    def handle_add_student(self):
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        address = self.address_input.text().strip()

        if not name or not phone:
            QMessageBox.warning(self, "Input Error", "Name and phone number are required.")
            return

        add_student(name, phone, email, address)
        self.name_input.clear()
        self.phone_input.clear()
        self.email_input.clear()
        self.address_input.clear()
        self.refresh_students()
        
        # Switch to listing tab to show the newly added student
        self.tab_widget.setCurrentIndex(0)

    def refresh_students(self):
        self.all_students = get_students()
        self.student_table.blockSignals(True)
        self.filter_students()
        self.student_table.blockSignals(False)

    def filter_students(self):
        filter_text = self.search_input.text().strip().lower() if hasattr(self, 'search_input') else ''
        self.student_table.blockSignals(True)
        self.student_table.setRowCount(0)
        for stu in getattr(self, 'all_students', get_students()):
            sid, student_id, name, phone, email, address, certificate_id = stu
            if filter_text and filter_text not in name.lower():
                continue
            row_idx = self.student_table.rowCount()
            self.student_table.insertRow(row_idx)
            id_item = QTableWidgetItem(student_id or str(sid))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            id_item.setData(Qt.UserRole, sid)
            self.student_table.setItem(row_idx, 0, id_item)
            self.student_table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.student_table.setItem(row_idx, 2, QTableWidgetItem(phone))
            self.student_table.setItem(row_idx, 3, QTableWidgetItem(email or ''))
            self.student_table.setItem(row_idx, 4, QTableWidgetItem(address or ''))
            self.add_certificate_widget(row_idx, sid, certificate_id)
            self.add_delete_button(row_idx, sid)
        self.student_table.blockSignals(False)

    def _make_copy_button(self, text, on_copy):
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("tableCopyBtn")
        copy_btn.setToolTip("Copy certificate ID to clipboard")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setFixedSize(54, 24)
        copy_btn.setStyleSheet("""
            QPushButton#tableCopyBtn {
                background-color: #ffffff;
                color: #3498db;
                border: 1px solid #3498db;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                padding: 0px 8px;
                min-height: 0px;
                max-height: 24px;
            }
            QPushButton#tableCopyBtn:hover {
                background-color: #ebf5fb;
                color: #217dbb;
                border-color: #217dbb;
            }
            QPushButton#tableCopyBtn:pressed {
                background-color: #d6eaf8;
                color: #1a5276;
                border-color: #1a5276;
            }
        """)
        copy_btn.clicked.connect(lambda _, value=text: on_copy(value))
        return copy_btn

    def copy_certificate_id(self, certificate_id):
        QApplication.clipboard().setText(certificate_id)
        self.toast.show_message(f"Certificate ID copied: {certificate_id}")

    def add_certificate_widget(self, row, student_id, certificate_id):
        """Add certificate ID with copy link, or Generate button if missing"""
        if certificate_id:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(4, 0, 4, 0)
            layout.setSpacing(6)

            cert_label = QLabel(certificate_id)
            cert_label.setStyleSheet("""
                color: #2c3e50;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Menlo', 'Consolas', monospace;
            """)
            layout.addWidget(cert_label)
            layout.addWidget(self._make_copy_button(certificate_id, self.copy_certificate_id))
            layout.addStretch()

            self.student_table.setCellWidget(row, 5, container)
        else:
            # Show Generate button
            btn = QPushButton("Generate")
            btn.setToolTip('Generate certificate ID')
            btn.setFixedSize(100, 25)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """)
            btn.clicked.connect(lambda _, sid=student_id: self.generate_certificate_id(sid))
            self.student_table.setCellWidget(row, 5, btn)

    def generate_certificate_id(self, student_id):
        """Generate and save certificate ID for a student"""
        cert_id = generate_certificate_id()
        update_certificate_id(student_id, cert_id)
        self.refresh_students()
        QMessageBox.information(self, "Success", f"Certificate ID generated: {cert_id}")

    def add_delete_button(self, row, student_id):
        btn = QPushButton()
        icon = QIcon.fromTheme('user-trash')
        if icon.isNull():
            icon = QIcon.fromTheme('edit-delete')
        if icon.isNull():
            icon = QIcon.fromTheme('window-close')
        if icon.isNull():
            btn.setText("🗑️")
        else:
            btn.setIcon(icon)
            btn.setText("")
        btn.setToolTip('Delete this student')
        btn.setFlat(True)
        btn.setFixedSize(28, 20)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-radius: 3px;
            }
            QPushButton:pressed {
                background-color: #ffcdd2;
            }
        """)
        btn.clicked.connect(lambda _, sid=student_id: self.confirm_delete_student(sid))
        self.student_table.setCellWidget(row, 6, btn)

    def confirm_delete_student(self, student_id):
        reply = QMessageBox.question(self, 'Confirm Delete', 'Are you sure you want to delete this student?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            delete_student(student_id)
            self.refresh_students()

    def handle_item_changed(self, item):
        if item.column() == 0:
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return
        row = item.row()
        id_item = self.student_table.item(row, 0)
        if not id_item:
            return
        sid = id_item.data(Qt.UserRole)
        if sid is None:
            sid = int(id_item.text())
        name = self.student_table.item(row, 1).text().strip()
        phone = self.student_table.item(row, 2).text().strip()
        email = self.student_table.item(row, 3).text().strip()
        address = self.student_table.item(row, 4).text().strip()
        from database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE students SET name=?, phone=?, email=?, address=? WHERE id=?", (name, phone, email, address, sid))
        conn.commit()
        conn.close()
        self.refresh_students()
