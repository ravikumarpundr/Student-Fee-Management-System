import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from database import initialize_db
from course_manager import open_course_manager,open_enroll_window,open_payment_window,open_payment_history  # Assume this will be converted too
from course_manager import open_student_manager
from settings_manager import open_settings_window

# Initialize DB on app startup
initialize_db()

class InstituteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Institute Management System")
        self.setGeometry(100, 100, 800, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#title {
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
                margin: 10px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 18px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-height: 60px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title with professional styling
        title = QLabel("PriorCoder Tech Studio")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Management System")
        subtitle.setStyleSheet("""
            color: #34495e;
            font-size: 16px;
            font-weight: 500;
            margin: 10px;
            text-align: center;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Add some spacing
        layout.addSpacing(20)

        # Create grid layout for buttons (2 columns)
        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(15)
        buttons_grid.setContentsMargins(0, 0, 0, 0)

        # Buttons with improved styling - arranged in 2 columns
        btn_course = QPushButton("📚 Course Management")
        btn_course.clicked.connect(open_course_manager)
        buttons_grid.addWidget(btn_course, 0, 0)

        btn_student = QPushButton("👨‍🎓 Student Management")
        btn_student.clicked.connect(open_student_manager)
        buttons_grid.addWidget(btn_student, 0, 1)

        btn_enroll = QPushButton("📝 Enroll Student")
        btn_enroll.clicked.connect(open_enroll_window)
        buttons_grid.addWidget(btn_enroll, 1, 0)

        btn_payment = QPushButton("💰 Record Payment")
        btn_payment.clicked.connect(open_payment_window)
        buttons_grid.addWidget(btn_payment, 1, 1)

        btn_history = QPushButton("📊 Payment History")
        btn_history.clicked.connect(open_payment_history)
        buttons_grid.addWidget(btn_history, 2, 0)

        btn_settings = QPushButton("⚙️ Settings")
        btn_settings.clicked.connect(open_settings_window)
        buttons_grid.addWidget(btn_settings, 2, 1)

        # Add grid to main layout
        layout.addLayout(buttons_grid)
        
        # Add some bottom spacing
        layout.addStretch()

        self.setLayout(layout)

# Main launcher
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = InstituteApp()
    window.show()
    sys.exit(app.exec_())
