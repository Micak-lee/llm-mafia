import os
from dotenv import load_dotenv

load_dotenv()

# 1. GPT-4o 配置 (法官/上帝视角)
config_gpt4 = {
    "config_list": [
        {
            "model": "gpt-4o",
            "api_key": os.environ.get("OPENAI_API_KEY"),
        }
    ],
    "temperature": 0.1,
}

# 2. DeepSeek 配置 (狼人)
config_deepseek = {
    "config_list": [
        {
            "model": "deepseek-chat",
            "api_key": os.environ.get("DEEPSEEK_API_KEY"),
            "base_url": os.environ.get("DEEPSEEK_BASE_URL"),
        }
    ],
    "temperature": 0.7,
}

# 3. 通义千问 Qwen 配置 (平民/预言家)
config_tongyi = {
    "config_list": [
        {
            "model": "qwen-plus-latest",
            "api_key": os.environ.get("TONGYI_API_KEY"),
            "base_url": os.environ.get("TONGYI_BASE_URL"),
            "extra_body": {
                "enable_thinking":False
            },
            "price": [0.0011, 0.0011]
        }
    ],
    "temperature": 0.7,
}

# 4. 本地 Ollama 配置 (备用)
config_ollama = {
    "config_list": [
        {
            "model": "llama3",
            "api_key": "NULL",
            "base_url": os.environ.get("OLLAMA_BASE_URL"),
        }
    ],
    "temperature": 0.7,
}
