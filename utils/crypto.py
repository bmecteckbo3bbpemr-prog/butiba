import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

_encryption_manager = None

class EncryptionManager:
    def __init__(self, key: str = None):
        if key:
            # Используем ключ из переменной окружения
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            # Генерируем новый (ВРЕМЕННЫЙ)
            self.cipher = Fernet(Fernet.generate_key())
            logger.warning("⚠️  Generated new encryption key - not recommended for production!")
    
    def encrypt(self, data: str) -> str:
        """Шифрует строку"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Расшифровывает строку"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise

def get_encryption_manager() -> EncryptionManager:
    """Получить менеджер шифрования"""
    global _encryption_manager
    
    if _encryption_manager is None:
        # Пытаемся получить ключ из .env
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if encryption_key:
            logger.info("✅ Using encryption key from .env")
            _encryption_manager = EncryptionManager(encryption_key)
        else:
            logger.warning("⚠️  No ENCRYPTION_KEY in .env, using temporary key")
            _encryption_manager = EncryptionManager()
    
    return _encryption_manager
