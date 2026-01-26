from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSizePolicy, QHeaderView, QAbstractItemView, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from database import add_student, get_students, delete_student, generate_certificate_id, update_certificate_id

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
        self.refresh_students()

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
        self.student_table.setColumnWidth(5, 120)
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
            sid, name, phone, email, address, certificate_id = stu
            if filter_text and filter_text not in name.lower():
                continue
            row_idx = self.student_table.rowCount()
            self.student_table.insertRow(row_idx)
            self.student_table.setItem(row_idx, 0, QTableWidgetItem(str(sid)))
            self.student_table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.student_table.setItem(row_idx, 2, QTableWidgetItem(phone))
            self.student_table.setItem(row_idx, 3, QTableWidgetItem(email or ''))
            self.student_table.setItem(row_idx, 4, QTableWidgetItem(address or ''))
            self.add_certificate_widget(row_idx, sid, certificate_id)
            self.add_delete_button(row_idx, sid)
        self.student_table.blockSignals(False)

    def add_certificate_widget(self, row, student_id, certificate_id):
        """Add certificate ID display or Generate button"""
        if certificate_id:
            # Show the certificate ID as text
            item = QTableWidgetItem(certificate_id)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.student_table.setItem(row, 5, item)
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
        # Prevent editing ID column and Certificate ID column
        if item.column() == 0 or item.column() == 5:
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return
        row = item.row()
        sid = int(self.student_table.item(row, 0).text())
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
