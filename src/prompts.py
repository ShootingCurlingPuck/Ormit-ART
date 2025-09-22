from src.constants import PromptName
from src.data_models import Prompt

PROMPTS = [
    Prompt(
        name=PromptName.FIRST_IMPRESSION,
        text="""You're an Assessor at Ormit Talent.  Give a concise first impression of a trainee named Piet (max 35 words).
**Input Documents:** Utilize the following documents to gather information:
    * 'Assessment Notes', specifically look for mentions of 'first impression' or 'FI'.

**Instructions:**
Focus on: Overall vibe, communication style, nervousness, body language, and emotional tone.
Don't judge: Rely *only* on assessor observations in 'Assessment Notes'.
Output: One short paragraph (max 35 words) in English.  *Only* the first impression, no extra words or formatting.
""",
        temperature=0.4,
    ),
    Prompt(
        name=PromptName.PERSONALITY,
        text="""
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
        temperature=0.4,
    ),
    Prompt(
        name=PromptName.COGCAP_SCORES,
        text="""Analyze the provided images containing cognitive capacity test results.
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
    *   **DO NOT USE BACKSLASHES. SO NO \\**

**Example for DIFFERENT scores (do not copy these numbers):** "[75, 80, 85, 70, 65, 78]"

**Based on the provided images, generate the required Python list string.**
""",
        temperature=0.0,
    ),
    Prompt(
        name=PromptName.COGCAP_REMARKS,
        text="""Read 'Capacity test results'.
Write a 2-3 sentence summary interpreting the results of a trainee named Piet.
Focus on:
  - Overall general ability.
  - Speed vs. accuracy.
  - Sub-test performance (verbal, numerical, abstract).
  - average performance is good, frame the performance positively.

Output: *Only* the summary text in English. No labels, formatting, or extra sentences. Do not give any lists relates to other prompts! **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        temperature=0.3,
    ),
    Prompt(
        name=PromptName.LANGUAGE,
        text="""Determine the trainee's language levels (Dutch, French, English).
Use: 'Context and Task description' and 'Assessment Notes'.

Instructions:
  1. If 'Assessment Notes' specifies levels (e.g., 'B2'), use those.
  2. Otherwise, use the guide in 'Context and Task description'(section '5. Language Skills') and estimate the language level based on the 'Assessment Notes'.

Output: A *string* containing a Python list: [Dutch level, French level, English level]
Example: "['C1', 'B2', 'C2']"

*Only* the list string. No other text.  The output *must* be a directly usable Python list string (enclosed in double quotes). **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        temperature=0.2,
    ),
    Prompt(
        name=PromptName.CONQUAL,
        text="""Identify 6-7 of Piet the trainee's *strengths* based on the Assessment Notes, specifically the end evaluation if available. List both aspects mentioned in the personality section and skill-based qualities. Focus on strengths that were present during multiple stages of the assessment.
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
        temperature=0.3,
    ),
    Prompt(
        name=PromptName.CONIMPROV,
        text="""Identify 3-5 of Piet the trainee's *development points* based on the 'Assessment Notes', specifically the end evaluation if available. List both aspects mentioned in the personality section and skill-based improvements. Focus on development points that were present during multiple stages of the assessment.
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
        temperature=0.3,
    ),
    Prompt(
        name=PromptName.QUALSCORE,
        text="""Match trainee's characteristics to these ratings found in 'Assessment Notes': "Strong yes", "Yes", "Not sure", or "No".

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
        temperature=0.1,
    ),
    Prompt(
        name=PromptName.QUALSCORE_DATA,
        text="""Match trainee's qualities to these ratings found in 'Assessment Notes': "Strong yes", "Yes", "Not sure", or "No".

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
        temperature=0.1,
    ),
    Prompt(
        name=PromptName.DATATOOLS,
        text="""Analyze 'Assessment Notes' for data skill proficiency.
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
        temperature=0.2,
    ),
    Prompt(
        name=PromptName.INTERESTS,
        text="""Identify 3-5 data-related interests from 'Assessment Notes'. Be specific, do not just mention data. Keep the descriptions short (maximum 10 words each) and *in English*.

If no clear interests are mentioned, output "N/A".

Output: A *string* containing a Python list.
Example: "['Machine Learning', 'Data Visualization']"
Example with no interests: "["N/A"]"

*Only* the list string. No extra text, no "python" labels. The output *must* be a directly usable Python list string (enclosed in double quotes). **DO NOT USE BACKSLASHES IN THE OUTPUT. NEVER USE BACKSLASHES.**
""",
        temperature=0.4,
    ),
]
