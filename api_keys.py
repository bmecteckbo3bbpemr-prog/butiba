"""
routes/api_keys.py - API endpoints для управления ключами (ФИНАЛЬНАЯ v1.3)

Дата создания: 22.11.2025
Версия: 1.3.0 (COMPLETE - CORS fixed)
Назначение: Endpoints для добавления/удаления/проверки API ключей

Endpoints:
1. POST /api/keys/add - добавить новые ключи (JSON body)
2. GET /api/keys/status - статус подключения
3. POST /api/keys/test - протестировать ключи (JSON body)
4. DELETE /api/keys - удалить ключи
5. OPTIONS /api/keys/* - CORS preflight
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
from typing import Dict
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import ExchangeAPI
from utils.crypto import get_encryption_manager
from bybit_service import get_bybit_client, reset_bybit_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/keys", tags=["API Keys"])


# ===================== PYDANTIC MODELS =====================

class AddKeyRequest(BaseModel):
    exchange: str = "bybit"
    api_key: str
    api_secret: str
    testnet: bool = False


class TestKeyRequest(BaseModel):
    exchange: str = "bybit"
    api_key: str
    api_secret: str
    testnet: bool = False


class RemoveKeyRequest(BaseModel):
    exchange: str = "bybit"


# ===================== CORS PREFLIGHT =====================

@router.options("/add")
@router.options("/status")
@router.options("/test")
@router.options("/remove")
async def options_handler(request: Request) -> JSONResponse:
    """Обработка CORS preflight OPTIONS запросов"""
    return JSONResponse(
        content={},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600",
        }
    )


# ===================== ENDPOINTS =====================

@router.post("/add")
async def add_api_keys(
    request: AddKeyRequest,
    db: Session = Depends(get_db)
) -> Dict:
    """Добавить API ключи для биржи"""
    try:
        # Валидация входных данных
        if not request.api_key or not request.api_secret:
            raise HTTPException(
                status_code=400,
                detail="api_key и api_secret обязательны"
            )
        
        if request.exchange.lower() != "bybit":
            raise HTTPException(
                status_code=400,
                detail="Пока поддерживается только Bybit"
            )
        
        # Шифруем ключи
        encryptor = get_encryption_manager()
        encrypted_key = encryptor.encrypt(request.api_key)
        encrypted_secret = encryptor.encrypt(request.api_secret)
        
        # Проверяем что ключи валидны
        try:
            bybit_client = get_bybit_client(request.api_key, request.api_secret, request.testnet)
            if not bybit_client.validate_credentials():
                reset_bybit_client()
                raise HTTPException(
                    status_code=401,
                    detail="API ключи невалидны или нет доступа"
                )
        except Exception as e:
            logger.error(f"Failed to validate credentials: {e}")
            raise HTTPException(
                status_code=401,
                detail=f"Ошибка подключения: {str(e)}"
            )
        
        # Удаляем старые ключи если существуют
        existing = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == request.exchange.lower()
        ).first()
        
        if existing:
            db.delete(existing)
            logger.info(f"Removed old API keys for {request.exchange}")
        
        # Создаём новую запись
        new_exchange_api = ExchangeAPI(
            exchange=request.exchange.lower(),
            api_key_encrypted=encrypted_key,
            api_secret_encrypted=encrypted_secret,
            testnet=request.testnet,
            is_connected=True,
            last_connection_check=datetime.utcnow(),
        )
        
        db.add(new_exchange_api)
        db.commit()
        db.refresh(new_exchange_api)
        
        logger.info(f"✅ API keys added for {request.exchange} (testnet={request.testnet})")
        
        return {
            "status": "success",
            "message": f"API ключи для {request.exchange} успешно добавлены",
            "exchange": request.exchange,
            "testnet": request.testnet,
            "exchange_id": new_exchange_api.id,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding API keys: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при добавлении ключей: {str(e)}"
        )


@router.get("/status")
async def get_keys_status(db: Session = Depends(get_db)) -> Dict:
    """Получить статус подключения к биржам"""
    try:
        exchanges = db.query(ExchangeAPI).all()
        
        statuses = []
        for exchange in exchanges:
            statuses.append({
                "exchange": exchange.exchange,
                "is_connected": exchange.is_connected,
                "testnet": exchange.testnet,
                "total_positions": exchange.total_positions,
                "closed_positions": exchange.closed_positions,
                "last_check": exchange.last_connection_check.isoformat() if exchange.last_connection_check else None,
            })
        
        return {
            "status": "success",
            "exchanges": statuses,
            "total_exchanges": len(statuses),
        }
    
    except Exception as e:
        logger.error(f"Error getting keys status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статуса: {str(e)}"
        )


@router.post("/test")
async def test_api_keys(request: TestKeyRequest) -> Dict:
    """Протестировать API ключи БЕЗ сохранения"""
    try:
        if not request.api_key or not request.api_secret:
            raise HTTPException(
                status_code=400,
                detail="api_key и api_secret обязательны"
            )
        
        # Пытаемся подключиться
        bybit_client = get_bybit_client(request.api_key, request.api_secret, request.testnet)
        is_valid = bybit_client.validate_credentials()
        reset_bybit_client()
        
        if is_valid:
            return {
                "status": "success",
                "message": "API ключи валидны!",
                "is_valid": True,
            }
        else:
            return {
                "status": "error",
                "message": "API ключи невалидны",
                "is_valid": False,
            }
    
    except Exception as e:
        logger.error(f"Error testing API keys: {e}")
        return {
            "status": "error",
            "message": f"Ошибка теста: {str(e)}",
            "is_valid": False,
        }


@router.delete("/remove")
async def remove_api_keys(
    request: RemoveKeyRequest,
    db: Session = Depends(get_db)
) -> Dict:
    """Удалить API ключи"""
    try:
        exchange_api = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == request.exchange.lower()
        ).first()
        
        if not exchange_api:
            raise HTTPException(
                status_code=404,
                detail=f"API ключи для {request.exchange} не найдены"
            )
        
        db.delete(exchange_api)
        db.commit()
        
        # Сбрасываем клиент
        reset_bybit_client()
        
        logger.info(f"✅ API keys removed for {request.exchange}")
        
        return {
            "status": "success",
            "message": f"API ключи для {request.exchange} удалены",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing API keys: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления: {str(e)}"
        )
