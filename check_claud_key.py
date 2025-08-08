import requests

API_KEY = "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"

# Step 1: Minimal call to check key validity
headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01"
}

test_payload = {
    "model": "claude-3-haiku-20240307",  # public model
    "max_tokens": 10,
    "messages": [
        {"role": "user", "content": "Hello Claude!"}
    ]
}

print("=== Step 1: Testing key validity ===")
res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=test_payload)
print("Status:", res.status_code)
print("Response:", res.text)

# Step 2: Try listing models (if supported by your account)
print("\n=== Step 2: Checking available models ===")
models_res = requests.get("https://api.anthropic.com/v1/models", headers=headers)
print("Status:", models_res.status_code)
print("Response:", models_res.text)
