"""Media analysis providers and routers."""

from .audio import OpenAICompatibleSpeechProvider
from .base import ImageAnalysisProvider, SpeechToTextProvider, VideoAnalysisProvider
from .image import MiniMaxImageProvider, OpenAICompatibleImageProvider, create_image_analysis_provider
from .video import OpenAICompatibleVideoProvider
from .router import MediaRouter

__all__ = [
    "ImageAnalysisProvider",
    "SpeechToTextProvider",
    "VideoAnalysisProvider",
    "MediaRouter",
    "MiniMaxImageProvider",
    "OpenAICompatibleImageProvider",
    "OpenAICompatibleSpeechProvider",
    "OpenAICompatibleVideoProvider",
    "create_image_analysis_provider",
]
