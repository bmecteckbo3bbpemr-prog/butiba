"""
routes/events.py - API endpoints для событий

Дата создания: 22.11.2025
Версия: 1.0.0
Назначение: Endpoints для получения логов событий

Endpoints:
1. GET /api/events - список событий
2. GET /api/events/{id} - детали события
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import logging
from typing import Dict

from database import get_db
from models import ExchangeAPI, Event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["Events"])


# ===================== ENDPOINTS =====================

@router.get("")
async def get_events(
    exchange_id: int = Query(1, description="ID биржи"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    event_type: str = Query(None, description="Фильтр по типу события"),
    severity: str = Query(None, description="Фильтр по серьезности"),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Получить события
    
    Args:
        exchange_id: ID биржи
        limit: Максимум записей
        offset: Смещение
        event_type: Фильтр по типу (open, close, tp, sl, error)
        severity: Фильтр по серьезности (info, warning, error)
        db: БД сессия
        
    Returns:
        Dict: Список событий
    """
    try:
        # Проверяем что биржа существует
        exchange = db.query(ExchangeAPI).filter(
            ExchangeAPI.id == exchange_id
        ).first()
        
        if not exchange:
            raise HTTPException(
                status_code=404,
                detail=f"Exchange {exchange_id} not found"
            )
        
        # Получаем события
        query = db.query(Event).filter(
            Event.exchange_id == exchange_id
        )
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        if severity:
            query = query.filter(Event.severity == severity)
        
        events = query.order_by(
            Event.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        result = []
        for event in events:
            result.append({
                "id": event.id,
                "event_type": event.event_type,
                "title": event.title,
                "description": event.description,
                "severity": event.severity,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "position_id": event.position_id,
            })
        
        return {
            "status": "success",
            "exchange": exchange.exchange,
            "events": result,
            "total": len(result),
            "limit": limit,
            "offset": offset,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting events: {str(e)}"
        )


@router.get("/{event_id}")
async def get_event(
    event_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Получить детали события
    
    Args:
        event_id: ID события
        db: БД сессия
        
    Returns:
        Dict: Детали события
    """
    try:
        event = db.query(Event).filter(
            Event.id == event_id
        ).first()
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail=f"Event {event_id} not found"
            )
        
        return {
            "status": "success",
            "event": {
                "id": event.id,
                "exchange_id": event.exchange_id,
                "position_id": event.position_id,
                "event_type": event.event_type,
                "title": event.title,
                "description": event.description,
                "data": event.data,
                "severity": event.severity,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting event: {str(e)}"
        )
