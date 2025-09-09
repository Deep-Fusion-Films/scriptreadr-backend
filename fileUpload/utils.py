import re
import requests
from django.conf import settings

def chunk_script_text(text, chunk_size=5000):
        """
        Break script into intelligent chunks for AI processing.
        Priority order for break points:
        1. Lines starting with INT., EXT., SCENE or [PAGE_BREAK] markers
        2. Double line breaks
        3. Single line breaks (last resort)
        """
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_word_count = 0
        
        def add_chunk():
            if current_chunk:
                chunk_text = '\n'.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                current_chunk.clear()
                current_word_count = 0
        
        def count_words(text):
            return len(text.split())
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_word_count = count_words(line)
            
            # Check if we should break here (priority break points)
            should_break = False
            
            # Check for scene headers or page breaks
            if re.match(r'^(INT\.|EXT\.|SCENE|.*\[PAGE_BREAK\])', line.strip(), re.IGNORECASE):
                if current_chunk and current_word_count >= chunk_size * 0.7:  # At least 70% of target
                    should_break = True
            
            # If adding this line would exceed chunk size significantly
            if current_word_count + line_word_count > chunk_size * 1.3:  # 130% of target
                should_break = True
            
            if should_break and current_chunk:
                add_chunk()
            
            # Add current line to chunk
            current_chunk.append(line)
            current_word_count += line_word_count
            
            # Look ahead for double line breaks if we're near target size
            if current_word_count >= chunk_size:
                # Look for next double line break
                double_break_found = False
                for j in range(i + 1, min(i + 20, len(lines))):  # Look ahead up to 20 lines
                    if j < len(lines) - 1 and lines[j].strip() == "" and lines[j + 1].strip() == "":
                        # Found double break, add lines up to it
                        for k in range(i + 1, j + 2):
                            if k < len(lines):
                                current_chunk.append(lines[k])
                        i = j + 1
                        add_chunk()
                        double_break_found = True
                        break
                
                if not double_break_found:
                    # Look for single line break as fallback
                    for j in range(i + 1, min(i + 10, len(lines))):  # Look ahead up to 10 lines
                        if lines[j].strip() == "":
                            # Found single break
                            for k in range(i + 1, j + 1):
                                if k < len(lines):
                                    current_chunk.append(lines[k])
                            i = j
                            add_chunk()
                            break
            
            i += 1
        
        # Add final chunk
        add_chunk()
        
        return chunks
    
    
 

def call_claude_api(prompt, text_chunk):
    """
    Call Claude API to format a script chunk.
    
    Args:
        prompt (str): The instruction or prompt to Claude.
        text_chunk (str): The text to be formatted.
        claude_api_key (str): Your Claude API key.
    
    Returns:
        str | None: The formatted text or None if an error occurred.
    """
    headers = {
        "Content-Type":"application/json",
        "x-api-key":settings.CLAUD_API_KEY,  
        "anthropic-version": "2023-06-01"
    }

#-20241022
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8191,
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}\n\n{text_chunk}"
            }
        ]
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"].strip()
        else:
            print(f"Claude API Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"Exception calling Claude API: {e}")
        return None
    
    
    