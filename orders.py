"""
routes/orders.py - API endpoints для ордеров (НОВЫЙ v1.0)

Дата создания: 23.11.2025
Версия: 1.0.0 (NEW - Orders API)
Назначение: Получение активных ордеров с Bybit
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
router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("/")
async def get_orders(db: Session = Depends(get_db)) -> Dict:
    """Получить активные ордеры"""
    try:
        exchange = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == "bybit"
        ).first()
        
        if not exchange:
            return {
                "status": "error",
                "message": "API ключи не добавлены",
                "orders": [],
                "total": 0,
            }
        
        try:
            encryptor = get_encryption_manager()
            api_key = encryptor.decrypt(exchange.api_key_encrypted)
            api_secret = encryptor.decrypt(exchange.api_secret_encrypted)
            
            client = get_bybit_client(api_key, api_secret, exchange.testnet)
            
            # Получаем активные ордеры
            result = client.client.get_open_orders(category="linear")
            
            if result and result.get('retCode') == 0:
                orders = result.get('result', {}).get('list', [])
                
                formatted_orders = []
                for order in orders:
                    formatted_orders.append({
                        "symbol": order.get('symbol'),
                        "side": order.get('side'),
                        "order_type": order.get('orderType'),
                        "qty": float(order.get('qty', 0)),
                        "price": float(order.get('price', 0)),
                        "status": order.get('orderStatus'),
                        "order_id": order.get('orderId'),
                        "created_at": order.get('createdTime'),
                    })
                
                logger.info(f"✅ Retrieved {len(formatted_orders)} orders")
                
                return {
                    "status": "success",
                    "orders": formatted_orders,
                    "total": len(formatted_orders),
                }
            else:
                logger.warning(f"Empty orders response: {result}")
                return {
                    "status": "success",
                    "orders": [],
                    "total": 0,
                }
        
        except Exception as e:
            logger.error(f"Failed to get orders: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Ошибка получения ордеров: {str(e)}",
                "orders": [],
                "total": 0,
            }
    
    except Exception as e:
        logger.error(f"Error in orders endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_orders_count(db: Session = Depends(get_db)) -> Dict:
    """Получить количество активных ордеров"""
    try:
        exchange = db.query(ExchangeAPI).filter(
            ExchangeAPI.exchange == "bybit"
        ).first()
        
        if not exchange:
            return {
                "status": "success",
                "active_orders": 0,
            }
        
        try:
            encryptor = get_encryption_manager()
            api_key = encryptor.decrypt(exchange.api_key_encrypted)
            api_secret = encryptor.decrypt(exchange.api_secret_encrypted)
            
            client = get_bybit_client(api_key, api_secret, exchange.testnet)
            result = client.client.get_open_orders(category="linear")
            
            if result and result.get('retCode') == 0:
                orders = result.get('result', {}).get('list', [])
                return {
                    "status": "success",
                    "active_orders": len(orders),
                }
        
        except Exception as e:
            logger.error(f"Error counting active orders: {e}")
        
        return {
            "status": "success",
            "active_orders": 0,
        }
    
    except Exception as e:
        logger.error(f"Error in active orders count: {e}")
        return {
            "status": "error",
            "active_orders": 0,
        }
