import contextlib
import logging
import os
import shutil

import fitz

from src.constants import LOGGER_NAME
from src.data_models import GuiData, IcpGuiData

logger = logging.getLogger(LOGGER_NAME)


class Redactor:
    def __init__(self, target_names: list[str]) -> None:
        self.target_names = [
            name for name in target_names if name
        ]  # Ensure list and remove empty strings
        logger.debug(f"Redactor initialized to target: {self.target_names}")

    def redaction(self, filename: str) -> None:
        """Performs redaction on the given PDF filename."""
        if not self.target_names:
            logger.warning(f"Skipping redaction: No target names provided for {filename}")
            return

        logger.debug(f"Starting redaction for {filename}")
        try:
            doc = fitz.open(filename)
            changes = 0
            for page in doc:
                for name_to_redact in self.target_names:
                    # --- Redact full name ---
                    sensitive_areas = page.search_for(name_to_redact, quads=True)
                    if sensitive_areas:
                        logger.debug(
                            f"Found {len(sensitive_areas)} sensitive areas for {name_to_redact} on page {page.number} of {filename}"
                        )
                        changes += len(sensitive_areas)
                        for quad in sensitive_areas:
                            # Create a solid black rectangle for redaction
                            # Set text color to white (invisible against black) and fill color to black
                            annot = page.add_redact_annot(
                                quad, text=" ", fill=(0, 0, 0), text_color=(1, 1, 1)
                            )
                            # Ensure we have proper settings for solid appearance
                            annot.set_border(width=0)  # No border
                            annot.set_opacity(1.0)  # Fully opaque

                # Apply the redactions for the current page
                page.apply_redactions()

            if changes > 0:
                # Save the redacted file, overwriting the original in the temp folder
                doc.save(filename, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
                logger.info(f"Applied redactions for {filename} - {changes} changes made")
            else:
                logger.info(f"No target names found for {filename}")

            doc.close()

        except Exception:
            logger.exception(f"Error during redaction for {filename}")
            # Ensure the document is closed even if an error occurs during processing
            if "doc" in locals() and doc:
                with contextlib.suppress(Exception):
                    doc.close()


def create_temp_folder() -> None:
    temp_folder = "temp"
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)


def redact_folder(gui_data: GuiData | IcpGuiData) -> None:
    """Redacts specified names in the specific PDF files provided via GUI_data."""
    # Make sure temp folder exists
    create_temp_folder()

    # Extract names needed for redaction from GUI_data
    applicant_name = gui_data.applicant_name.strip()
    assessor_name = gui_data.assessor_name.strip()
    target_names_list = [
        name for name in [applicant_name, assessor_name] if name
    ]  # Filter out empty strings

    # Instantiate Redactor ONCE with the names
    if not target_names_list:
        logger.warning("No Applicant or Assessor names provided for redaction. Skipping redaction.")
        return  # No names to redact

    try:
        redactor = Redactor(target_names=target_names_list)
    except Exception:
        logger.exception("Error initializing Redactor")
        return

    logger.info("Starting redaction process on provided files...")

    # --- Iterate through the files provided by the user ---
    files_to_process = gui_data.files
    if not files_to_process:
        logger.warning("No files found in gui_data.files to process.")
        return

    # --- First, copy all files to the temp directory ---
    for file_key, file_path in files_to_process.items():
        if not file_path or not os.path.isfile(file_path):
            logger.warning(
                f"Skipping copy: File path missing or invalid for {file_key} - {file_path}"
            )
            continue

        # Determine destination name in temp directory
        extension = os.path.splitext(file_path)[1][1:].lower()
        # Use standard names expected by send_prompts
        dest_path = f"temp/{file_key}.{extension}"

        try:
            # Copy the file to temp directory
            logger.info(f"Copying {file_path} to {dest_path}")
            shutil.copy2(file_path, dest_path)

            # Update the file path in GUI_data to point to the new location
            gui_data.files[file_key] = dest_path
        except Exception:
            logger.exception(f"Error copying {file_path} to temp directory")
            continue

    # --- Now redact the files in the temp directory ---
    for file_key, file_path in gui_data.files.items():
        # Skip if file path is invalid after copying
        if not file_path or not os.path.isfile(file_path):
            logger.warning(f"Skipping redaction for {file_key} - {file_path}")
            continue

        # --- Only redact PDF files ---
        if file_path.lower().endswith(".pdf"):
            logger.info(f"Processing PDF file: {file_path}")
            try:
                redactor.redaction(filename=file_path)  # Pass the correct filename
            except Exception:
                # Log error but continue with other files
                logger.exception(f"Error redacting file: {file_path}")

    logger.info("Redaction process finished.")
