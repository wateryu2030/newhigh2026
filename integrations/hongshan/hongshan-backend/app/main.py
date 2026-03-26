"""
红山量化交易平台 - FastAPI 应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from app.config import settings
from app.db import init_db
from app.routes import auth, users, stocks, orders, positions, strategies, risk, websocket

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="红山量化交易平台 API",
    description="提供股票行情、交易、策略、风控等功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 中间件：请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    
    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.DEBUG else "Unknown error"}
    )


# 路由注册
app.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["股票行情"])
app.include_router(orders.router, prefix="/api/orders", tags=["交易委托"])
app.include_router(positions.router, prefix="/api/positions", tags=["持仓"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略"])
app.include_router(risk.router, prefix="/api/risk", tags=["风控"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    return {
        "status": "healthy",
        "service": "hongshan-quant-platform",
        "version": "1.0.0"
    }


# 根路径
@app.get("/", tags=["根路径"])
async def root():
    return {
        "message": "欢迎使用红山量化交易平台 API",
        "docs": "/docs",
        "version": "1.0.0"
    }


# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Hongshan Quant Platform...")
    if settings.AUTO_INIT_DB:
        logger.info("Initializing database...")
        init_db()
    logger.info("Startup complete!")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Hongshan Quant Platform...")
