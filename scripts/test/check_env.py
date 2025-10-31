"""Check current environment variables"""
import os
from dotenv import load_dotenv

load_dotenv()

print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')[:20]}..." if os.getenv('SUPABASE_KEY') else "None")
