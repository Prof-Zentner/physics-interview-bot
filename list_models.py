import google.generativeai as genai
import os

# Get API key
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    print("ERROR: GEMINI_API_KEY environment variable not set!")
    print("Run: set GEMINI_API_KEY=your-api-key")
    exit(1)

genai.configure(api_key=API_KEY)

print("=" * 60)
print("Available Gemini Models:")
print("=" * 60)

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✅ {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Supported Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"\nError listing models: {e}")
    print("\nMake sure your API key is valid and has access to Gemini models.")

print("\n" + "=" * 60)
