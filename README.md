# PDF Assistant with Perplexity AI

A Streamlit application that uses Perplexity AI with dual API keys for PDF processing, summarization, MCQ generation, and question answering.

## Features

- **Dual API Key Support**: Uses two Perplexity API keys with automatic load balancing and fallback
- **PDF Processing**: Upload and extract text from PDFs
- **AI-Powered Summarization**: Generate comprehensive, structured summaries
- **Multiple Choice Questions**: Create quizzes based on PDF content
- **Question Answering**: Ask specific questions about PDF content
- **Cloud Storage**: Secure file storage with Supabase
- **Usage Statistics**: Monitor API key usage and success rates

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with your API keys:

```env
# Perplexity API Keys - Get your keys from https://www.perplexity.ai/settings/api
# You can start with just one key, add the second one later for better reliability
PERPLEXITY_API_KEY_1=your_first_perplexity_api_key_here
PERPLEXITY_API_KEY_2=your_second_perplexity_api_key_here

# Supabase Configuration (for file storage)
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_KEY=your_supabase_service_key_here
SUPABASE_BUCKET_NAME=your_bucket_name_here
```

### 3. Get Perplexity API Keys

1. Go to [Perplexity AI Settings](https://www.perplexity.ai/settings/api)
2. Create one or two API keys (you can start with one and add the second later)
3. Add them to your `.env` file

### 4. Run the Application

```bash
streamlit run main.py
```

## How It Works

### Dual API Key System

The application supports one or two Perplexity API keys with intelligent load balancing:

- **Single Key Support**: Works with just one API key
- **Load Balancing**: When two keys are available, requests are distributed based on usage and error rates
- **Automatic Fallback**: If one key fails, the system automatically tries the other
- **Rate Limiting**: Built-in rate limiting to respect Perplexity's API limits
- **Usage Tracking**: Monitor request counts, errors, and success rates for each key

### AI Features

- **Summarization**: Generates structured summaries with clear sections
- **MCQ Generation**: Creates multiple choice questions with JSON parsing and fallback
- **Question Answering**: Provides accurate answers based on PDF context

## API Usage Statistics

The application includes a sidebar option to view real-time API usage statistics:
- Request counts for each key
- Error rates and success percentages
- Automatic monitoring of key performance

## Error Handling

- Graceful fallback between API keys
- Fallback MCQ generation if JSON parsing fails
- Comprehensive error messages for debugging
- Automatic retry logic for failed requests

## Requirements

- Python 3.7+
- Perplexity API keys
- Supabase account (for file storage)
- Internet connection for API calls

## Troubleshooting

1. **API Key Errors**: Ensure both API keys are valid and have sufficient credits
2. **Rate Limiting**: The app includes built-in rate limiting, but you may need to adjust if you hit limits
3. **JSON Parsing**: MCQ generation includes fallback logic if Perplexity doesn't return valid JSON
4. **File Upload**: Ensure Supabase credentials are correct for file storage functionality
