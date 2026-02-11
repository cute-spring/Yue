import requests
import json
import sys

def verify_ollama_sync():
    print("Step 1: Fetching actual models from Ollama API...")
    try:
        ollama_res = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_res.raise_for_status()
        ollama_data = ollama_res.json()
        actual_models = sorted([m['name'] for m in ollama_data.get('models', [])])
        print(f"Found {len(actual_models)} models in Ollama: {actual_models}")
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return

    print("\nStep 2: Fetching providers from Backend API (with refresh=1)...")
    try:
        backend_res = requests.get("http://localhost:3000/api/models/providers?refresh=1", timeout=10)
        backend_res.raise_for_status()
        providers = backend_res.json()
        
        ollama_provider = next((p for p in providers if p['name'] == 'ollama'), None)
        if not ollama_provider:
            print("Error: Ollama provider not found in backend response")
            return
        
        discovered_models = sorted(ollama_provider.get('models', []))
        available_models = sorted(ollama_provider.get('available_models', []))
        
        print(f"Found {len(discovered_models)} models in Backend 'models' list: {discovered_models}")
        print(f"Found {len(available_models)} models in Backend 'available_models' list (allowlist): {available_models}")

        print("\nStep 3: Comparing results...")
        
        # We check if discovered_models matches actual_models
        mismatch = False
        if discovered_models != actual_models:
            print("❌ FAILURE: Backend 'models' list does not match Ollama API output!")
            print(f"Missing in Backend: {set(actual_models) - set(discovered_models)}")
            print(f"Extra in Backend: {set(discovered_models) - set(actual_models)}")
            mismatch = True
        else:
            print("✅ SUCCESS: Backend 'models' list matches Ollama API exactly.")
            
        if mismatch:
            sys.exit(1)
            
    except Exception as e:
        print(f"Error connecting to Backend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_ollama_sync()
