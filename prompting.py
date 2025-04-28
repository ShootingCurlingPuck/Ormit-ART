from google import genai
import time
from datetime import datetime
import json
from global_signals import global_signals
import re
import os
import PyPDF2
from docx import Document
import ast

# Set the default Gemini model for all prompts
default_model = "gemini-2.5-flash-preview-04-17"

def read_pdf(file_path):
    """Reads and returns text from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text

def read_docx(file_path):
    """Reads and returns text from a DOCX file."""
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
    return text

def _extract_list_from_string(text):
    """
    Safely extracts a Python list from a string and returns it as a *string*
    representation suitable for JSON, handling various Gemini output quirks.
    """
    match = re.search(r'\[[^\]]*\]', text)
    if match:
        list_str = match.group(0)
        try:
            parsed_list = ast.literal_eval(list_str)
            if isinstance(parsed_list, list):
                return json.dumps(parsed_list)
        except (SyntaxError, ValueError):
            pass
    return '[]'

max_wait_time = 200

# Dictionary containing prompts with their respective temperatures
prompts_with_temps = {
    'prompt2_firstimpr': {
        'text': """You're an Assessor at Ormit Talent.  Give a concise first impression of a trainee named Piet (max 35 words).
**Input Documents:** Utilize the following documents to gather information:
    * 'Assessment Notes', specifically look for mentions of 'first impression' or 'FI'.

**Instructions:**
Focus on: Overall vibe, communication style, nervousness, body language, and emotional tone.
Don't judge: Rely *only* on assessor observations in 'Assessment Notes'.
Output: One short paragraph (max 35 words) in English.  *Only* the first impression, no extra words or formatting.
""",
        'temperature': 0.4
    },

  "prompt3_personality": {
        'text': """
**Objective:** Generate an in-depth and balanced personality description of the trainee, Piet, as a starting point for his personal development during his traineeship.
The description should highlight both strengths and areas for development of Piet's personality, technical skills should not be discussed here.

**Target Audience:** Piet and his coach.

**Input Documents:** Utilize the following documents to gather information:
    * 'Assessment Notes' (primary source for observations and examples)
        Put more emphasis on information from the end evaluation (if available) and PAPI interview. You can use information from the Role play (RP), Business case (BC), and curious case (CC) for behavioural examples where applicable.
    * 'PAPI Gebruikersrapport' (personality test results, only to elaborate on 'Assessment Notes')
    * 'Personality Section Examples' (for *structure and tone* examples only, **not** for content)
    * 'Context and Task description' (for background context).


**Instructions for Generating the Personality Description:**

*   **Overall Tone and Style:**
    *   Write in a conversational yet professional tone, like you are summarizing the trainee's assessment for a colleague. Use simple, realistic language, like you are a fluent, non-native speaker.
    *   Be concise and to the point, but provide sufficient detail to be insightful. Avoid repeting the same information.
    
    **Ensure a balanced perspective:**
    * make 75-85 percent of the description strengths, and 15-25 percent development points
    * When discussing development areas, ensure these points are framed as growth opportunities, emphasizing how they can enhance Piet's existing strengths.
    * Use the 'sandwich' approach, where every development point is framed between two positive observations. When providing constructive feedback, ensure it is directly linked to a strength and end with an additional positive note, focusing on how the development area can enhance an already strong quality
        For example: "Piet is really great at staying organized and meeting deadlines, which helps a lot in team settings. One area he could work on is delegating tasks more to avoid feeling overwhelmed. Overall, his positive attitude and dedication to the team's success make him an invaluable member."
    * Avoid using 'However, ...' to introduce development points.

*   **Content - Introduction (Optional - Max 3 sentences):**
    *   Begin with a brief introduction (maximum 3 sentences) to provide context:
        *   Include relevant background or experience of Piet *if mentioned in the input documents*.
        *   Include Piet's specific motivation for the traineeship *if explicitly stated in the input documents*. Keep this concise and avoid exaggeration.

