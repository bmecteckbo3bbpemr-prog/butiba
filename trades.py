"""
routes/trades.py - API endpoints для истории сделок (FIXED v1.1)

Дата создания: 23.11.2025
Версия: 1.1.0 (FIXED - removed trade_service dependency)
Назначение: Endpoints для получения истории сделок и статистики
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import logging
from typing import Dict

from database import get_db
from models import ExchangeAPI, Trade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.get("")
async def get_trades(
    exchange_id: int = Query(1, description="ID биржи"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    symbol: str = Query(None, description="Фильтр по символу"),
    status: str = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db)
) -> Dict:
    """Получить историю сделок"""
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
        
        # Строим запрос
        query = db.query(Trade).filter(Trade.exchange_id == exchange_id)
        
        # Фильтры
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        if status:
            query = query.filter(Trade.status == status)
        
        # Получаем сделки
        total = query.count()
        trades = query.order_by(Trade.closed_at.desc()).limit(limit).offset(offset).all()
        
        formatted_trades = [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "size": float(t.size),
                "entry_price": float(t.entry_price) if t.entry_price else 0,
                "exit_price": float(t.exit_price) if t.exit_price else 0,
                "pnl": float(t.pnl) if t.pnl else 0,
                "pnl_percent": float(t.pnl_percent) if t.pnl_percent else 0,
                "commission": float(t.commission) if t.commission else 0,
                "net_pnl": float(t.net_pnl) if t.net_pnl else 0,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                "duration_seconds": t.duration_seconds,
                "status": t.status,
                "close_reason": t.close_reason,
            }
            for t in trades
        ]
        
        logger.info(f"✅ Retrieved {len(formatted_trades)} trades")
        
        return {
            "status": "success",
            "exchange": exchange.exchange,
            "trades": formatted_trades,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting trades: {str(e)}"
        )


@router.get("/stats")
async def get_trade_stats(
    exchange_id: int = Query(1, description="ID биржи"),
    db: Session = Depends(get_db)
) -> Dict:
    """Получить статистику по сделкам"""
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
        
        # Получаем все сделки
        trades = db.query(Trade).filter(Trade.exchange_id == exchange_id).all()
        
        if not trades:
            return {
                "status": "success",
                "exchange": exchange.exchange,
                "stats": {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_pnl": 0,
                    "win_rate": 0,
                    "avg_win": 0,
                    "avg_loss": 0,
                    "profit_factor": 0,
                }
            }
        
        # Рассчитываем статистику
        total_pnl = sum(float(t.net_pnl or 0) for t in trades)
        winning_trades = [t for t in trades if float(t.net_pnl or 0) > 0]
        losing_trades = [t for t in trades if float(t.net_pnl or 0) < 0]
        
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        avg_win = (sum(float(t.net_pnl or 0) for t in winning_trades) / len(winning_trades)) if winning_trades else 0
        avg_loss = (sum(float(t.net_pnl or 0) for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        profit_factor = (abs(sum(float(t.net_pnl or 0) for t in winning_trades)) / abs(sum(float(t.net_pnl or 0) for t in losing_trades))) if losing_trades and sum(float(t.net_pnl or 0) for t in losing_trades) != 0 else 0
        
        logger.info(f"✅ Calculated stats for {len(trades)} trades")
        
        return {
            "status": "success",
            "exchange": exchange.exchange,
            "stats": {
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2),
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting trade stats: {str(e)}"
        )
