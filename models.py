"""
models/__init__.py & models/position.py - SQLAlchemy модели для БД

Дата создания: 22.11.2025
Версия: 1.0.0
Назначение: Определение структуры данных в базе данных

Модели:
1. ExchangeAPI - Хранение API ключей (зашифрованные)
2. Position - Открытая позиция на бирже
3. Trade - История закрытых сделок
4. Event - Лог всех событий
5. ClosingLogic - Настройки логики закрытия
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Boolean, Text, Enum, Index, ForeignKey, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


# ===================== EXCHANGE API =====================

class ExchangeAPI(Base):
    """
    Модель для хранения API ключей биржи
    
    ⚠️ ВАЖНО: API ключи ВСЕГДА должны быть зашифрованы в БД!
    """
    __tablename__ = "exchange_api"
    __table_args__ = (
        Index('idx_exchange', 'exchange'),
    )
    
    id = Column(Integer, primary_key=True)
    
    # Название биржи: "bybit", "okx", "binance"
    exchange = Column(String(50), unique=True, nullable=False)
    
    # API KEY (зашифрованный!)
    api_key_encrypted = Column(Text, nullable=False)
    
    # API SECRET (зашифрованный!)
    api_secret_encrypted = Column(Text, nullable=False)
    
    # Passphrase (для OKX, опционально, зашифрованный!)
    passphrase_encrypted = Column(Text, nullable=True)
    
    # Использовать тестовую сеть?
    testnet = Column(Boolean, default=False)
    
    # Статус подключения
    is_connected = Column(Boolean, default=False)
    last_connection_check = Column(DateTime, nullable=True)
    connection_error = Column(Text, nullable=True)
    
    # Статистика
    total_positions = Column(Integer, default=0)
    closed_positions = Column(Integer, default=0)
    failed_closures = Column(Integer, default=0)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    positions = relationship("Position", back_populates="exchange_api", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="exchange_api", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="exchange_api", cascade="all, delete-orphan")
    closing_logic = relationship("ClosingLogic", back_populates="exchange_api", cascade="all, delete-orphan", uselist=False)
    
    def __repr__(self):
        return f"<ExchangeAPI {self.exchange}>"


# ===================== POSITION =====================

class Position(Base):
    """
    Модель для открытой позиции на бирже
    """
    __tablename__ = "positions"
    __table_args__ = (
        Index('idx_exchange_symbol', 'exchange_id', 'symbol'),
        Index('idx_is_open', 'is_open'),
    )
    
    id = Column(Integer, primary_key=True)
    
    # FK на биржу
    exchange_id = Column(Integer, ForeignKey("exchange_api.id"), nullable=False)
    exchange_api = relationship("ExchangeAPI", back_populates="positions")
    
    # Информация о позиции
    symbol = Column(String(50), nullable=False)  # "BTC/USDT", "ETH-USDT"
    side = Column(String(10), nullable=False)     # "buy"/"sell" или "long"/"short"
    size = Column(Float, nullable=False)          # Размер позиции
    entry_price = Column(Float, nullable=True)    # Цена входа
    current_price = Column(Float, nullable=True)  # Текущая цена
    
    # P&L
    pnl = Column(Float, default=0)                # Прибыль/убыток в USD
    pnl_percent = Column(Float, default=0)        # Прибыль/убыток в %
    
    # Take Profit & Stop Loss
    take_profit = Column(Float, nullable=True)    # TP цена
    stop_loss = Column(Float, nullable=True)      # SL цена
    
    # Статус
    is_open = Column(Boolean, default=True)       # Открыта ли позиция?
    
    # Логика закрытия
    has_tp = Column(Boolean, default=False)       # Есть ли TP?
    opened_at = Column(DateTime, default=datetime.utcnow)
    needs_auto_close = Column(Boolean, default=False)  # Нужно ли закрывать?
    close_reason = Column(String(100), nullable=True)  # Причина закрытия
    
    # Идентификаторы
    position_id = Column(String(100), nullable=True)  # ID позиции на бирже
    order_id = Column(String(100), nullable=True)     # ID ордера
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    trades = relationship("Trade", back_populates="position", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="position", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Position {self.symbol} {self.side} {self.size}>"


# ===================== TRADE =====================

class Trade(Base):
    """
    Модель для закрытой сделки (история)
    """
    __tablename__ = "trades"
    __table_args__ = (
        Index('idx_exchange_closed', 'exchange_id', 'closed_at'),
        Index('idx_status', 'status'),
    )
    
    id = Column(Integer, primary_key=True)
    
    # FK на биржу и позицию
    exchange_id = Column(Integer, ForeignKey("exchange_api.id"), nullable=False)
    exchange_api = relationship("ExchangeAPI", back_populates="trades")
    
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    position = relationship("Position", back_populates="trades")
    
    # Информация о сделке
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    
    # P&L
    pnl = Column(Float)                 # Прибыль/убыток
    pnl_percent = Column(Float)         # В процентах
    commission = Column(Float, default=0)
    net_pnl = Column(Float)             # После комиссии
    
    # Время
    opened_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer)
    
    # Статус
    status = Column(String(50), default="closed")  # "closed", "failed", "partial"
    close_reason = Column(String(200), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade {self.symbol} {self.side} PnL={self.pnl}>"


# ===================== EVENT =====================

class EventType(enum.Enum):
    """Типы событий"""
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"
    TP_SET = "tp_set"
    TP_REMOVED = "tp_removed"
    AUTO_CLOSE_TRIGGERED = "auto_close_triggered"
    ERROR_CLOSE_FAILED = "error_close_failed"
    ERROR_API = "error_api"
    API_KEY_ADDED = "api_key_added"
    SETTINGS_CHANGED = "settings_changed"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    INFO = "info"


class Event(Base):
    """
    Модель для логирования всех событий
    """
    __tablename__ = "events"
    __table_args__ = (
        Index('idx_exchange_created', 'exchange_id', 'created_at'),
        Index('idx_event_type', 'event_type'),
    )
    
    id = Column(Integer, primary_key=True)
    
    # FK на биржу и позицию (опционально)
    exchange_id = Column(Integer, ForeignKey("exchange_api.id"), nullable=False)
    exchange_api = relationship("ExchangeAPI", back_populates="events")
    
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    position = relationship("Position", back_populates="events")
    
    # Информация о событии
    event_type = Column(Enum(EventType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Данные события (JSON-like)
    data = Column(Text, nullable=True)  # JSON string
    
    # Уровень важности
    severity = Column(String(20), default="info")  # "info", "warning", "error", "critical"
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Event {self.event_type} at {self.created_at}>"


# ===================== CLOSING LOGIC =====================

class ClosingLogic(Base):
    """
    Модель для настроек логики автоматического закрытия позиций
    """
    __tablename__ = "closing_logic"
    
    id = Column(Integer, primary_key=True)
    
    # FK на биржу
    exchange_id = Column(Integer, ForeignKey("exchange_api.id"), unique=True, nullable=False)
    exchange_api = relationship("ExchangeAPI", back_populates="closing_logic")
    
    # Мод закрытия
    # "disabled" - не закрывать
    # "no_tp_timeout" - закрывать если нет TP через N секунд
    # "profit_target" - закрывать если прибыль > X%
    # "loss_limit" - закрывать если убыток < X%
    # "manual" - только ручное закрытие
    mode = Column(String(50), default="disabled")
    
    # Параметры для режима "no_tp_timeout"
    timeout_seconds = Column(Integer, default=60)
    
    # Параметры для режима "profit_target"
    profit_percent = Column(Float, default=5.0)
    
    # Параметры для режима "loss_limit"
    loss_percent = Column(Float, default=-5.0)
    
    # Опции
    enabled = Column(Boolean, default=False)
    retry_on_fail = Column(Boolean, default=True)
    max_retries = Column(Integer, default=3)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)  # Кто изменил
    
    def __repr__(self):
        return f"<ClosingLogic {self.exchange_api.exchange} mode={self.mode}>"


# ===================== SETTINGS =====================

class Settings(Base):
    """
    Модель для глобальных настроек приложения
    """
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    
    # Ключ настройки
    key = Column(String(100), unique=True, nullable=False)
    
    # Значение (JSON string для сложных типов)
    value = Column(Text, nullable=False)
    
    # Тип значения
    value_type = Column(String(50))  # "string", "integer", "float", "boolean", "json"
    
    # Описание
    description = Column(Text, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Settings {self.key}={self.value}>"