*   **Content - Main Body (250-400 words):**
    *   **Identify Main Traits (Key Areas to Consider):** Based on 'Assessment Notes' (especially the end evaluation), identify Piet's key personality traits, including both strengths and areas for development. 
        * These are examples of themes of interest (non-exhaustive): Personal leadership, connecting with people, complexity management, results-oriented execution, adaptability, taking broad perspective, self-awareness, interpersonal style, and thinking/problem-solving approaches.
        * When multiple traits overlap, reframe the point to highlight the nuance between them rather than repeating the same concepts. 

    *   **Integrate Sources - Assessment Notes with PAPI Gebruikersrapport insights:** Rely on the Assessment Notes and use the PAPI Gebruikersrapport as background information. To integrate PAPI insights smoothly, link the findings with observed behavior, showing how the personality traits interact. Do not discuss PAPI results in a separate bullet point.
        For example, if the PAPI indicates a low need for dominance, and the assessment notes show Piet being collaborative, connect these points. Explain the *implications* of personality traits. 
        For instance, "Due to a lower need for dominance discussed during the PAPI interview, Piet is less likely to readily take charge in group settings, and more inclined to seek consensus." 
        If there are contradictions between the Assessment Notes and the PAPI Gebruikersrapport, mention them.

    *   **Provide Examples:** For each trait, elaborate on *how* it presents itself in Piet's behavior, providing concrete examples from the 'Assessment Notes'. Mention the specific assessment step or activity where the trait was observed (e.g., "during the Curious Case," "in the role-play exercise"). 
    *   **Avoid Repetition:** Mention each trait only once in the main body. 
    *   **Structure with Bullet Points:**  Organize the main body using concise bullet points, with each bullet point discussing a single trait.
    *   **No Direct Quotes:** Do not directly quote from the input documents. Paraphrase and synthesize the information.

*   **Content - Final Summary (max. 3 sentences):**
    *   Conclude with a short summary of maximum 3 sentences. This summary describes Piet's the main strenghts and overall impression, highlighting why we hired him.

**Output Format:**

*   **English Language Only**
*   **Stay in the word limit:** total of maximum 400 - 500 words.
*   **No Lists for Other Prompts:** Do not include any lists or content related to other prompts (e.g., cognitive scores, language skills, conclusion points).
*   **No Extra Text or Formatting:**  Do not add any extra text, labels, section titles, or special formatting beyond bullet points and blank lines.
*   **Section Separation:** Separate the optional introduction, the bulleted main body, and the final summary with blank lines (hard enter).
*   **Bullet Point Format:** Each bullet point should start with an asterisk (*) and be followed by a space. After each bullet point, add a newline character (\n) to ensure proper spacing in the output.
*   **Example Format:**
    ```
    [Introduction paragraph]

    * First bullet point with trait description
    * Second bullet point with trait description
    * Third bullet point with trait description
    \n -> new white line
    [Summary paragraph]
    ```
""",
        'temperature': 0.4
    },
     
'prompt4_cogcap_scores': {
        'text': """Analyze the provided images containing cognitive capacity test results.
Your task is to extract the **percentile scores** for six specific categories.

1.  **Identify the Categories:** Look for 'Total score', 'Speed', 'Accuracy' in the first image, and 'Verbal', 'Numerical', 'Abstract' in the second image.
2.  **Map 'Total score':** Treat the 'Total score' value as the 'general_ability' score.
3.  **Extract Percentile Scores:** For each category, find the **large blue number** located at the end of the blue bar. **Ignore** the smaller number in parentheses (the sten score).
4.  **Required Scores & Order:** You must find these six scores and arrange them in this specific order:
    [general_ability, speed, accuracy, verbal, numerical, abstract]
5.  **Output Format:**
    *   Your output must be a *string* representing a standard Python list of integers.
    *   The string must start *exactly* with `[` and end *exactly* with `]`.
    *   There should be *absolutely no other text*, formatting, labels (like "python"), or explanations before or after the list string.
    *   **DO NOT USE BACKSLASHES. SO NO \**

**Example for DIFFERENT scores (do not copy these numbers):** "[75, 80, 85, 70, 65, 78]"

**Based on the provided images, generate the required Python list string.**
""",
        'temperature': 0.0
    },
    'prompt4_cogcap_remarks': {
        'text': """Read 'Capacity test results'.
Write a 2-3 sentence summary interpreting the results of a trainee named Piet.
Focus on:
  - Overall general ability.
  - Speed vs. accuracy.
  - Sub-test performance (verbal, numerical, abstract).
  - average performance is good, frame the performance positively.

