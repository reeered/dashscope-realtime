import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable

import websockets


@dataclass(frozen=True)
class TTSConfig:
    model: str = "cosyvoice-v1"
    voice: str = "longxiaoxia"
    volume: int = 80
    speech_rate: float = 1.0
    pitch_rate: float = 1.0
    sample_rate: int = 22050
    audio_format: str = "pcm"


class DashScopeRealtimeTTS:
    def __init__(
            self,
            api_key: str,
            config: TTSConfig = TTSConfig(),
            url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/",
            on_audio_chunk: Optional[Callable[[bytes], None]] = None,
            on_end: Optional[Callable[[], None]] = None,
            on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.api_key = api_key
        self.config = config
        self.url = url
        self.task_id = uuid.uuid4().hex[:32]
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

        # Callbacks
        self.on_audio_chunk = on_audio_chunk
        self.on_end = on_end
        self.on_error = on_error

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        if self.ws:
            return
        self.ws = await websockets.connect(
            self.url,
            additional_headers={"Authorization": f"Bearer {self.api_key}"}
        )
        await self._send_run_task()
        asyncio.create_task(self._receive_loop())

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def say(self, text: str):
        if not self.ws:
            await self.connect()
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
        if self.ws:
            await self.ws.send(json.dumps({
                "header": {
                    "action": "finish-task",
                    "task_id": self.task_id,
                    "streaming": "duplex"
                },
                "payload": {"input": {}}
            }))

    async def interrupt(self):
        await self.disconnect()
        await self.connect()

    async def _send_run_task(self):
        params = {
            "text_type": "PlainText",
            "voice": self.config.voice,
            "format": self.config.audio_format,
            "sample_rate": self.config.sample_rate,
            "volume": self.config.volume,
            "rate": self.config.speech_rate,
            "pitch": self.config.pitch_rate
        }

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
                "parameters": params,
                "input": {}
            }
        }))

    async def _receive_loop(self):
        try:
            async for msg in self.ws:
                if isinstance(msg, bytes):
                    if self.on_audio_chunk:
                        self.on_audio_chunk(msg)
                else:
                    data = json.loads(msg)
                    event = data.get("header", {}).get("event")

                    if event == "task-finished":
                        if self.on_end:
                            self.on_end()

                    elif event == "task-failed":
                        if self.on_error:
                            self.on_error(RuntimeError(data.get("payload", {}).get("message", "Unknown error")))

        except Exception as e:
            if self.on_error:
                self.on_error(e)
