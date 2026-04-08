import sys
import os
import json
from datetime import datetime
import webbrowser
import urllib.parse

from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QPixmap, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QFileDialog, QTableWidget, QHeaderView,
    QMessageBox, QDateEdit, QTextEdit, QTableWidgetItem,
    QDialog, QScrollArea, QPlainTextEdit, QCheckBox,
    QGroupBox, QFrame, QAbstractItemView, QStyledItemDelegate, QComboBox, QSplashScreen, QProgressBar
)

from PIL import Image, ImageDraw, ImageFont
from num2words import num2words
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


class AnimatedSplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setFixedSize(pixmap.size())

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        # Adjust these values to match your splash design
        self.progress.setGeometry(110, 375, 140, 10)

        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 60);
                border: none;
                border-radius: 7px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #22c55e,
                    stop:1 #a3e635
                );
                border-radius: 7px;
            }
        """)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.current_value = 0

    def start_animation(self, interval=18):
        self.timer.start(interval)

    def update_progress(self):
        self.current_value += 1
        if self.current_value > 100:
            self.current_value = 0
        self.progress.setValue(self.current_value)

class ReceiptPreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ReceiptFlow")
        self.setWindowIcon(QIcon("icon.png"))
        self.setMinimumSize(950, 720)

        layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(image_path)
        scaled = pixmap.scaled(
            820, 1200, # Adjust max dimensions to your window size
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        image_label.setPixmap(scaled)

        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)


class ReceiptHistoryDialog(QDialog):
    def __init__(self, history_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ReceiptFlow")
        self.setWindowIcon(QIcon("icon.png"))
        self.setMinimumSize(900, 650)

        layout = QVBoxLayout(self)

        self.history_box = QPlainTextEdit()
        self.history_box.setReadOnly(True)
        self.history_box.setPlainText(history_text)

        layout.addWidget(self.history_box)


class ReceiptTableDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if editor:
            font = QFont("Segoe UI", 11)
            editor.setFont(font)
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    color: #172033;
                    border: 2px solid #2563eb;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11pt;
                }
            """)
            editor.setMinimumHeight(30)
        return editor