Output: *Only* the summary text in English. No labels, formatting, or extra sentences. Do not give any lists relates to other prompts! **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.3
    },
    'prompt5_language': {
        'text': """Determine the trainee's language levels (Dutch, French, English).
Use: 'Context and Task description' and 'Assessment Notes'.

Instructions:
  1. If 'Assessment Notes' specifies levels (e.g., 'B2'), use those.
  2. Otherwise, use the guide in 'Context and Task description'(section '5. Language Skills') and estimate the language level based on the 'Assessment Notes'.

Output: A *string* containing a Python list: [Dutch level, French level, English level]
Example: "['C1', 'B2', 'C2']"

*Only* the list string. No other text.  The output *must* be a directly usable Python list string (enclosed in double quotes). **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.2
    },
        'prompt6a_conqual': {
        'text': """Identify 6-7 of Piet the trainee's *strengths* based on the Assessment Notes, specifically the end evaluation if available. List both aspects mentioned in the personality section and skill-based qualities. Focus on strengths that were present during multiple stages of the assessment.
Use: 'Context and Task Description', 'Assessment Notes', 'PAPI Gebruikersrapport' and the personality section you've written.
Target audience: Piet and his coach.

Instructions:
  - Describe each strenght with a few key words (under 7 words each), followed by 1 to 2 sentences giving some context. 
  - Be precise, make sure there is no contradiction with the personality section or development points. 
  - Simple language.
  - In English

Output: A *string* containing a Python list.
Example: "['Good listener: Piet listened to everyone's ideas during the curious case task.', 'Communicates clearly: He brings his ideas across in a way that is easy to understand.', 'Works well in teams: Piet finds a balance between giving everyone space to express their idea and moving on in an effective manner.',...]"
*Only* the list string. No other text. The output *must* be a directly usable Python list string (enclosed in double quotes).  **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.3
    },
    'prompt6b_conimprov': {
        'text': """Identify 3-5 of Piet the trainee's *development points* based on the 'Assessment Notes', specifically the end evaluation if available. List both aspects mentioned in the personality section and skill-based improvements. Focus on development points that were present during multiple stages of the assessment.
Use: 'Context and Task Description', 'Assessment Notes', 'PAPI Gebruikersrapport' and the personality section you've written.
Target audience: Piet and his coach.

Instructions:
  - Describe each development point with key words (under 7 key words each), followed by 1 to 2 full sentences explaining what is meant and giving some context (in total around 120 words).
  - Frame development points constructively. Present areas for development as learning opportunities, emphasizing how they can enhance Piet's existing strengths.
  - Be precise, make sure there is no contradiction with the personality section or strengths.
  - Use simple language, but full sentences.
  - In English

Output: A *string* containing a Python list.
Example: "['Develop assertiveness: Piet hesitates to express his opinion when he knows others disagree.', 'work on being proactive: He tends to let things happen instead of taking ownership himself.',...]"

*Only* the list string. No other text. The output *must* be a directly usable Python list string (enclosed in double quotes). **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.3
    },

'prompt7_qualscore': {
          'text': """Match trainee's characteristics to these ratings found in 'Assessment Notes': "Strong yes", "Yes", "Not sure", or "No".

Create a scored list of *20 numbers* (-1s, 0s, and 1s) based on these ratings. Output *only* the Python list string.

**Input:** 'Assessment Notes'

**Scoring Rules for Characteristics 1-20:**

1.  **Identify Ratings:** For each characteristic (listed below), find the corresponding rating in 'Assessment Notes'. *Only* consider explicit "Strong yes", "Yes", "Not sure", or "No" ratings. Ignore any other comments or descriptions for scoring these characteristics.

2.  **Numerical Conversion:** Convert each rating to a numerical score:
    *   "Strong yes": 3 points
    *   "Yes": 2 points
    *   "Not sure": 1 point
    *   "No": 0 points

3.  **Average Score (if multiple ratings):** If there are multiple ratings for the *same* characteristic in 'Assessment Notes', calculate the average of their numerical scores. If there is no rating for a characteristic, treat it as if it's not mentioned and proceed to the next characteristic.

4.  **Final Score Conversion:** Convert the average score (or single rating's score) to the final integer score using these ranges:
    *   **-1:** Average score between 0 and 1.4 (inclusive).
    *   **0:** Average score between 1.5 and 2.4 (inclusive).
    *   **1:** Average score between 2.5 and 3 (inclusive).

**Important Considerations:**

*   **Strict but Fair:** Be strict in identifying areas for development. If there's *any* indication of a need for growth, even with strengths, lean towards a lower score (0 or -1).
*   **No Inference:** Only use *explicit* ratings. Do *not* infer or extrapolate ratings from other comments.
*   **Contradictory Information:** If you find contradictory ratings for a characteristic, use the average score and then convert it as per rule 4. If there's uncertainty after averaging, default to 0.
*   **Example:** If a candidate is described as "friendly" but also "sometimes interrupts," the "Collaborative" score should be lower (0 or -1).
*   **Example:** If the candidate is "interested in learning new things" but no specific examples of self-directed learning are given, rate "Autodidact/Learning Agility" as 0.

**Characteristics to be Scored (in order):**

1. Motivation
2. Personal development
3. Gut/Toughness
4. Ownership
5. Positive & Inspiring attitude
6. Involved
7. Collaborative
8. Communication skills
9. Autodidact/ learning agility
10. Complexity management
11. Thinking flexibility
12. Multiple thinking
13. Proactive
14. Delivers results
15. Agile worker
16. Stakeholder management
17. Innovative & creative
18. Perspective thinking
19. Customer oriented attitude
20. (Informal) networker


**Output Format:**

Output a *string* containing a Python list of integers (-1, 0, 1).  Do *not* include any extra text or labels.

**Example Output:**  `"[0, 1, 0, -1, 1, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0]"`

*Only* provide the string representing the list. Do not use backticks or single quotes around the string. Use double quotes as shown in the example.
""",
        'temperature': 0.1
    },

'prompt7_qualscore_data': {
        'text': """Match trainee's qualities to these ratings found in 'Assessment Notes': "Strong yes", "Yes", "Not sure", or "No".

Create a scored list of *23 items* (numbers: -1s, 0s, 1s and strings: "N/A") based on these ratings. Output *only* the Python list string.

**Input:** 'Assessment Notes'

**Scoring Rules for Qualities 1-23:**

1.  **Identify Ratings:** For each quality (listed below), find the corresponding rating in 'Assessment Notes'. *Only* consider explicit "Strong yes", "Yes", "Not sure", or "No" ratings. Ignore any other comments or descriptions for scoring these qualities.

2.  **Numerical Conversion:** Convert each rating to a numerical score:
    *   "Strong yes": 3 points
    *   "Yes": 2 points
    *   "Not sure": 1 point
    *   "No": 0 points

3.  **Average Score (if multiple ratings):** If there are multiple ratings for the *same* quality in 'Assessment Notes', calculate the average of their numerical scores.

4.  **Handle Missing Information ("N/A"):** If a quality is *not mentioned at all* in the 'Assessment Notes', the score for that quality should be "N/A".

5.  **Final Score Conversion (for qualities that are mentioned):** Convert the average score (or single rating's score) to the final integer score using these ranges:
    *   **-1:** Average score between 0 and 1.4 (inclusive).
    *   **0:** Average score between 1.5 and 2.4 (inclusive).
    *   **1:** Average score between 2.5 and 3 (inclusive).

**Important Considerations:**

*   **Strict but Fair:** Be strict in identifying areas for development. If there's *any* indication of a need for growth, even with strengths, lean towards a lower score (0 or -1) when the score is numerical.  "N/A" indicates no information, not necessarily a weakness or strength.
*   **No Inference:** Only use *explicit* ratings. Do *not* infer or extrapolate ratings from other comments.
*   **Contradictory Information:** If you find contradictory ratings for a quality, use the average score and then convert it as per rule 5. If there's uncertainty after averaging, default to 0 (if a numerical score is applicable, otherwise, if there's no mention at all still output "N/A").
*   **Example:** If a candidate is described as "good at teamwork" but also "sometimes dominates the conversation," rate "Collaborative" as 0.
*   **Example:** If the candidate is "interested in learning new things" but no specific examples of self-directed learning are given, rate "Curious perseverance" (or similar quality) as 0.

**Qualities to be Scored (in order - Order is Important!):**

1.  Motivation
2.  Guts
3.  Self-aware & aiming at learning
4.  Enthusiast & Inspiring
5.  Interested and open
6.  Communication
7.  Collaborative
8.  Curious perseverance
9.  Analytical
10. Critical solution focused mindset
11. Business perspective
12. Thorough
13. Delivers results/PM
14. Flexibility
15. Stakeholder Management
16. Service oriented
17. Creative & Innovative drive
18. End-to-End/Bigger picture
19. Analytics Project Management
20. Knowledge of Business & IT
21. Visualizing data
22. Analyzing data
23. Data Science Models

**Output Format:**

Output a *string* containing a Python list of integers (-1, 0, 1) and/or strings ("N/A"). Do *not* include any extra text or labels.

**Example Output:** `"[0, 1, 0, -1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, "N/A", -1, "N/A", -1]"`

*Only* provide the string representing the list. Do not use backticks or single quotes around the string. Use double quotes as shown in the example.  **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.1
    }, 
    
    'prompt8_datatools': {
        'text': """Analyze 'Assessment Notes' for data skill proficiency.
Output: a *string* containing a Python list of 5 numbers (-1, 0, or 1).

Skills (in order):
  1. Excel/VBA
  2. Power BI/Tableau/Qlik Sense
  3. Python/R
  4. SQL
  5. Azure Databricks

Scale:
  -1: Beginner/Improvement point.
  0: Average
  1: Proficient
  "N/A": Not mentioned or not applicable

Don't be too strict on proficiency, especially for Excel/VBA.
For example: if the trainee is described as 'has used excel a lot', rate Excel/VBA as 1.
If a skill is not mentioned at all, use "N/A" instead of guessing.

Output:  *Only* the list string. No extra text, no "python" labels.
Example: "[-1, 1, 0, 1, -1]"
Example with N/A: "[-1, 1, 0, "N/A", -1]"

The output *must* be a directly usable Python list string (enclosed in double quotes). No extra text. **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.2
    },
    'prompt9_interests': {
        'text': """Identify 3-5 data-related interests from 'Assessment Notes'. Be specific, do not just mention data. Keep the descriptions short (maximum 10 words each) and *in English*.

If no clear interests are mentioned, output "N/A".

Output: A *string* containing a Python list.
Example: "['Machine Learning', 'Data Visualization']"
Example with no interests: "["N/A"]"

*Only* the list string. No extra text, no "python" labels. The output *must* be a directly usable Python list string (enclosed in double quotes). **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        'temperature': 0.4
    },
}

