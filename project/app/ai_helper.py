# app/ai_helper.py
import google.generativeai as genai
import PyPDF2
import PIL.Image
from django.conf import settings
import io

# Configure API Key (Make sure this matches your settings)
GOOGLE_API_KEY = "AIzaSyDcC5evL35dUsmmuBI9VMrl8drlPgM0eOA" 
genai.configure(api_key=GOOGLE_API_KEY)

def analyze_case_file(case_obj):
    """
    Reads the file from a CaseSubmission object and sends it to Gemini.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = "You are a legal assistant. Analyze the following case document/image. Identify the key legal issues, relevant laws, and predict a likely court judgment based on general legal principles. Keep it professional."
        
        content_parts = [prompt]

        # Check if a document exists
        if case_obj.document:
            file_path = case_obj.document.path
            file_ext = file_path.split('.')[-1].lower()

            # --- HANDLE PDF ---
            if file_ext == 'pdf':
                text_content = ""
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text_content += page.extract_text() + "\n"
                content_parts.append("Document Content:\n" + text_content)

            # --- HANDLE IMAGES (JPG, PNG) ---
            elif file_ext in ['jpg', 'jpeg', 'png', 'webp']:
                img = PIL.Image.open(file_path)
                content_parts.append(img)
            
            # --- HANDLE TEXT FILES ---
            elif file_ext == 'txt':
                with open(file_path, 'r') as f:
                    content_parts.append(f.read())

        # Add user's manual text description if provided
        if case_obj.case_text:
            content_parts.append(f"Additional User Notes: {case_obj.case_text}")

        # Send to Gemini
        response = model.generate_content(content_parts)
        return response.text

    except Exception as e:
        return f"Error analyzing document: {str(e)}"