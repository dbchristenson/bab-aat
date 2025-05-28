import threading
from typing import Optional

from loguru import logger
from paddleocr import PaddleOCR


class ModelManager:
    """Singleton class to manage shared PaddleOCR model instances."""

    _instance: Optional["ModelManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._models = {}
                    cls._instance._model_lock = threading.Lock()
        return cls._instance

    def get_model(self, config_key: str = "default", **kwargs) -> PaddleOCR:
        """
        Get or create a PaddleOCR model instance.

        Args:
            config_key: Unique key for this model configuration
            **kwargs: PaddleOCR initialization parameters

        Returns:
            PaddleOCR: Shared model instance
        """
        with self._model_lock:
            if config_key not in self._models:
                logger.info(f"Creating new PaddleOCR model: {config_key}")
                # Default PaddleOCR settings for memory efficiency
                default_kwargs = {
                    "use_angle_cls": True,
                    "lang": "en",
                    "show_log": False,
                    "use_gpu": False,  # CPU usage to avoid GPU memory issues
                }
                default_kwargs.update(kwargs)
                self._models[config_key] = PaddleOCR(**default_kwargs)
                logger.info(f"Successfully created model: {config_key}")
            else:
                logger.debug(f"Reusing existing model: {config_key}")

            return self._models[config_key]

    def clear_models(self):
        """Clear all cached models to free memory."""
        with self._model_lock:
            for key in list(self._models.keys()):
                logger.info(f"Clearing model: {key}")
                del self._models[key]
            self._models.clear()
            logger.info("All models cleared from cache")


# Global instance
model_manager = ModelManager()
