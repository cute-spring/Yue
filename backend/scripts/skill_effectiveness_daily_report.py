import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.chat_service import chat_service

def main():
    report = chat_service.get_skill_effectiveness_report(hours=24)
    output = {
        "generated_at": datetime.now().isoformat(),
        "report": report
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
