from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TopicSettings(BaseModel):
    """Configuration settings for a topic"""
    system_prompt: str = Field(default="You are a helpful AI assistant.", description="System prompt for the model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature parameter for generation")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p parameter for generation")
    top_k: int = Field(default=40, ge=1, le=100, description="Top-k parameter for generation")
    max_tokens: int = Field(default=500, ge=1, description="Maximum tokens for generation")
    no_think: bool = Field(default=False, description="Add /no_think prefix to prompts")
    force_json: bool = Field(default=False, description="Force JSON-only output")


class GrammarConfig(BaseModel):
    """Grammar configuration for a topic"""
    enabled: bool = Field(default=False, description="Whether to use grammar")
    file: Optional[str] = Field(default=None, description="Grammar filename in data/test_grammars/")


class Topic(BaseModel):
    """Topic configuration model"""
    name: str = Field(..., description="Display name for the topic")
    description: str = Field(default="", description="Description of the topic's purpose")
    enabled: bool = Field(default=True, description="Whether the topic is active")
    model: str = Field(..., description="Model filename to use for this topic")
    settings: TopicSettings = Field(default_factory=TopicSettings, description="Generation settings")
    grammar: GrammarConfig = Field(default_factory=GrammarConfig, description="Grammar configuration")
    
    # Dispatcher configuration
    dispatcher: Optional[str] = Field(default=None, description="Dispatcher to use for executing LLM output")
    
    # Tracking fields
    auto_discovered: bool = Field(default=False, description="Whether topic was auto-created")
    first_seen: Optional[datetime] = Field(default=None, description="When topic was first created/discovered")
    last_used: Optional[datetime] = Field(default=None, description="When topic was last used for generation")
    
    # Heartbeat tracking fields for live status
    last_heartbeat: Optional[datetime] = Field(default=None, description="Last heartbeat from wake word system")
    wake_word: Optional[str] = Field(default=None, description="Associated wake word phrase")
    trigger_count: int = Field(default=0, description="Number of times wake word was triggered")
    heartbeat_status: str = Field(default="unknown", description="Status from heartbeat: active, idle, unknown")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }