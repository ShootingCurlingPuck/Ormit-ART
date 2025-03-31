import sys
import os
import traceback
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLineEdit, QLabel,
                             QGridLayout, QFileDialog, QComboBox, QMessageBox)
from PyQt6.QtGui import QPixmap, QFont, QIcon
from redact import *
from prompting import * 
from time import sleep
from global_signals import global_signals
from report_utils import clean_up, resource_path

# Import write_report modules (MCP and DATA)
import write_report_mcp as mcp_write_report
import write_report_data as data_write_report

# Define paths for resources
logo_path_abs = "resources/ormittalentV3.png"
icon_path_abs = "resources/assessmentReport.ico"

logo_path = resource_path(logo_path_abs)
icon_path = resource_path(icon_path_abs)

programs = ['MCP', 'DATA', 'ICP']
genders = ['M', 'F']

class ProcessingThread(QThread):
    processing_completed = pyqtSignal(str)

    def __init__(self, GUI_data):
        super().__init__()
        self.GUI_data = GUI_data

    def run(self):
        try:
            # Create temp directory if it doesn't exist
            if not os.path.exists('temp'):
                os.makedirs('temp')
                
            # Check if all required files exist
            for file_key, file_path in self.GUI_data["Files"].items():
                if not os.path.exists(file_path):
                    global_signals.update_message.emit(f"Error: File not found: {file_path}")
                    return
            
            # Redact and store files
            global_signals.update_message.emit("Redacting sensitive information...")
            redact_folder(self.GUI_data)

            # Send prompts to Gemini
            global_signals.update_message.emit("Sending prompts to Gemini...")
            output_path = send_prompts(self.GUI_data)

            # Convert JSON to report
            global_signals.update_message.emit("Generating report...")
            clean_data = clean_up(output_path)
            selected_program = self.GUI_data["Traineeship"]
            
            if selected_program == 'MCP' or selected_program == 'ICP':
                updated_doc = mcp_write_report.update_document(clean_data, self.GUI_data["Applicant Name"], self.GUI_data["Assessor Name"], self.GUI_data["Gender"], self.GUI_data["Traineeship"])
            elif selected_program == 'DATA':
                updated_doc = data_write_report.update_document(clean_data, self.GUI_data["Applicant Name"], self.GUI_data["Assessor Name"], self.GUI_data["Gender"], self.GUI_data["Traineeship"])
            else:
                # Default fallback (can remain MCP or be made more specific if needed)
                global_signals.update_message.emit(f"Warning: Unknown program '{selected_program}', defaulting to MCP report.")
                updated_doc = mcp_write_report.update_document(clean_data, self.GUI_data["Applicant Name"], self.GUI_data["Assessor Name"], self.GUI_data["Gender"], self.GUI_data["Traineeship"])

            if updated_doc:
                global_signals.update_message.emit(f"Report generated successfully: {updated_doc}")
                # Emit the path of the generated document
                self.processing_completed.emit(updated_doc)
            else:
                global_signals.update_message.emit("Error: Failed to generate report.")
                
        except Exception as e:
            # Print full traceback for better debugging
            traceback_str = traceback.format_exc()
            print(f"Error in processing thread: {e}\n{traceback_str}")
            global_signals.update_message.emit(f"Error: {str(e)}")

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
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
        self.msg_box.setWindowFlags(self.msg_box.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint)
        self.msg_box.setStandardButtons(QMessageBox.StandardButton.Close)
        self.msg_box.button(QMessageBox.StandardButton.Close).clicked.connect(self.close_application)

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
            Qt.TransformationMode.SmoothTransformation
        )
        pixmap_label.setPixmap(scaled_pixmap)
        layout.addWidget(pixmap_label, 0, 0, 1, 2)

        # OpenAI Key input
        self.key_label = QLabel('Gemini Key:')
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.key_label, 1, 0)

        self.openai_key_input = QLineEdit(placeholderText='Enter Gemini Key: ***************')
        layout.addWidget(self.openai_key_input, 1, 1, 1, 2)

        # Applicant information
        self.applicant_label = QLabel('Applicant:')
        self.applicant_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.applicant_label, 2, 0)

        self.applicant_name_input = QLineEdit(placeholderText='Applicant Full Name')
        layout.addWidget(self.applicant_name_input, 2, 1, 1, 2)

        # Assessor information
        self.assessor_label = QLabel('Assessor:')
        self.assessor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.assessor_label, 3, 0)

        self.assessor_name_input = QLineEdit(placeholderText='Assessor Full Name')
        layout.addWidget(self.assessor_name_input, 3, 1, 1, 2)

        # Select Gender
        self.gender_label = QLabel('Gender:')
        self.gender_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.gender_label, 4, 0)

        self.gender_combo = QComboBox(self)
        for i in genders:
            self.gender_combo.addItem(i)
        self.gender_combo.setToolTip('Select a gender')
        layout.addWidget(self.gender_combo, 4, 1)

        # Select Traineeship
        self.program_label = QLabel('Traineeship:')
        self.program_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.program_label, 5, 0)

        self.program_combo = QComboBox(self)
        for i in programs:
            self.program_combo.addItem(i)
        self.program_combo.setToolTip('Select a traineeship')
        layout.addWidget(self.program_combo, 5, 1)

        # Document labels
        self.file_label1 = QLabel("No file selected", self)
        self.file_label2 = QLabel("No file selected", self)
        self.file_label3 = QLabel("No file selected", self)

        # File selection buttons
        self.selected_files = {}
        self.file_browser_btn1 = QPushButton('PAPI Gebruikersrapport')
        self.file_browser_btn1.clicked.connect(lambda: self.open_file_dialog(1))
        layout.addWidget(self.file_browser_btn1, 6, 0)
        layout.addWidget(self.file_label1, 6, 1, 1, 2)

        self.file_browser_btn2 = QPushButton('Cog. Test')
        self.file_browser_btn2.clicked.connect(lambda: self.open_file_dialog(2))
        layout.addWidget(self.file_browser_btn2, 7, 0)
        layout.addWidget(self.file_label2, 7, 1, 1, 2)

        self.file_browser_btn3 = QPushButton('Assessment Notes')
        self.file_browser_btn3.clicked.connect(lambda: self.open_file_dialog(3))
        layout.addWidget(self.file_browser_btn3, 8, 0)
        layout.addWidget(self.file_label3, 8, 1, 1, 2)

        # ICP Info for Prompt 3 (Personality)
        self.icp_info_prompt3_label = QLabel('ICP Info (Personality):')
        self.icp_info_prompt3_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.icp_info_prompt3_label.setVisible(False)
        layout.addWidget(self.icp_info_prompt3_label, 9, 0)

        self.icp_info_prompt3_input = QLineEdit(placeholderText='Optional: Specific instructions/context for Prompt 3')
        self.icp_info_prompt3_input.setVisible(False)
        layout.addWidget(self.icp_info_prompt3_input, 9, 1, 1, 2)

        # ICP Info for Prompt 6a (Strengths)
        self.icp_info_prompt6a_label = QLabel('ICP Info (Strengths):')
        self.icp_info_prompt6a_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.icp_info_prompt6a_label.setVisible(False)
        layout.addWidget(self.icp_info_prompt6a_label, 10, 0)

        self.icp_info_prompt6a_input = QLineEdit(placeholderText='Optional: Specific instructions/context for Prompt 6a')
        self.icp_info_prompt6a_input.setVisible(False)
        layout.addWidget(self.icp_info_prompt6a_input, 10, 1, 1, 2)

        # ICP Info for Prompt 6b (Improvements)
        self.icp_info_prompt6b_label = QLabel('ICP Info (Improvements):')
        self.icp_info_prompt6b_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.icp_info_prompt6b_label.setVisible(False)
        layout.addWidget(self.icp_info_prompt6b_label, 11, 0)

        self.icp_info_prompt6b_input = QLineEdit(placeholderText='Optional: Specific instructions/context for Prompt 6b')
        self.icp_info_prompt6b_input.setVisible(False)
        layout.addWidget(self.icp_info_prompt6b_input, 11, 1, 1, 2)

        # ICP Description File Button/Label
        self.icp_desc_button = QPushButton('ICP Description File')
        self.icp_desc_button.setVisible(False)
        self.icp_desc_button.clicked.connect(lambda: self.open_file_dialog(4))
        layout.addWidget(self.icp_desc_button, 12, 0)

        self.icp_desc_label = QLabel("No file selected (Required for ICP)", self)
        self.icp_desc_label.setVisible(False)
        layout.addWidget(self.icp_desc_label, 12, 1, 1, 2)

        # Connect program selection change signal AFTER ICP widgets are created
        self.program_combo.currentIndexChanged.connect(self.handle_program_change)

        # Submit button
        self.submitbtn = QPushButton('Submit')
        self.submitbtn.setFixedWidth(90)
        self.submitbtn.hide()
        layout.addWidget(self.submitbtn, 13, 2, Qt.AlignmentFlag.AlignRight)
        self.submitbtn.clicked.connect(self.handle_submit)

        # Initialize UI based on default selection
        self.handle_program_change()

    def refresh_message_box(self, message):
        self.msg_box.setText(message)
        # Make sure the message box is visible
        if not self.msg_box.isVisible():
            self.msg_box.show()
        # Force update of the UI
        QApplication.processEvents()

    def close_application(self):
        # This will close the application when the messagebox is closed manually
        QApplication.quit()

    def handle_program_change(self):
        """Shows or hides ICP-specific widgets based on program selection."""
        selected_program = self.program_combo.currentText()
        # print(f"handle_program_change called. Selected program: {selected_program}") # Keep DEBUG if needed
        is_icp = (selected_program == 'ICP')
        # print(f"Is ICP selected? {is_icp}") # Keep DEBUG if needed

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
        # print("ICP Widget visibility set.") # Keep DEBUG if needed

    def open_file_dialog(self, file_index):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if file_index == 4:
            dialog.setNameFilter("Word Files (*.docx);;All Files (*)")
        else:
            dialog.setNameFilter("PDF Files (*.pdf);;All Files (*)")
        dialog.setViewMode(QFileDialog.ViewMode.List)

        if dialog.exec():
            filenames = dialog.selectedFiles()
            if filenames:
                selected_file = str(filenames[0])
                file_basename = os.path.basename(selected_file)

                if file_index == 1:
                    self.file_label1.setText(file_basename)
                    self.selected_files["PAPI Gebruikersrapport"] = selected_file
                elif file_index == 2:
                    self.file_label2.setText(file_basename)
                    self.selected_files["Cog. Test"] = selected_file
                elif file_index == 3:
                    self.file_label3.setText(file_basename)
                    self.selected_files["Assessment Notes"] = selected_file
                elif file_index == 4:
                    self.icp_desc_label.setText(file_basename)
                    self.selected_files["ICP Description"] = selected_file

                # Check if standard files are selected to show submit button
                standard_files_selected = all(key in self.selected_files for key in ["PAPI Gebruikersrapport", "Cog. Test", "Assessment Notes"])
                if standard_files_selected:
                    self.submitbtn.show()
                # Submit button remains hidden otherwise

    def handle_submit(self):
        # Validate input
        if not self.openai_key_input.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter a Gemini API key.")
            return
            
        if not self.applicant_name_input.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter the applicant's name.")
            return
            
        if not self.assessor_name_input.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter the assessor's name.")
            return
        
        # Check if all required files are selected
        required_files = ["PAPI Gebruikersrapport", "Cog. Test", "Assessment Notes"]
        missing_files = [f for f in required_files if f not in self.selected_files or not self.selected_files[f]]
        
        if missing_files:
            QMessageBox.warning(self, "Missing Files", f"Please select the following files: {', '.join(missing_files)}")
            return
        
        selected_program = self.program_combo.currentText()

        # Gather all the data into a dictionary
        GUI_data = {
            "Gemini Key": self.openai_key_input.text(),
            "Applicant Name": self.applicant_name_input.text(),
            "Assessor Name": self.assessor_name_input.text(),
            "Gender": self.gender_combo.currentText(),
            "Traineeship": selected_program,
            "Files": self.selected_files.copy()
        }

        # Add ICP-specific data and validation
        if selected_program == 'ICP':
            # Check required ICP description file
            if "ICP Description" not in self.selected_files or not self.selected_files["ICP Description"]:
                QMessageBox.warning(self, "Missing ICP File", "Please select the ICP Description Word file.")
                return
            # Gather text from the THREE specific input fields
            GUI_data["ICP_Info_Prompt3"] = self.icp_info_prompt3_input.text().strip()
            GUI_data["ICP_Info_Prompt6a"] = self.icp_info_prompt6a_input.text().strip()
            GUI_data["ICP_Info_Prompt6b"] = self.icp_info_prompt6b_input.text().strip()

        # Show processing message
        self.msg_box.setText("Starting processing...")
        self.msg_box.show()

        # Start the processing thread
        self.processing_thread = ProcessingThread(GUI_data)
        self.processing_thread.processing_completed.connect(self.on_processing_completed)
        self.processing_thread.start()

    def on_processing_completed(self, updated_doc):
        self.msg_box.close()
        if updated_doc and os.path.exists(updated_doc):
            os.startfile(updated_doc)
        elif updated_doc:
            QMessageBox.warning(self, "File Not Found", f"Report generation finished, but the file could not be found:\n{updated_doc}")
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    main()