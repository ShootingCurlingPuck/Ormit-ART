import os
import re
import shutil

import fitz


class Redactor:
    @staticmethod
    def get_sensitive_data(lines, target_names):
        """Function to get sensitive data lines containing specified keywords and other sensitive information"""
        NAME_REG = r"\b(" + "|".join(re.escape(name) for name in target_names) + r")\b"
        EMAIL_REG = r"[\w\.-]+@[\w\.-]+"
        PHONE_REG = r"\+\d{1,3}\s*\d{1,3}(\s*\d{2,3}){2,4}"

        keywords = [
            "gender",
            "address",
            "phone",
            "e-mail",
            "date of birth",
            "links",
            "socials",
        ]

        previous_line = None

        for line in lines:
            for keyword in keywords:
                if previous_line and previous_line.lower().startswith(keyword):
                    yield line

            previous_line = line

            for match in re.finditer(NAME_REG, line, re.IGNORECASE):
                yield match.group(0)

            for match in re.finditer(EMAIL_REG, line):
                yield match.group(0)

            for match in re.finditer(PHONE_REG, line):
                yield match.group(0)

    def __init__(self, target_names):
        if not isinstance(target_names, list):
            raise TypeError("target_names must be a list of strings")
        self.target_names = [
            name for name in target_names if name
        ]  # Ensure list and remove empty strings
        print(f"Redactor initialized to target: {self.target_names}")  # Debug print

    def redaction(self, filename):
        """Performs redaction on the given PDF filename."""
        if not self.target_names:
            print(f"Skipping redaction for {filename}: No target names provided.")
            return

        print(f"Starting redaction for: {filename}")  # Debug print
        try:
            doc = fitz.open(filename)
            changes = 0
            for page in doc:
                for name_to_redact in self.target_names:
                    # Split name into parts if needed (e.g., "First Last")
                    name_parts = name_to_redact.split()
                    # --- Redact full name ---
                    sensitive_areas = page.search_for(name_to_redact, quads=True)
                    if sensitive_areas:
                        print(
                            f"  Found '{name_to_redact}' {len(sensitive_areas)} times on page {page.number}"
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
                print(f"  Applied {changes} redactions to {filename}")
            else:
                print(f"  No target names found in {filename}")

            doc.close()

        except Exception as e:
            print(f"ERROR during redaction of {filename}: {e}")
            # Ensure the document is closed even if an error occurs during processing
            if "doc" in locals() and doc:
                try:
                    doc.close()
                except:  # Handle cases where doc might be invalid
                    pass


def create_temp_folder():
    temp_folder = "temp"
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)


def redact_folder(GUI_data):
    """Redacts specified names in the specific PDF files provided via GUI_data."""

    # Make sure temp folder exists
    create_temp_folder()

    # Extract names needed for redaction from GUI_data
    applicant_name = GUI_data.get("Applicant Name", "").strip()
    assessor_name = GUI_data.get("Assessor Name", "").strip()
    target_names_list = [
        name for name in [applicant_name, assessor_name] if name
    ]  # Filter out empty strings

    # Instantiate Redactor ONCE with the names
    if not target_names_list:
        print(
            "Warning: No Applicant or Assessor names provided for redaction. Skipping redaction."
        )
        return  # No names to redact

    try:
        redactor = Redactor(target_names=target_names_list)
    except Exception as e:
        print(f"Error initializing Redactor: {e}")
        return

    print("Starting redaction process on provided files...")

    # --- Iterate through the files provided by the user ---
    files_to_process = GUI_data.get("Files", {})
    if not files_to_process:
        print("Warning: No files found in GUI_data['Files'] to process.")
        return

    # --- First, copy all files to the temp directory ---
    for file_key, file_path in files_to_process.items():
        if not file_path or not os.path.isfile(file_path):
            print(
                f"Skipping copy for '{file_key}': File path missing or invalid ('{file_path}')"
            )
            continue

        # Determine destination name in temp directory
        # Use standard names expected by send_prompts
        if file_key == "PAPI Gebruikersrapport":
            dest_path = "temp/PAPI Gebruikersrapport.pdf"
        elif file_key == "Cog. Test":
            dest_path = "temp/Cog. Test.pdf"
        elif file_key == "Assessment Notes":
            dest_path = "temp/Assessment Notes.pdf"
        elif file_key == "ICP Description":
            # For ICP Description, keep the original extension
            extension = os.path.splitext(file_path)[1]
            dest_path = f"temp/ICP Description{extension}"
        else:
            # For any other files, keep original name
            dest_path = f"temp/{os.path.basename(file_path)}"

        try:
            # Copy the file to temp directory
            print(f"Copying {file_path} to {dest_path}")
            shutil.copy2(file_path, dest_path)

            # Update the file path in GUI_data to point to the new location
            GUI_data["Files"][file_key] = dest_path
        except Exception as e:
            print(f"Error copying file {file_path} to temp directory: {e}")
            continue

    # --- Now redact the files in the temp directory ---
    for file_key, file_path in GUI_data["Files"].items():
        # Skip if file path is invalid after copying
        if not file_path or not os.path.isfile(file_path):
            print(
                f"Skipping redaction for '{file_key}': File path missing or invalid after copy ('{file_path}')"
            )
            continue

        # --- Only redact PDF files ---
        if file_path.lower().endswith(".pdf"):
            print(f"Processing PDF file: {file_path}")
            try:
                redactor.redaction(filename=file_path)  # Pass the correct filename
            except Exception as e:
                # Log error but continue with other files
                print(f"ERROR redacting file {file_path}: {e}")

    print("Redaction process finished.")
