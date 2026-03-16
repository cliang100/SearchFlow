from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FetchResult:
    url: str
    html: str
    status_code: int
    final_url: str
    success: bool
    error: Optional[str] = None
    
@dataclass
class ExtractedContent:
    url: str
    title: str
    content: str
    links: List[str]
    word_count: int
    success: bool
    error: Optional[str] = None