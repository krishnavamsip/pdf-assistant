# PDF Assistant - Deployment Guide

## Option 1: Streamlit Cloud (Recommended)

### Step 1: Prepare Your Repository
1. Create a GitHub repository
2. Push your code to GitHub (make sure `.env` is in `.gitignore`)

### Step 2: Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository and main branch
5. Set the main file path to: `main.py`
6. Click "Deploy"

### Step 3: Configure Environment Variables
In Streamlit Cloud dashboard:
1. Go to your app settings
2. Add these secrets:
```
PERPLEXITY_API_KEY_1 = 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
PERPLEXITY_API_KEY_2 = your_second_key_here
SUPABASE_URL = your_supabase_url
SUPABASE_SERVICE_KEY = your_supabase_service_key
SUPABASE_BUCKET_NAME = your_bucket_name
```

## Option 2: Render (Alternative)

### Step 1: Create render.yaml
```yaml
services:
  - type: web
    name: pdf-assistant
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run main.py --server.port $PORT --server.address 0.0.0.0
    envVars:
      - key: PERPLEXITY_API_KEY_1
        value: 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
      - key: PERPLEXITY_API_KEY_2
        value: your_second_key_here
      - key: SUPABASE_URL
        value: your_supabase_url
      - key: SUPABASE_SERVICE_KEY
        value: your_supabase_service_key
      - key: SUPABASE_BUCKET_NAME
        value: your_bucket_name
```

### Step 2: Deploy to Render
1. Go to [render.com](https://render.com)
2. Connect your GitHub repository
3. Create a new Web Service
4. Select your repository
5. Render will auto-detect the configuration

## Important Notes

⚠️ **Security**: Never commit your `.env` file to version control
✅ **Environment Variables**: Always use the platform's secret management
🌐 **Public Access**: Your app will be publicly accessible
📊 **Usage Limits**: Free tiers have usage limitations

## Troubleshooting

- **Import Errors**: Make sure all dependencies are in `requirements.txt`
- **Environment Variables**: Double-check all API keys and URLs
- **File Uploads**: Ensure Supabase bucket permissions are correct 