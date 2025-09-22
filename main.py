import contextlib
import json
import logging
import logging.config
import os
import stat
import sys
from typing import Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

import src.write_report_data as data_write_report
import src.write_report_mcp as mcp_write_report
from src.constants import (
    LOGGER_NAME,
    REQUIRED_FILE_CATEGORIES,
    FileCategory,
    FileTypeFilter,
    Gender,
    Program,
)
from src.data_models import GuiData, IcpGuiData
from src.global_signals import global_signals
from src.prompting import send_prompts
from src.redact import redact_folder
from src.report_utils import clean_up, resource_path

# Set up logging
logger = logging.getLogger(LOGGER_NAME)
with open("logging_config.json") as config:
    logging_config = json.load(config)
logging.config.dictConfig(logging_config)

# Define paths for resources
logo_path_abs = "resources/ormittalentV3.png"
icon_path_abs = "resources/assessmentReport.ico"

logo_path = resource_path(logo_path_abs)
icon_path = resource_path(icon_path_abs)


class ProcessingThread(QThread):
    processing_completed = pyqtSignal(str)

    def __init__(self, gui_data: GuiData | IcpGuiData):
        super().__init__()
        self.gui_data = gui_data

    def run(self) -> None:
        try:
            # Create temp directory if it doesn't exist
            if not os.path.exists("temp"):
                os.makedirs("temp")

            # Check if all required files exist
            for file_path in self.gui_data.files.values():
                if not os.path.exists(file_path):
                    global_signals.update_message.emit(f"Error: File not found: {file_path}")
                    return

            # Redact and store files
            global_signals.update_message.emit("Redacting sensitive information...")
            redact_folder(self.gui_data)

            # Send prompts to Gemini
            global_signals.update_message.emit("Sending prompts to Gemini...")
            output_path = send_prompts(self.gui_data)

            # Convert JSON to report
            global_signals.update_message.emit("Generating report...")
            clean_data = clean_up(output_path)
            selected_program = self.gui_data.traineeship

            if selected_program in (Program.MNGT, Program.ICP):
                updated_doc = mcp_write_report.update_document(
                    clean_data,
                    self.gui_data.applicant_name,
                    self.gui_data.assessor_name,
                    self.gui_data.gender,
                    self.gui_data.traineeship,
                )
            elif selected_program == Program.DATA:
                updated_doc = data_write_report.update_document(
                    clean_data,
                    self.gui_data.applicant_name,
                    self.gui_data.assessor_name,
                    self.gui_data.gender,
                    self.gui_data.traineeship,
                )
            else:
                # Default fallback (can remain MCP or be made more specific if needed)
                global_signals.update_message.emit(
                    f"Warning: Unknown program '{selected_program}', defaulting to MCP report."
                )
                updated_doc = mcp_write_report.update_document(
                    clean_data,
                    self.gui_data.applicant_name,
                    self.gui_data.assessor_name,
                    self.gui_data.gender,
                    self.gui_data.traineeship,
                )

            if updated_doc:
                global_signals.update_message.emit(f"Report generated successfully: {updated_doc}")
                # Emit the path of the generated document
                self.processing_completed.emit(updated_doc)
            else:
                global_signals.update_message.emit("Error: Failed to generate report.")

        except Exception as e:
            logger.exception("Error in processing thread:")
            global_signals.update_message.emit(f"Error: {e!s}")


