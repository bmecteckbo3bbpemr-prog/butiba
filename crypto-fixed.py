"""
utils/crypto.py - Шифрование API ключей

Дата создания: 22.11.2025
Версия: 1.0.0
Назначение: Безопасное шифрование/дешифрование API ключей (Fernet)

Основные функции:
1. get_encryption_manager() - получить менеджер шифрования
2. encrypt() - зашифровать строку
3. decrypt() - расшифровать строку

Использует Fernet (симметричное шифрование) из cryptography
"""

import os
from cryptography.fernet import Fernet
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Менеджер для шифрования/дешифрования данных (Fernet)
    
    Использует симметричное шифрование для безопасного хранения
    API ключей в БД
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Инициализация менеджера шифрования
        
        Args:
            key: Ключ шифрования (если None - генерируется новый)
        """
        if key is None:
            # Генерируем новый ключ
            self.key = Fernet.generate_key()
            logger.warning("Generated new encryption key - not recommended for production!")
        else:
            self.key = key
        
        # Инициализируем Fernet с ключом
        self.cipher_suite = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Зашифровать строку
        
        Args:
            data: Строка для шифрования
            
        Returns:
            str: Зашифрованная строка (base64-кодированная)
        """
        try:
            # Кодируем строку в bytes
            data_bytes = data.encode('utf-8')
            
            # Шифруем
            encrypted_bytes = self.cipher_suite.encrypt(data_bytes)
            
            # Декодируем в строку (base64)
            encrypted_str = encrypted_bytes.decode('utf-8')
            
            return encrypted_str
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise Exception(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Расшифровать строку
        
        Args:
            encrypted_data: Зашифрованная строка (base64-кодированная)
            
        Returns:
            str: Исходная строка
        """
        try:
            # Кодируем строку в bytes
            encrypted_bytes = encrypted_data.encode('utf-8')
            
            # Дешифруем
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            
            # Декодируем в строку
            decrypted_str = decrypted_bytes.decode('utf-8')
            
            return decrypted_str
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise Exception(f"Failed to decrypt data: {str(e)}")


# ===================== GLOBAL INSTANCE =====================

_encryption_manager: Optional[EncryptionManager] = None


def init_encryption_manager(encryption_key: Optional[str] = None) -> EncryptionManager:
    """
    Инициализировать глобальный менеджер шифрования
    
    Args:
        encryption_key: Ключ шифрования (если None - генерируется новый)
        
    Returns:
        EncryptionManager: Инициализированный менеджер
    """
    global _encryption_manager
    
    key_bytes = None
    if encryption_key:
        # Если ключ - строка, кодируем его в bytes
        if isinstance(encryption_key, str):
            # Ключ должен быть base64-кодированным 32-байтным ключом
            try:
                key_bytes = encryption_key.encode('utf-8')
                # Проверяем что это валидный Fernet ключ
                Fernet(key_bytes)
            except Exception as e:
                logger.error(f"Invalid encryption key: {e}")
                # Генерируем новый
                key_bytes = None
        else:
            key_bytes = encryption_key
    
    _encryption_manager = EncryptionManager(key=key_bytes)
    return _encryption_manager


def get_encryption_manager() -> EncryptionManager:
    """
    Получить глобальный менеджер шифрования
    
    Если менеджер не инициализирован - инициализирует с новым ключом
    
    Returns:
        EncryptionManager: Менеджер шифрования
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        # Пытаемся загрузить ключ из переменной окружения
        encryption_key = os.getenv('ENCRYPTION_KEY')
        _encryption_manager = init_encryption_manager(encryption_key)
    
    return _encryption_manager


def generate_key() -> str:
    """
    Сгенерировать новый ключ шифрования
    
    Используйте этот ключ в ENCRYPTION_KEY переменной окружения
    
    Returns:
        str: Новый ключ (base64-кодированный)
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')