def send_prompts(data):
    global_signals.update_message.emit("Connecting to Gemini...")

    GOOGLE_API_KEY = data["Gemini Key"]
    # Create client with API key
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # Get the thinking setting from GUI data
    enable_thinking = data.get("Enable Thinking", False)
    # Define which prompts should use thinking when enabled
    thinking_prompts = [
        'prompt3_personality', 
        'prompt6a_conqual', 
        'prompt6b_conimprov', 
        'prompt7_qualscore', 
        'prompt7_qualscore_data'
    ]
    
    current_time = datetime.now()
    formatted_time = current_time.strftime("%m%d%H%M")
    appl_name = data["Applicant Name"]
    # Update to save to output_reports directory
    output_dir = "output_reports"
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Set the file path to be in the output directory
    filename_with_timestamp = os.path.join(output_dir, f"{appl_name}_{formatted_time}.json")

    path_to_notes = r'temp/Assessment Notes.pdf'
    path_to_persontest = r'temp/PAPI Gebruikersrapport.pdf'
    path_to_cogcap = r'temp/Cog. Test.pdf'
    path_to_contextfile = r'resources/Context and Task Description.docx'
    path_to_toneofvoice = r'resources/Examples Personality Section.docx'
    path_to_mcpprofile = r'resources/The MCP Profile.docx'
    path_to_dataprofile = r'resources/The Data Chiefs profile.docx'

    lst_files = [
        path_to_notes,
        path_to_persontest,
        path_to_cogcap,
        path_to_contextfile,
        path_to_toneofvoice,
    ]

    selected_program = data["Traineeship"]
    # Use MCP profile for both MCP and NEW programs
    if selected_program == 'DATA':
        lst_files.append(path_to_dataprofile)
    else: # Handles MCP, NEW, and any potential unknown as MCP
        lst_files.append(path_to_mcpprofile)

    file_contents = {}
    for file_path in lst_files:
        file_name = os.path.basename(file_path)
        if file_path.endswith('.pdf'):
            file_contents[file_name] = read_pdf(file_path)
        elif file_path.endswith('.docx'):
            file_contents[file_name] = read_docx(file_path)
        else:
            print(f"Warning: Unsupported file type: {file_path}")
            file_contents[file_name] = ""

    # --- Read ICP Description File (if applicable) --- Append to file_contents
    icp_description_content = ""
    if selected_program == 'ICP':
        icp_file_path = data.get("Files", {}).get("ICP Description") # Safer get
        if icp_file_path and os.path.exists(icp_file_path):
            try:
                icp_description_content = read_docx(icp_file_path)
                # Add with a clear key to context
                file_contents["ICP Traineeship Description.docx"] = icp_description_content
            except Exception as e:
                 print(f"Error reading ICP description file {icp_file_path}: {e}")
                 file_contents["ICP Traineeship Description.docx"] = "[Error reading ICP description]"
        else:
            print(f"Warning: ICP Description file path not found or file missing: {icp_file_path}")
            # Don't add to file_contents if missing

    # --- Get ICP Specific Prompt Info --- (Store them for use in the loop)
    icp_info_p3 = data.get("ICP_Info_Prompt3", "") if selected_program == 'ICP' else ""
    icp_info_p6a = data.get("ICP_Info_Prompt6a", "") if selected_program == 'ICP' else ""
    icp_info_p6b = data.get("ICP_Info_Prompt6b", "") if selected_program == 'ICP' else ""

    global_signals.update_message.emit("Files uploaded, starting prompts...")

    # Define lists of prompts for each program
    common_prompts = [
        'prompt2_firstimpr', 'prompt3_personality', 'prompt4_cogcap_scores',
        'prompt4_cogcap_remarks', 'prompt5_language', 'prompt6a_conqual',
        'prompt6b_conimprov', 'prompt9_interests'
    ]
    lst_prompts_mcp = common_prompts + ['prompt7_qualscore']
    lst_prompts_data = common_prompts + ['prompt7_qualscore_data', 'prompt8_datatools']

    # Define which prompts are expected to return lists (for parsing/evaluation)
    list_output_prompts = [
        'prompt4_cogcap_scores', 'prompt5_language', 'prompt6a_conqual',
        'prompt6b_conimprov', 'prompt7_qualscore', 'prompt7_qualscore_data',
        'prompt8_datatools', 'prompt9_interests'
    ]

    # --- Select appropriate list of prompts ---
    # Use MCP prompts for both MCP and NEW programs
    if selected_program == 'DATA':
        lst_prompts = lst_prompts_data
    else: # Handles MCP, NEW, and any potential unknown as MCP
        lst_prompts = lst_prompts_mcp

    # --- Run Prompts --- 
    results = {}
    start_time_all = time.time()

    # Build the general context string ONCE (includes ICP description if present)
    general_context = "\n\n---\n\n".join([f"File: {file_name}\nContent:\n{content}"
                                     for file_name, content in file_contents.items()])

    for promno, prom in enumerate(lst_prompts, start=1):
        global_signals.update_message.emit(f"Submitting prompt {promno}/{len(lst_prompts)}, please wait...")

        prompt_data = prompts_with_temps[prom]
        prompt_text = prompt_data['text']
        temperature = prompt_data['temperature']
        
        # --- Inject SPECIFIC ICP Info with HIGH EMPHASIS ---
        final_prompt_text = prompt_text
        icp_instruction = ""

        if selected_program == 'ICP':
            if prom == 'prompt3_personality' and icp_info_p3:
                icp_instruction = icp_info_p3
            elif prom == 'prompt6a_conqual' and icp_info_p6a:
                icp_instruction = icp_info_p6a
            elif prom == 'prompt6b_conimprov' and icp_info_p6b:
                icp_instruction = icp_info_p6b

            if icp_instruction: # Only modify if specific info was provided
                final_prompt_text = f"""\
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
                print(f"Applied CRITICAL ICP info to prompt: {prom}")

        # Prepare generation config with temperature
        generation_config = {"temperature": temperature}
        
        # Add thinking configuration if enabled and this prompt should use thinking
        if enable_thinking and prom in thinking_prompts:
            # Use the thinking_config parameter when enabled
            generation_config = {
                "temperature": temperature,
                "thinking_config": {
                    "thinking_budget": 8096
                }
            }
            global_signals.update_message.emit(f"Using AI thinking for prompt {promno} ({prom})...")
        
        # Construct the full prompt using the general context
        full_prompt = f"{final_prompt_text}\n\nUse the following files to complete the tasks. Do not give any output for this prompt.\n{general_context}"

        # Initial attempt
        max_attempts = 3  # Maximum number of attempts per prompt
        attempt = 0
        success = False
        
        while attempt < max_attempts and not success:
            try:
                if attempt > 0:
                    global_signals.update_message.emit(f"Retrying prompt {promno}/{len(lst_prompts)} (attempt {attempt+1}/{max_attempts})...")
                    # Add a short delay between retry attempts to avoid hammering the API
                    time.sleep(1)
                    
                response = client.models.generate_content(
                    model=default_model,
                    contents=full_prompt,
                    config=generation_config
                )
                output_text = response.text

                # Check if we got a valid response
                if prom in list_output_prompts:
                    result = _extract_list_from_string(output_text)
                    if result != "[]" and result.strip():
                        results[prom] = result
                        success = True
                    else:
                        print(f"Warning: Empty list result for prompt '{prom}' on attempt {attempt+1}.")
                else:
                    if output_text.strip():
                        results[prom] = output_text.strip()
                        success = True
                    else:
                        print(f"Warning: Empty text result for prompt '{prom}' on attempt {attempt+1}.")
                
                # If this is the last attempt and we haven't succeeded, use whatever we got
                if not success and attempt == max_attempts - 1:
                    if prom in list_output_prompts:
                        results[prom] = _extract_list_from_string(output_text)
                    else:
                        results[prom] = output_text.strip()
                    print(f"Warning: Using potentially empty result for '{prom}' after {max_attempts} attempts.")

            except Exception as e:
                print(f"Error processing prompt {prom} (attempt {attempt+1}): {e}")
                if attempt == max_attempts - 1:  # Last attempt
                    results[prom] = "[]" if prom in list_output_prompts else ""  # Ensure empty result matches type
            
            attempt += 1

        if time.time() - start_time_all > max_wait_time:
            print("Timeout for all prompts reached.")
            break

    # --- Retry Logic for Critical Prompts ---
    # This provides additional retries for specific critical prompts
    critical_prompts = ['prompt6b_conimprov']
    # Use MCP critical prompt for both MCP and NEW
    if selected_program == 'DATA':
        critical_prompts.append('prompt7_qualscore_data')
    else: # Handles MCP, NEW, and any potential unknown as MCP
        critical_prompts.append('prompt7_qualscore')
        
    max_retries = 2
    for prom in critical_prompts:
        if prom not in results or results[prom] == "" or results[prom] == "[]":
            print(f"Warning: Result for critical prompt '{prom}' is still empty after initial attempts. Retrying...")
            for attempt in range(max_retries):
                if time.time() - start_time_all > max_wait_time:
                    print("Timeout reached during critical prompt retry.")
                    break # Break retry loop if overall timeout hit
                    
                global_signals.update_message.emit(f"Retrying critical prompt '{prom}' (Extra attempt {attempt + 1}/{max_retries})...")
                
                # Add a short delay between retry attempts to avoid hammering the API
                time.sleep(1)
                
                # Reuse prompt details from initial run
                prompt_data = prompts_with_temps[prom]
                prompt_text = prompt_data['text']
                temperature = prompt_data['temperature']
                
                # --- Inject SPECIFIC ICP Info for RETRY with HIGH EMPHASIS ---
                final_prompt_text_retry = prompt_text
                icp_instruction_retry = "" # Reset for retry

                if selected_program == 'ICP':
                    # Check which specific prompt it is and get the corresponding info
                    if prom == 'prompt3_personality' and icp_info_p3: # Use stored info
                        icp_instruction_retry = icp_info_p3
                    elif prom == 'prompt6a_conqual' and icp_info_p6a: # Use stored info
                        icp_instruction_retry = icp_info_p6a
                    elif prom == 'prompt6b_conimprov' and icp_info_p6b: # Use stored info
                        icp_instruction_retry = icp_info_p6b

                    if icp_instruction_retry: # Only modify if specific info was provided
                        final_prompt_text_retry = f"""\
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
                        print(f"Applied CRITICAL ICP info to RETRY prompt: {prom}")

                # Prepare generation config with temperature
                generation_config = {"temperature": temperature}
                
                # Add thinking configuration if enabled and this prompt should use thinking
                if enable_thinking and prom in thinking_prompts:
                    # Use the thinking_config parameter when enabled
                    generation_config = {
                        "temperature": temperature,
                        "thinking_config": {
                            "thinking_budget": 8096
                        }
                    }
                    global_signals.update_message.emit(f"Using AI thinking for prompt {promno} ({prom})...")
                
                # Use general_context built earlier
                full_prompt_retry = f"{final_prompt_text_retry}\n\nUse the following files to complete the tasks. Do not give any output for this prompt.\n{general_context}"
                
                try:
                    response = client.models.generate_content(
                        model=default_model,
                        contents=full_prompt_retry,
                        config=generation_config
                    )
                    output_text_retry = response.text

                    if prom in list_output_prompts:
                        results[prom] = _extract_list_from_string(output_text_retry)
                    else:
                        results[prom] = output_text_retry.strip()

                    # Check if retry was successful
                    if results[prom] != "" and results[prom] != "[]":
                        print(f"Success: Extra retry for '{prom}' successful on attempt {attempt + 1}.")
                        break # Exit retry loop
                    else:
                         print(f"Warning: Extra retry attempt {attempt + 1} for '{prom}' still resulted in empty response.")

                except Exception as e:
                    print(f"Error processing extra retry for prompt {prom} (Attempt {attempt + 1}): {e}")
                    # Don't update results[prom] here as we want to keep the best result so far

            # After all retries, check final result
            if prom in results and (results[prom] == "" or results[prom] == "[]"):
                print(f"Error: Critical prompt '{prom}' still empty after all attempts.")
                
    # --- End Retry Logic ---

    def process_prompt_results(results):
        """Process the results from the prompts to ensure proper formatting."""
        
        # Format personality section (prompt3_personality) for template insertion
        if 'prompt3_personality' in results and isinstance(results['prompt3_personality'], str):
            text = results['prompt3_personality']
            lines = text.split('\n')
            formatted_parts = []
            first_point = True

            # Check for summary indicators
            summary_indicators = ["in summary", "to summarize", "overall", "in conclusion", 
                              "to conclude", "in short", "is a promising", "makes him a promising", 
                              "makes her a promising", "these qualities make"]

            for i, line in enumerate(lines):
                stripped_line = line.strip()
                is_bullet = stripped_line.startswith('*') or stripped_line.startswith('•')
                
                # Improved summary detection - check for various indicators
                is_summary = False
                lower_line = stripped_line.lower()
                
                # Check if this is the last paragraph/bullet (likely to be summary)
                is_last_content = (i == len(lines) - 1 or all(not l.strip() for l in lines[i+1:]))
                
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
                    if formatted_parts and not formatted_parts[-1] == "<<BREAK>>":
                        formatted_parts.append("<<BREAK>>")
                        formatted_parts.append("<<BREAK>>")
                    formatted_parts.append(stripped_line)
                
                # Regular text handling (no change)
                elif stripped_line and not first_point:
                    # Handle intro/summary lines *after* the first bullet
                    # Add break before non-bullet lines if needed
                    if formatted_parts and not formatted_parts[-1] == "<<BREAK>>":
                        formatted_parts.append("<<BREAK>>")
                    formatted_parts.append(stripped_line)
                elif stripped_line and first_point:
                    # Handle intro line *before* any bullets
                    formatted_parts.append(stripped_line)
                    # Don't set first_point = False yet, wait for actual bullet

            # Join parts, <<BREAK>> will be handled later
            # We join with a space just to ensure parts are concatenated.
            # The <<BREAK>> marker is the important part for splitting.
            results['prompt3_personality'] = ' '.join(formatted_parts).replace("<<BREAK>> ", "<<BREAK>>")


        # --- Format list prompts (prompt6a/b) ---
        # These likely go into tables, so keep their original JSON/List format processing
        list_prompts = ['prompt6a_conqual', 'prompt6b_conimprov']
        for prompt_key in list_prompts:
             if prompt_key in results and results[prompt_key]:
                original_data = results[prompt_key]
                # Store original JSON if it's a string that looks like JSON
                if isinstance(original_data, str) and original_data.strip().startswith('['):
                     results[f"{prompt_key}_original"] = original_data
                     # Attempt to parse, but prioritize keeping original if error
                     try:
                         items = json.loads(original_data)
                         results[prompt_key] = items if isinstance(items, list) else original_data
                     except (json.JSONDecodeError, TypeError):
                         results[prompt_key] = original_data # Keep original string on error
                elif isinstance(original_data, list):
                    results[prompt_key] = original_data # Already a list
                    results[f"{prompt_key}_original"] = json.dumps(original_data) # Store JSON version
                else:
                     # Not a list or JSON string, store original and keep as is
                     results[f"{prompt_key}_original"] = str(original_data)
                     results[prompt_key] = original_data


        return results

    results = process_prompt_results(results)

    with open(filename_with_timestamp, 'w') as json_file:
        json.dump(results, json_file, indent=4)

    global_signals.update_message.emit("Prompting finished, generating report...")
    return filename_with_timestamp