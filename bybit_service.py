"""
bybit_service.py - Сервис для работы с Bybit API (ИСПРАВЛЕННАЯ v1.2)

Дата создания: 23.11.2025
Версия: 1.2.0 (FIXED - recv_window increased)
Назначение: Интеграция с Bybit API для получения данных аккаунта и позиций

ОСНОВНЫЕ МЕТОДЫ:
1. get_bybit_client() - инициализация клиента
2. get_account_info() - баланс, equity, available balance
3. get_positions() - открытые позиции
4. validate_credentials() - проверка ключей
"""

from pybit.unified_trading import HTTP
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_bybit_client = None
_testnet_mode = False


class BybitClientWrapper:
    """Обертка над Bybit клиентом с исправленными параметрами"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Инициализируем клиент с УВЕЛИЧЕННЫМ recv_window
        self.client = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
            recv_window=15000,  # УВЕЛИЧИЛИ с 5000 до 15000ms!
        )
        logger.info(f"✅ Bybit API initialized ({'testnet' if testnet else 'live'})")
    
    def validate_credentials(self) -> bool:
        """Проверить что ключи валидны"""
        try:
            result = self.client.get_wallet_balance(accountType="UNIFIED")
            if result and result.get('retCode') == 0:
                logger.info("✅ Bybit credentials validated")
                return True
            else:
                logger.error(f"Bybit validation error: {result}")
                return False
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return False
    
    def get_account_info(self) -> Dict:
        """
        Получить информацию об аккаунте
        
        Returns:
            Dict с ключами:
            - total_wallet_balance
            - total_equity
            - available_balance
            - total_unrealised_loss
        """
        try:
            result = self.client.get_wallet_balance(accountType="UNIFIED")
            
            if result and result.get('retCode') == 0:
                data = result.get('result', {})
                list_data = data.get('list', [{}])[0]
                
                return {
                    "total_wallet_balance": float(list_data.get('totalWalletBalance', 0)),
                    "total_equity": float(list_data.get('totalEquity', 0)),
                    "available_balance": float(list_data.get('totalAvailableBalance', 0)),
                    "total_unrealised_loss": float(list_data.get('totalUnrealisedLoss', 0)),
                }
            else:
                logger.warning(f"Empty or error response: {result}")
                return {
                    "total_wallet_balance": 0,
                    "total_equity": 0,
                    "available_balance": 0,
                    "total_unrealised_loss": 0,
                }
        
        except Exception as e:
            logger.error(f"Failed to get account info: {e}", exc_info=True)
            return {
                "total_wallet_balance": 0,
                "total_equity": 0,
                "available_balance": 0,
                "total_unrealised_loss": 0,
            }
    
    def get_positions(self) -> list:
        """Получить открытые позиции"""
        try:
            result = self.client.get_open_orders(category="linear")
            
            if result and result.get('retCode') == 0:
                data = result.get('result', {})
                return data.get('list', [])
            else:
                logger.warning(f"No positions: {result}")
                return []
        
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []


# ==================== ГЛОБАЛЬНЫЕ ФУНКЦИИ ====================

def get_bybit_client(api_key: str, api_secret: str, testnet: bool = False) -> BybitClientWrapper:
    """
    Получить или создать Bybit клиент
    
    Args:
        api_key: API ключ Bybit
        api_secret: API секрет Bybit
        testnet: Использовать testnet (по умолчанию False)
    
    Returns:
        BybitClientWrapper
    """
    global _bybit_client, _testnet_mode
    
    # Если параметры изменились, создаем новый клиент
    if (_bybit_client is None or 
        _testnet_mode != testnet or 
        _bybit_client.api_key != api_key):
        
        try:
            _bybit_client = BybitClientWrapper(api_key, api_secret, testnet)
            _testnet_mode = testnet
            logger.info("✅ New Bybit client created")
        except Exception as e:
            logger.error(f"Failed to create Bybit client: {e}")
            raise
    
    return _bybit_client


def reset_bybit_client():
    """Сбросить клиент (для переключения ключей)"""
    global _bybit_client
    _bybit_client = None
    logger.info("🔄 Bybit client reset")


def get_account_balance() -> Dict:
    """Удобная функция для получения баланса"""
    if not _bybit_client:
        return {
            "total_wallet_balance": 0,
            "total_equity": 0,
            "available_balance": 0,
            "total_unrealised_loss": 0,
        }
    
    return _bybit_client.get_account_info()


def get_positions() -> list:
    """Удобная функция для получения позиций"""
    if not _bybit_client:
        return []
    
    return _bybit_client.get_positions()
