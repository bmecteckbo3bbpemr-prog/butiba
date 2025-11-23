"""
database.py - Инициализация БД

Дата создания: 22.11.2025
Версия: 1.0.0
Назначение: SQLAlchemy engine и session manager

Основные этапы:
1. Создаём подключение к SQLite
2. Инициализируем session factory
3. Создаём все таблицы из models.py
4. Предоставляем dependency injection для routes
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging

from config import get_settings
from models import Base

logger = logging.getLogger(__name__)
settings = get_settings()

# ==================== DATABASE CONFIGURATION ====================

# Создаём engine
# Для SQLite используем StaticPool чтобы избежать проблем с потоками
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.DEBUG,  # Логирование SQL запросов в debug mode
)

# Создаём session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# ==================== DATABASE INITIALIZATION ====================

def init_db() -> None:
    """
    Инициализировать БД - создать все таблицы
    
    Вызывается при запуске приложения
    """
    try:
        # Создаём все таблицы из Base.metadata
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise


# ==================== DEPENDENCY INJECTION ====================

def get_db() -> Session:
    """
    Dependency для получения БД сессии в routes
    
    Usage:
        @app.get("/api/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    
    Yields:
        Session: SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== CONNECTION HELPERS ====================

def get_db_session() -> Session:
    """
    Получить БД сессию (не для routes, для сервисов)
    
    Usage:
        db = get_db_session()
        try:
            # работаем с db
        finally:
            db.close()
    
    Returns:
        Session: SQLAlchemy session
    """
    return SessionLocal()


def close_db() -> None:
    """Закрыть все подключения"""
    engine.dispose()
    logger.info("Database connections closed")
