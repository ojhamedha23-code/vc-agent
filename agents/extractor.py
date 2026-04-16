"""
Agent 1: Claim Extractor
Reads the full pitch deck text and extracts structured claims into ClaimsJSON.
"""
import json
from pathlib import Path

import anthropic

from schemas.models import ClaimsJSON
from tools.pdf_parser import SlideContent, slides_to_text

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extractor.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()


def run(slides: list[SlideContent], client: anthropic.Anthropic) -> ClaimsJSON:
    deck_text = slides_to_text(slides)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the full pitch deck content:\n\n{deck_text}",
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    return ClaimsJSON(**data)
