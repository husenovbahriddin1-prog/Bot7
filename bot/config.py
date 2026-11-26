import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    admin_id: int = int(os.getenv("ADMIN_ID", "0"))
    database_url: str = os.getenv("DATABASE_URL", "")
    port: int = int(os.getenv("PORT", "10000"))
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def validate(self):
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.admin_id:
            missing.append("ADMIN_ID")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if missing:
            raise RuntimeError("Quyidagi Environment Variable’lar kiritilmagan: " + ", ".join(missing))


settings = Settings()import os
from dataclasses import dataclass

@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    admin_id: int = int(os.getenv("ADMIN_ID", "0"))
    database_url: str = os.getenv("DATABASE_URL", "")
    port: int = int(os.getenv("PORT", "10000"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def validate(self):
        missing = []
        if not self.bot_token: missing.append("BOT_TOKEN")
        if not self.openai_api_key: missing.append("OPENAI_API_KEY")
        if not self.admin_id: missing.append("ADMIN_ID")
        if not self.database_url: missing.append("DATABASE_URL")
        if missing:
            raise RuntimeError("Quyidagi Environment Variable’lar kiritilmagan: " + ", ".join(missing))

settings = Settings()
