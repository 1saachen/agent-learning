"""启动 DeepSeek 真实模型版本：python -m phase2.run_api"""

import uvicorn

from .api import create_app
from .client import OpenAIModelCaller
from .prompts import SYSTEM_PROMPT


app = create_app(OpenAIModelCaller(SYSTEM_PROMPT))


if __name__ == "__main__":
    uvicorn.run("phase2.run_api:app", host="127.0.0.1", port=8000, reload=False)
