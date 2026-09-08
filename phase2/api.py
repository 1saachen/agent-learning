from fastapi import FastAPI, HTTPException

from .client import ModelCallError, ModelCaller
from .contracts import ResumeAnalysis, ResumeRequest
from .service import AnalysisService, ParseFailure


def create_app(caller: ModelCaller) -> FastAPI:
    app = FastAPI(title="Phase 2 Resume Analysis API")
    service = AnalysisService(caller)

    @app.post("/resume/analyze", response_model=ResumeAnalysis)
    async def analyze(request: ResumeRequest):
        try:
            result = await service.analyze(request.resume, request.job_description)
        except ModelCallError as exc:
            raise HTTPException(status_code=504, detail="模型服务暂时不可用") from exc
        if isinstance(result, ParseFailure):
            raise HTTPException(status_code=502, detail="模型返回无法解析")
        return result

    return app
