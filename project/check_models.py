import google.generativeai as genai
import os

# REPLACE THIS WITH YOUR REAL API KEY
genai.configure(api_key="AIzaSyDViJN8ZTdL_Jq3THFoesbIBsj8jUC_8kk")

print("Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")