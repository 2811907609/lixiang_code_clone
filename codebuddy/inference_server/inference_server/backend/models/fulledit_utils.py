
import re


_EDITABLE_REGION_PATTERN = re.compile(r'(<\|editable_region_start\|>.*?<\|editable_region_end\|>)', re.DOTALL)

def extract_draft_from_prompt(input_excerpt: str) -> str:
    match = _EDITABLE_REGION_PATTERN.search(input_excerpt)
    if match:
        return match.group(1)
    return ''
