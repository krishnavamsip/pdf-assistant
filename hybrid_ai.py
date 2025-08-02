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
        # Split text into chunks if it's too long
        max_chars = Config.MAX_SUMMARY_CHARS
        if len(text) > max_chars:
            # Split into chunks and process each
            chunks = self._split_text_into_chunks(text, max_chars)
            
            # Limit to maximum 10 chunks to avoid rate limits
            if len(chunks) > 10:
                # Combine chunks to reduce total number
                combined_chunks = self._combine_chunks_to_limit(chunks, 10)
                chunks = combined_chunks
            
            summaries = []
            
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress_percent = (i + 1) / len(chunks)
                    progress_callback(progress_percent * 0.8, f"Processing chunk {i+1}/{len(chunks)}...")
                
                # Add delay between requests to respect rate limits
                if i > 0:
                    time.sleep(Config.MIN_REQUEST_INTERVAL)
                
                chunk_summary = self._process_chunk_summary(chunk, i+1, len(chunks))
                summaries.append(chunk_summary)
            
            # Combine summaries
            if progress_callback:
                progress_callback(0.9, "Combining summaries...")
            
            combined_summary = self._combine_summaries(summaries)
            
            if progress_callback:
                progress_callback(1.0, "✅ Summary complete!")
            
            return combined_summary
        else:
            # Process single chunk
            if progress_callback:
                progress_callback(0.5, "Processing text...")
            
            summary = self._process_chunk_summary(text, 1, 1)
            
            if progress_callback:
                progress_callback(1.0, "✅ Summary complete!")
            
            return summary
    
    def _split_text_into_chunks(self, text: str, max_chars: int) -> list:
        """Split text into chunks, trying to break at chapter boundaries"""
        chunks = []
        current_chunk = ""
        
        # Split by lines to preserve structure
        lines = text.split('\n')
        
        for line in lines:
            # Check if this line would exceed the limit
            if len(current_chunk + line) > max_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If we only have one chunk, try to split it more intelligently
        if len(chunks) == 1 and len(text) > max_chars:
            # Try to split at chapter boundaries
            chapter_splits = self._split_at_chapters(text, max_chars)
            if len(chapter_splits) > 1:
                return chapter_splits
        
        return chunks
    
    def _split_at_chapters(self, text: str, max_chars: int) -> list:
        """Split text at chapter boundaries when possible"""
        import re
        
        # Look for chapter patterns
        chapter_patterns = [
            r'Chapter\s+\d+[:\s]',  # Chapter 1:, Chapter 2, etc.
            r'CHAPTER\s+\d+[:\s]',  # CHAPTER 1:, CHAPTER 2, etc.
            r'\d+\.\s+[A-Z]',       # 1. Title, 2. Title, etc.
            r'Section\s+\d+[:\s]',  # Section 1:, Section 2, etc.
        ]
        
        # Find all chapter positions
        chapter_positions = []
        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            chapter_positions.extend([match.start() for match in matches])
        
        chapter_positions.sort()
        
        if not chapter_positions:
            # No chapters found, split by size
            return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
        
        # Split at chapter boundaries
        chunks = []
        start = 0
        
        for pos in chapter_positions:
            if pos - start > max_chars:
                # Current chunk is too big, split it
                chunks.append(text[start:start+max_chars])
                start = start + max_chars
            elif pos - start > 0:
                # Add chunk up to this chapter
                chunks.append(text[start:pos])
                start = pos
        
        # Add the last chunk
        if start < len(text):
            chunks.append(text[start:])
        
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def _combine_chunks_to_limit(self, chunks: list, max_chunks: int) -> list:
        """Combine chunks to limit the total number"""
        if len(chunks) <= max_chunks:
            return chunks
        
        # Calculate how many chunks to combine
        combine_factor = len(chunks) // max_chunks + 1
        
        combined_chunks = []
        for i in range(0, len(chunks), combine_factor):
            combined_text = "\n\n".join(chunks[i:i+combine_factor])
            combined_chunks.append(combined_text)
        
        return combined_chunks
    
    def _process_chunk_summary(self, text: str, chunk_num: int, total_chunks: int) -> str:
        """Process a single chunk of text"""
        prompt = f"""
        This is chunk {chunk_num} of {total_chunks} from a larger document. 
        Please provide a comprehensive summary of this section.
        
        IMPORTANT: Skip author information, preface, acknowledgments, and focus ONLY on the actual content.
        
        Structure your summary like this:
        
        ## Section {chunk_num}: [Section Title or Chapter Title]
        - **Main Topics**: [List the main topics covered in this section]
        - **Key Concepts**: [Important concepts, definitions, or theories introduced]
        - **Key Points**: [3-5 most important points from this section]
        
        If you can identify chapter titles or section headers, use them. Otherwise, describe the content clearly.
        
        Text to summarize:
        {text}
        
        Focus on the actual educational content, not metadata about the book or author.
        """
        
        try:
            return self._make_request_with_fallback(prompt)
        except Exception as e:
            # If it's a rate limit error, provide helpful message
            if "rate limit" in str(e).lower() or "429" in str(e):
                return f"Rate limit reached while processing chunk {chunk_num}. Please wait a moment and try again."
            else:
                return f"Error processing chunk {chunk_num}: {str(e)}"
    
    def _combine_summaries(self, summaries: list) -> str:
        """Combine multiple chunk summaries into a final summary"""
        combined_text = "\n\n".join(summaries)
        
        prompt = f"""
        Please combine and organize the following summaries into a comprehensive, well-structured summary.
        
        IMPORTANT: 
        1. Remove any duplicate information
        2. Organize by chapters or major sections
        3. Create a coherent flow
        4. Add an overall summary at the end
        
        Structure the final summary like this:
        
        ## Chapter 1: [Chapter Title]
        - **Main Topics**: [List the main topics covered in this chapter]
        - **Key Concepts**: [Important concepts, definitions, or theories introduced]
        - **Key Points**: [3-5 most important points from this chapter]
        
        [Continue for all chapters...]
        
        ## Overall Summary
        - **Total Chapters**: [Number of chapters covered]
        - **Main Themes**: [Recurring themes across chapters]
        - **Key Takeaways**: [Most important learnings from the entire book]
        
        Summaries to combine:
        {combined_text}
        """
        
        try:
            return self._make_request_with_fallback(prompt)
        except Exception as e:
            # If combining fails, just return the summaries concatenated
            return f"## Combined Summary\n\n" + "\n\n".join(summaries)
    
    def generate_mcqs(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate multiple choice questions using Perplexity"""
        # Truncate text if too long
        max_chars = Config.MAX_MCQ_CHARS
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""
        Generate {num_questions} multiple choice questions based on the following text. 
        
        IMPORTANT REQUIREMENTS:
        1. Focus on MAIN CONTENT, KEY CONCEPTS, and IMPORTANT TOPICS from the actual chapters
        2. AVOID questions about author, preface, acknowledgments, or publication details
        3. Create questions that test understanding of the actual educational material
        4. Distribute questions across different chapters/sections (beginning, middle, end)
        5. Include questions about definitions, concepts, processes, and key facts from the content
        6. Make sure questions cover different difficulty levels (basic concepts to advanced topics)
        
        Question Types to Include:
        - Definition questions (What is X?)
        - Concept understanding (How does X work?)
        - Application questions (Which of the following is an example of X?)
        - Comparison questions (What is the difference between X and Y?)
        - Process questions (What are the steps in X?)
        
        For each question, provide:
        1. A clear, specific question about the content
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
        
        Make sure the questions test understanding of key concepts and important details from the actual educational content, not metadata.
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