class ReceiptApp(QWidget):
    def __init__(self):
        super().__init__()
        self.logo_path = None
        self.data_folder = "app_data"
        self.settings_file = os.path.join(self.data_folder, "app_settings.json")
        self.output_folder = "output"
        self.profile_file = os.path.join(self.data_folder, "business_profile.json")
        self.history_file = os.path.join(self.data_folder, "receipt_history.json")
        self.invoice_counter_file = os.path.join(self.data_folder, "invoice_counter.txt")
        self.customers_file = os.path.join(self.data_folder, "saved_customers.json")
        self.updating_table = False
        self.last_generated_image_path = None
        self.last_generated_pdf_path = None
        self.current_theme = "light"

        os.makedirs(self.data_folder, exist_ok=True)
        self.load_app_settings()
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.data_folder, exist_ok=True)
        self.init_ui()

    def get_light_theme(self):
        return """
            QWidget {
                background-color: #f3f6fb;
                color: #172033;
                font-size: 14px;
                font-family: Segoe UI, Arial, sans-serif;
            }

            QLabel {
                background: transparent;
            }

            QLabel#AppTitle {
                font-size: 24px;
                font-weight: 800;
                color: #0f172a;
                padding: 0;
            }

            QLabel#AppSubtitle {
                font-size: 12px;
                color: #64748b;
                padding: 0;
            }

            QLabel#SectionHint {
                font-size: 12px;
                color: #64748b;
            }

            QGroupBox {
                background-color: white;
                border: 1px solid #d9e3f0;
                border-radius: 16px;
                margin-top: 12px;
                font-size: 17px;
                font-weight: 700;
                color: #0f172a;
                padding: 12px 12px 10px 12px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
            }

            QLineEdit, QDateEdit, QTextEdit, QPlainTextEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 10px;
                padding: 8px 10px;
                selection-background-color: #1d4ed8;
                color: #172033;
            }

            QLineEdit:focus, QDateEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
                border: 2px solid #2563eb;
            }

            QTextEdit {
                padding-top: 10px;
            }

            QPushButton {
                background-color: #1d4ed8;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: 700;
                min-height: 20px;
            }

            QPushButton:hover {
                background-color: #1e40af;
            }

            QPushButton:pressed {
                background-color: #1e3a8a;
            }

            QPushButton#SecondaryButton {
                background-color: #f8fbff;
                color: #1e3a8a;
                border: 1px solid #d6e4fb;
            }

            QPushButton#SecondaryButton:hover {
                background-color: #eef4ff;
            }

            QCheckBox {
                spacing: 8px;
                font-weight: 600;
                color: #1e293b;
                background: transparent;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }

            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #d6e0ea;
                border-radius: 14px;
                gridline-color: #e6edf5;
                color: #172033;
            }

            QHeaderView::section {
                background-color: #10256f;
                color: white;
                padding: 12px 10px;
                border: none;
                font-weight: 700;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QFrame#LogoPreviewFrame {
                background-color: #f8fbff;
                border: 1px dashed #cad6e5;
                border-radius: 14px;
            }

            QFrame#TopBanner {
                background-color: white;
                border: 1px solid #d9e3f0;
                border-radius: 18px;
            }

            QLabel#HeaderIconFrame {
                background-color: #f8fbff;
                border: 1px solid #d9e3f0;
                border-radius: 14px;
            }

            QFrame#UtilityBar {
                background-color: #f8fbff;
                border: 1px solid #d9e3f0;
                border-radius: 12px;
            }
        """

    def get_dark_theme(self):
        return """
            QWidget {
                background-color: #0f172a;
                color: #e5e7eb;
                font-size: 14px;
                font-family: Segoe UI, Arial, sans-serif;
            }

            QLabel {
                background: transparent;
                color: #e5e7eb;
            }

            QLabel#AppTitle {
                font-size: 24px;
                font-weight: 800;
                color: #f8fafc;
                padding: 0;
            }

            QLabel#AppSubtitle {
                font-size: 12px;
                color: #94a3b8;
                padding: 0;
            }

            QLabel#SectionHint {
                font-size: 12px;
                color: #94a3b8;
            }

            QGroupBox {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 16px;
                margin-top: 12px;
                font-size: 17px;
                font-weight: 700;
                color: #f8fafc;
                padding: 12px 12px 10px 12px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #f8fafc;
            }

            QLineEdit, QDateEdit, QTextEdit, QPlainTextEdit, QComboBox {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 10px;
                padding: 8px 10px;
                selection-background-color: #3b82f6;
                color: #f8fafc;
            }

            QLineEdit:focus, QDateEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
                border: 2px solid #60a5fa;
            }

            QTextEdit {
                padding-top: 10px;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: 700;
                min-height: 20px;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton:pressed {
                background-color: #1e40af;
            }

            QPushButton#SecondaryButton {
                background-color: #1e293b;
                color: #dbeafe;
                border: 1px solid #475569;
            }

            QPushButton#SecondaryButton:hover {
                background-color: #334155;
            }

            QCheckBox {
                spacing: 8px;
                font-weight: 600;
                color: #e2e8f0;
                background: transparent;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }

            QTableWidget {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 14px;
                gridline-color: #334155;
                color: #f8fafc;
            }

            QTableWidget::item:selected {
                background-color: #1d4ed8;
                color: white;
            }

            QHeaderView::section {
                background-color: #1e3a8a;
                color: white;
                padding: 12px 10px;
                border: none;
                font-weight: 700;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QFrame#LogoPreviewFrame {
                background-color: #0f172a;
                border: 1px dashed #475569;
                border-radius: 14px;
            }

            QFrame#TopBanner {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 18px;
            }

            QLabel#HeaderIconFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 14px;
            }

            QFrame#UtilityBar {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """

    def apply_theme(self):
        if self.current_theme == "dark":
            self.setStyleSheet(self.get_dark_theme())
        else:
            self.setStyleSheet(self.get_light_theme())

        if hasattr(self, "theme_toggle_btn"):
            self.theme_toggle_btn.setText("☀ Light Mode" if self.current_theme == "dark" else "🌙 Dark Mode")

        self.update_theme_dependent_widgets()

    def update_theme_dependent_widgets(self):
        if not hasattr(self, "preview_logo"):
            return

        if self.current_theme == "dark":
            if hasattr(self, "status_label"):
                self.status_label.setStyleSheet("color:#4ade80; font-size:12px; font-weight:700;")
            if hasattr(self, "edition_badge"):
                self.edition_badge.setStyleSheet("""
                    background-color: #1e293b;
                    color: #dbeafe;
                    border: 1px solid #475569;
                    border-radius: 15px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 700;
                """)
            if hasattr(self, "support_btn"):
                self.support_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #16a34a;
                        color: white;
                        font-weight: bold;
                        border-radius: 10px;
                        padding: 8px 14px;
                    }
                    QPushButton:hover {
                        background-color: #15803d;
                    }
                """)
            if hasattr(self, "whatsapp_btn"):
                self.whatsapp_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0f766e;
                        color: white;
                        font-weight: bold;
                        border-radius: 10px;
                        padding: 8px 14px;
                    }
                    QPushButton:hover {
                        background-color: #0d9488;
                    }
                """)
            if hasattr(self, "preview_box_ref"):
                self.preview_box_ref.setStyleSheet("""
                    QGroupBox {
                        background: #111827;
                        border: 1px solid #334155;
                        border-radius: 18px;
                        padding: 16px;
                        color: #f8fafc;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 14px;
                        padding: 0 8px;
                        font-size: 16px;
                        font-weight: 700;
                        color: #f8fafc;
                    }
                """)
            self.preview_logo.setStyleSheet("""
                background-color: #0f172a;
                border: 1px dashed #475569;
                border-radius: 10px;
                color: #94a3b8;
                font-weight: 600;
            """)
            self.preview_business_name.setStyleSheet("font-size:20px; font-weight:800; color:#f8fafc;")
            self.preview_tagline.setStyleSheet("font-size:11px; color:#94a3b8;")
            self.preview_customer.setStyleSheet("font-size:13px; color:#e2e8f0; font-weight:700;")
            self.preview_doc_number.setStyleSheet("font-size:11px; color:#94a3b8;")
            self.preview_template.setStyleSheet("font-size:11px; color:#94a3b8;")
            self.preview_notes.setStyleSheet("""
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
                color: #cbd5e1;
            """)
        else:
            if hasattr(self, "status_label"):
                self.status_label.setStyleSheet("color:#22c55e; font-size:12px; font-weight:700;")
            if hasattr(self, "edition_badge"):
                self.edition_badge.setStyleSheet("""
                    background-color: #eef4ff;
                    color: #153e96;
                    border: 1px solid #c6d6f5;
                    border-radius: 15px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 700;
                """)
            if hasattr(self, "support_btn"):
                self.support_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #25D366;
                        color: white;
                        font-weight: bold;
                        border-radius: 10px;
                        padding: 8px 14px;
                    }
                    QPushButton:hover {
                        background-color: #1ebe5d;
                    }
                """)
            if hasattr(self, "whatsapp_btn"):
                self.whatsapp_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #128C7E;
                        color: white;
                        font-weight: bold;
                        border-radius: 10px;
                        padding: 8px 14px;
                    }
                    QPushButton:hover {
                        background-color: #0f766e;
                    }
                """)
            if hasattr(self, "preview_box_ref"):
                self.preview_box_ref.setStyleSheet("""
                    QGroupBox {
                        background: #f8fbff;
                        border: 1px solid #dbeafe;
                        border-radius: 18px;
                        padding: 16px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 14px;
                        padding: 0 8px;
                        font-size: 16px;
                        font-weight: 700;
                    }
                """)
            self.preview_logo.setStyleSheet("""
                background-color: #f8fbff;
                border: 1px dashed #cad6e5;
                border-radius: 10px;
                color: #64748b;
                font-weight: 600;
            """)
            self.preview_business_name.setStyleSheet("font-size:20px; font-weight:800; color:#0f172a;")
            self.preview_tagline.setStyleSheet("font-size:11px; color:#64748b;")
            self.preview_customer.setStyleSheet("font-size:13px; color:#172033; font-weight:700;")
            self.preview_doc_number.setStyleSheet("font-size:11px; color:#64748b;")
            self.preview_template.setStyleSheet("font-size:11px; color:#64748b;")
            self.preview_notes.setStyleSheet("""
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
                color: #334155;
            """)

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.save_app_settings()
        self.apply_theme()
        self.update_live_preview()

    def style_table(self):
        table_font = QFont("Segoe UI", 10)
        self.items_table.setFont(table_font)

        self.items_table.setAlternatingRowColors(False)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.items_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.items_table.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.EditKeyPressed |
            QAbstractItemView.SelectedClicked
        )
        self.items_table.setShowGrid(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setWordWrap(False)
        self.items_table.setCornerButtonEnabled(False)
        self.items_table.setMinimumHeight(400)
        self.items_table.setColumnWidth(0, 70)
        self.items_table.setColumnWidth(2, 120)
        self.items_table.setColumnWidth(3, 140)
        self.items_table.horizontalHeader().setMinimumHeight(42)
        self.items_table.horizontalHeader().setStretchLastSection(False)
        self.items_table.setStyleSheet("""
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #0f172a;
            }
        """)

        for row in range(self.items_table.rowCount()):
            self.items_table.setRowHeight(row, 38)

    def init_ui(self):
        self.setWindowTitle("ReceiptFlow")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(1440, 920)
        self.setMinimumSize(1240, 820)

        self.apply_theme()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_widget = QWidget()
        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setContentsMargins(8, 8, 8, 18)
        main_layout.setSpacing(14)

        top_banner = QFrame()
        top_banner.setObjectName("TopBanner")
        top_banner.setFixedHeight(86)

        top_banner_layout = QHBoxLayout(top_banner)
        top_banner_layout.setContentsMargins(20, 12, 20, 12)
        top_banner_layout.setSpacing(16)

        # LEFT: ICON + BRAND TEXT
        header_left = QHBoxLayout()
        header_left.setSpacing(12)

        self.header_icon = QLabel()
        self.header_icon.setObjectName("HeaderIconFrame")
        self.header_icon.setFixedSize(56, 56)
        self.header_icon.setAlignment(Qt.AlignCenter)

        if os.path.exists("icon.png"):
            pix = QPixmap("icon.png").scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.header_icon.setPixmap(pix)
        else:
            self.header_icon.setText("RF")
            self.header_icon.setStyleSheet("""
                background-color: #eef4ff;
                color: #153e96;
                border: 1px solid #d9e3f0;
                border-radius: 14px;
                font-size: 22px;
                font-weight: 800;
            """)

        title_block = QVBoxLayout()
        title_block.setSpacing(1)

        title = QLabel("ReceiptFlow")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignLeft)

        subtitle = QLabel("Smart Receipt & Invoice Generator")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignLeft)

        brand_note = QLabel("by RefinoTech")
        brand_note.setAlignment(Qt.AlignLeft)
        brand_note.setStyleSheet("font-size: 12px; color: #94a3b8; font-weight: 600;")

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addWidget(brand_note)

        header_left.addWidget(self.header_icon)
        header_left.addLayout(title_block)

        # RIGHT: STATUS + EDITION BADGE
        header_right = QHBoxLayout()
        header_right.setSpacing(10)

        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color:#22c55e; font-size:12px; font-weight:700;")

        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.setObjectName("SecondaryButton")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)

        self.edition_badge = QLabel("Professional Edition")
        self.edition_badge.setAlignment(Qt.AlignCenter)
        self.edition_badge.setFixedHeight(30)

        header_right.addStretch()
        header_right.addWidget(self.status_label)
        header_right.addWidget(self.theme_toggle_btn)
        header_right.addWidget(self.edition_badge)

        top_banner_layout.addLayout(header_left, 1)
        top_banner_layout.addLayout(header_right)

        main_layout.addWidget(top_banner)


        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # LEFT COLUMN
        business_box = QGroupBox("Business Information")
        business_grid = QGridLayout()
        business_grid.setHorizontalSpacing(12)
        business_grid.setVerticalSpacing(10)

        self.business_name_input = QLineEdit()
        self.business_name_input.setPlaceholderText("Enter business name")

        self.tagline_input = QLineEdit()
        self.tagline_input.setPlaceholderText("Enter business tagline")

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Enter business address")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter business email")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter business phone")

        self.business_header_line_input = QLineEdit()
        self.business_header_line_input.setPlaceholderText("Enter business category/header line")

        self.template_selector_input = QComboBox()
        self.template_selector_input.addItems([
            "Classic Blue",
            "Minimal Clean",
            "Premium Corporate"
        ])

        business_grid.addWidget(QLabel("Business Name"), 0, 0)
        business_grid.addWidget(self.business_name_input, 0, 1)

        business_grid.addWidget(QLabel("Tagline"), 1, 0)
        business_grid.addWidget(self.tagline_input, 1, 1)

        business_grid.addWidget(QLabel("Address"), 2, 0)
        business_grid.addWidget(self.address_input, 2, 1)

        business_grid.addWidget(QLabel("Email"), 3, 0)
        business_grid.addWidget(self.email_input, 3, 1)

        business_grid.addWidget(QLabel("Phone"), 4, 0)
        business_grid.addWidget(self.phone_input, 4, 1)

        business_grid.addWidget(QLabel("Header Line"), 5, 0)
        business_grid.addWidget(self.business_header_line_input, 5, 1)

        business_grid.addWidget(QLabel("Receipt Template"), 6, 0)
        business_grid.addWidget(self.template_selector_input, 6, 1)

        business_btn_row = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Business Profile")
        self.load_profile_btn = QPushButton("Load Business Profile")
        self.load_profile_btn.setObjectName("SecondaryButton")
        self.save_profile_btn.clicked.connect(self.save_business_profile)
        self.load_profile_btn.clicked.connect(self.load_business_profile)
        business_btn_row.addWidget(self.save_profile_btn)
        business_btn_row.addWidget(self.load_profile_btn)

        business_card_layout = QVBoxLayout()
        business_card_layout.addLayout(business_grid)
        business_card_layout.addSpacing(6)
        business_card_layout.addLayout(business_btn_row)
        business_box.setLayout(business_card_layout)
        left_col.addWidget(business_box)

        customer_box = QGroupBox("Customer / Invoice / Payment Information")
        customer_grid = QGridLayout()
        customer_grid.setHorizontalSpacing(12)
        customer_grid.setVerticalSpacing(10)

        self.customer_search_input = QLineEdit()
        self.customer_search_input.setPlaceholderText("Search customer...")

        self.customer_selector_input = QComboBox()
        self.customer_selector_input.addItem("Select saved customer")

        self.customer_name_input = QLineEdit()
        self.customer_name_input.setPlaceholderText("Enter customer name")

        self.customer_phone_input = QLineEdit()
        self.customer_phone_input.setPlaceholderText("Enter customer phone (e.g. 08012345678)")

        self.save_customer_btn = QPushButton("Save Customer")
        self.save_customer_btn.setObjectName("SecondaryButton")
        self.delete_customer_btn = QPushButton("Delete Customer")
        self.delete_customer_btn.setObjectName("SecondaryButton")

        self.document_type_input = QComboBox()

        self.document_type_input.addItems([
            "Invoice",
            "Receipt",
            "Proforma Invoice",
            "Sales Receipt"
        ])

        self.invoice_number_input = QLineEdit()
        self.invoice_number_input.setPlaceholderText("Enter document number (optional)")

        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)

        self.amount_words_input = QTextEdit()
        self.amount_words_input.setPlaceholderText("Amount in words")
        self.amount_words_input.setFixedHeight(90)

        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText("Enter account name (optional)")

        self.account_number_input = QLineEdit()
        self.account_number_input.setPlaceholderText("Enter account number (optional)")

        self.bank_name_input = QLineEdit()
        self.bank_name_input.setPlaceholderText("Enter bank name (optional)")

        self.show_payment_details_checkbox = QCheckBox("Show Payment Details on Receipt")

        self.receipt_notes_input = QTextEdit()
        self.receipt_notes_input.setPlaceholderText(
            "Optional receipt notes / terms.\n"
            "Example:\n"
            "Goods sold are not returnable.\n"
            "No refund after payment.\n"
            "Thank you for your patronage."
        )
        self.receipt_notes_input.setFixedHeight(90)

        customer_grid.addWidget(QLabel("Search Customer"), 0, 0)
        customer_grid.addWidget(self.customer_search_input, 0, 1)

        customer_grid.addWidget(QLabel("Saved Customers"), 1, 0)
        customer_grid.addWidget(self.customer_selector_input, 1, 1)

        customer_grid.addWidget(QLabel("Customer Name"), 2, 0)
        customer_grid.addWidget(self.customer_name_input, 2, 1)

        customer_grid.addWidget(QLabel("Customer Phone"), 3, 0)
        customer_grid.addWidget(self.customer_phone_input, 3, 1)

        button_row = QHBoxLayout()
        button_row.addWidget(self.save_customer_btn)
        button_row.addWidget(self.delete_customer_btn)

        customer_grid.addLayout(button_row, 4, 1)

        customer_grid.addWidget(QLabel("Document Type"), 5, 0)
        customer_grid.addWidget(self.document_type_input, 5, 1)

        customer_grid.addWidget(QLabel("Document Number"), 6, 0)
        customer_grid.addWidget(self.invoice_number_input, 6, 1)

        customer_grid.addWidget(QLabel("Invoice Date"), 7, 0)
        customer_grid.addWidget(self.date_input, 7, 1)

        customer_grid.addWidget(QLabel("Amount in Words"), 8, 0)
        customer_grid.addWidget(self.amount_words_input, 8, 1)

        customer_grid.addWidget(QLabel("Account Name"), 9, 0)
        customer_grid.addWidget(self.account_name_input, 9, 1)

        customer_grid.addWidget(QLabel("Account Number"), 10, 0)
        customer_grid.addWidget(self.account_number_input, 10, 1)

        customer_grid.addWidget(QLabel("Bank Name"), 11, 0)
        customer_grid.addWidget(self.bank_name_input, 11, 1)

        customer_grid.addWidget(QLabel("Receipt Notes / Terms"), 12, 0)
        customer_grid.addWidget(self.receipt_notes_input, 12, 1)

        customer_grid.addWidget(self.show_payment_details_checkbox, 13, 0, 1, 2)

        customer_box.setLayout(customer_grid)
        left_col.addWidget(customer_box)

        logo_box = QGroupBox("Business Logo")
        logo_box.setMaximumHeight(180)
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(14)

        left_logo_actions = QVBoxLayout()
        left_logo_actions.setSpacing(10)

        self.upload_logo_btn = QPushButton("Upload Logo")
        self.upload_logo_btn.clicked.connect(self.upload_logo)
        left_logo_actions.addWidget(self.upload_logo_btn)
        left_logo_actions.addStretch()

        logo_preview_frame = QFrame()
        logo_preview_frame.setObjectName("LogoPreviewFrame")
        logo_preview_frame.setFixedSize(170, 170)

        logo_preview_layout = QVBoxLayout(logo_preview_frame)
        logo_preview_layout.setContentsMargins(10, 10, 10, 10)

        self.logo_preview = QLabel("No Logo Uploaded")
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setStyleSheet(
            "border:none; background:transparent; font-weight:600; color:#64748b;"
        )
        logo_preview_layout.addWidget(self.logo_preview)

        logo_hint_layout = QVBoxLayout()
        logo_hint_layout.setSpacing(6)

        logo_hint_title = QLabel("Brand Preview")
        logo_hint_title.setStyleSheet("font-size:16px; font-weight:700; color:#0f172a;")

        logo_hint_text = QLabel("Your uploaded logo will be used in the app preview and receipt output.")
        logo_hint_text.setWordWrap(True)
        logo_hint_text.setObjectName("SectionHint")

        logo_hint_layout.addWidget(logo_hint_title)
        logo_hint_layout.addWidget(logo_hint_text)
        logo_hint_layout.addStretch()

        logo_layout.addLayout(left_logo_actions)
        logo_layout.addWidget(logo_preview_frame)
        logo_layout.addLayout(logo_hint_layout)
        logo_layout.addStretch()

        logo_box.setLayout(logo_layout)
        left_col.addWidget(logo_box)
        left_col.addStretch()

        # RIGHT COLUMN
        items_box = QGroupBox("Goods / Services")
        items_layout = QVBoxLayout()
        items_layout.setSpacing(10)

        self.items_table = QTableWidget(8, 4)
        self.items_table.setHorizontalHeaderLabels(["Qty", "Description", "Rate", "Amount"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.items_table.itemChanged.connect(self.on_table_item_changed)
        self.items_table.setItemDelegate(ReceiptTableDelegate(self.items_table))
        self.style_table()

        items_layout.addWidget(self.items_table)
        items_box.setLayout(items_layout)
        right_col.addWidget(items_box)

        totals_box = QGroupBox("Totals")
        totals_grid = QGridLayout()
        totals_grid.setHorizontalSpacing(12)
        totals_grid.setVerticalSpacing(10)

        self.vat_percent_input = QLineEdit()
        self.vat_percent_input.setText("0")
        self.vat_percent_input.textChanged.connect(self.update_totals)

        self.subtotal_input = QLineEdit()
        self.subtotal_input.setReadOnly(True)

        self.vat_amount_input = QLineEdit()
        self.vat_amount_input.setReadOnly(True)

        self.gross_total_input = QLineEdit()
        self.gross_total_input.setReadOnly(True)

        totals_grid.addWidget(QLabel("VAT %"), 0, 0)
        totals_grid.addWidget(self.vat_percent_input, 0, 1)

        totals_grid.addWidget(QLabel("Subtotal"), 0, 2)
        totals_grid.addWidget(self.subtotal_input, 0, 3)

        totals_grid.addWidget(QLabel("VAT Amount"), 1, 0)
        totals_grid.addWidget(self.vat_amount_input, 1, 1)

        totals_grid.addWidget(QLabel("Gross Total"), 1, 2)
        totals_grid.addWidget(self.gross_total_input, 1, 3)

        totals_box.setLayout(totals_grid)
        right_col.addWidget(totals_box)

        action_box = QGroupBox("Actions")
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)

        # PRIMARY ACTIONS
        primary_row = QHBoxLayout()
        primary_row.setSpacing(10)

        self.generate_btn = QPushButton("Generate Receipt")
        self.preview_btn = QPushButton("Preview Receipt")
        self.history_btn = QPushButton("View Receipt History")
        self.clear_btn = QPushButton("Clear Form")

        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d4ed8;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #1e40af;
            }
        """)

        self.preview_btn.setObjectName("SecondaryButton")
        self.history_btn.setObjectName("SecondaryButton")
        self.clear_btn.setObjectName("SecondaryButton")

        self.generate_btn.clicked.connect(self.generate_receipt)
        self.preview_btn.clicked.connect(self.preview_receipt)
        self.history_btn.clicked.connect(self.view_receipt_history)
        self.clear_btn.clicked.connect(self.clear_form)

        primary_row.addWidget(self.generate_btn)
        primary_row.addWidget(self.preview_btn)
        primary_row.addWidget(self.history_btn)
        primary_row.addWidget(self.clear_btn)

        # SECONDARY TOOLS
        tools_row = QHBoxLayout()
        tools_row.setSpacing(10)

        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.setObjectName("SecondaryButton")

        self.open_latest_folder_btn = QPushButton("Open Latest Receipt Folder")
        self.open_latest_folder_btn.setObjectName("SecondaryButton")

        self.open_last_pdf_btn = QPushButton("Open Last PDF")
        self.open_last_pdf_btn.setObjectName("SecondaryButton")

        self.open_last_png_btn = QPushButton("Open Last PNG")
        self.open_last_png_btn.setObjectName("SecondaryButton")

        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_latest_folder_btn.clicked.connect(self.open_latest_receipt_folder)
        self.open_last_pdf_btn.clicked.connect(self.open_last_pdf)
        self.open_last_png_btn.clicked.connect(self.open_last_png)

        tools_row.addWidget(self.open_folder_btn)
        tools_row.addWidget(self.open_latest_folder_btn)
        tools_row.addWidget(self.open_last_pdf_btn)
        tools_row.addWidget(self.open_last_png_btn)

        # SUPPORT ROW
        support_row = QHBoxLayout()
        support_row.setSpacing(10)

        self.support_btn = QPushButton("💬 Contact Support")
        self.support_btn.setStyleSheet("""
            QPushButton {
                background-color: #25D366;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #1ebe5d;
            }
        """)
        self.support_btn.clicked.connect(self.open_whatsapp)

        self.whatsapp_btn = QPushButton("📲 Send via WhatsApp")
        self.whatsapp_btn.setStyleSheet("""
            QPushButton {
                background-color: #128C7E;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #0f766e;
            }
        """)
        self.whatsapp_btn.clicked.connect(self.send_whatsapp_message)

        support_row.addWidget(self.support_btn)
        support_row.addWidget(self.whatsapp_btn)

        # INFO LABELS
        self.output_folder_label = QLabel(f"Output Folder: {os.path.abspath(self.output_folder)}")
        self.output_folder_label.setWordWrap(True)
        self.output_folder_label.setStyleSheet("font-size: 11px; color: #64748b;")

        self.data_folder_label = QLabel(f"Data Folder: {os.path.abspath(self.data_folder)}")
        self.data_folder_label.setWordWrap(True)
        self.data_folder_label.setStyleSheet("font-size: 11px; color: #64748b;")

        self.brand_label = QLabel("Powered by RefinoTech")
        self.brand_label.setAlignment(Qt.AlignCenter)
        self.brand_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
            padding-top: 4px;
        """)

        action_layout.addLayout(primary_row)
        action_layout.addLayout(tools_row)
        action_layout.addWidget(self.output_folder_label)
        action_layout.addWidget(self.data_folder_label)
        action_layout.addLayout(support_row)
        action_layout.addWidget(self.brand_label)

        action_box.setLayout(action_layout)
        right_col.addWidget(action_box)

        # LIVE MINI PREVIEW
        preview_box = QGroupBox("Live Mini Preview")
        self.preview_box_ref = preview_box
        preview_box.setStyleSheet("""
            QGroupBox {
                background: #f8fbff;
                border: 1px solid #dbeafe;
                border-radius: 18px;
                padding: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                font-size: 16px;
                font-weight: 700;
            }
        """)
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(8)

        self.preview_logo = QLabel("No Logo")
        self.preview_logo.setAlignment(Qt.AlignCenter)
        self.preview_logo.setFixedSize(120, 80)
        self.preview_logo.setStyleSheet("""
            background-color: #f8fbff;
            border: 1px dashed #cad6e5;
            border-radius: 10px;
            color: #64748b;
            font-weight: 600;
        """)

        self.preview_business_name = QLabel("Business Name")
        self.preview_business_name.setAlignment(Qt.AlignCenter)
        self.preview_business_name.setStyleSheet("font-size:18px; font-weight:800; color:#0f172a;")

        self.preview_tagline = QLabel("Business Tagline")
        self.preview_tagline.setAlignment(Qt.AlignCenter)
        self.preview_tagline.setWordWrap(True)
        self.preview_tagline.setStyleSheet("font-size:12px; color:#64748b;")

        self.preview_doc_type = QLabel("INVOICE")
        self.preview_doc_type.setAlignment(Qt.AlignCenter)
        self.preview_doc_type.setStyleSheet("font-size:16px; font-weight:800; color:#153e96;")

        self.preview_customer = QLabel("Customer: -")
        self.preview_customer.setWordWrap(True)
        self.preview_customer.setStyleSheet("font-size:13px; color:#172033; font-weight:600;")

        self.preview_doc_number = QLabel("Doc No: -")
        self.preview_doc_number.setStyleSheet("font-size:12px; color:#475569;")

        self.preview_template = QLabel("Template: Classic Blue")
        self.preview_template.setStyleSheet("font-size:12px; color:#475569;")

        self.preview_notes = QLabel("Notes preview will appear here.")
        self.preview_notes.setWordWrap(True)
        self.preview_notes.setStyleSheet("""
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 8px;
            font-size: 12px;
            color: #334155;
        """)

        preview_layout.addWidget(self.preview_logo, alignment=Qt.AlignCenter)
        preview_layout.addWidget(self.preview_business_name)
        preview_layout.addWidget(self.preview_tagline)
        preview_layout.addWidget(self.preview_doc_type)
        preview_layout.addWidget(self.preview_customer)
        preview_layout.addWidget(self.preview_doc_number)
        preview_layout.addWidget(self.preview_template)
        preview_layout.addWidget(self.preview_notes)

        preview_box.setLayout(preview_layout)
        right_col.addWidget(preview_box)
        right_col.addStretch()

        body_layout.addLayout(left_col, 4)
        body_layout.addLayout(right_col, 6)

        main_layout.addLayout(body_layout)

        scroll_area.setWidget(scroll_widget)
        root_layout.addWidget(scroll_area)

        self.utility_bar = QFrame()
        self.utility_bar.setObjectName("UtilityBar")

        utility_layout = QHBoxLayout(self.utility_bar)
        utility_layout.setContentsMargins(10, 8, 10, 8)
        utility_layout.setSpacing(10)

        self.choose_output_folder_btn = QPushButton("Choose Output Folder")
        self.choose_output_folder_btn.setObjectName("SecondaryButton")

        self.choose_data_folder_btn = QPushButton("Choose Data Folder")
        self.choose_data_folder_btn.setObjectName("SecondaryButton")

        self.archive_old_receipts_btn = QPushButton("Archive Old Receipts")
        self.archive_old_receipts_btn.setObjectName("SecondaryButton")

        self.choose_output_folder_btn.clicked.connect(self.choose_output_folder)
        self.choose_data_folder_btn.clicked.connect(self.choose_data_folder)
        self.archive_old_receipts_btn.clicked.connect(self.archive_old_receipts)

        utility_layout.addWidget(self.choose_output_folder_btn)
        utility_layout.addWidget(self.choose_data_folder_btn)
        utility_layout.addWidget(self.archive_old_receipts_btn)
        utility_layout.addStretch()

        root_layout.addWidget(self.utility_bar)

        # live preview signals
        self.business_name_input.textChanged.connect(self.update_live_preview)
        self.tagline_input.textChanged.connect(self.update_live_preview)
        self.customer_name_input.textChanged.connect(self.update_live_preview)
        self.invoice_number_input.textChanged.connect(self.update_live_preview)
        self.receipt_notes_input.textChanged.connect(self.update_live_preview)
        self.document_type_input.currentTextChanged.connect(self.update_live_preview)
        self.template_selector_input.currentTextChanged.connect(self.update_live_preview)

        self.save_customer_btn.clicked.connect(self.save_customer)
        self.delete_customer_btn.clicked.connect(self.delete_selected_customer)
        self.customer_selector_input.currentIndexChanged.connect(self.load_selected_customer)

        self.customer_search_input.textChanged.connect(self.filter_customers)

        self.load_customers_into_dropdown()

        self.update_theme_dependent_widgets()
        self.update_live_preview()

    def update_live_preview(self):
        business_name = self.business_name_input.text().strip() or "Business Name"
        tagline = self.tagline_input.text().strip() or "Business Tagline"
        document_type = self.document_type_input.currentText().strip().upper() or "INVOICE"
        customer_name = self.customer_name_input.text().strip() or "-"
        doc_number = self.invoice_number_input.text().strip() or "-"
        template_name = self.template_selector_input.currentText().strip() or "Classic Blue"

        notes_text = self.receipt_notes_input.toPlainText().strip()
        if notes_text:
            notes_lines = [line.strip() for line in notes_text.splitlines() if line.strip()]
            preview_notes = "\n".join(notes_lines[:3])
        else:
            preview_notes = "Notes preview will appear here."

        self.preview_business_name.setText(business_name)
        self.preview_tagline.setText(tagline)
        self.preview_doc_type.setText(document_type)
        self.preview_customer.setText(f"Customer: {customer_name}")
        self.preview_doc_number.setText(f"Doc No: {doc_number}")
        self.preview_template.setText(f"Template: {template_name}")
        self.preview_notes.setText(preview_notes)

        if self.logo_path and os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            scaled_pixmap = pixmap.scaled(100, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_logo.setPixmap(scaled_pixmap)
            self.preview_logo.setText("")
        else:
            self.preview_logo.clear()
            self.preview_logo.setText("No Logo")

        template_colors = {
            "Classic Blue": "#153e96",
            "Minimal Clean": "#5b6472",
            "Premium Corporate": "#14234d",
        }
        accent_color = template_colors.get(template_name, "#153e96")
        self.preview_doc_type.setStyleSheet(
            f"font-size:16px; font-weight:800; color:{accent_color};"
        )

    def get_template_style(self, template_name: str) -> dict:
        templates = {
            "Classic Blue": {
                "top_bar": (14, 28, 92),
                "bottom_bar": (14, 28, 92),
                "primary": (14, 28, 92),
                "accent": (188, 132, 42),
                "text": (18, 18, 18),
                "muted": (105, 105, 105),
                "light_fill": (236, 243, 252),
                "paper": (255, 255, 255),
                "watermark_opacity": 16,
            },
            "Minimal Clean": {
                "top_bar": (80, 88, 102),
                "bottom_bar": (80, 88, 102),
                "primary": (68, 76, 89),
                "accent": (120, 120, 120),
                "text": (40, 40, 40),
                "muted": (125, 125, 125),
                "light_fill": (248, 249, 251),
                "paper": (255, 255, 255),
                "watermark_opacity": 12,
            },
            "Premium Corporate": {
                "top_bar": (20, 35, 77),
                "bottom_bar": (20, 35, 77),
                "primary": (20, 35, 77),
                "accent": (166, 123, 45),
                "text": (20, 22, 28),
                "muted": (96, 103, 115),
                "light_fill": (243, 245, 248),
                "paper": (255, 255, 255),
                "watermark_opacity": 14,
            }
        }
        return templates.get(template_name, templates["Classic Blue"])

    def upload_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.logo_path = file_path
            self.show_logo_preview(file_path)
            self.update_live_preview()

    def show_logo_preview(self, file_path):
        pixmap = QPixmap(file_path)
        scaled_pixmap = pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_preview.setPixmap(scaled_pixmap)
        self.logo_preview.setText("")

    def load_app_settings(self):
        # First try root settings file for bootstrapping
        bootstrap_settings_file = "app_settings.json"

        settings = {}

        if os.path.exists(bootstrap_settings_file):
            try:
                with open(bootstrap_settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)

            except Exception:
                settings = {}

        saved_data_folder = settings.get("data_folder", "").strip()
        if saved_data_folder:
            self.data_folder = saved_data_folder

        saved_theme = settings.get("theme", "light").strip().lower()
        if saved_theme in {"light", "dark"}:
            self.current_theme = saved_theme

        self.settings_file = os.path.join(self.data_folder, "app_settings.json")
        self.profile_file = os.path.join(self.data_folder, "business_profile.json")
        self.history_file = os.path.join(self.data_folder, "receipt_history.json")
        self.invoice_counter_file = os.path.join(self.data_folder, "invoice_counter.txt")
        self.customers_file = os.path.join(self.data_folder, "saved_customers.json")

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}

        saved_output_folder = settings.get("output_folder", "").strip()
        if saved_output_folder:
            self.output_folder = saved_output_folder

        saved_data_folder = settings.get("data_folder", "").strip()
        if saved_data_folder:
            self.data_folder = saved_data_folder

        saved_theme = settings.get("theme", "").strip().lower()
        if saved_theme in {"light", "dark"}:
            self.current_theme = saved_theme

        self.settings_file = os.path.join(self.data_folder, "app_settings.json")
        self.profile_file = os.path.join(self.data_folder, "business_profile.json")
        self.history_file = os.path.join(self.data_folder, "receipt_history.json")
        self.invoice_counter_file = os.path.join(self.data_folder, "invoice_counter.txt")
        self.customers_file = os.path.join(self.data_folder, "saved_customers.json")
        
    def save_app_settings(self):
        settings = {
            "output_folder": self.output_folder,
            "data_folder": self.data_folder,
            "theme": self.current_theme
        }

        try:
            os.makedirs(self.data_folder, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            with open("app_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception:
            pass

    def choose_output_folder(self):
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Output Folder",
            self.output_folder
        )

        if not selected_folder:
            return
        
        self.output_folder = selected_folder
        os.makedirs(self.output_folder, exist_ok=True)
        self.save_app_settings()

        if hasattr(self, "output_folder_label"):
            self.output_folder_label.setText(f"Output Folder: {os.path.abspath(self.output_folder)}")

        QMessageBox.information(self, "Output Folder Updated", f"Receipts will now be saved to:\n{self.output_folder}")

    
    def choose_data_folder(self):
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Data Folder",
            self.data_folder
        )

        if not selected_folder:
            return
        
        old_profile = self.profile_file
        old_history = self.history_file
        old_customers = self.customers_file

        self.data_folder = selected_folder
        os.makedirs(self.data_folder, exist_ok=True)

        self.settings_file = os.path.join(self.data_folder, "app_settings.json")
        self.profile_file = os.path.join(self.data_folder, "business_profile.json")
        self.history_file = os.path.join(self.data_folder, "receipt_history.json")
        self.invoice_counter_file = os.path.join(self.data_folder, "invoice_counter.txt")
        self.customers_file = os.path.join(self.data_folder, "saved_customers.json")

        # Optionally migrate existing files if they exist
        for old_path, new_path in [
            (old_profile, self.profile_file),
            (old_history, self.history_file),
            (old_customers, self.customers_file),
        ]:
            try:
                if os.path.exists(old_path) and not os.path.exists(new_path):
                    with open(old_path, "r", encoding="utf-8") as src:
                        content = src.read()
                    with open(new_path, "w", encoding="utf-8") as dst:
                        dst.write(content)
            except Exception:
                pass

        self.save_app_settings()
        self.load_customers_into_dropdown()

        if hasattr(self, "data_folder_label"):
            self.data_folder_label.setText(f"Data Folder: {os.path.abspath(self.data_folder)}")

        QMessageBox.information(self, "Data Folder Updated", f"App data will now be stored in:\n{self.data_folder}")


    def open_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(os.path.abspath(self.output_folder))
            elif sys.platform == "darwin":
                os.system(f'open "{os.path.abspath(self.output_folder)}"')
            else:
                os.system(f'xdg-open "{os.path.abspath(self.output_folder)}"')
        except Exception as e:
            QMessageBox.warning(self, "Open Folder Error", f"Could not open output folder.\n{str(e)}")

    def get_receipt_save_folder(self):
        now = datetime.now()
        year_folder = now.strftime("%Y")
        month_folder = now.strftime("%m-%b")

        save_folder = os.path.join(self.output_folder, year_folder, month_folder)
        os.makedirs(save_folder, exist_ok=True)
        return save_folder
    
    def get_archive_folder(self):
        archive_folder = os.path.join(self.output_folder, "Archive")
        os.makedirs(archive_folder, exist_ok=True)
        return archive_folder
    
    def archive_old_receipts(self):
        reply = QMessageBox.question(
            self,
            "Confirm Archive",
            "Move all old receipt PDF/PNG files outside the current month folder into Archive?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        current_folder = os.path.abspath(self.get_receipt_save_folder())
        archive_root = os.path.abspath(self.get_archive_folder())

        moved_count = 0

        try:
            for root, dirs, files in os.walk(self.output_folder):
                abs_root = os.path.abspath(root)

                if abs_root.startswith(archive_root):
                    continue

                if abs_root == current_folder:
                    continue

                for file_name in files:
                    if not (file_name.lower().endswith(".pdf") or file_name.lower().endswith(".png")):
                        continue

                    source_path = os.path.join(root, file_name)

                    # Preserve year/month structure inside Archive
                    relative_path = os.path.relpath(root, self.output_folder)
                    target_folder = os.path.join(archive_root, relative_path)
                    os.makedirs(target_folder, exist_ok=True)

                    target_path = os.path.join(target_folder, file_name)

                    if os.path.exists(target_path):
                        base, ext = os.path.splitext(file_name)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        target_path = os.path.join(target_folder, f"{base}_{timestamp}{ext}")

                    os.replace(source_path, target_path)
                    moved_count += 1

            QMessageBox.information(
                self,
                "Archive Complete",
                f"{moved_count} old receipt file(s) moved to Archive successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Archive Error",
                f"Could not archive old receipts.\n\n{str(e)}"
            )

    def open_last_pdf(self):
        if not self.last_generated_pdf_path or not os.path.exists(self.last_generated_pdf_path):
            QMessageBox.information(self, "No PDF", "No generated PDF found yet.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(os.path.abspath(self.last_generated_pdf_path))
            elif sys.platform == "darwin":
                os.system(f'open "{os.path.abspath(self.last_generated_pdf_path)}"')
            else:
                os.system(f'xdg-open "{os.path.abspath(self.last_generated_pdf_path)}"')
        except Exception as e:
            QMessageBox.warning(self, "Open PDF Error", f"Could not open PDF.\n{str(e)}")

    def open_last_png(self):
        if not self.last_generated_image_path or not os.path.exists(self.last_generated_image_path):
            QMessageBox.information(self, "No PNG", "No generated PNG found yet.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(os.path.abspath(self.last_generated_image_path))
            elif sys.platform == "darwin":
                os.system(f'open "{os.path.abspath(self.last_generated_image_path)}"')
            else:
                os.system(f'xdg-open "{os.path.abspath(self.last_generated_image_path)}"')
        except Exception as e:
            QMessageBox.warning(self, "Open PNG Error", f"Could not open PNG.\n{str(e)}")

    def open_latest_receipt_folder(self):
        try:
            folder = self.get_receipt_save_folder()

            if os.path.exists(folder):
                os.startfile(folder)
            else:
                QMessageBox.information(self, "Not Found", "No receipts have been generated yet.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open folder:\n{str(e)}")

    def save_business_profile(self):
        data = {
            "business_name": self.business_name_input.text().strip(),
            "tagline": self.tagline_input.text().strip(),
            "address": self.address_input.text().strip(),
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "business_header_line": self.business_header_line_input.text().strip(),
            "template_name": self.template_selector_input.currentText(),
            "document_type": self.document_type_input.currentText(),
            "vat_percent": self.vat_percent_input.text().strip(),
            "logo_path": self.logo_path or "",
            "account_name": self.account_name_input.text().strip(),
            "account_number": self.account_number_input.text().strip(),
            "bank_name": self.bank_name_input.text().strip(),
            "receipt_notes": self.receipt_notes_input.toPlainText().strip(),
            "show_payment_details": self.show_payment_details_checkbox.isChecked(),
        }

        if not data["business_name"]:
            QMessageBox.warning(self, "Missing Field", "Please enter business name before saving profile.")
            return

        try:
            with open(self.profile_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            QMessageBox.information(self, "Profile Saved", f"Business profile saved successfully to:\n{self.profile_file}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save profile.\n{str(e)}")

    def load_business_profile(self):
        if not os.path.exists(self.profile_file):
            QMessageBox.information(self, "No Profile Found", "No saved business profile found yet.")
            return

        try:
            with open(self.profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.business_name_input.setText(data.get("business_name", ""))
            self.tagline_input.setText(data.get("tagline", ""))
            self.address_input.setText(data.get("address", ""))
            self.email_input.setText(data.get("email", ""))
            self.phone_input.setText(data.get("phone", ""))
            self.business_header_line_input.setText(data.get("business_header_line", ""))

            saved_template = data.get("template_name", "Classic Blue")
            template_index = self.template_selector_input.findText(saved_template)
            if template_index >= 0:
                self.template_selector_input.setCurrentIndex(template_index)

            saved_doc_type = data.get("document_type", "Invoice")
            doc_index = self.document_type_input.findText(saved_doc_type)
            if doc_index >= 0:
                self.document_type_input.setCurrentIndex(doc_index)

            self.vat_percent_input.setText(data.get("vat_percent", "7.5"))
            self.account_name_input.setText(data.get("account_name", ""))
            self.account_number_input.setText(data.get("account_number", ""))
            self.bank_name_input.setText(data.get("bank_name", ""))
            self.receipt_notes_input.setPlainText(data.get("receipt_notes", ""))
            self.show_payment_details_checkbox.setChecked(data.get("show_payment_details", False))

            logo_path = data.get("logo_path", "")
            if logo_path and os.path.exists(logo_path):
                self.logo_path = logo_path
                self.show_logo_preview(logo_path)
            else:
                self.logo_path = None
                self.logo_preview.clear()
                self.logo_preview.setText("No Logo Uploaded")

            self.update_live_preview()
            QMessageBox.information(self, "Profile Loaded", "Business profile loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not load profile.\n{str(e)}")

    def load_customers_from_file(self):
        if not os.path.exists(self.customers_file):
            return []

        try:
            with open(self.customers_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
        
    def save_customers_to_file(self, customers):
        with open(self.customers_file, "w", encoding="utf-8") as f:
            json.dump(customers, f, indent=4)

    def load_customers_into_dropdown(self):
        self.customer_search_input.clear()
        customers = self.load_customers_from_file()

        self.customer_selector_input.blockSignals(True)
        self.customer_selector_input.clear()
        self.customer_selector_input.addItem("Select saved customer")

        for customer in customers:
            name = customer.get("name", "").strip()
            phone = customer.get("phone", "").strip()
            if name:
                display_text = f"{name} - {phone}" if phone else name
                self.customer_selector_input.addItem(display_text, customer)

        self.customer_selector_input.blockSignals(False)

    def filter_customers(self):
        search_text = self.customer_search_input.text().strip().lower()
        customers = self.load_customers_from_file()

        self.customer_selector_input.blockSignals(True)
        self.customer_selector_input.clear()
        self.customer_selector_input.addItem("Select saved customer")

        for customer in customers:
            name = customer.get("name", "").lower()
            phone = customer.get("phone", "").lower()

            if search_text in name or search_text in phone:
                display = f"{customer.get('name')} - {customer.get('phone')}"
                self.customer_selector_input.addItem(display, customer)

        self.customer_selector_input.blockSignals(False)

    def save_customer(self):
        name = self.customer_name_input.text().strip()
        phone = self.customer_phone_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter customer name.")
            return
        
        customers = self.load_customers_from_file()

        # update existing by same name+phone or same name
        updated = False
        for customer in customers:
            existing_name = customer.get("name", "").strip().lower()
            existing_phone = customer.get("phone", "").strip()

            if existing_name == name.lower() and (existing_phone == phone or not phone):
                customer["name"] = name
                customer["phone"] = phone
                updated = True
                break

        if not updated:
            customers.append({
                "name": name,
                "phone": phone
            })

        customers = sorted(customers, key=lambda c: c.get("name", "").lower())
        self.save_customers_to_file(customers)
        self.load_customers_into_dropdown()

        QMessageBox.information(self, "Saved", f"{name} saved successfully.")

    def load_selected_customer(self):
        index = self.customer_selector_input.currentIndex()
        if index <= 0:
            return
        
        customer = self.customer_selector_input.currentData()
        if not isinstance(customer, dict):
            return
        
        self.customer_name_input.setText(customer.get("name", ""))
        self.customer_phone_input.setText(customer.get("phone", ""))
        self.update_live_preview()

    def delete_selected_customer(self):
        index = self.customer_selector_input.currentIndex()
        
        if index <= 0:
            QMessageBox.warning(self, "No Selection", "Please select a saved customer to delete.")
            return
        
        customer = self.customer_selector_input.currentData()
        if not isinstance(customer, dict):
            QMessageBox.warning(self, "Invalid Selection", "Could not read selected customer.")
            return
        
        name = customer.get("name", "").strip()
        phone = customer.get("phone", "").strip()

        customers = self.load_customers_from_file()

        updated_customers = []
        for item in customers:
            item_name = item.get("name", "").strip()
            item_phone = item.get("phone", "").strip()

            if item_name == name and item_phone == phone:
                continue
            updated_customers.append(item)

        self.save_customers_to_file(updated_customers)
        self.load_customers_into_dropdown()

        self.customer_selector_input.setCurrentIndex(0)
        self.customer_name_input.clear()
        self.customer_phone_input.clear()

        QMessageBox.information(self, "Deleted", f"{name} deleted successfully.")

    def save_receipt_history(self, record):
        history = []

        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(record)

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

    def view_receipt_history(self):
        if not os.path.exists(self.history_file):
            QMessageBox.information(self, "No History", "No receipt history found yet.")
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)

            if not history:
                QMessageBox.information(self, "No History", "Receipt history is empty.")
                return

            lines = []
            for index, item in enumerate(reversed(history), start=1):
                lines.append(f"Receipt {index}")
                lines.append(f"Generated At: {item.get('generated_at', '-')}")
                lines.append(f"Document Type: {item.get('document_type', '-')}")
                lines.append(f"Template: {item.get('template_name', '-')}")
                lines.append(f"Document No: {item.get('invoice_number', '-')}")
                lines.append(f"Customer Name: {item.get('customer_name', '-')}")
                lines.append(f"Invoice Date: {item.get('invoice_date', '-')}")
                lines.append(f"Subtotal: ₦{item.get('subtotal', '0.00')}")
                lines.append(f"VAT %: {item.get('vat_percent', '0')}")
                lines.append(f"VAT Amount: ₦{item.get('vat_amount', '0.00')}")
                lines.append(f"Gross Total: ₦{item.get('gross_total', '0.00')}")
                lines.append(f"PNG Path: {item.get('image_path', '-')}")
                lines.append(f"PDF Path: {item.get('pdf_path', '-')}")
                lines.append("-" * 80)

            dialog = ReceiptHistoryDialog("\n".join(lines), self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "History Error", f"Could not open receipt history.\n{str(e)}")

    def parse_float(self, value):
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return 0.0

    def format_currency(self, value):
        return f"{value:,.2f}"

    def split_currency_parts(self, value):
        value = round(float(value), 2)
        value_str = f"{value:.2f}"
        naira_part, kobo_part = value_str.split(".")
        naira_int = int(naira_part)
        return f"{naira_int:,}", kobo_part

    def normalize_name_case(self, text):
        text = " ".join(text.strip().split())
        return text.title()

    def normalize_item_case(self, text):
        text = " ".join(text.strip().split())
        words = text.split()
        normalized = []
        for w in words:
            if w.isupper() and len(w) <= 5:
                normalized.append(w)
            elif any(ch.isdigit() for ch in w):
                normalized.append(w.upper())
            else:
                normalized.append(w.capitalize())
        return " ".join(normalized)

    def amount_to_words(self, amount):
        try:
            naira = int(amount)
            kobo = int(round((amount - naira) * 100))

            words = num2words(naira, lang="en").replace(",", "").replace(" and", "").title()

            if kobo > 0:
                kobo_words = num2words(kobo, lang="en").replace(",", "").replace(" and", "").title()
                return f"{words} Naira, {kobo_words} Kobo Only"
            return f"{words} Naira Only"
        except Exception:
            return ""

    def on_table_item_changed(self, item):
        if self.updating_table:
            return

        if item.column() in [0, 2]:
            row = item.row()
            qty_item = self.items_table.item(row, 0)
            rate_item = self.items_table.item(row, 2)

            qty_text = qty_item.text().strip() if qty_item and qty_item.text() else ""
            rate_text = rate_item.text().strip() if rate_item and rate_item.text() else ""

            qty = self.parse_float(qty_text) if qty_text else 0.0
            rate = self.parse_float(rate_text) if rate_text else 0.0

            amount_text = ""
            if qty_text and rate_text:
                amount_text = self.format_currency(qty * rate)

            self.updating_table = True
            self.items_table.setItem(row, 3, self.create_table_item(amount_text))
            self.updating_table = False

        self.update_totals()

    def create_table_item(self, text):
        return QTableWidgetItem(text)

    def update_totals(self):
        subtotal = 0.0

        for row in range(self.items_table.rowCount()):
            amount_item = self.items_table.item(row, 3)
            if amount_item and amount_item.text().strip():
                subtotal += self.parse_float(amount_item.text())

        vat_percent = self.parse_float(self.vat_percent_input.text())
        vat_amount = subtotal * (vat_percent / 100)
        gross_total = subtotal + vat_amount

        self.subtotal_input.setText(self.format_currency(subtotal))
        self.vat_amount_input.setText(self.format_currency(vat_amount))
        self.gross_total_input.setText(self.format_currency(gross_total))
        self.amount_words_input.setPlainText(self.amount_to_words(gross_total))

    def clear_form(self):
        self.business_name_input.clear()
        self.tagline_input.clear()
        self.address_input.clear()
        self.email_input.clear()
        self.phone_input.clear()
        self.business_header_line_input.clear()
        self.template_selector_input.setCurrentText("Classic Blue")
        self.customer_name_input.clear()
        self.customer_phone_input.clear()
        self.customer_selector_input.setCurrentIndex(0)
        self.invoice_number_input.clear()
        self.document_type_input.setCurrentText("Invoice")
        self.amount_words_input.clear()
        self.account_name_input.clear()
        self.account_number_input.clear()
        self.bank_name_input.clear()
        self.receipt_notes_input.clear()
        self.show_payment_details_checkbox.setChecked(False)
        self.date_input.setDate(QDate.currentDate())
        self.logo_preview.clear()
        self.logo_preview.setText("No Logo Uploaded")
        self.logo_path = None
        self.items_table.clearContents()
        self.vat_percent_input.setText("0")
        self.subtotal_input.clear()
        self.vat_amount_input.clear()
        self.gross_total_input.clear()
        self.last_generated_image_path = None
        self.last_generated_pdf_path = None
        self.update_live_preview()
        QMessageBox.information(self, "Cleared", "Form has been cleared.")

    def get_next_invoice_number(self):
        document_type = self.document_type_input.currentText().strip()

        prefix_map = {
            "Invoice": "INV",
            "Receipt": "REC",
            "Proforma Invoice": "PRO",
            "Sales Receipt": "SAL"
        }

        prefix = prefix_map.get(document_type, "DOC")
        counter_file = os.path.join(self.data_folder, f"{prefix.lower()}_counter.txt")

        if not os.path.exists(counter_file):
            with open(counter_file, "w") as f:
                f.write("1")

        with open(counter_file, "r") as f:
            current = int(f.read().strip())

        next_number = current + 1

        with open(counter_file, "w") as f:
            f.write(str(next_number))

        return f"{prefix}-{current:04d}"

    def get_font(self, size=20, bold=False):
        possible_fonts = [
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
            "arialbd.ttf" if bold else "arial.ttf",
        ]

        for font_path in possible_fonts:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue

        return ImageFont.load_default()

    def collect_items(self):
        items = []
        for row in range(self.items_table.rowCount()):
            qty_item = self.items_table.item(row, 0)
            desc_item = self.items_table.item(row, 1)
            rate_item = self.items_table.item(row, 2)
            amount_item = self.items_table.item(row, 3)

            qty = qty_item.text().strip() if qty_item and qty_item.text() else ""
            desc = desc_item.text().strip() if desc_item and desc_item.text() else ""
            rate = rate_item.text().strip() if rate_item and rate_item.text() else ""
            amount = amount_item.text().strip() if amount_item and amount_item.text() else ""

            if qty or desc or rate or amount:
                items.append({
                    "qty": qty,
                    "desc": desc,
                    "rate": rate,
                    "amount": amount
                })
        return items

    def fit_logo(self, logo, max_size):
        temp = logo.copy()
        temp.thumbnail(max_size, Image.LANCZOS)
        return temp

    def crop_transparent_edges(self, img):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            return img.crop(bbox)
        return img

    def apply_opacity(self, img, opacity=45):
        img = img.convert("RGBA")
        pixels = []
        for r, g, b, a in img.getdata():
            if a == 0:
                pixels.append((r, g, b, 0))
            else:
                pixels.append((r, g, b, opacity))
        img.putdata(pixels)
        return img

    def draw_centered_text(self, draw, text, font, fill, box_x1, box_y1, box_x2, box_y2):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = box_x1 + ((box_x2 - box_x1) - text_w) // 2
        y = box_y1 + ((box_y2 - box_y1) - text_h) // 2
        draw.text((x, y), text, fill=fill, font=font)

    def draw_right_text(self, draw, text, font, fill, right_x, y):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text((right_x - text_w, y), text, fill=fill, font=font)

    def fit_text_to_width(self, draw, text, max_width, start_size=44, min_size=18, bold=True):
        size = start_size
        while size >= min_size:
            font = self.get_font(size, bold=bold)
            bbox = draw.textbbox((0, 0), text, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                return font
            size -= 2
        return self.get_font(min_size, bold=bold)

    def wrap_text_to_width(self, draw, text, font, max_width):
        if not text:
            return []
        words = text.split()
        lines = []
        current = ""

        for word in words:
            test = word if not current else f"{current} {word}"
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def truncate_text_to_width(self, draw, text, font, max_width):
        if not text:
            return ""
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return text

        trimmed = text
        while trimmed:
            candidate = trimmed + "..."
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                return candidate
            trimmed = trimmed[:-1]
        return "..."

    def save_image_as_pdf(self, image_path, pdf_path):
        page_width, page_height = A4
        pdf = canvas.Canvas(pdf_path, pagesize=A4)

        img = Image.open(image_path)
        img_width, img_height = img.size

        scale = min(page_width / img_width, page_height / img_height)
        draw_width = img_width * scale
        draw_height = img_height * scale

        x = (page_width - draw_width) / 2
        y = (page_height - draw_height) / 2

        pdf.drawImage(image_path, x, y, width=draw_width, height=draw_height)
        pdf.showPage()
        pdf.save()

    def preview_receipt(self):
        if not self.last_generated_image_path or not os.path.exists(self.last_generated_image_path):
            QMessageBox.information(
                self,
                "No Preview Available",
                "No generated receipt found yet. Please generate a receipt first."
            )
            return

        dialog = ReceiptPreviewDialog(self.last_generated_image_path, self)
        dialog.exec()

    def open_whatsapp(self):
        webbrowser.open("https://wa.me/2347047893541")

    def send_whatsapp_message(self):
        phone = self.customer_phone_input.text().strip()
        customer = self.customer_name_input.text().strip() or "Customer"
        business_name = self.business_name_input.text().strip() or "Our Company"
        doc_type = self.document_type_input.currentText().strip()
        doc_number = self.invoice_number_input.text().strip()

        if not phone:
            QMessageBox.warning(self, "Missing Phone", "Please enter customer phone number.")
            return

        if not doc_number:
            QMessageBox.warning(self, "Missing Document Number", "Please generate a receipt first.")
            return

        if not self.last_generated_pdf_path or not os.path.exists(self.last_generated_pdf_path):
            QMessageBox.warning(self, "Missing File", "Receipt file not found. Generate again.")
            return

        # Convert Nigerian number
        if phone.startswith("0"):
            phone = "234" + phone[1:]
        elif phone.startswith("+"):
            phone = phone[1:]

        message = (
            f"Hello {customer},\n\n"
            f"Your {doc_type} is ready.\n"
            f"Document No: {doc_number}\n\n"
            f"Thank you for your patronage.\n"
            f"- {business_name}"
        )

        encoded_message = urllib.parse.quote(message)
        url = f"https://wa.me/{phone}?text={encoded_message}"
        webbrowser.open(url)

        # OPEN THE PDF FILE AUTOMATICALLY
        try:
            os.startfile(self.last_generated_pdf_path)
        except Exception:
            QMessageBox.information(self, "Info", "Could not auto-open file. Please open manually.")



    def generate_receipt(self):
        business_name = self.business_name_input.text().strip()
        tagline = self.tagline_input.text().strip()
        address = self.address_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        business_header_line = self.business_header_line_input.text().strip()
        template_name = self.template_selector_input.currentText().strip()
        template = self.get_template_style(template_name)
        document_type = self.document_type_input.currentText().strip().upper()
        customer_name = self.normalize_name_case(self.customer_name_input.text())
        invoice_number = self.invoice_number_input.text().strip()
        if not invoice_number:
            invoice_number = self.get_next_invoice_number()
            self.invoice_number_input.setText(invoice_number)
        invoice_date_obj = self.date_input.date()
        invoice_date = invoice_date_obj.toString("dd/MM/yyyy")
        amount_words = self.amount_words_input.toPlainText().strip()

        account_name = self.account_name_input.text().strip()
        account_number = self.account_number_input.text().strip()
        bank_name = self.bank_name_input.text().strip()
        show_account_details = self.show_payment_details_checkbox.isChecked() and any(
            [account_name, account_number, bank_name]
        )

        notes_lines = [
            line.strip()
            for line in self.receipt_notes_input.toPlainText().splitlines()
            if line.strip()
        ]

        if not business_name:
            QMessageBox.warning(self, "Missing Field", "Please enter business name.")
            return

        if not customer_name:
            QMessageBox.warning(self, "Missing Field", "Please enter customer name.")
            return

        items = self.collect_items()
        if not items:
            QMessageBox.warning(self, "Missing Items", "Please enter at least one item in the table.")
            return

        subtotal = self.parse_float(self.subtotal_input.text())
        vat_amount = self.parse_float(self.vat_amount_input.text())
        gross_total = self.parse_float(self.gross_total_input.text())
        vat_percent = self.parse_float(self.vat_percent_input.text())

        img_width = 1400
        img_height = 1980
        margin = 70

        primary = template["primary"]
        accent = template["accent"]
        black = template["text"]
        white = template["paper"]
        light_fill = template["light_fill"]
        gray = template["muted"]

        image = Image.new("RGBA", (img_width, img_height), white)
        draw = ImageDraw.Draw(image)

        font_small = self.get_font(18, bold=False)
        font_normal = self.get_font(22, bold=False)
        font_table_header = self.get_font(24, bold=True)

        draw.rectangle([0, 0, img_width, 28], fill=template["top_bar"])

        content_center_x = img_width // 2

        top_logo_height_used = 0
        if self.logo_path:
            try:
                original_logo = Image.open(self.logo_path).convert("RGBA")
                original_logo = self.crop_transparent_edges(original_logo)
                top_logo = self.fit_logo(original_logo, (210, 130))
                logo_x = (img_width - top_logo.width) // 2
                logo_y = 40
                image.paste(top_logo, (logo_x, logo_y), top_logo)
                top_logo_height_used = top_logo.height
            except Exception:
                top_logo_height_used = 0

        brand_y = 42 + top_logo_height_used

        business_font = self.fit_text_to_width(draw, business_name, max_width=900, start_size=54, min_size=28, bold=True)
        bbox = draw.textbbox((0, 0), business_name, font=business_font)
        business_w = bbox[2] - bbox[0]
        business_h = bbox[3] - bbox[1]
        draw.text((content_center_x - business_w // 2, brand_y), business_name, fill=primary, font=business_font)
        brand_y += business_h + 8

        if tagline:
            tagline_font = self.fit_text_to_width(draw, tagline, max_width=900, start_size=24, min_size=16, bold=False)
            bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
            tagline_w = bbox[2] - bbox[0]
            tagline_h = bbox[3] - bbox[1]
            draw.text((content_center_x - tagline_w // 2, brand_y), tagline, fill=gray, font=tagline_font)
            brand_y += tagline_h + 14

        banner_text = business_header_line if business_header_line else "BUSINESS SERVICES AND PROFESSIONAL SOLUTIONS"
        banner_x1 = 250
        banner_x2 = img_width - 250
        banner_y1 = brand_y
        banner_y2 = brand_y + 48
        draw.rounded_rectangle([banner_x1, banner_y1, banner_x2, banner_y2], radius=10, fill=primary)

        banner_font = self.fit_text_to_width(draw, banner_text, max_width=(banner_x2 - banner_x1 - 30), start_size=20, min_size=12, bold=True)
        self.draw_centered_text(draw, banner_text, banner_font, white, banner_x1, banner_y1, banner_x2, banner_y2)
        brand_y = banner_y2 + 12

        contact_lines = []
        if address:
            contact_lines.append(address)

        second_line = "   ".join(filter(None, [email, phone]))
        if second_line:
            contact_lines.append(second_line)

        for line in contact_lines:
            contact_font = self.fit_text_to_width(draw, line, max_width=1000, start_size=22, min_size=14, bold=False)
            bbox = draw.textbbox((0, 0), line, font=contact_font)
            line_w = bbox[2] - bbox[0]
            draw.text((content_center_x - line_w // 2, brand_y), line, fill=black, font=contact_font)
            brand_y += (bbox[3] - bbox[1]) + 5

        invoice_title_y = brand_y + 4

        doc_title_font = self.fit_text_to_width(
            draw,
            document_type,
            max_width=420,
            start_size=34,
            min_size=20,
            bold=True
        )
        doc_bbox = draw.textbbox((0, 0), document_type, font=doc_title_font)
        doc_w = doc_bbox[2] - doc_bbox[0]

        draw.text(
            (content_center_x - doc_w // 2, invoice_title_y),
            document_type,
            fill=accent,
            font=doc_title_font
        )

        draw.line((content_center_x - 110, invoice_title_y + 46, content_center_x + 110, invoice_title_y + 46), fill=accent, width=3)

        section_y = invoice_title_y + 72

        name_x = margin
        name_label_font = self.get_font(28, bold=True)
        draw.text((name_x, section_y), "Name", fill=primary, font=name_label_font)
        draw.line((name_x + 105, section_y + 28, 700, section_y + 28), fill=primary, width=3)
        draw.line((name_x, section_y + 95, 700, section_y + 95), fill=primary, width=3)

        customer_font = self.fit_text_to_width(draw, customer_name, max_width=540, start_size=24, min_size=16, bold=False)
        draw.text((name_x + 120, section_y - 2), customer_name, fill=black, font=customer_font)

        date_box_x1 = 900
        date_box_y1 = section_y - 12
        date_box_x2 = img_width - margin
        date_box_y2 = section_y + 120

        draw.rectangle([date_box_x1, date_box_y1, date_box_x2, date_box_y2], outline=primary, width=3)

        title_row_h = 32
        header_row_h = 42

        draw.line((date_box_x1, date_box_y1 + title_row_h, date_box_x2, date_box_y1 + title_row_h), fill=primary, width=2)
        draw.line((date_box_x1, date_box_y1 + title_row_h + header_row_h, date_box_x2, date_box_y1 + title_row_h + header_row_h), fill=primary, width=2)

        date_col1 = date_box_x1 + 95
        date_col2 = date_col1 + 125
        draw.line((date_col1, date_box_y1 + title_row_h, date_col1, date_box_y2), fill=primary, width=2)
        draw.line((date_col2, date_box_y1 + title_row_h, date_col2, date_box_y2), fill=primary, width=2)

        self.draw_centered_text(draw, f"{document_type} DATE", self.get_font(18, bold=False), primary, date_box_x1, date_box_y1, date_box_x2, date_box_y1 + title_row_h)

        header_top = date_box_y1 + title_row_h
        header_bottom = header_top + header_row_h

        self.draw_centered_text(draw, "Date", self.get_font(18, bold=True), primary, date_box_x1, header_top, date_col1, header_bottom)
        self.draw_centered_text(draw, "Month", self.get_font(18, bold=True), primary, date_col1, header_top, date_col2, header_bottom)
        self.draw_centered_text(draw, "Year", self.get_font(18, bold=True), primary, date_col2, header_top, date_box_x2, header_bottom)

        val_top = header_bottom
        day_val = invoice_date_obj.toString("dd")
        month_val = invoice_date_obj.toString("MM")
        year_val = invoice_date_obj.toString("yyyy")

        self.draw_centered_text(draw, day_val, self.get_font(18, bold=False), black, date_box_x1, val_top, date_col1, date_box_y2)
        self.draw_centered_text(draw, month_val, self.get_font(18, bold=False), black, date_col1, val_top, date_col2, date_box_y2)
        self.draw_centered_text(draw, year_val, self.get_font(18, bold=False), black, date_col2, val_top, date_box_x2, date_box_y2)

        if invoice_number:
            draw.text(
                (date_box_x1 + 10, date_box_y1 - 28),
                f"No: {invoice_number}",
                fill=primary,
                font=self.get_font(18, bold=True)
            )

        table_y = section_y + 145
        table_x = margin
        col_qty = 120
        col_desc = 720
        col_rate = 150
        col_amount_main = 190
        col_kobo = 50
        row_height = 58
        table_h_rows = 8

        x1 = table_x + col_qty
        x2 = x1 + col_desc
        x3 = x2 + col_rate
        x4 = x3 + col_amount_main
        x5 = x4 + col_kobo

        header_y2 = table_y + row_height
        draw.rectangle([table_x, table_y, x5, header_y2], fill=primary, outline=primary, width=3)
        draw.line((x1, table_y, x1, header_y2), fill=white, width=3)
        draw.line((x2, table_y, x2, header_y2), fill=white, width=3)
        draw.line((x3, table_y, x3, header_y2), fill=white, width=3)
        draw.line((x4, table_y, x4, header_y2), fill=white, width=3)

        self.draw_centered_text(draw, "QTY", font_table_header, white, table_x, table_y, x1, header_y2)
        self.draw_centered_text(draw, "DESCRIPTION OF GOODS", font_table_header, white, x1, table_y, x2, header_y2)
        self.draw_centered_text(draw, "RATE", self.get_font(22, bold=True), white, x2, table_y, x3, header_y2)
        self.draw_centered_text(draw, "AMOUNT", self.get_font(21, bold=True), white, x3, table_y, x4, table_y + 28)
        self.draw_centered_text(draw, "₦", self.get_font(22, bold=True), white, x3, table_y + 24, x4, header_y2)
        self.draw_centered_text(draw, "K", self.get_font(22, bold=True), white, x4, table_y, x5, header_y2)

        body_top = header_y2
        body_bottom = body_top + (table_h_rows * row_height)

        draw.rectangle([table_x, body_top, x5, body_bottom], outline=primary, width=3)

        for x in [x1, x2, x3, x4]:
            draw.line((x, body_top, x, body_bottom), fill=primary, width=2)

        for row in range(table_h_rows):
            y1 = body_top + (row * row_height)
            y2 = y1 + row_height
            draw.line((table_x, y2, x5, y2), fill=primary, width=2)

            draw.rectangle([table_x, y1, x1, y2], fill=light_fill)
            draw.rectangle([x3, y1, x4, y2], fill=light_fill)
            draw.rectangle([x4, y1, x5, y2], fill=light_fill)

        if self.logo_path:
            try:
                original_logo = Image.open(self.logo_path).convert("RGBA")
                original_logo = self.crop_transparent_edges(original_logo)
                watermark = self.fit_logo(original_logo, (350, 250))
                watermark = self.apply_opacity(watermark, opacity=template["watermark_opacity"])
                wm_x = x1 + ((col_desc - watermark.width) // 2)
                wm_y = body_top + ((body_bottom - body_top - watermark.height) // 2)
                image.paste(watermark, (wm_x, wm_y), watermark)
            except Exception:
                pass

        desc_max_width = col_desc - 40
        current_y = body_top

        for index in range(table_h_rows):
            if index >= len(items):
                break

            item = items[index]
            row_mid_y = current_y + 13

            qty_text = self.truncate_text_to_width(draw, item["qty"], font_normal, col_qty - 20) if item["qty"] else ""
            desc_font = self.get_font(20, bold=False)
            normalized_desc = self.normalize_item_case(item["desc"]) if item["desc"] else ""

            rate_text = ""
            if item["rate"]:
                rate_value = self.parse_float(item["rate"])
                rate_text = f"{int(rate_value):,}" if rate_value else item["rate"]

            naira_part = ""
            kobo_part = ""
            if item["amount"]:
                amount_value = self.parse_float(item["amount"])
                naira_part, kobo_part = self.split_currency_parts(amount_value)

            if qty_text:
                draw.text((table_x + 18, row_mid_y), qty_text, fill=black, font=font_normal)

            if normalized_desc:
                wrapped_desc = self.wrap_text_to_width(draw, normalized_desc, desc_font, desc_max_width)
                if len(wrapped_desc) > 2:
                    wrapped_desc = wrapped_desc[:2]
                    wrapped_desc[-1] = self.truncate_text_to_width(draw, wrapped_desc[-1], desc_font, desc_max_width)

                if len(wrapped_desc) == 1:
                    draw.text((x1 + 20, row_mid_y), wrapped_desc[0], fill=black, font=desc_font)
                else:
                    line_y = current_y + 8
                    for line in wrapped_desc[:2]:
                        draw.text((x1 + 20, line_y), line, fill=black, font=desc_font)
                        line_y += 22

            if rate_text:
                self.draw_right_text(draw, rate_text, self.get_font(20, bold=False), black, x3 - 14, row_mid_y)
            if naira_part:
                self.draw_right_text(draw, naira_part, self.get_font(19, bold=False), black, x4 - 14, row_mid_y)
            if kobo_part:
                self.draw_right_text(draw, kobo_part, self.get_font(16, bold=False), black, x5 - 12, row_mid_y)

            current_y += row_height

        # ---------------------------
        # NOTES / TERMS (DYNAMIC PREMIUM)
        # ---------------------------
        lower_block_top = body_bottom + 25
        notes_block_bottom = lower_block_top

        if notes_lines:
            notes_x1 = table_x
            notes_x2 = x3 - 30
            notes_y1 = lower_block_top

            padding = 12
            line_spacing = 24
            max_width = (notes_x2 - notes_x1) - (padding * 2)

            wrapped_lines = []
            for note in notes_lines[:4]:
                wrapped_lines.extend(self.wrap_text_to_width(draw, note, font_small, max_width))

            content_height = len(wrapped_lines) * line_spacing
            notes_y2 = notes_y1 + 40 + content_height + 10

            draw.rectangle(
                [notes_x1, notes_y1, notes_x2, notes_y2],
                fill=light_fill,
                outline=primary,
                width=2
            )

            draw.text(
                (notes_x1 + padding, notes_y1 + 10),
                "NOTES / TERMS",
                fill=primary,
                font=self.get_font(19, bold=True)
            )

            text_y = notes_y1 + 40
            for line in wrapped_lines:
                draw.text(
                    (notes_x1 + padding, text_y),
                    line,
                    fill=black,
                    font=font_small
                )
                text_y += line_spacing

            notes_block_bottom = notes_y2 + 10
        else:
            notes_block_bottom = body_bottom + 25

        # ---------------------------
        # TOTALS BLOCK (AUTO LAYOUT)
        # ---------------------------
        subtotal_naira, subtotal_kobo = self.split_currency_parts(subtotal)
        gross_naira, gross_kobo = self.split_currency_parts(gross_total)

        if vat_amount > 0:
            totals_top = max(body_bottom + 10, notes_block_bottom + 10)
            totals_bottom_y = totals_top + 108

            draw.text((x3 - 255, totals_top + 8), "TOTAL ₦", fill=primary, font=self.get_font(22, bold=True))
            draw.text((x3 - 255, totals_top + 44), f"Add VAT {vat_percent}%", fill=black, font=self.get_font(19, bold=False))
            draw.text((x3 - 255, totals_top + 80), "GROSS TOTAL", fill=primary, font=self.get_font(22, bold=True))

            draw.rectangle([x3, totals_top, x5, totals_bottom_y], outline=primary, width=3)

            vat_row_y = totals_top + 36
            gross_row_y = totals_top + 72

            draw.line((x3, vat_row_y, x5, vat_row_y), fill=primary, width=2)
            draw.line((x3, gross_row_y, x5, gross_row_y), fill=primary, width=2)
            draw.line((x4, totals_top, x4, totals_bottom_y), fill=primary, width=2)

            for y1, y2 in [
                (totals_top, vat_row_y),
                (vat_row_y, gross_row_y),
                (gross_row_y, totals_bottom_y)
            ]:
                draw.rectangle([x3, y1, x4, y2], fill=light_fill)
                draw.rectangle([x4, y1, x5, y2], fill=light_fill)

            vat_naira, vat_kobo = self.split_currency_parts(vat_amount)

            self.draw_right_text(draw, subtotal_naira, self.get_font(19, bold=False), black, x4 - 14, totals_top + 8)
            self.draw_right_text(draw, subtotal_kobo, self.get_font(16, bold=False), black, x5 - 12, totals_top + 8)

            self.draw_right_text(draw, vat_naira, self.get_font(19, bold=False), black, x4 - 14, totals_top + 44)
            self.draw_right_text(draw, vat_kobo, self.get_font(16, bold=False), black, x5 - 12, totals_top + 44)

            self.draw_right_text(draw, gross_naira, self.get_font(22, bold=True), black, x4 - 14, totals_top + 80)
            self.draw_right_text(draw, gross_kobo, self.get_font(18, bold=True), black, x5 - 12, totals_top + 80)
        else:
            totals_top = max(body_bottom + 10, notes_block_bottom + 10)
            totals_bottom_y = totals_top + 72

            draw.text((x3 - 255, totals_top + 8), "TOTAL ₦", fill=primary, font=self.get_font(22, bold=True))
            draw.text((x3 - 255, totals_top + 44), "GROSS TOTAL", fill=primary, font=self.get_font(22, bold=True))

            draw.rectangle([x3, totals_top, x5, totals_bottom_y], outline=primary, width=3)

            gross_row_y = totals_top + 36

            draw.line((x3, gross_row_y, x5, gross_row_y), fill=primary, width=2)
            draw.line((x4, totals_top, x4, totals_bottom_y), fill=primary, width=2)

            for y1, y2 in [
                (totals_top, gross_row_y),
                (gross_row_y, totals_bottom_y)
            ]:
                draw.rectangle([x3, y1, x4, y2], fill=light_fill)
                draw.rectangle([x4, y1, x5, y2], fill=light_fill)

            self.draw_right_text(draw, subtotal_naira, self.get_font(19, bold=False), black, x4 - 14, totals_top + 8)
            self.draw_right_text(draw, subtotal_kobo, self.get_font(16, bold=False), black, x5 - 12, totals_top + 8)

            self.draw_right_text(draw, gross_naira, self.get_font(22, bold=True), black, x4 - 14, totals_top + 44)
            self.draw_right_text(draw, gross_kobo, self.get_font(18, bold=True), black, x5 - 12, totals_top + 44)

        payment_block_bottom = totals_bottom_y

        if show_account_details:
            payment_x1 = margin
            payment_x2 = img_width - margin
            payment_y1 = totals_bottom_y + 32

            payment_lines = []
            if account_name:
                payment_lines.append(f"Account Name: {account_name}")
            if account_number:
                payment_lines.append(f"Account Number: {account_number}")
            if bank_name:
                payment_lines.append(f"Bank Name: {bank_name}")

            payment_y2 = payment_y1 + 54 + (len(payment_lines) * 24)
            payment_y2 = max(payment_y2, payment_y1 + 90)

            draw.rectangle([payment_x1, payment_y1, payment_x2, payment_y2], outline=primary, width=2)
            draw.text((payment_x1 + 18, payment_y1 + 12), "PAYMENT DETAILS", fill=primary, font=self.get_font(22, bold=True))

            line_y = payment_y1 + 48
            info_font = self.get_font(19, bold=False)

            for line in payment_lines:
                draw.text((payment_x1 + 18, line_y), line, fill=black, font=info_font)
                line_y += 24

            payment_block_bottom = payment_y2

        words_y = payment_block_bottom + 32
        draw.text((margin, words_y), "Amount in words", fill=primary, font=self.get_font(28, bold=True))
        draw.line((340, words_y + 30, img_width - margin, words_y + 30), fill=primary, width=2)
        draw.line((margin, words_y + 95, img_width - margin, words_y + 95), fill=primary, width=2)

        if amount_words:
            words_font = self.fit_text_to_width(draw, amount_words, max_width=960, start_size=22, min_size=15, bold=False)
            draw.text((355, words_y + 3), amount_words, fill=black, font=words_font)

        signature_y = words_y + 120
        draw.line((margin, signature_y + 48, 500, signature_y + 48), fill=primary, width=3)
        draw.text((margin, signature_y + 55), "Customer's Signature", fill=primary, font=self.get_font(24, bold=True))

        if self.logo_path:
            try:
                original_logo = Image.open(self.logo_path).convert("RGBA")
                original_logo = self.crop_transparent_edges(original_logo)
                bottom_logo = self.fit_logo(original_logo, (135, 95))
                bottom_x = img_width - margin - 225
                bottom_y = signature_y - 6
                image.paste(bottom_logo, (bottom_x, bottom_y), bottom_logo)

                bottom_name_font = self.fit_text_to_width(draw, business_name, max_width=210, start_size=22, min_size=16, bold=True)
                bottom_name_bbox = draw.textbbox((0, 0), business_name, font=bottom_name_font)
                bottom_name_w = bottom_name_bbox[2] - bottom_name_bbox[0]
                bottom_name_x = bottom_x + (bottom_logo.width - bottom_name_w) // 2
                bottom_name_y = bottom_y + bottom_logo.height + 6
                draw.text((bottom_name_x, bottom_name_y), business_name, fill=primary, font=bottom_name_font)
            except Exception:
                pass

        draw.rectangle([0, img_height - 24, img_width, img_height], fill=template["bottom_bar"])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_folder = self.get_receipt_save_folder()
        image_path = os.path.join(save_folder, f"receipt_{timestamp}.png")
        pdf_path = os.path.join(save_folder, f"receipt_{timestamp}.pdf")

        image.convert("RGB").save(image_path)
        self.save_image_as_pdf(image_path, pdf_path)

        self.last_generated_image_path = image_path
        self.last_generated_pdf_path = pdf_path

        history_record = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "invoice_number": invoice_number or "-",
            "document_type": document_type,
            "template_name": template_name,
            "customer_name": customer_name,
            "invoice_date": invoice_date,
            "subtotal": self.subtotal_input.text() or "0.00",
            "vat_percent": self.vat_percent_input.text() or "0",
            "vat_amount": self.vat_amount_input.text() or "0.00",
            "gross_total": self.gross_total_input.text() or "0.00",
            "image_path": image_path,
            "pdf_path": pdf_path
        }
        self.save_receipt_history(history_record)

        QMessageBox.information(
            self,
            "Success",
            f"Receipt generated successfully.\n\nPNG saved to:\n{image_path}\n\nPDF saved to:\n{pdf_path}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    splash_pix = QPixmap("splash.png")
    splash_pix = splash_pix.scaled(
        1250, 560,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )
    splash = AnimatedSplashScreen(splash_pix)
    splash.show()
    splash.start_animation()

    window = ReceiptApp()

    def show_main_window():
        splash.close()
        window.showMaximized()

    QTimer.singleShot(2500, show_main_window)

    sys.exit(app.exec())