"""
routes/positions.py - API endpoints для позиций (НОВЫЙ v1.0)

Дата создания: 23.11.2025
Версия: 1.0.0 (NEW - Positions API)
Назначение: Получение открытых позиций с Bybit
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from typing import Dict

from database import get_db
from models import ExchangeAPI
from utils.crypto import get_encryption_manager
from bybit_service import get_bybit_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/positions", tags=["Positions"])


@router.get("/")
async def get_positions(db: Session = Depends(get_db)) -> Dict:
    """Получить открытые позиции"""
    try:
        exchange = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == "bybit"
        ).first()
        
        if not exchange:
            return {
                "status": "error",
                "message": "API ключи не добавлены",
                "positions": [],
                "total": 0,
            }
        
        try:
            encryptor = get_encryption_manager()
            api_key = encryptor.decrypt(exchange.api_key_encrypted)
            api_secret = encryptor.decrypt(exchange.api_secret_encrypted)
            
            client = get_bybit_client(api_key, api_secret, exchange.testnet)
            
            # Получаем открытые позиции
            result = client.client.get_positions(category="linear")
            
            if result and result.get('retCode') == 0:
                positions = result.get('result', {}).get('list', [])
                
                formatted_positions = []
                for pos in positions:
                    size = float(pos.get('size', 0))
                    # Пропускаем закрытые позиции (size = 0)
                    if size > 0:
                        formatted_positions.append({
                            "symbol": pos.get('symbol'),
                            "side": pos.get('side'),
                            "size": size,
                            "entry_price": float(pos.get('entryPrice', 0)),
                            "mark_price": float(pos.get('markPrice', 0)),
                            "pnl": float(pos.get('unrealisedPnl', 0)),
                            "pnl_percent": float(pos.get('unrealisedPnlPct', 0)) * 100,
                            "leverage": float(pos.get('leverage', 1)),
                            "position_id": pos.get('positionIdx'),
                        })
                
                logger.info(f"✅ Retrieved {len(formatted_positions)} open positions")
                
                return {
                    "status": "success",
                    "positions": formatted_positions,
                    "total": len(formatted_positions),
                }
            else:
                logger.warning(f"Empty positions response: {result}")
                return {
                    "status": "success",
                    "positions": [],
                    "total": 0,
                }
        
        except Exception as e:
            logger.error(f"Failed to get positions: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Ошибка получения позиций: {str(e)}",
                "positions": [],
                "total": 0,
            }
    
    except Exception as e:
        logger.error(f"Error in positions endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/open")
async def get_open_positions_count(db: Session = Depends(get_db)) -> Dict:
    """Получить количество открытых позиций"""
    try:
        exchange = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == "bybit"
        ).first()
        
        if not exchange:
            return {
                "status": "success",
                "open_positions": 0,
            }
        
        try:
            encryptor = get_encryption_manager()
            api_key = encryptor.decrypt(exchange.api_key_encrypted)
            api_secret = encryptor.decrypt(exchange.api_secret_encrypted)
            
            client = get_bybit_client(api_key, api_secret, exchange.testnet)
            result = client.client.get_positions(category="linear")
            
            if result and result.get('retCode') == 0:
                positions = result.get('result', {}).get('list', [])
                open_count = len([p for p in positions if float(p.get('size', 0)) > 0])
                
                return {
                    "status": "success",
                    "open_positions": open_count,
                }
        
        except Exception as e:
            logger.error(f"Error counting open positions: {e}")
        
        return {
            "status": "success",
            "open_positions": 0,
        }
    
    except Exception as e:
        logger.error(f"Error in open positions count: {e}")
        return {
            "status": "error",
            "open_positions": 0,
        }
