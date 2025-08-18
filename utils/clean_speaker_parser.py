import re

def clean_speaker_voices(input_dict):
    """
    Returns a new dictionary with all non-alphanumeric characters
    removed from the keys, keeping the values intact.
    """
    cleaned_dict = {}
    for key, value in input_dict.items():
        cleaned_key = re.sub(r'[^A-Za-z0-9]', '', key)
        cleaned_dict[cleaned_key] = value
    return cleaned_dict
            