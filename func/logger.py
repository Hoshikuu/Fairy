import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

# GRACIAS CLAUDE AI POR HACERME ESTO QUE HARIA SIN TI

class BotLogger:
    """
    Sistema de logging centralizado para el bot de Discord.
    """
    
    _instance: Optional['BotLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'BotLogger':
        """Implementa el patrón Singleton para asegurar una sola instancia."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa el logger solo una vez."""
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Configura el sistema de logging centralizado."""
        # Crear directorio de logs si no existe
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Configurar el logger principal
        self._logger = logging.getLogger('DiscordBot')
        self._logger.setLevel(logging.DEBUG)
        
        # Evitar duplicar handlers si ya están configurados
        if self._logger.handlers:
            return
        
        # Formato detallado para los logs
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(name)s.%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo con rotación (max 10MB, mantener 5 archivos)
        file_handler = RotatingFileHandler(
            f'{logs_dir}/bot.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Handler para archivos de error separados
        error_handler = RotatingFileHandler(
            f'{logs_dir}/errors.log',
            maxBytes=5*1024*1024,   # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Handler para consola (solo WARNING y superiores)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Agregar handlers al logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(error_handler)
        self._logger.addHandler(console_handler)
        
        # Configurar nivel para librerías externas (evitar spam)
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.gateway').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Obtiene un logger hijo con el nombre especificado.
        
        Args:
            name: Nombre del módulo/archivo (usa __name__ del archivo que llama)
        
        Returns:
            Logger configurado
        """
        if name:
            # Simplificar el nombre del módulo para los logs
            simplified_name = name.split('.')[-1] if '.' in name else name
            return self._logger.getChild(simplified_name)
        return self._logger
    
    def set_level(self, level: str) -> None:
        """
        Cambia el nivel de logging dinámicamente.
        
        Args:
            level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self._logger.setLevel(level_map[level.upper()])
            self._logger.info(f"Nivel de logging cambiado a {level.upper()}")


# Función de conveniencia para obtener logger
def get_logger(name: str = None) -> logging.Logger:
    """
    Función global para obtener el logger centralizado.
    
    Usage:
        from func.logger import get_logger
        logger = get_logger(__name__)
    """
    bot_logger = BotLogger()
    return bot_logger.get_logger(name)


# Funciones de conveniencia para logging directo
def log_info(message: str, module_name: str = "Bot") -> None:
    """Log mensaje de información."""
    logger = get_logger(module_name)
    logger.info(message)

def log_error(message: str, module_name: str = "Bot", exc_info: bool = True) -> None:
    """Log mensaje de error."""
    logger = get_logger(module_name)
    logger.error(message, exc_info=exc_info)

def log_warning(message: str, module_name: str = "Bot") -> None:
    """Log mensaje de advertencia."""
    logger = get_logger(module_name)
    logger.warning(message)

def log_debug(message: str, module_name: str = "Bot") -> None:
    """Log mensaje de debug."""
    logger = get_logger(module_name)
    logger.debug(message)


# Inicializar el logger al importar el módulo
_bot_logger = BotLogger()