import re

def parse_script_generic(script_text):
    dialogues = []
    current_speaker = None
    current_gender = "unknown"
    current_text = []

    # Regex that captures "speaker, GENDER: gender" up to the first colon
    pattern = r'^([\w\'. \s-]+), GENDER: (\w+):\s*(.*)$'

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
            # Save previous speaker's dialogue
            if current_speaker is not None and current_text:
                dialogues.append({
                    "speaker": current_speaker,
                    "gender": current_gender,
                    "dialogue": "\n".join(current_text)
                })

            # Start new speaker
            current_speaker = match.group(1).strip()
            current_gender = match.group(2).strip()
            current_text = [match.group(3).strip()]
            i += 1
        else:
            # Add lines to current speaker until a new speaker appears
            if current_speaker is not None:
                current_text.append(line)
            i += 1

    # Add last speaker's dialogue
    if current_speaker is not None and current_text:
        dialogues.append({
            "speaker": current_speaker,
            "gender": current_gender,
            "dialogue": "\n".join(current_text)
        })

    return dialogues
