from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.api.v1 import agent, analytics, chat, intent, knowledge, order, product
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.utils.logger import setup_logger
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    logger = setup_logger(__name__)
    logger.info('应用启动中...')

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info('应用启动完成')
    yield
    logger.info('应用关闭中...')
    await engine.dispose()
    logger.info('应用关闭完成')

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description='电商智能客服系统 API',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(chat.router, prefix='/api/v1/chat', tags=['对话服务'])
app.include_router(intent.router, prefix='/api/v1/intent', tags=['意图识别'])
app.include_router(agent.router, prefix='/api/v1/agent', tags=['智能体服务'])
app.include_router(knowledge.router, prefix='/api/v1/knowledge', tags=['知识库服务'])
app.include_router(order.router, prefix='/api/v1/order', tags=['订单服务'])
app.include_router(product.router, prefix='/api/v1/product', tags=['商品服务'])
app.include_router(analytics.router, prefix='/api/v1/analytics', tags=['数据分析'])

@app.get('/')
async def root():
    return {'message': '电商智能客服系统 API', 'version': settings.VERSION}

@app.get('/health')
async def health_check():
    return {'status': 'healthy'}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
