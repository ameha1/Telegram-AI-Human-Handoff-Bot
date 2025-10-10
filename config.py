import os
from dataclasses import dataclass

@dataclass
class Config:
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
    REDIS_URL: str = os.getenv('UPSTASH_REDIS_REST_URL')
    REDIS_TOKEN: str = os.getenv('UPSTASH_REDIS_REST_TOKEN')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY')
    PORT: int = int(os.getenv('PORT', 10000))
    
    # AI Settings
    AI_MODEL: str = "gpt-3.5-turbo"
    MAX_CONVERSATION_HISTORY: int = 10
    AI_TEMPERATURE: float = 0.7
    
    # Conversation settings
    CONVERSATION_TTL: int = 86400  # 24 hours
    USER_SETTINGS_TTL: int = 2592000  # 30 days

config = Config()