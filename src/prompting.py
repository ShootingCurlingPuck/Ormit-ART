import ast
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pypdf
from docx import Document
from google import genai

from src.constants import (
    GEMINI_MODEL,
    LOGGER_NAME,
    MAX_WAIT_TIME,
    FileCategory,
    Program,
    PromptName,
)
from src.data_models import GuiData, IcpGuiData
from src.global_signals import global_signals
from src.prompts import PROMPTS

if TYPE_CHECKING:
    from google.genai import types as genai_types

logger = logging.getLogger(LOGGER_NAME)


def read_pdf(file_path: str) -> str:
    """Reads and returns text from a PDF file."""
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception:
        logger.exception(f"Error reading PDF file {file_path}")
    return text


def read_docx(file_path: str) -> str:
    """Reads and returns text from a DOCX file."""
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception:
        logger.exception(f"Error reading DOCX file {file_path}")
    return text


def _extract_list_from_string(text: str) -> str:
    """Safely extracts a Python list from a string and returns it as a *string*
    representation suitable for JSON, handling various Gemini output quirks.
    """
    match = re.search(r"\[[^\]]*\]", text)
    if match:
        list_str = match.group(0)
        try:
            parsed_list = ast.literal_eval(list_str)
            if isinstance(parsed_list, list):
                return json.dumps(parsed_list)
        except (SyntaxError, ValueError):
            pass
    return "[]"


def process_prompt_results(results: dict[PromptName, str]) -> dict[Any, str]:
    """Process the results from the prompts to ensure proper formatting."""
    # Format personality section (prompt3_personality) for template insertion
    if PromptName.PERSONALITY in results:
        text = results[PromptName.PERSONALITY]
        lines = text.split("\n")
        formatted_parts: list[str] = []
        first_point = True

        # Check for summary indicators
        summary_indicators = [
            "in summary",
            "to summarize",
            "overall",
            "in conclusion",
            "to conclude",
            "in short",
            "is a promising",
            "makes him a promising",
            "makes her a promising",
            "these qualities make",
        ]

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            is_bullet = stripped_line.startswith(("*", "•"))

            # Improved summary detection - check for various indicators
            is_summary = False
            lower_line = stripped_line.lower()

            # Check if this is the last paragraph/bullet (likely to be summary)
            is_last_content = i == len(lines) - 1 or all(
                not line.strip() for line in lines[i + 1 :]
            )

            # Check if this contains any summary indicators
            for indicator in summary_indicators:
                if indicator in lower_line:
                    is_summary = True
                    break

            # Special handling for last bullet that looks like a summary
            if is_bullet and (is_summary or is_last_content):
                content = stripped_line[1:].strip()
                if first_point:
                    # First point's text goes directly after the template bullet
                    formatted_parts.append(content)
                    first_point = False
                else:
                    # Add TWO extra breaks for the summary bullet point
                    formatted_parts.append("<<BREAK>>")
                    formatted_parts.append("<<BREAK>>")
                    formatted_parts.append(f"• {content}")

            # Regular bullet handling (no change to existing logic)
            elif is_bullet:
                content = stripped_line[1:].strip()
                if first_point:
                    # First point's text goes directly after the template bullet
                    formatted_parts.append(content)
                    first_point = False
                else:
                    formatted_parts.append("<<BREAK>>")
                    formatted_parts.append(f"• {content}")

            # Non-bullet text that looks like a summary
            elif stripped_line and not first_point and (is_summary or is_last_content):
                # Add extra breaks for non-bullet summary paragraph
                if formatted_parts and formatted_parts[-1] != "<<BREAK>>":
                    formatted_parts.append("<<BREAK>>")
                    formatted_parts.append("<<BREAK>>")
                formatted_parts.append(stripped_line)

            # Regular text handling (no change)
            elif stripped_line and not first_point:
                # Handle intro/summary lines *after* the first bullet
                # Add break before non-bullet lines if needed
                if formatted_parts and formatted_parts[-1] != "<<BREAK>>":
                    formatted_parts.append("<<BREAK>>")
                formatted_parts.append(stripped_line)
            elif stripped_line and first_point:
                # Handle intro line *before* any bullets
                formatted_parts.append(stripped_line)
                # Don't set first_point = False yet, wait for actual bullet

        # Join parts, <<BREAK>> will be handled later
        # We join with a space just to ensure parts are concatenated.
        # The <<BREAK>> marker is the important part for splitting.
        results[PromptName.PERSONALITY] = " ".join(formatted_parts).replace(
            "<<BREAK>> ", "<<BREAK>>"
        )

    # --- Format list prompts (prompt6a/b) ---
    # These likely go into tables, so keep their original JSON/List format processing
    list_prompts = [PromptName.CONQUAL, PromptName.CONIMPROV]
    for prompt_key in list_prompts:
        if results.get(prompt_key):
            original_data = results[prompt_key]
            prompt_key_original = PromptName(f"{prompt_key}_original")
            # Store original JSON if it's a string that looks like JSON
            if original_data.strip().startswith("["):
                results[prompt_key_original] = original_data
                # Attempt to parse, but prioritize keeping original if error
                try:
                    items = json.loads(original_data)
                    results[prompt_key] = items if isinstance(items, list) else original_data
                except (json.JSONDecodeError, TypeError):
                    results[prompt_key] = original_data  # Keep original string on error
            elif isinstance(original_data, list):
                results[prompt_key] = original_data  # Already a list
                results[prompt_key_original] = json.dumps(original_data)  # Store JSON version
            else:
                # Not a list or JSON string, store original and keep as is
                results[prompt_key_original] = str(original_data)
                results[prompt_key] = original_data

    return results


def send_prompts(data: GuiData | IcpGuiData) -> str:
    global_signals.update_message.emit("Connecting to Gemini...")

    # Create client with API key
    client = genai.Client(api_key=data.gemini_key)

    # Get the thinking setting from GUI data
    enable_thinking = data.enable_thinking
    # Define which prompts should use thinking when enabled
    thinking_prompts = [
        PromptName.PERSONALITY,
        PromptName.CONQUAL,
        PromptName.CONIMPROV,
        PromptName.QUALSCORE,
        PromptName.QUALSCORE_DATA,
    ]

    current_time = datetime.now()
    formatted_time = current_time.strftime("%m%d%H%M")
    appl_name = data.applicant_name
    # Update to save to output_reports directory
    output_dir = "output_reports"
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Set the file path to be in the output directory
    filename_with_timestamp = os.path.join(output_dir, f"{appl_name}_{formatted_time}.json")

    path_to_contextfile = "resources/Context and Task Description.docx"
    path_to_toneofvoice = "resources/Examples Personality Section.docx"
    path_to_mngtprofile = "resources/The MNGT Profile.docx"
    path_to_dataprofile = "resources/The Data Chiefs profile.docx"

    lst_files = [
        os.path.join("temp/", path_to_file)
        for path_to_file in os.listdir("temp/")
        if os.path.isfile(os.path.join("temp/", path_to_file))
    ]
    lst_files.append(path_to_contextfile)
    lst_files.append(path_to_toneofvoice)

    selected_program = data.traineeship
    # Use MNGT profile for both MNGT and NEW programs
    if selected_program == Program.DATA:
        lst_files.append(path_to_dataprofile)
    else:  # Handles MNGT, NEW, and any potential unknown as MNGT
        lst_files.append(path_to_mngtprofile)

    file_contents: dict[str, str] = {}
    for file_path in lst_files:
        file_name, extension = os.path.splitext(os.path.basename(file_path))
        if extension.lower() == ".pdf":
            file_contents[file_name] = read_pdf(file_path)
        elif extension.lower() == ".docx":
            file_contents[file_name] = read_docx(file_path)
        else:
            logger.warning(f"Unsupported file format for {file_path}")
            file_contents[file_name] = ""

    # --- Read ICP Description File (if applicable) --- Append to file_contents
    icp_description_content = ""
    if selected_program == Program.ICP:
        icp_file_path = data.files.get(FileCategory.ICP)  # Safer get
        if icp_file_path and os.path.exists(icp_file_path):
            try:
                icp_description_content = read_docx(icp_file_path)
                # Add with a clear key to context
                file_contents[FileCategory.ICP] = icp_description_content
            except Exception:
                logger.exception(f"Error reading ICP description from {icp_file_path}")
                file_contents[FileCategory.ICP] = "[Error reading ICP description]"
        else:
            logger.warning(f"ICP Description file path not found or file missing: {icp_file_path}")
            # Don't add to file_contents if missing

    # --- Get ICP Specific Prompt Info --- (Store them for use in the loop)
    icp_info_p3 = ""
    icp_info_p6a = ""
    icp_info_p6b = ""
    if isinstance(data, IcpGuiData):
        icp_info_p3 = data.icp_info_prompt3
        icp_info_p6a = data.icp_info_prompt6a
        icp_info_p6b = data.icp_info_prompt6b

    global_signals.update_message.emit("Files uploaded, starting prompts...")

    # Define lists of prompts for each program
    common_prompts = [
        PromptName.FIRST_IMPRESSION,
        PromptName.PERSONALITY,
        PromptName.COGCAP_SCORES,
        PromptName.COGCAP_REMARKS,
        PromptName.LANGUAGE,
        PromptName.CONQUAL,
        PromptName.CONIMPROV,
        PromptName.INTERESTS,
    ]
    lst_prompts_mngt = [*common_prompts, PromptName.QUALSCORE]
    lst_prompts_data = [*common_prompts, PromptName.QUALSCORE_DATA, PromptName.DATATOOLS]

    # Define which prompts are expected to return lists (for parsing/evaluation)
    list_output_prompts = [
        PromptName.COGCAP_SCORES,
        PromptName.LANGUAGE,
        PromptName.CONQUAL,
        PromptName.CONIMPROV,
        PromptName.QUALSCORE,
        PromptName.QUALSCORE_DATA,
        PromptName.DATATOOLS,
        PromptName.INTERESTS,
    ]

    # --- Select appropriate list of prompts ---
    # Use MNGT prompts for both MNGT and NEW programs
    lst_prompts = lst_prompts_data if selected_program == Program.DATA else lst_prompts_mngt

    # --- Run Prompts ---
    results: dict[PromptName, str] = {}
    start_time_all = time.time()

    # Build the general context string ONCE (includes ICP description if present)
    general_context = "\n\n---\n\n".join(
        [f"File: {file_name}\nContent:\n{content}" for file_name, content in file_contents.items()]
    )

    promno = -1
    for promno, prompt_name in enumerate(lst_prompts, start=1):
        global_signals.update_message.emit(
            f"Submitting prompt {promno}/{len(lst_prompts)}, please wait..."
        )

        prompt_data = next(filter(lambda p: p.name == prompt_name, PROMPTS), None)
        if prompt_data is None:
            logger.error(f"Prompt data not found for {prompt_name}")
            continue
        prompt_text, temperature = prompt_data.text, prompt_data.temperature

        # --- Inject SPECIFIC ICP Info with HIGH EMPHASIS ---
        icp_instruction = ""

        if selected_program == Program.ICP:
            if prompt_name == PromptName.PERSONALITY and icp_info_p3:
                icp_instruction = icp_info_p3
            elif prompt_name == PromptName.CONQUAL and icp_info_p6a:
                icp_instruction = icp_info_p6a
            elif prompt_name == PromptName.CONIMPROV and icp_info_p6b:
                icp_instruction = icp_info_p6b

            if icp_instruction:  # Only modify if specific info was provided
                prompt_text = f"""\
########################################################################
# CRITICAL INSTRUCTION OVERRIDE FOR THIS TASK                          #
########################################################################

THE FOLLOWING INSTRUCTIONS ARE PARAMOUNT AND MUST BE FOLLOWED EXACTLY, SUPERSEDING ANY CONFLICTING GENERAL INSTRUCTIONS IN THE ORIGINAL PROMPT BELOW. FAILURE TO ADHERE STRICTLY WILL RESULT IN AN INCORRECT RESPONSE.

Specific Instructions:
{icp_instruction}

########################################################################
# END OF CRITICAL INSTRUCTIONS - NOW FOLLOW ORIGINAL PROMPT BELOW      #
########################################################################

--- Original Prompt ---
{prompt_text}"""
                logger.info(f"Applied CRITICAL ICP info to prompt {prompt_name}")

        # Construct the full prompt using the general context
        full_prompt = f"{prompt_text}\n\nUse the following files to complete the tasks. Do not give any output for this prompt.\n{general_context}"

        # Prepare generation config with temperature
        generation_config: genai_types.GenerateContentConfigOrDict = {"temperature": temperature}

        # Add thinking configuration if enabled and this prompt should use thinking
        if enable_thinking and prompt_name in thinking_prompts:
            # Use the thinking_config parameter when enabled
            generation_config = {
                "temperature": temperature,
                "thinking_config": {"thinking_budget": 8096},
            }
            global_signals.update_message.emit(
                f"Using AI thinking for prompt {promno} ({prompt_name})..."
            )

        # Initial attempt
        max_attempts = 3  # Maximum number of attempts per prompt
        attempt = 0
        success = False

        while attempt < max_attempts and not success:
            try:
                if attempt > 0:
                    global_signals.update_message.emit(
                        f"Retrying prompt {promno}/{len(lst_prompts)} (attempt {attempt + 1}/{max_attempts})..."
                    )
                    # Add a short delay between retry attempts to avoid hammering the API
                    time.sleep(1)

                response = client.models.generate_content(
                    model=GEMINI_MODEL, contents=full_prompt, config=generation_config
                )
                output_text = response.text

                # Check if we got a valid response
                if prompt_name in list_output_prompts and output_text is not None:
                    result = _extract_list_from_string(output_text)
                    if result != "[]" and result.strip():
                        results[prompt_name] = result
                        success = True
                    else:
                        logger.warning(
                            f"Empty list result for prompt {prompt_name} (attempt {attempt + 1})"
                        )
                elif output_text is not None and output_text.strip():
                    results[prompt_name] = output_text.strip()
                    success = True
                else:
                    logger.warning(
                        f"Empty text result for prompt {prompt_name} (attempt {attempt + 1})"
                    )

                # If this is the last attempt and we haven't succeeded, use whatever we got
                if not success and attempt == max_attempts - 1:
                    if prompt_name in list_output_prompts and output_text is not None:
                        results[prompt_name] = _extract_list_from_string(output_text)
                    elif output_text is not None:
                        results[prompt_name] = output_text.strip()
                    logger.warning(
                        f"Using potentially empty result for prompt {prompt_name} (attempt {max_attempts})"
                    )

            except Exception:
                logger.exception(f"Error processing prompt {prompt_name} (attempt {attempt + 1})")
                if attempt == max_attempts - 1:  # Last attempt
                    results[prompt_name] = (
                        "[]" if prompt_name in list_output_prompts else ""
                    )  # Ensure empty result matches type

            attempt += 1

        if time.time() - start_time_all > MAX_WAIT_TIME:
            logger.warning("Timeout for all prompts reached.")
            break

    # --- Retry Logic for Critical Prompts ---
    # This provides additional retries for specific critical prompts
    critical_prompts = [PromptName.CONIMPROV]
    # Use MNGT critical prompt for both MNGT and NEW
    if selected_program == Program.DATA:
        critical_prompts.append(PromptName.QUALSCORE_DATA)
    else:  # Handles MNGT, NEW, and any potential unknown as MNGT
        critical_prompts.append(PromptName.QUALSCORE)

    max_retries = 2
    for prompt_name in critical_prompts:
        if prompt_name not in results or results[prompt_name] == "" or results[prompt_name] == "[]":
            logger.warning(
                f"Result for critical prompt {prompt_name} still empty after initial attempts. Retrying..."
            )
            for attempt in range(max_retries):
                if time.time() - start_time_all > MAX_WAIT_TIME:
                    logger.warning("Timeout reached during critical prompt retry.")
                    break  # Break retry loop if overall timeout hit

                global_signals.update_message.emit(
                    f"Retrying critical prompt '{prompt_name}' (Extra attempt {attempt + 1}/{max_retries})..."
                )

                # Add a short delay between retry attempts to avoid hammering the API
                time.sleep(1)

                # Reuse prompt details from initial run
                prompt_data = next(filter(lambda p: p.name == prompt_name, PROMPTS), None)
                if prompt_data is None:
                    logger.error(f"Prompt data not found for {prompt_name} during retry")
                    continue
                prompt_text, temperature = prompt_data.text, prompt_data.temperature

                # --- Inject SPECIFIC ICP Info for RETRY with HIGH EMPHASIS ---
                icp_instruction_retry = ""  # Reset for retry

                if selected_program == Program.ICP:
                    # Check which specific prompt it is and get the corresponding info
                    if prompt_name == PromptName.PERSONALITY and icp_info_p3:  # Use stored info
                        icp_instruction_retry = icp_info_p3
                    elif prompt_name == PromptName.CONQUAL and icp_info_p6a:  # Use stored info
                        icp_instruction_retry = icp_info_p6a
                    elif prompt_name == PromptName.CONIMPROV and icp_info_p6b:  # Use stored info
                        icp_instruction_retry = icp_info_p6b

                    if icp_instruction_retry:  # Only modify if specific info was provided
                        prompt_text = f"""\
########################################################################
# CRITICAL INSTRUCTION OVERRIDE FOR THIS TASK (RETRY ATTEMPT)          #
########################################################################

THE FOLLOWING INSTRUCTIONS ARE PARAMOUNT AND MUST BE FOLLOWED EXACTLY, SUPERSEDING ANY CONFLICTING GENERAL INSTRUCTIONS IN THE ORIGINAL PROMPT BELOW. FAILURE TO ADHERE STRICTLY WILL RESULT IN AN INCORRECT RESPONSE.

Specific Instructions:
{icp_instruction_retry}

########################################################################
# END OF CRITICAL INSTRUCTIONS - NOW FOLLOW ORIGINAL PROMPT BELOW      #
########################################################################

--- Original Prompt ---
{prompt_text}"""
                        logger.info(f"Applied CRITICAL ICP info to RETRY prompt {prompt_name}")

                full_prompt_retry = f"{prompt_text}\n\nUse the following files to complete the tasks. Do not give any output for this prompt.\n{general_context}"

                # Prepare generation config with temperature
                generation_config: genai_types.GenerateContentConfigOrDict = {
                    "temperature": temperature
                }

                # Add thinking configuration if enabled and this prompt should use thinking
                if enable_thinking and prompt_name in thinking_prompts:
                    # Use the thinking_config parameter when enabled
                    generation_config = {
                        "temperature": temperature,
                        "thinking_config": {"thinking_budget": 8096},
                    }
                    global_signals.update_message.emit(
                        f"Using AI thinking for prompt {promno} ({prompt_name})..."
                    )

                # Use general_context built earlier

                try:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL, contents=full_prompt_retry, config=generation_config
                    )
                    output_text_retry = response.text

                    if prompt_name in list_output_prompts and output_text_retry is not None:
                        results[prompt_name] = _extract_list_from_string(output_text_retry)
                    elif output_text_retry is not None:
                        results[prompt_name] = output_text_retry.strip()
                    else:
                        results[prompt_name] = ""  # Ensure empty string if None

                    # Check if retry was successful
                    if results[prompt_name] != "" and results[prompt_name] != "[]":
                        logger.info(
                            f"Success: Extra retry for prompt {prompt_name} (attempt {attempt + 1})"
                        )
                        break  # Exit retry loop
                    logger.warning(
                        f"Extra retry attempt still resulted in empty response for {prompt_name} (attempt {attempt + 1})"
                    )

                except Exception:
                    logger.exception(
                        f"Error processing extra retry for prompt {prompt_name} (attempt {attempt + 1})"
                    )
                    # Don't update results[prom] here as we want to keep the best result so far

            # After all retries, check final result
            if prompt_name in results and (
                results[prompt_name] == "" or results[prompt_name] == "[]"
            ):
                logger.error(f"Critical prompt still empty after all attempts for {prompt_name}")

    # --- End Retry Logic ---

    results = process_prompt_results(results)

    with open(filename_with_timestamp, "w") as json_file:
        json.dump(results, json_file, indent=4)

    global_signals.update_message.emit("Prompting finished, generating report...")
    return filename_with_timestamp