class MainWindow(QWidget):
    KEY_FILE = os.path.expanduser("~/.ormit_gemini_key")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("ORMIT - Draft Assessment Report v1.0")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(1000)
        self.setStyleSheet("background-color: white; color: black;")
        bold_font = QFont()
        bold_font.setBold(True)

        layout = QGridLayout()
        self.setLayout(layout)

        # Initialize the message box once here
        self.msg_box = QMessageBox(self)
        self.msg_box.setWindowTitle("Processing")
        self.msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
        self.msg_box.setWindowFlags(
            self.msg_box.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.msg_box.setStandardButtons(QMessageBox.StandardButton.Close)
        msg_box_close = self.msg_box.button(QMessageBox.StandardButton.Close)
        if msg_box_close is not None:
            msg_box_close.clicked.connect(self.close_application)

        global_signals.update_message.connect(self.refresh_message_box)

        # Load the logo
        pixmap = QPixmap(logo_path)
        pixmap_label = QLabel()
        pixmap_label.setScaledContents(True)
        resize_fac = 3
        scaled_pixmap = pixmap.scaled(
            round(pixmap.width() / resize_fac),
            round(pixmap.height() / resize_fac),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap_label.setPixmap(scaled_pixmap)
        layout.addWidget(pixmap_label, 0, 0, 1, 2)

        # OpenAI Key input
        self.key_label = QLabel("Gemini Key:")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.key_label, 1, 0)

        self.openai_key_input = QLineEdit()
        self.openai_key_input.setPlaceholderText("Enter Gemini Key: ***************")
        # Load saved key if available
        self._load_saved_key()
        layout.addWidget(self.openai_key_input, 1, 1, 1, 2)

        # Applicant information
        self.applicant_label = QLabel("Applicant:")
        self.applicant_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.applicant_label, 2, 0)

        self.applicant_name_input = QLineEdit()
        self.applicant_name_input.setPlaceholderText("Applicant Full Name")
        layout.addWidget(self.applicant_name_input, 2, 1, 1, 2)

        # Assessor information
        self.assessor_label = QLabel("Assessor:")
        self.assessor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.assessor_label, 3, 0)

        self.assessor_name_input = QLineEdit()
        self.assessor_name_input.setPlaceholderText("Assessor Full Name")
        layout.addWidget(self.assessor_name_input, 3, 1, 1, 2)

        # Select Gender
        self.gender_label = QLabel("Gender:")
        self.gender_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.gender_label, 4, 0)

        self.gender_combo = QComboBox(self)
        for gender in Gender:
            self.gender_combo.addItem(gender)
        self.gender_combo.setToolTip("Select a gender")
        layout.addWidget(self.gender_combo, 4, 1)

        # Enable Thinking checkbox
        self.enable_thinking_label = QLabel("Enable AI Thinking:")
        self.enable_thinking_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.enable_thinking_label, 5, 0)

        # Create a horizontal layout for the checkbox and tooltip
        thinking_layout = QHBoxLayout()

        self.enable_thinking_checkbox = QCheckBox(self)
        self.enable_thinking_checkbox.setStyleSheet("""
            QCheckBox {
                background-color: #f0f0f0;
                border: 1px solid #999999;
                border-radius: 3px;
                padding: 1px;
                min-width: 18px;
                min-height: 18px;
                max-width: 16px;
                max-height: 22px;
            }
            QCheckBox:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
            QCheckBox:checked {
                background-color: #f0f0f0;
                border-color: #999999;
            }
        """)
        thinking_layout.addWidget(self.enable_thinking_checkbox)

        # Add tooltip icon with simple hover functionality
        tooltip_label = QLabel("?")
        tooltip_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            }
            QLabel:hover {
                color: #000000;
            }
        """)
        tooltip_label.setToolTip("""Pros: Higher quality, more detailed.
