import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the PDF Assistant application"""
    
    # Perplexity API Configuration
    PERPLEXITY_API_KEY_1 = os.getenv('PERPLEXITY_API_KEY_1')
    PERPLEXITY_API_KEY_2 = os.getenv('PERPLEXITY_API_KEY_2')
    
    # Check if we have at least one API key
    @classmethod
    def has_api_keys(cls):
        """Check if at least one API key is available"""
        return bool(os.getenv('PERPLEXITY_API_KEY_1') or os.getenv('PERPLEXITY_API_KEY_2'))
    
    # Perplexity Model Settings
    DEFAULT_MODEL = "sonar"
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    
    # Alternative models to try if the default fails
    FALLBACK_MODELS = [
        # Correct Perplexity model names from documentation
        "sonar",
        "sonar reasoning",
        "sonar deep research"
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = 20  # Reduced to be more conservative
    MIN_REQUEST_INTERVAL = 60 / RATE_LIMIT_PER_MINUTE  # seconds between requests
    
    # Text Processing Limits
    MAX_SUMMARY_CHARS = 100000  # Much higher for full textbook coverage
    MAX_MCQ_CHARS = 50000      # Higher for better coverage
    MAX_QA_CHARS = 30000       # Higher for better coverage
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
    SUPABASE_BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME')
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        errors = []
        
        if not cls.has_api_keys():
            errors.append("At least one PERPLEXITY_API_KEY must be set (PERPLEXITY_API_KEY_1 or PERPLEXITY_API_KEY_2)")
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
        
        return True
    
    @classmethod
    def get_api_keys(cls):
        """Get both API keys as a tuple"""
        return os.getenv('PERPLEXITY_API_KEY_1'), os.getenv('PERPLEXITY_API_KEY_2') 