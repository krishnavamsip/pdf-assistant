import os
import time
import uuid
from supabase import create_client
from dotenv import load_dotenv
from config import Config

load_dotenv()

# Get Supabase configuration from Config class
url = Config.SUPABASE_URL
key = Config.SUPABASE_SERVICE_KEY
bucket_name = Config.SUPABASE_BUCKET_NAME

if not url or not key or not url.startswith("https://") or not url.endswith(".supabase.co"):
    raise ValueError(
        "Supabase configuration error: Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file. "
        "SUPABASE_URL should start with 'https://' and end with '.supabase.co'."
    )

if not bucket_name:
    raise ValueError(
        "Supabase configuration error: Please set SUPABASE_BUCKET_NAME in your .env file."
    )

supabase = create_client(url, key)

def upload_pdf_to_supabase(file, user_id=None):
    """
    Upload a PDF file to Supabase with a unique filename.
    
    Args:
        file: The file object to upload
        user_id: Optional user identifier to include in the filename
    
    Returns:
        tuple: (public_url, unique_filename)
    """
    bucket = bucket_name
    
    # Generate a unique filename to prevent conflicts
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]  # First 8 characters of UUID
    user_prefix = f"user_{user_id}_" if user_id else "user_"
    
    # Get the original filename and extension
    original_name = file.name
    name_parts = original_name.rsplit('.', 1)
    base_name = name_parts[0] if len(name_parts) > 1 else original_name
    extension = f".{name_parts[1]}" if len(name_parts) > 1 else ""
    
    # Create unique filename: user_prefix + original_name + timestamp + unique_id + extension
    unique_filename = f"{user_prefix}{base_name}_{timestamp}_{unique_id}{extension}"
    
    file_bytes = file.read()
    supabase.storage.from_(bucket).upload(unique_filename, file_bytes, {"content-type": "application/pdf"})
    public_url = supabase.storage.from_(bucket).get_public_url(unique_filename)
    
    return public_url, unique_filename

def delete_pdf_from_supabase(filename):
    bucket = bucket_name
    supabase.storage.from_(bucket).remove(filename)