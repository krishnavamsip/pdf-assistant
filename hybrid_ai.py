import requests
import os
import json
import hashlib
import time
from typing import Optional, List, Dict, Any
from config import Config

class HybridAI:
    def __init__(self):
        # Validate configuration
        Config.validate_config()
        
        # Initialize two Perplexity API keys
        self.api_key_1, self.api_key_2 = Config.get_api_keys()
        
        # Perplexity API endpoint
        self.api_url = "https://api.perplexity.ai/chat/completions"
        
        # Track usage for load balancing
        self.key_usage = {
            'key_1': {'requests': 0, 'last_used': 0, 'errors': 0},
            'key_2': {'requests': 0, 'last_used': 0, 'errors': 0}
        }
        
        # Rate limiting settings
        self.rate_limit_per_minute = Config.RATE_LIMIT_PER_MINUTE
        self.last_request_time = 0
        self.min_request_interval = Config.MIN_REQUEST_INTERVAL
    
    def _get_available_api_key(self) -> tuple[str, str]:
        """Get the best available API key based on usage and errors"""
        current_time = time.time()
        
        # Check if we need to wait due to rate limiting
        if current_time - self.last_request_time < self.min_request_interval:
            time.sleep(self.min_request_interval - (current_time - self.last_request_time))
        
        # If only one key is available, use it
        if not self.api_key_1 and self.api_key_2:
            return self.api_key_2, 'key_2'
        elif not self.api_key_2 and self.api_key_1:
            return self.api_key_1, 'key_1'
        elif not self.api_key_1 and not self.api_key_2:
            raise Exception("No API keys available")
        
        # If both keys are available, choose the one with fewer errors and requests
        key_1_score = self.key_usage['key_1']['requests'] + (self.key_usage['key_1']['errors'] * 10)
        key_2_score = self.key_usage['key_2']['requests'] + (self.key_usage['key_2']['errors'] * 10)
        
        if key_1_score <= key_2_score:
            return self.api_key_1, 'key_1'
        else:
            return self.api_key_2, 'key_2'
    
    def _update_usage(self, key_name: str, success: bool = True):
        """Update usage statistics for a key"""
        current_time = time.time()
        self.key_usage[key_name]['requests'] += 1
        self.key_usage[key_name]['last_used'] = current_time
        if not success:
            self.key_usage[key_name]['errors'] += 1
        self.last_request_time = current_time
    
    def _make_request_with_fallback(self, prompt: str, model: str = None) -> str:
        """Make a request with automatic fallback between keys and models"""
        if model is None:
            models_to_try = Config.FALLBACK_MODELS
        else:
            models_to_try = [model]
        
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                api_key, key_name = self._get_available_api_key()
            except Exception as e:
                raise Exception(f"No API keys available: {str(e)}")
            
            # Try different models
            for model_to_try in models_to_try:
                try:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    data = {
                        "model": model_to_try,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": Config.MAX_TOKENS,
                        "temperature": Config.TEMPERATURE
                    }
                    
                    print(f"Trying model: {model_to_try} with {key_name}")
                    response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        self._update_usage(key_name, success=True)
                        print(f"✅ Success with model: {model_to_try}")
                        return content
                    else:
                        print(f"❌ Model {model_to_try} failed with status {response.status_code}: {response.text}")
                        
                except Exception as e:
                    print(f"Error with {key_name} and model {model_to_try}: {str(e)}")
                    self._update_usage(key_name, success=False)
                    continue
            
            # If we get here, all models failed for this key
            if attempt < max_retries - 1:
                time.sleep(1)  # Brief delay before retry
                continue
            else:
                raise Exception(f"All API keys and models failed after {max_retries} attempts")
    
    def get_summary(self, text: str, progress_callback=None) -> str:
        """Generate a comprehensive summary using Perplexity"""
        # Truncate text if too long (Perplexity has token limits)
        max_chars = Config.MAX_SUMMARY_CHARS
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""
        Please provide a comprehensive, well-structured summary of the following text. 
        Organize the summary into clear sections with headers like:
        
        ## Overview
        ## Key Points  
        ## Main Features
        ## Important Details
        ## Conclusions
        
        Text to summarize:
        {text}
        
        Please ensure the summary is detailed, accurate, and maintains the key information from the original text.
        """
        
        if progress_callback:
            progress_callback(0.5)  # Indicate processing started
        
        try:
            summary = self._make_request_with_fallback(prompt)
            
            if progress_callback:
                progress_callback(1.0)  # Indicate completion
            
            return summary
        except Exception as e:
            if progress_callback:
                progress_callback(1.0)
            return f"Error generating summary: {str(e)}"
    
    def generate_mcqs(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate multiple choice questions using Perplexity"""
        # Truncate text if too long
        max_chars = Config.MAX_MCQ_CHARS
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""
        Generate {num_questions} multiple choice questions based on the following text. 
        For each question, provide:
        1. A clear, specific question
        2. Four answer options (A, B, C, D)
        3. The correct answer
        
        Format your response as a JSON array with this structure:
        [
            {{
                "question": "Question text here?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "Correct option text"
            }}
        ]
        
        Text to base questions on:
        {text}
        
        Make sure the questions test understanding of key concepts and important details from the text.
        """
        
        try:
            response = self._make_request_with_fallback(prompt)
            
            # Try to extract JSON from response
            try:
                # Find JSON array in the response
                start_idx = response.find('[')
                end_idx = response.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx]
                    questions = json.loads(json_str)
                    
                    # Validate and clean up questions
                    valid_questions = []
                    for q in questions:
                        if isinstance(q, dict) and 'question' in q and 'options' in q and 'answer' in q:
                            if len(q['options']) == 4 and q['answer'] in q['options']:
                                valid_questions.append(q)
                    
                    return valid_questions[:num_questions]
                else:
                    raise ValueError("No JSON array found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback: create simple questions if JSON parsing fails
                print(f"JSON parsing failed: {e}")
                return self._create_fallback_mcqs(text, num_questions)
                
        except Exception as e:
            print(f"Error generating MCQs: {e}")
            return self._create_fallback_mcqs(text, num_questions)
    
    def _create_fallback_mcqs(self, text: str, num_questions: int) -> List[Dict[str, Any]]:
        """Create simple fallback MCQs if Perplexity fails"""
        import re
        import random
        
        # Extract sentences and key terms
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
        key_terms = list(set(re.findall(r'\b[A-Z][a-zA-Z]+\b', text)))
        
        questions = []
        for i in range(min(num_questions, len(sentences))):
            if i < len(sentences) and key_terms:
                sentence = sentences[i]
                answer = random.choice(key_terms)
                question = sentence.replace(answer, '_____')
                
                # Create distractors
                distractors = random.sample([t for t in key_terms if t != answer], min(3, len(key_terms) - 1))
                options = distractors + [answer]
                random.shuffle(options)
                
                questions.append({
                    "question": f"Fill in the blank: {question}",
                    "options": options,
                    "answer": answer
                })
        
        return questions
    
    def answer_question(self, context: str, question: str) -> tuple[str, str]:
        """Answer a specific question based on the provided context"""
        # Truncate context if too long
        max_chars = Config.MAX_QA_CHARS
        if len(context) > max_chars:
            context = context[:max_chars] + "..."
        
        prompt = f"""
        Based on the following context, please answer the question accurately and concisely.
        If the answer cannot be found in the context, say "The answer cannot be found in the provided context."
        
        Context:
        {context}
        
        Question: {question}
        
        Please provide a clear, direct answer based only on the information in the context.
        """
        
        try:
            answer = self._make_request_with_fallback(prompt)
            return answer, context
        except Exception as e:
            return f"Error generating answer: {str(e)}", context
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics for both API keys"""
        return {
            'key_1': {
                'requests': self.key_usage['key_1']['requests'],
                'errors': self.key_usage['key_1']['errors'],
                'success_rate': (self.key_usage['key_1']['requests'] - self.key_usage['key_1']['errors']) / max(1, self.key_usage['key_1']['requests']) * 100
            },
            'key_2': {
                'requests': self.key_usage['key_2']['requests'],
                'errors': self.key_usage['key_2']['errors'],
                'success_rate': (self.key_usage['key_2']['requests'] - self.key_usage['key_2']['errors']) / max(1, self.key_usage['key_2']['requests']) * 100
            }
        } 