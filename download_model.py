import os
import ssl
import sys
import urllib.request

model_dir = os.path.join(os.path.dirname(__file__), "llm", "models")
os.makedirs(model_dir, exist_ok=True)

model_path = os.path.join(model_dir, "fptester-circuit-llm.gguf")
url = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q2_k.gguf"

if os.path.exists(model_path) and os.path.getsize(model_path) > 100000000:
    print(f"[+] Model already exists at: {model_path} ({os.path.getsize(model_path) // (1024*1024)} MB)")
    sys.exit(0)

print(f"[*] Downloading GGUF LLM Model from HuggingFace to {model_path}...")
ctx = ssl._create_unverified_context()
req = urllib.request.Request(url, headers={'User-Agent': 'Python'})

with urllib.request.urlopen(req, context=ctx) as resp, open(model_path, "wb") as f:
    total_size = int(resp.headers.get('Content-Length', 0))
    downloaded = 0
    block_size = 1024 * 1024  # 1 MB blocks
    while True:
        buffer = resp.read(block_size)
        if not buffer:
            break
        f.write(buffer)
        downloaded += len(buffer)
        percent = (downloaded / total_size) * 100 if total_size else 0
        print(f"\r[*] Downloading Model: {downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB ({percent:.1f}%)", end="")

print("\n[+] Model Download Complete!")
