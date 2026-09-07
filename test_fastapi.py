from fastapi import FastAPI
from pydantic import BaseModel, field_validator
import asyncio

# 1. 实例化“门店”
app = FastAPI()

# 定义请求校验模型 (你写的部分，非常完美)
class TranslationRequest(BaseModel):
    text: str
    target_language: str

    @field_validator('target_language')
    @classmethod
    def validate_target_language(cls, value):
        valid_languages = ['en', 'es', 'fr', 'de', 'zh']
        if value not in valid_languages:
            raise ValueError(f'Target language must be one of {valid_languages}')
        return value

# 新增：定义响应数据模型 (规范输出格式)
class TranslationResponse(BaseModel):
    original_text: str
    target_language: str
    translated_text: str

# 修正：将 response_model 设置为刚刚定义的 TranslationResponse 类
@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    # 模拟调用大模型 API 的耗时操作（等待 2 秒）
    await asyncio.sleep(2)
    
    # 模拟翻译逻辑
    fake_translated_text = f"Translated '{request.text}' to {request.target_language}"
    
    # 按照 TranslationResponse 的格式返回数据
    # FastAPI 会自动把它转成 JSON 格式发给前端
    return {
        "original_text": request.text,
        "target_language": request.target_language,
        "translated_text": fake_translated_text
    }