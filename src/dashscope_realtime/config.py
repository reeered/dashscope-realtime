from dataclasses import dataclass
import logging

# WebSocket URL
DASHSCOPE_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"


@dataclass(frozen=True)
class ASRConfig:
    model: str = "paraformer-realtime-v2"
    sample_rate: int = 16000
    audio_format: str = "wav"


@dataclass(frozen=True)
class TTSConfig:
    model: str = "cosyvoice-v1"
    sample_rate: int = 16000
    audio_format: str = "pcm"
    voice: str = "longwan"
    volume: int = 50,
    rate: float = 1.0,
    pitch: float = 1.0


logger = logging.getLogger("dashscope_realtime")
logger.setLevel(logging.INFO)
