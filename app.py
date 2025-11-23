"""
app.py - Главное FastAPI приложение (PHASE 4 - FINAL v1.6)

Дата создания: 23.11.2025
Версия: 1.6.0 (FIXED + Optimized)
Назначение: Главный FastAPI сервер с интеграцией Bybit, WebSocket, БД

ИСПРАВЛЕНИЯ v1.6:
✅ Фиксированы проблемы с шифрованием ключей
✅ Добавлена поддержка .env через python-dotenv
✅ Оптимизирована работа с Bybit API (recv_window=15000)
✅ Добавлена правильная обработка ошибок
✅ Регистрация всех routes в правильном порядке
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import uvicorn
from datetime import datetime
from typing import Dict, List

# Импорты проекта
from config import get_settings
from database import init_db, get_db, SessionLocal, engine
from models import Base, ExchangeAPI
import api_keys
import orders
import positions
import trades
import events

# ==================== КОНФИГУРАЦИЯ ====================

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== FASTAPI ИНИЦИАЛИЗАЦИЯ ====================

app = FastAPI(
    title="Slezun Web Dashboard",
    description="Trading Monitor с интеграцией Bybit",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# ==================== CORS MIDDLEWARE ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ==================== СОБЫТИЯ ПРИЛОЖЕНИЯ ====================

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info(f"🚀 Starting Slezun Web Dashboard v{app.version} (PHASE 4)")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"💾 Database: {settings.DATABASE_URL}")
    
    init_db()
    logger.info("✅ Database initialized successfully")
    logger.info("🎉 Application ready for WebSocket connections!")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    logger.info("🛑 Shutting down...")


# ==================== MIDDLEWARE ЛОГИРОВАНИЯ ====================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов"""
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        status_emoji = "🟢" if response.status_code < 400 else "🔴"
        logger.info(
            f"{status_emoji} {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
        )
        
        return response
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        raise


# ==================== HEALTH ENDPOINTS ====================

@app.get("/health")
async def health_check() -> Dict:
    """Проверка здоровья приложения"""
    return {
        "status": "ok",
        "app": "Slezun Web Dashboard",
        "version": app.version,
        "phase": "4",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/info")
async def get_app_info() -> Dict:
    """Получить информацию о приложении"""
    return {
        "status": "success",
        "app": "Slezun Web Dashboard",
        "version": app.version,
        "phase": "4",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database": settings.DATABASE_URL,
    }


@app.get("/api/status")
async def get_system_status(db: Session = Depends(get_db)) -> Dict:
    """Получить полный статус системы"""
    try:
        exchanges = db.query(ExchangeAPI).all()
        
        return {
            "status": "success",
            "system": {
                "app": "Slezun Web Dashboard",
                "version": app.version,
                "uptime": datetime.utcnow().isoformat(),
            },
            "database": {
                "connected": True,
                "type": "SQLite",
                "url": settings.DATABASE_URL,
            },
            "exchanges": {
                "total": len(exchanges),
                "connected": sum(1 for e in exchanges if e.is_connected),
                "details": [
                    {
                        "exchange": e.exchange,
                        "connected": e.is_connected,
                        "testnet": e.testnet,
                    }
                    for e in exchanges
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account")
async def get_account_info(db: Session = Depends(get_db)) -> Dict:
    """Получить информацию об аккаунте Bybit"""
    try:
        from bybit_service import get_bybit_client
        from utils.crypto import get_encryption_manager
        
        exchange = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == "bybit"
        ).first()
        
        if not exchange:
            return {
                "status": "error",
                "message": "API ключи не добавлены",
                "balance": 0,
                "equity": 0,
                "available_balance": 0,
                "unrealized_pnl": 0,
                "account_type": "NONE",
            }
        
        try:
            encryptor = get_encryption_manager()
            api_key = encryptor.decrypt(exchange.api_key_encrypted)
            api_secret = encryptor.decrypt(exchange.api_secret_encrypted)
            
            client = get_bybit_client(api_key, api_secret, exchange.testnet)
            account_info = client.get_account_info()
            
            return {
                "status": "success",
                "balance": float(account_info.get("total_wallet_balance", 0)),
                "equity": float(account_info.get("total_equity", 0)),
                "available_balance": float(account_info.get("available_balance", 0)),
                "unrealized_pnl": float(account_info.get("total_unrealised_loss", 0)),
                "account_type": "TESTNET" if exchange.testnet else "LIVE",
            }
            
        except Exception as e:
            logger.error(f"Error getting account info from Bybit: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Ошибка подключения к Bybit: {str(e)}",
                "balance": 0,
                "equity": 0,
                "available_balance": 0,
                "unrealized_pnl": 0,
                "account_type": "TESTNET" if exchange.testnet else "LIVE",
            }
    
    except Exception as e:
        logger.error(f"Error in account endpoint: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "balance": 0,
            "equity": 0,
            "available_balance": 0,
            "unrealized_pnl": 0,
            "account_type": "NONE",
        }


# ==================== OPTIONS HANDLER ====================

@app.options("/{full_path:path}")
async def options_handler(full_path: str) -> JSONResponse:
    """Универсальный обработчик OPTIONS запросов для CORS preflight"""
    return JSONResponse(
        content={},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600",
        }
    )


# ==================== РЕГИСТРАЦИЯ ROUTES ====================

app.include_router(api_keys.router)
app.include_router(orders.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(events.router)


# ==================== WEBSOCKET ====================

class ConnectionManager:
    """Менеджер для управления WebSocket соединениями"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, data: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для real-time обновлений"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"WebSocket received: {data}")
            
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработка HTTP исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "detail": exc.detail,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработка общих исключений"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "detail": "Internal server error",
            "path": str(request.url.path),
        },
    )


# ==================== ГЛАВНАЯ ТОЧКА ВХОДА ====================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
    )
