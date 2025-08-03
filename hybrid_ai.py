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
                    print(f"API Key (first 10 chars): {api_key[:10]}...")
                    print(f"Request data: {data}")
                    
                    response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
                    
                    print(f"Response status: {response.status_code}")
                    print(f"Response headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        self._update_usage(key_name, success=True)
                        print(f"✅ Success with model: {model_to_try}")
                        return content
                    else:
                        print(f"❌ Model {model_to_try} failed with status {response.status_code}")
                        print(f"Response text: {response.text}")
                        
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
        print(f"📊 Summary generation: Text length = {len(text):,} characters")
        print(f"📊 Summary generation: Max chars = {Config.MAX_SUMMARY_CHARS:,}")
        
        # Split text into chunks if it's too long
        max_chars = Config.MAX_SUMMARY_CHARS
        if len(text) > max_chars:
            # Split into chunks and process each
            chunks = self._split_text_into_chunks(text, max_chars)
            print(f"📊 Summary generation: Created {len(chunks)} initial chunks")
            
            # Limit to maximum 15 chunks for better coverage
            if len(chunks) > 15:
                # Combine chunks to reduce total number
                combined_chunks = self._combine_chunks_to_limit(chunks, 15)
                chunks = combined_chunks
                print(f"📊 Summary generation: Combined into {len(chunks)} chunks")
            
            print(f"📊 Summary generation: Processing {len(chunks)} chunks")
            
            summaries = []
            api_failures = 0
            
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress_percent = (i + 1) / len(chunks)
                    progress_callback(progress_percent * 0.8, f"Processing chunk {i+1}/{len(chunks)}...")
                
                # Add delay between requests to respect rate limits
                if i > 0:
                    time.sleep(Config.MIN_REQUEST_INTERVAL)
                
                chunk_summary = self._process_chunk_summary(chunk, i+1, len(chunks))
                
                # Check if API failed
                if chunk_summary.startswith("Error processing chunk"):
                    api_failures += 1
                    # Use fallback summary for this chunk
                    chunk_summary = self._create_fallback_summary(chunk, i+1, len(chunks))
                
                summaries.append(chunk_summary)
            
            # If too many API failures, use fallback for entire document
            if api_failures > len(chunks) * 0.5:  # More than 50% failed
                if progress_callback:
                    progress_callback(0.9, "Using fallback summary generation...")
                return self._create_fallback_summary(text, 1, 1)
            
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
            
            # If API failed, use fallback
            if summary.startswith("Error processing chunk"):
                summary = self._create_fallback_summary(text, 1, 1)
            
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
    
    def _create_fallback_summary(self, text: str, chunk_num: int, total_chunks: int) -> str:
        """Create a fallback summary without using the API"""
        import re
        
        # Extract chapter titles and key information
        lines = text.split('\n')
        chapter_titles = []
        key_sentences = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for chapter titles
            if re.match(r'^Chapter\s+\d+', line, re.IGNORECASE):
                chapter_titles.append(line)
            elif re.match(r'^\d+\.\s+[A-Z]', line):
                chapter_titles.append(line)
            
            # Extract sentences with key medical terms
            if len(line) > 20 and any(term in line.lower() for term in ['definition', 'diagnosis', 'treatment', 'symptoms', 'causes', 'risk', 'management']):
                key_sentences.append(line)
        
        # Create a structured summary
        summary_parts = []
        
        if chapter_titles:
            summary_parts.append(f"## Chapter {chunk_num}: {chapter_titles[0] if chapter_titles else 'Content Section'}")
        else:
            summary_parts.append(f"## Section {chunk_num}: Content Overview")
        
        # Add key points from important sentences
        if key_sentences:
            summary_parts.append("### Key Points:")
            for i, sentence in enumerate(key_sentences[:5], 1):  # Limit to 5 key points
                summary_parts.append(f"{i}. {sentence}")
        
        # Add general content overview
        words = text.split()
        if len(words) > 100:
            summary_parts.append(f"\n### Content Overview:")
            summary_parts.append(f"This section contains approximately {len(words)} words covering medical content.")
            summary_parts.append("The text includes definitions, diagnostic criteria, treatment approaches, and clinical guidelines.")
        
        return "\n\n".join(summary_parts)
    
    def _process_chunk_summary(self, text: str, chunk_num: int, total_chunks: int) -> str:
        """Process a single chunk of text"""
        prompt = f"""
        This is chunk {chunk_num} of {total_chunks} from a medical textbook. 
        Please provide a comprehensive, well-structured summary of this section.
        
        CRITICAL REQUIREMENTS:
        1. Focus EXCLUSIVELY on the actual educational content and medical concepts
        2. Skip any author information, preface, acknowledgments, or metadata
        3. Organize information clearly and logically
        4. Include important definitions, concepts, and clinical information
        5. Make the summary educational and useful for medical students
        
        Structure your summary like this:
        
        ## Chapter/Section: [Title]
        
        ### Main Topics Covered:
        - [List the main topics and subtopics]
        
        ### Key Concepts:
        - [Important definitions and concepts]
        - [Clinical principles and guidelines]
        
        ### Important Points:
        1. [Key point 1]
        2. [Key point 2]
        3. [Key point 3]
        4. [Key point 4]
        5. [Key point 5]
        
        ### Clinical Applications:
        - [How this information applies in clinical practice]
        
        Text to summarize:
        {text}
        
        Remember: This is medical educational content. Focus on making it clear, accurate, and useful for learning.
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
        Please combine and organize the following summaries into a comprehensive, well-structured medical textbook summary.
        
        CRITICAL REQUIREMENTS:
        1. Remove any duplicate information
        2. Organize by chapters in logical order
        3. Create a coherent, educational flow
        4. Focus on medical concepts and clinical applications
        5. Make it useful for medical students and professionals
        
        Structure the final summary like this:
        
        # Medical Textbook Summary
        
        ## Chapter 1: [Chapter Title]
        
        ### Main Topics Covered:
        - [List the main topics and subtopics]
        
        ### Key Concepts:
        - [Important definitions and concepts]
        - [Clinical principles and guidelines]
        
        ### Important Points:
        1. [Key point 1]
        2. [Key point 2]
        3. [Key point 3]
        4. [Key point 4]
        5. [Key point 5]
        
        ### Clinical Applications:
        - [How this information applies in clinical practice]
        
        [Continue for all chapters...]
        
        ## Overall Summary
        
        ### Total Chapters Covered: [Number]
        
        ### Main Themes:
        - [Recurring themes across chapters]
        
        ### Key Takeaways:
        1. [Most important learning 1]
        2. [Most important learning 2]
        3. [Most important learning 3]
        
        ### Clinical Relevance:
        - [How this knowledge applies in medical practice]
        
        Summaries to combine:
        {combined_text}
        
        Remember: This is medical educational content. Make it clear, accurate, and clinically relevant.
        """
        
        try:
            return self._make_request_with_fallback(prompt)
        except Exception as e:
            # If combining fails, just return the summaries concatenated
            return f"## Combined Summary\n\n" + "\n\n".join(summaries)
    
    def generate_mcqs(self, text: str, num_questions: int = 5, regenerate_count: int = 0) -> List[Dict[str, Any]]:
        """Generate multiple choice questions using Perplexity"""
        import random
        
        # Smart text sampling to avoid preface/front matter
        max_chars = Config.MAX_MCQ_CHARS
        
        if len(text) > max_chars:
            # Sample from different parts of the document with regeneration offset
            text = self._sample_text_for_mcqs(text, max_chars, regenerate_count)
        
        # Add randomization seed to get different questions each time
        random_seed = random.randint(1, 10000) + regenerate_count * 1000
        
        prompt = f"""
        Generate {num_questions} multiple choice questions based on the following text. 
        
        CRITICAL REQUIREMENTS:
        1. Focus EXCLUSIVELY on MAIN CONTENT, KEY CONCEPTS, and IMPORTANT TOPICS from the actual educational material
        2. STRICTLY AVOID questions about author, preface, acknowledgments, publication details, or front matter
        3. Create questions that test understanding of the actual subject matter and educational content
        4. Distribute questions across different sections (beginning, middle, end) of the actual content
        5. Include questions about definitions, concepts, processes, and key facts from the main content
        6. Make sure questions cover different difficulty levels (basic concepts to advanced topics)
        7. If the text contains preface/acknowledgments, IGNORE those sections completely
        8. Focus on the substantive educational content only
        9. Use randomization seed {random_seed} to ensure variety in question selection
        10. DO NOT ask about the author, book title, publisher, or any metadata
        11. ONLY ask about the actual subject matter and educational concepts
        
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
    
    def _sample_text_for_mcqs(self, text: str, max_chars: int, regenerate_count: int = 0) -> str:
        """Smart sampling to get content from different parts of the document"""
        import re
        import random
        
        # Set random seed based on regenerate count to get different samples
        random.seed(42 + regenerate_count * 10)  # Use consistent but different seed
        
        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Filter out preface/acknowledgments content more aggressively
        filtered_paragraphs = []
        preface_keywords = ['preface', 'acknowledgment', 'acknowledgement', 'foreword', 'introduction', 
                           'copyright', 'publisher', 'author', 'editor', 'dedication', 'table of contents']
        
        for paragraph in paragraphs:
            # Skip paragraphs that contain preface keywords
            if any(keyword in paragraph.lower() for keyword in preface_keywords):
                continue
            # Skip very short paragraphs (likely headers)
            if len(paragraph) < 50:
                continue
            # Skip paragraphs that are mostly numbers or special characters
            if len(re.findall(r'[a-zA-Z]', paragraph)) < len(paragraph) * 0.3:
                continue
            filtered_paragraphs.append(paragraph)
        
        if len(filtered_paragraphs) <= 3:
            # If few paragraphs, take from middle of original text
            start_idx = len(text) // 3  # Start from 33% into the text
            end_idx = start_idx + max_chars
            return text[start_idx:end_idx]
        
        # Skip first 30% of filtered paragraphs to avoid any remaining preface content
        skip_count = max(3, len(filtered_paragraphs) // 3)
        content_paragraphs = filtered_paragraphs[skip_count:]
        
        if not content_paragraphs:
            # If no content paragraphs, fall back to middle of original text
            start_idx = len(text) // 2
            end_idx = start_idx + max_chars
            return text[start_idx:end_idx]
        
        # Randomly sample from different sections
        sampled_paragraphs = []
        
        # Sample from different sections based on regenerate count
        # This ensures we get different chapters each time
        section_size = len(content_paragraphs) // 4  # Divide into 4 sections
        
        # Choose different sections based on regenerate count
        section_choices = [
            (section_size, 2 * section_size),      # Section 1 (25-50%)
            (2 * section_size, 3 * section_size),  # Section 2 (50-75%)
            (3 * section_size, len(content_paragraphs)),  # Section 3 (75-100%)
            (0, section_size)                      # Section 4 (0-25%)
        ]
        
        # Use regenerate count to cycle through sections
        section_idx = regenerate_count % len(section_choices)
        start_idx, end_idx = section_choices[section_idx]
        
        section_paragraphs = content_paragraphs[start_idx:end_idx]
        if section_paragraphs:
            # Randomly select paragraphs from this section
            step = max(1, len(section_paragraphs) // 6)
            for i in range(0, len(section_paragraphs), step):
                if len(sampled_paragraphs) < 5:  # Limit to 5 paragraphs
                    sampled_paragraphs.append(section_paragraphs[i])
        
        # If we need more content, sample from a different section
        if len(' '.join(sampled_paragraphs)) < max_chars // 2:
            # Choose a different section for additional content
            alt_section_idx = (regenerate_count + 1) % len(section_choices)
            alt_start_idx, alt_end_idx = section_choices[alt_section_idx]
            
            alt_section_paragraphs = content_paragraphs[alt_start_idx:alt_end_idx]
            if alt_section_paragraphs:
                # Randomly select from alternative section
                random.shuffle(alt_section_paragraphs)
                for paragraph in alt_section_paragraphs[:3]:  # Take up to 3 more
                    if len(' '.join(sampled_paragraphs)) + len(paragraph) < max_chars:
                        sampled_paragraphs.append(paragraph)
        
        # Combine sampled paragraphs
        sampled_text = '\n\n'.join(sampled_paragraphs)
        
        # If still too short, add some from the beginning of content (not preface)
        if len(sampled_text) < max_chars // 2 and len(content_paragraphs) > 0:
            early_content = content_paragraphs[:2]  # Take first 2 content paragraphs
            sampled_text = '\n\n'.join(early_content) + '\n\n' + sampled_text
        
        # Truncate if still too long
        if len(sampled_text) > max_chars:
            sampled_text = sampled_text[:max_chars] + "..."
        
        return sampled_text
    
    def detect_chapters(self, text: str) -> List[Dict[str, Any]]:
        """Detect chapters in the text and return their positions"""
        import re
        
        try:
            chapters = []
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Look for chapter patterns
                chapter_match = None
                
                try:
                    # Pattern 1: "Chapter 1: Title" or "CHAPTER 1: Title"
                    match = re.match(r'^(?:Chapter|CHAPTER)\s+(\d+)[:\s]+(.+)$', line, re.IGNORECASE)
                    if match:
                        chapter_match = {
                            'number': int(match.group(1)),
                            'title': match.group(2).strip(),
                            'line_number': i,
                            'full_line': line
                        }
                    
                    # Pattern 2: "1. Title" or "1 Title"
                    if not chapter_match:
                        match = re.match(r'^(\d+)[\.\s]+([A-Z][^.]*)$', line)
                        if match:
                            chapter_match = {
                                'number': int(match.group(1)),
                                'title': match.group(2).strip(),
                                'line_number': i,
                                'full_line': line
                            }
                    
                    # Pattern 3: "Section 1: Title"
                    if not chapter_match:
                        match = re.match(r'^(?:Section|SECTION)\s+(\d+)[:\s]+(.+)$', line, re.IGNORECASE)
                        if match:
                            chapter_match = {
                                'number': int(match.group(1)),
                                'title': match.group(2).strip(),
                                'line_number': i,
                                'full_line': line
                            }
                    
                    if chapter_match:
                        chapters.append(chapter_match)
                        
                except Exception as e:
                    # Skip this line if there's an error parsing it
                    continue
            
            # Sort by chapter number
            chapters.sort(key=lambda x: x['number'])
            
            # Estimate page ranges (rough approximation)
            total_lines = len(lines)
            for i, chapter in enumerate(chapters):
                if i == 0:
                    chapter['start_page'] = 1
                else:
                    # Estimate start page based on line position
                    chapter['start_page'] = max(1, (chapter['line_number'] * 100) // total_lines)
                
                if i == len(chapters) - 1:
                    chapter['end_page'] = "end"
                else:
                    # Estimate end page based on next chapter position
                    next_chapter = chapters[i + 1]
                    chapter['end_page'] = max(1, (next_chapter['line_number'] * 100) // total_lines)
            
            return chapters
            
        except Exception as e:
            # Return empty list if there's any error
            return []
    
    def extract_chapter_text(self, full_text: str, chapter_data: Dict[str, Any]) -> str:
        """Extract text for a specific chapter"""
        try:
            import re
            lines = full_text.split('\n')
            start_line = chapter_data['line_number']
            
            # Find the end of this chapter (start of next chapter or end of text)
            end_line = len(lines)
            
            # Look for the next chapter
            for i in range(start_line + 1, len(lines)):
                line = lines[i].strip()
                if line and any(pattern in line for pattern in ['Chapter', 'CHAPTER', 'Section', 'SECTION']):
                    # Check if it's a new chapter number
                    if re.match(r'^(?:Chapter|CHAPTER|Section|SECTION)\s+\d+', line, re.IGNORECASE):
                        end_line = i
                        break
                    elif re.match(r'^\d+[\.\s]+[A-Z]', line):
                        end_line = i
                        break
            
            # Extract the chapter text
            chapter_lines = lines[start_line:end_line]
            chapter_text = '\n'.join(chapter_lines)
            
            return chapter_text
            
        except Exception as e:
            # Return a safe fallback
            return f"Error extracting chapter text: {str(e)}"
    
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