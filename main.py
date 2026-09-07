import time
import asyncio
from fastapi import FastAPI
from test_pydantic import BaseModel, Field

# ==========================================
# 1. Pydantic 数据校验区
# ==========================================

# 定义接收请求的数据模型（强校验前端传来的数据）
class UserInput(BaseModel):
    # 必须传入字符串，且长度不少于 2 个字符
    query: str = Field(..., min_length=2, description="用户的提问文本")
    # 必须是大于 0 的整数，如果不传则默认是 1000
    user_id: int = Field(default=1000, gt=0, description="用户ID，必须大于0")

# 定义返回响应的数据模型（规范后端输出给前端的格式）
class AnalysisResult(BaseModel):
    original_query: str
    processed_length: int
    status: str
    processing_time: float

# ==========================================
# 2. FastAPI 服务初始化
# ==========================================
app = FastAPI(title="Agent 基础组件学习模板")

# 测试接口，验证服务是否正常启动
@app.get("/ping")
async def ping():
    return {"message": "pong"}

# ==========================================
# 3. 核心业务接口 (整合 FastAPI + 异步 asyncio + Pydantic)
# ==========================================
# response_model 参数强制校验返回的数据格式是否符合 AnalysisResult
@app.post("/analyze", response_model=AnalysisResult)
async def analyze_text(request: UserInput):
    start_time = time.time()
    
    # 【核心：异步等待】
    # 这里模拟调用大模型 API 的耗时操作（等待 2 秒）。
    # 使用 await asyncio.sleep 不会阻塞主线程，此时服务器可以去处理其他用户的请求。
    await asyncio.sleep(2)
    
    # 简单的业务逻辑处理
    text_length = len(request.query)
    cost_time = round(time.time() - start_time, 2)
    
    # 返回的数据字典会被 FastAPI 自动转换为 JSON，并被 Pydantic 校验
    return {
        "original_query": request.query,
        "processed_length": text_length,
        "status": "success",
        "processing_time": cost_time
    }