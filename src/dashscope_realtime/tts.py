import asyncio
import websockets
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class TTSConfig:
    model: str = "cosyvoice-v1"
    voice: str = "longxiaoxia"
    volume: int = 80
    speech_rate: float = 1.0
    pitch_rate: float = 1.0
    sample_rate: int = 22050
    audio_format: str = "pcm"


class DashScopeTTSClient:
    def __init__(self, api_key: str, config: TTSConfig = TTSConfig()):
        self.api_key = api_key
        self.config = config

        self.ws = None
        self.task_id = uuid.uuid4().hex[:32]

        # Callbacks
        self.on_audio_chunk: Optional[Callable[[bytes], None]] = None
        self.on_end: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    async def connect(self):
        self.ws = await websockets.connect(
            "wss://dashscope.aliyuncs.com/api-ws/v1/inference/",
            additional_headers={"Authorization": f"Bearer {self.api_key}"}
        )
        await self._send_run_task()
        asyncio.create_task(self._recv())

    async def disconnect(self):
        if self.ws:
            await self.ws.close()

    async def say(self, text: str):
        await self.ws.send(json.dumps({
            "header": {
                "action": "continue-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {"text": text}
            }
        }))

    async def finish(self):
        await self.ws.send(json.dumps({
            "header": {
                "action": "finish-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {}
            }
        }))

    async def _send_run_task(self):
        await self.ws.send(json.dumps({
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "task_group": "audio",
                "task": "tts",
                "function": "SpeechSynthesizer",
                "model": self.config.model,
                "parameters": {
                    "text_type": "PlainText",
                    "voice": self.config.voice,
                    "format": self.config.audio_format,
                    "sample_rate": self.config.sample_rate,
                    "volume": self.config.volume,
                    "rate": self.config.speech_rate,
                    "pitch": self.config.pitch_rate
                },
                "input": {}
            }
        }))

    async def _recv(self):
        try:
            async for msg in self.ws:
                if isinstance(msg, bytes):
                    if self.on_audio_chunk:
                        self.on_audio_chunk(msg)
                else:
                    data = json.loads(msg)
                    event = data["header"].get("event")
                    if event == "task-finished":
                        if self.on_end:
                            self.on_end()
                    elif event == "task-failed":
                        if self.on_error:
                            self.on_error(data)
        except Exception as e:
            if self.on_error:
                self.on_error(e)

    async def interrupt(self):
        try:
            await self.disconnect()
            await self.connect()
        except Exception as e:
            if self.on_error:
                self.on_error(e)
