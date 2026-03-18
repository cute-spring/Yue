import os
import re
import argparse
import json
from pathlib import Path

def analyze_markdown_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple regex for markdown tasks
    tasks = re.findall(r"- \[( |x|X)\] (.*)", content)
    
    completed = [t[1] for t in tasks if t[0].lower() == "x"]
    pending = [t[1] for t in tasks if t[0].strip() == ""]
    
    return {
        "file": str(file_path),
        "total": len(tasks),
        "completed_count": len(completed),
        "pending_count": len(pending),
        "completed": completed,
        "pending": pending
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans-dir", default="docs/plans")
    args = parser.parse_args()
    
    plans_dir = Path(args.plans_dir)
    if not plans_dir.exists():
        print(f"Directory not found: {plans_dir}")
        return
    
    results = []
    for root, _, files in os.walk(plans_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                analysis = analyze_markdown_file(file_path)
                if analysis["total"] > 0:
                    results.append(analysis)
    
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
