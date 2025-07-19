import os
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DATABASE_URL = os.getenv("DATABASE_URL")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")