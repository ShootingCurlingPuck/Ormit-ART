# Assessment Report Tool (ART)

ART is a Python-based application designed to automate the generation of assessment reports for ORMIT Talent. The tool leverages Gemini AI to analyze assessment data and produce professional, consistently formatted reports.

## Features
- **Multiple Program Types**: Supports various assessment types including MCP, DATA, ICP, and NEW traineeships
- **Multiple Program Types**: Supports various assessment types including MCP, DATA and ICP
- **Automated Report Generation**: Transforms assessment data into structured Word document reports
- **Sensitive Data Protection**: Automatically redacts candidate and assessor personal information
- **AI-Powered Analysis**: Uses Gemini AI to extract insights from assessment materials
- **Consistent Formatting**: Ensures all reports follow ORMIT Talent's styling guidelines
- **Model Selection**: Uses different Gemini models optimized for specific prompts

## Installation

1. Clone this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
   
   Key dependencies include:
   - PyQt6 for the GUI
   - python-docx for document manipulation
   - google-generativeai for Gemini API access
   - PyMuPDF for PDF processing

3. Run the application:
   ```
   python main.py
   ```

## Workflow

1. **Input Data Collection**:
   - Enter candidate's name, assessor's name, and select gender
   - Choose traineeship program (MCP, DATA, ICP, NEW)
   - Upload required assessment documents:
     - PAPI Report
     - Cognitive Test results
     - Assessment Notes
   - For ICP traineeships, provide additional context and program-specific information

2. **Data Processing**:
   - Documents are copied to a temporary directory
   - Sensitive information is automatically redacted
   - Redacted documents are processed to extract assessment data

3. **AI Analysis**:
   - The application sends a series of prompts to the Gemini AI
   - Different models are used for optimal results:
     - Gemini-2.0-flash for cognitive capacity and language prompts
     - Gemini-2.5-pro for personality assessment and other aspects
   - Results are stored in a structured JSON file in the output directory

4. **Report Generation**:
   - JSON data is processed into a formatted Word document
   - Document follows ORMIT Talent's template design
   - Special formatting is applied (bullet points, tables, language skills)
   - Final report is saved to the output_reports directory

## Architecture

The application consists of several key components:

- **main.py**: GUI interface and main application logic
- **prompting.py**: Handles communication with Gemini API
- **redact.py**: Processes and redacts sensitive information
- **write_report_mcp.py**: Generates reports for MCP and NEW traineeships
- **write_report_data.py**: Generates reports for DATA traineeships 
- **report_utils.py**: Shared utilities for report generation
- **global_signals.py**: Handles cross-component communication

## Output

The application generates two main outputs in the `output_reports` directory:
1. A JSON file containing the structured AI responses
2. A formatted Word document (.docx) containing the final assessment report

## Usage Guide

1. **Start the Application**: Run `python main.py` to open the GUI
2. **Enter Credentials**: Provide your Gemini API key
3. **Enter Assessment Information**:
   - Candidate and assessor names
   - Gender selection (for proper pronoun usage)
   - Select the appropriate traineeship program
4. **Upload Files**: Use the buttons to upload the required documents
5. **Submit and Wait**: The application processes the documents and generates the report
6. **Review Results**: The finished report opens automatically and is saved to the output_reports directory

## Development

- The project uses Python 3.8+ and is structured for maintainability
- Templates are stored in the resources directory
- Temporary files are created in the temp directory
- Output files are saved to the output_reports directory 
=======
- Output files are saved to the output_reports directory
