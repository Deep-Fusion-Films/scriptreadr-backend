import re 

def parse_script_generic(script_text):
        dialogues = []
        current_speaker = None
        current_text = []
        
        # Regex that captures "speaker name" up to the first colon
        pattern = r'^([\w\'. \s-]+):\s*(.*)$'
        
        lines = script_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip page break markers
            if '[PAGE_BREAK]' in line:
                i += 1
                continue
                
            match = re.match(pattern, line)
            
            if match:
                # If we had a previous speaker, save their dialogue
                if current_speaker is not None and current_text:
                    dialogues.append({
                        "speaker": current_speaker,
                        "text": "\n".join(current_text)
                    })
                # Start new speaker
                current_speaker = match.group(1).strip()
                # Start their text with everything after the colon
                current_text = [line[line.find(':') + 1:].lstrip()]
                i += 1
            else:
                # If we have a current speaker, keep adding lines until we find a new speaker
                if current_speaker is not None:
                    # Look ahead to see if next non-empty line is a new speaker
                    is_last_line = True
                    for next_line in lines[i+1:]:
                        if next_line.strip() and '[PAGE_BREAK]' not in next_line:  # Found next non-empty, non-page-marker line
                            is_last_line = False
                            if re.match(pattern, next_line):  # It's a new speaker
                                current_text.append(line)
                                i += 1
                                break
                            else:  # Not a new speaker, keep collecting
                                current_text.append(line)
                                i += 1
                                break
                    if is_last_line:  # No more non-empty lines
                        current_text.append(line)
                        i += 1
                else:
                    i += 1  # Skip lines before first speaker
        
        # Add the last speaker's text
        if current_speaker is not None and current_text:
            dialogues.append({
                "speaker": current_speaker,
                "text": "\n".join(current_text)
            })
        
        return dialogues
