"""
Config.py - Конфигурация приложения (ИСПРАВЛЕННАЯ v1.1)

Дата создания: 22.11.2025
Версия: 1.1.0 (FIXED - Pydantic2 model_config)
Назначение: Централизованное управление конфигурацией приложения
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    Главные настройки приложения
    
    Загружает переменные окружения из .env файла
    Все значения имеют default значения для разработки
    """

    # ==================== APP SETTINGS ====================
    APP_NAME: str = "Slezun Web Dashboard"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, staging, production

    # ==================== SERVER SETTINGS ====================
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    RELOAD: bool = True  # Hot reload для разработки

    # ==================== DATABASE SETTINGS ====================
    # SQLite для разработки (автоматически создается)
    DATABASE_URL: str = "sqlite:///./slezun.db"
    # Для production используйте PostgreSQL:
    # DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/slezun"

    # ==================== SECURITY SETTINGS ====================
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Encryption key для API ключей (32 байта для Fernet)
    ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"
    
    # CORS settings
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # ==================== WEBSOCKET SETTINGS ====================
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # секунды
    WEBSOCKET_HEARTBEAT_TIMEOUT: int = 10  # секунды

    # ==================== BYBIT SETTINGS ====================
    BYBIT_TESTNET: bool = False  # True для тестовой сети
    BYBIT_API_BASE_URL: str = "https://api.bybit.com"
    BYBIT_TESTNET_BASE_URL: str = "https://testnet.bybit.com"

    # ==================== MONITORING SETTINGS ====================
    # Интервал проверки позиций (секунды)
    MONITOR_CHECK_INTERVAL: int = 10
    
    # Интервал обновления UI (секунды)
    UI_UPDATE_INTERVAL: int = 1
    
    # Максимум записей событий в памяти до сохранения в БД
    MAX_EVENTS_IN_MEMORY: int = 1000

    # ==================== LOGGING SETTINGS ====================
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_FILE: str = "slezun.log"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT: int = 5

    # ==================== API RATE LIMITING ====================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # requests
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # ==================== CLOSE POSITION LOGIC (DEFAULT) ====================
    # По умолчанию НЕ закрывать позиции автоматически
    CLOSE_LOGIC_ENABLED: bool = False
    
    # Варианты логики:
    # 1. "no_close" - не закрывать (DEFAULT)
    # 2. "no_tp_timeout" - закрывать если нет TP через N секунд
    # 3. "profit_target" - закрывать если прибыль > X%
    # 4. "loss_limit" - закрывать если убыток > X%
    CLOSE_LOGIC_MODE: str = "no_close"
    
    # Для режима "no_tp_timeout"
    CLOSE_LOGIC_TIMEOUT_SECONDS: int = 60
    
    # Для режима "profit_target"
    CLOSE_LOGIC_PROFIT_PERCENT: float = 5.0
    
    # Для режима "loss_limit"
    CLOSE_LOGIC_LOSS_PERCENT: float = -5.0

    # ==================== PYDANTIC CONFIG ====================
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",  # ← РАЗРЕШАЕМ EXTRA ПОЛЯ ИЗ .env
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Получить настройки приложения (кэшируется)
    
    Returns:
        Settings: Объект настроек
    """
    return Settings()


# Создаем директорию для логов если не существует
settings = get_settings()
os.makedirs(settings.LOG_DIR, exist_ok=True)
