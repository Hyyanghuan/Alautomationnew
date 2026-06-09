"""常用大模型预置配置"""

from app.config import get_settings

settings = get_settings()


def get_preset_models() -> list[dict]:
    """从 .env 读取各厂商 Key，预置常用模型"""
    return [
        {
            "provider": "openai",
            "model_name": "gpt-4o",
            "api_endpoint": settings.openai_api_base,
            "api_key": settings.openai_api_key,
            "parameters": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096},
            "rate_limit": 60,
            "label": "OpenAI GPT-4o",
        },
        {
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "api_endpoint": settings.openai_api_base,
            "api_key": settings.openai_api_key,
            "parameters": {"temperature": 0.5, "top_p": 0.9, "max_tokens": 4096},
            "rate_limit": 120,
            "label": "OpenAI GPT-4o Mini",
        },
        {
            "provider": "qwen",
            "model_name": "qwen-plus",
            "api_endpoint": settings.qwen_api_base,
            "api_key": settings.qwen_api_key,
            "parameters": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096},
            "rate_limit": 60,
            "label": "通义千问 Qwen-Plus",
        },
        {
            "provider": "qwen",
            "model_name": "qwen-turbo",
            "api_endpoint": settings.qwen_api_base,
            "api_key": settings.qwen_api_key,
            "parameters": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096},
            "rate_limit": 120,
            "label": "通义千问 Qwen-Turbo",
        },
        {
            "provider": "deepseek",
            "model_name": "deepseek-chat",
            "api_endpoint": settings.deepseek_api_base,
            "api_key": settings.deepseek_api_key,
            "parameters": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096},
            "rate_limit": 60,
            "label": "DeepSeek Chat",
        },
        {
            "provider": "deepseek",
            "model_name": "deepseek-reasoner",
            "api_endpoint": settings.deepseek_api_base,
            "api_key": settings.deepseek_api_key,
            "parameters": {"temperature": 0.3, "top_p": 0.9, "max_tokens": 8192},
            "rate_limit": 30,
            "label": "DeepSeek Reasoner",
        },
    ]