Cons: Slower response, higher cost.""")
        # Use standard help cursor for better tooltip behavior
        tooltip_label.setCursor(Qt.CursorShape.WhatsThisCursor)
        thinking_layout.addWidget(tooltip_label)

        # Add the horizontal layout to the main grid
        layout.addLayout(thinking_layout, 5, 1)

        # Select Traineeship
        self.program_label = QLabel("Traineeship:")
        self.program_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.program_label, 6, 0)

        self.program_combo = QComboBox(self)
        for program in Program:
            self.program_combo.addItem(program)
        self.program_combo.setToolTip("Select a traineeship")
        layout.addWidget(self.program_combo, 6, 1)

        self.selected_files: dict[FileCategory, str] = {}

        idx = 0
        for idx, file_cat in enumerate(REQUIRED_FILE_CATEGORIES):
            file_label = QLabel(file_cat, self)
            file_browser_btn = QPushButton("No file selected")
            file_browser_btn.clicked.connect(
                lambda _,  # Uhm.... No idea why this "_" is needed, but it works... TODO: investigate
                file_button=file_browser_btn,
                file_category=file_cat: self.open_file_dialog(file_button, file_category)
            )
            layout.addWidget(file_label, 7 + idx, 0)
            layout.addWidget(file_browser_btn, 7 + idx, 1, 1, 2)

        # ICP Info for Prompt 3 (Personality)
        self.icp_info_prompt3_label = QLabel("ICP Info (Personality):")
        self.icp_info_prompt3_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.icp_info_prompt3_label.setVisible(False)
        layout.addWidget(self.icp_info_prompt3_label, 7 + idx + 1, 0)

        self.icp_info_prompt3_input = QLineEdit()
        self.icp_info_prompt3_input.setPlaceholderText(
            "Optional: Specific instructions/context for Prompt 3"
        )
        self.icp_info_prompt3_input.setVisible(False)
        layout.addWidget(self.icp_info_prompt3_input, 7 + idx + 1, 1, 1, 2)

        # ICP Info for Prompt 6a (Strengths)
        self.icp_info_prompt6a_label = QLabel("ICP Info (Strengths):")
        self.icp_info_prompt6a_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.icp_info_prompt6a_label.setVisible(False)
        layout.addWidget(self.icp_info_prompt6a_label, 7 + idx + 2, 0)

        self.icp_info_prompt6a_input = QLineEdit()
        self.icp_info_prompt6a_input.setPlaceholderText(
            "Optional: Specific instructions/context for Prompt 6a"
        )
        self.icp_info_prompt6a_input.setVisible(False)
        layout.addWidget(self.icp_info_prompt6a_input, 7 + idx + 2, 1, 1, 2)

        # ICP Info for Prompt 6b (Improvements)
        self.icp_info_prompt6b_label = QLabel("ICP Info (Improvements):")
        self.icp_info_prompt6b_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.icp_info_prompt6b_label.setVisible(False)
        layout.addWidget(self.icp_info_prompt6b_label, 7 + idx + 3, 0)

        self.icp_info_prompt6b_input = QLineEdit()
        self.icp_info_prompt6b_input.setPlaceholderText(
            "Optional: Specific instructions/context for Prompt 6b"
        )
        self.icp_info_prompt6b_input.setVisible(False)
        layout.addWidget(self.icp_info_prompt6b_input, 7 + idx + 3, 1, 1, 2)

        # ICP Description File Button/Label
        self.icp_desc_button = QPushButton("No file selected (Required for ICP)")
        self.icp_desc_button.setVisible(False)
        self.icp_desc_button.clicked.connect(
            lambda: self.open_file_dialog(
                self.icp_desc_button, FileCategory.ICP, FileTypeFilter.WORD
            )
        )

        self.icp_desc_label = QLabel(FileCategory.ICP, self)
        self.icp_desc_label.setVisible(False)
        layout.addWidget(self.icp_desc_button, 7 + idx + 4, 1, 1, 2)
        layout.addWidget(self.icp_desc_label, 7 + idx + 4, 0)

        # Connect program selection change signal AFTER ICP widgets are created
        self.program_combo.currentIndexChanged.connect(self.handle_program_change)

        # Submit button
        self.submitbtn = QPushButton("Submit")
        self.submitbtn.setFixedWidth(90)
        self.submitbtn.hide()
        layout.addWidget(self.submitbtn, 7 + idx + 5, 2, Qt.AlignmentFlag.AlignRight)
        self.submitbtn.clicked.connect(self.handle_submit)

        # Initialize UI based on default selection
        self.handle_program_change()

    def refresh_message_box(self, message: str) -> None:
        self.msg_box.setText(message)
        # Make sure the message box is visible
        if not self.msg_box.isVisible():
            self.msg_box.show()
        # Force update of the UI
        QApplication.processEvents()

    def close_application(self) -> None:
        # This will close the application when the messagebox is closed manually
        QApplication.quit()

    def handle_program_change(self) -> None:
        """Shows or hides ICP-specific widgets based on program selection."""
        selected_program = self.program_combo.currentText()
        is_icp = selected_program == Program.ICP

        # Show/Hide the 3 labels and 3 inputs for specific prompts
        self.icp_info_prompt3_label.setVisible(is_icp)
        self.icp_info_prompt3_input.setVisible(is_icp)
        self.icp_info_prompt6a_label.setVisible(is_icp)
        self.icp_info_prompt6a_input.setVisible(is_icp)
        self.icp_info_prompt6b_label.setVisible(is_icp)
        self.icp_info_prompt6b_input.setVisible(is_icp)

        # Show/Hide the ICP Description file widgets
        self.icp_desc_button.setVisible(is_icp)
        self.icp_desc_label.setVisible(is_icp)

    def open_file_dialog(
        self,
        file_selector_button: QPushButton,
        file_cat: FileCategory,
        file_type_filter=FileTypeFilter.PDF,
    ) -> None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter(file_type_filter)
        dialog.setViewMode(QFileDialog.ViewMode.List)

        if dialog.exec():
            filenames = dialog.selectedFiles()
            if filenames:
                selected_file = str(filenames[0])
                file_basename = os.path.basename(selected_file)

                file_selector_button.setText(file_basename)
                self.selected_files[file_cat] = selected_file

                # Check if standard files are selected to show submit button
                standard_files_selected = all(
                    key in self.selected_files for key in REQUIRED_FILE_CATEGORIES
                )
                if standard_files_selected:
                    self.submitbtn.show()
                # Submit button remains hidden otherwise

    def _load_saved_key(self) -> None:
        try:
            if os.path.exists(MainWindow.KEY_FILE):
                with open(MainWindow.KEY_FILE) as f:
                    key = f.read().strip()
                    if key:
                        self.openai_key_input.setText(key)
        except Exception:
            logger.exception("Could not load saved Gemini key.")

    def _save_key(self, key: str) -> None:
        try:
            with open(self.KEY_FILE, "w") as f:
                f.write(key.strip())
            # Set file permissions to user read/write only (if possible)
            with contextlib.suppress(Exception):
                os.chmod(self.KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            logger.exception("Could not load saved Gemini key.")

    def handle_submit(self) -> None:
        # Validate input
        if not self.openai_key_input.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter a Gemini API key.")
            return
        # Save the key if changed
        current_key = self.openai_key_input.text().strip()
        if not os.path.exists(self.KEY_FILE) or open(self.KEY_FILE).read().strip() != current_key:
            self._save_key(current_key)

        if not self.applicant_name_input.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter the applicant's name.")
            return

        if not self.assessor_name_input.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter the assessor's name.")
            return

        # Check if all required files are selected
        missing_files = [
            f
            for f in REQUIRED_FILE_CATEGORIES
            if f not in self.selected_files or not self.selected_files[f]
        ]

        if missing_files:
            QMessageBox.warning(
                self,
                "Missing Files",
                f"Please select the following files: {', '.join(missing_files)}",
            )
            return

        selected_program = Program(self.program_combo.currentText())
        selected_gender = Gender(self.gender_combo.currentText())

        # Gather all the data into a dictionary
        gui_data = GuiData(
            gemini_key=self.openai_key_input.text(),
            applicant_name=self.applicant_name_input.text(),
            assessor_name=self.assessor_name_input.text(),
            gender=selected_gender,
            traineeship=selected_program,
            files=self.selected_files.copy(),
            enable_thinking=self.enable_thinking_checkbox.isChecked(),
        )

        # Add ICP-specific data and validation
        if selected_program == Program.ICP:
            # Check required ICP description file
            if (
                FileCategory.ICP not in self.selected_files
                or self.selected_files[FileCategory.ICP] == ""
            ):
                QMessageBox.warning(
                    self, "Missing ICP File", "Please select the ICP Description Word file."
                )
                return
            # Gather text from the THREE specific input fields
            gui_data = IcpGuiData(
                **gui_data.__dict__,
                icp_info_prompt3=self.icp_info_prompt3_input.text().strip(),
                icp_info_prompt6a=self.icp_info_prompt6a_input.text().strip(),
                icp_info_prompt6b=self.icp_info_prompt6b_input.text().strip(),
            )

        # Show processing message
        self.msg_box.setText("Starting processing...")
        self.msg_box.show()

        # Start the processing thread
        self.processing_thread = ProcessingThread(gui_data)
        self.processing_thread.processing_completed.connect(self.on_processing_completed)
        self.processing_thread.start()

    def on_processing_completed(self, updated_doc: str) -> None:
        self.msg_box.close()
        if updated_doc and os.path.exists(updated_doc):
            if os.name == "nt":  # Windows
                os.startfile(updated_doc)
            elif os.name == "posix":  # macOS, Linux
                os.system(f'open "{updated_doc}"')
        elif updated_doc:
            QMessageBox.warning(
                self,
                "File Not Found",
                f"Report generation finished, but the file could not be found:\n{updated_doc}",
            )
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
