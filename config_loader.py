from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import yaml

class FieldConfig(BaseModel):
    selector: str
    attr: str = "text"
    regex: Optional[str] = None
    transform: Optional[str] = None
    optional: bool = False

class PaginationConfig(BaseModel):
    type: str = "next_selector"  # next_selector, url_param, click
    selector: Optional[str] = None
    max_pages: int = 1

class StepConfig(BaseModel):
    action: str  # wait_for_selector, click, scroll, fill
    selector: Optional[str] = None
    value: Optional[str] = None
    wait: Optional[int] = None

class ExtractionConfig(BaseModel):
    items_selector: str
    fields: Dict[str, FieldConfig]

class CrawlConfig(BaseModel):
    name: str
    start_url: str
    engine: str = "playwright"
    proxy_required: bool = False
    proxy_pool: Optional[List[str]] = Field(default_factory=list)
    captcha_service: Optional[str] = None
    captcha_api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    cookies: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    steps: List[StepConfig] = Field(default_factory=list)
    pagination: PaginationConfig = PaginationConfig()
    extraction: ExtractionConfig
    detail_extraction: Optional[Dict[str, FieldConfig]] = None
    detail_steps: List[StepConfig] = Field(default_factory=list)
    delay: Dict[str, float] = Field(default_factory=lambda: {"min": 1.0, "max": 2.0})
    output: Dict[str, Any] = Field(default_factory=lambda: {"format": "csv", "file": "output.csv"})
    concurrency: int = 1

    @validator('engine')
    def engine_must_be_valid(cls, v):
        if v not in ['static', 'playwright', 'api']:
            raise ValueError('engine must be static, playwright, or api')
        return v

def load_config(path: str) -> CrawlConfig:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return CrawlConfig(**data)