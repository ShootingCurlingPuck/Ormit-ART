import fitz
import re
import os
import shutil

class Redactor:
    @staticmethod
    def get_sensitive_data(lines, target_names):
        """ Function to get sensitive data lines containing specified keywords and other sensitive information """
        NAME_REG = r'\b(' + '|'.join(re.escape(name) for name in target_names) + r')\b'
        EMAIL_REG = r'[\w\.-]+@[\w\.-]+'
        PHONE_REG = r'\+\d{1,3}\s*\d{1,3}(\s*\d{2,3}){2,4}'
        
        keywords = ["gender", "address", "phone", "e-mail", "date of birth", "links", "socials"]

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
        self.target_names = [name for name in target_names if name] # Ensure list and remove empty strings
        print(f"Redactor initialized to target: {self.target_names}") # Debug print

    def redaction(self, filename):
        """Performs redaction on the given PDF filename."""
        if not self.target_names:
             print(f"Skipping redaction for {filename}: No target names provided.")
             return

        print(f"Starting redaction for: {filename}") # Debug print
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
                        print(f"  Found '{name_to_redact}' {len(sensitive_areas)} times on page {page.number}")
                        changes += len(sensitive_areas)
                        for quad in sensitive_areas:
                            page.add_redact_annot(quad, fill=(0, 0, 0)) # Black fill

                     # --- Redact individual parts (first name, last name) if name has parts ---
                     # Be cautious with common first names - might over-redact
                     # Add more specific logic here if needed based on requirements
                     # For now, let's skip redacting individual parts to be safe
                     # if len(name_parts) > 1:
                     #     for part in name_parts:
                     #         if len(part) > 2: # Avoid redacting very short parts like initials
                     #             part_areas = page.search_for(part, quads=True)
                     #             # Add checks here to avoid redacting common words if 'part' is common
                     #             # ...
                     #             for quad in part_areas:
                     #                  page.add_redact_annot(quad, fill=(0, 0, 0))
                     #                  changes += 1


                # Apply the redactions for the current page
                page.apply_redactions()

            if changes > 0:
                # Save the redacted file, overwriting the original in the temp folder
                doc.save(filename, incremental=False, encryption=fitz.PDF_ENCRYPT_KEEP)
                print(f"  Applied {changes} redactions to {filename}")
            else:
                print(f"  No target names found in {filename}")

            doc.close()

        except Exception as e:
            print(f"ERROR during redaction of {filename}: {e}")
            # Ensure the document is closed even if an error occurs during processing
            if 'doc' in locals() and doc:
                try:
                    doc.close()
                except: # Handle cases where doc might be invalid
                    pass

def create_temp_folder():
    temp_folder = 'temp'
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
            
def redact_folder(GUI_data):
    """Redacts specified names in the specific PDF files provided via GUI_data."""

    # Extract names needed for redaction from GUI_data
    applicant_name = GUI_data.get("Applicant Name", "").strip()
    assessor_name = GUI_data.get("Assessor Name", "").strip()
    target_names_list = [name for name in [applicant_name, assessor_name] if name] # Filter out empty strings

    # Instantiate Redactor ONCE with the names
    if not target_names_list:
        print("Warning: No Applicant or Assessor names provided for redaction. Skipping redaction.")
        return # No names to redact

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

    for file_key, file_path in files_to_process.items():
        # The file_path should be the full path copied to the temp folder
        # or the original path if copying wasn't implemented.
        # Let's assume the path passed is the one to redact.

        if not file_path or not os.path.isfile(file_path):
            print(f"Skipping redaction for '{file_key}': File path missing or invalid ('{file_path}')")
            continue

        # --- Only redact PDF files ---
        if file_path.lower().endswith('.pdf'):
            print(f"Processing PDF file: {file_path}")
            try:
                redactor.redaction(filename=file_path) # Pass the correct filename
            except Exception as e:
                # Log error but continue with other files
                print(f"ERROR redacting file {file_path}: {e}")
        # else: # Implicitly skip non-PDF files like the ICP Description docx
            # print(f"Skipping non-PDF file: {file_path}")


    print("Redaction process finished.")