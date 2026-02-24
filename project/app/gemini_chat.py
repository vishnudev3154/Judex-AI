import google.generativeai as genai
import PIL.Image
import PyPDF2
import json
import os

# ==========================================
# 🔴 KEY CHECK 🔴
# Ensure this matches the key in your Google AI Studio
GOOGLE_API_KEY = "AIzaSyDcC5evL35dUsmmuBI9VMrl8drlPgM0eOA" # REPLACE WITH YOUR REAL KEY
genai.configure(api_key=GOOGLE_API_KEY)
# ==========================================


# --- TOOL 1: For the Chatbot ---
def ask_ai(message, uploaded_file=None):
    try:
        # ✅ UPDATED TO 'gemini-2.5-flash' based on your list
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        system_guardrail = """
        ROLE: You are Judex AI, a specialized legal assistant.
        STRICT RULES:
        1. Answer ONLY questions related to Law, Court Cases, IPC, and Legal Procedures.
        2. If the user asks non-legal questions (e.g., cooking, coding, jokes), REFUSE politely.
        3. Keep answers professional, concise, and legally grounded.
        """

        content_parts = [system_guardrail]

        if uploaded_file:
            file_name = uploaded_file.name.lower()
            if file_name.endswith('.pdf'):
                try:
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    pdf_text = ""
                    for i, page in enumerate(pdf_reader.pages):
                        if i >= 5: break 
                        pdf_text += page.extract_text() + "\n"
                    content_parts.append(f"\n[Document Content]:\n{pdf_text}")
                except:
                    pass 
            elif file_name.endswith(('.png', '.jpg', '.jpeg')):
                try:
                    # Note: Newer flash models often handle images directly.
                    # If this fails, we can catch the error below.
                    image = PIL.Image.open(uploaded_file)
                    content_parts.append(image)
                except:
                    return "Error: Image analysis unavailable."

        content_parts.append(f"User Query: {message}")

        response = model.generate_content(content_parts)
        return response.text if response.text else "No response."

    except Exception as e:
        return f"AI Error: {str(e)}"


# --- TOOL 2: For the Virtual Court ---
def get_virtual_judge_verdict(argument, case_details="", evidence_text=""):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        ROLE: You are an AI Judge and Defense Attorney Simulator.
        
        CASE CONTEXT:
        "{case_details}"
        
        EVIDENCE/DOCUMENTS:
        "{evidence_text}"
        
        CURRENT ARGUMENT (Prosecution): 
        "{argument}"
        
        TASK:
        1. Act as Defense: Counter the argument strictly based on the provided Case Context and Evidence. 
           If the argument is irrelevant to this specific case, point that out aggressively.
        2. Act as Judge: Analyze the argument's strength regarding THIS case.
        3. Score: 0 (Weak/Innocent) to 100 (Strong/Guilty).
        
        Output JSON only:
        {{
            "defense_argument": "...",
            "verdict": "Guilty" or "Not Guilty",
            "score": 50,
            "judicial_reasoning": "..."
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        if "{" in text: text = "{" + text.split("{", 1)[1]
        if "}" in text: text = text.rsplit("}", 1)[0] + "}"
        
        return json.loads(text)

    except Exception as e:
        print(f"------------ GEMINI ERROR: {e} ------------")
        return {
            "defense_argument": "I cannot process that argument right now.",
            "verdict": "Mistrial",
            "score": 50,
            "judicial_reasoning": "Technical error."
        }