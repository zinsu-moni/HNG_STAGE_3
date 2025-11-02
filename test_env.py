from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
base_url = os.getenv('OPENAI_BASE_URL')
model = os.getenv('A2A_MODEL')

print(f"API Key exists: {api_key is not None}")
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"API Key first 30: {api_key[:30] if api_key else 'None'}")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
