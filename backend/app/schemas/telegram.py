from pydantic import BaseModel, Field


class TelegramConfigOut(BaseModel):
    enabled: bool = False
    chat_id: str = ""
    bot_token_set: bool = False
    bot_token_masked: str = ""
    auto_send_after_execution: bool = False


class TelegramConfigUpdate(BaseModel):
    enabled: bool | None = None
    chat_id: str | None = None
    bot_token: str | None = Field(None, description="留空表示不修改已有 Token")
    auto_send_after_execution: bool | None = None


class TelegramSendResult(BaseModel):
    success: bool
    message: str
