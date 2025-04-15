import asyncio
import json
import uuid
from typing import Optional, Callable, Awaitable, Union

from websockets.asyncio.client import connect

from .config import DASHSCOPE_WS_URL, TTSConfig, logger


class DashScopeRealtimeTTS:
    def __init__(
        self,
        api_key: str,
        config: TTSConfig = TTSConfig(),
        url: str = DASHSCOPE_WS_URL,
    ):
        self.api_key = api_key
        self.config = config
        self.url = url

        self.task_id = uuid.uuid4().hex
        self.ws = None
        self._on_audio_chunk: Optional[Callable[[bytes], Awaitable[None]]] = None
        self._task_started = asyncio.Event()
        self._receive_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self, on_audio_chunk: Optional[Callable[[bytes], Awaitable[None]]] = None):
        self.ws = await connect(
            self.url,
            additional_headers={
                "Authorization": f"bearer {self.api_key}",
                "X-DashScope-DataInspection": "enable",
            },
        )
        self._on_audio_chunk = on_audio_chunk
        await self._send_run_task()
        self._receive_task = asyncio.create_task(self._receive())

    async def _send_run_task(self):
        msg = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex",
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
                    "rate": self.config.rate,
                    "pitch": self.config.pitch,
                },
                "input": {},
            },
        }
        await self.ws.send(json.dumps(msg))

    async def send_text(self, text: str):
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        await self._task_started.wait()

        msg = {
            "header": {
                "action": "continue-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {
                "input": {
                    "text": text,
                }
            },
        }
        await self.ws.send(json.dumps(msg))

    async def finish(self):
        if not self.ws:
            return

        await self._task_started.wait()

        msg = {
            "header": {
                "action": "finish-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {
                "input": {},
            },
        }
        await self.ws.send(json.dumps(msg))
        await self._receive_task

    async def _receive(self):
        async for data in self.ws:
            if isinstance(data, bytes):
                if self._on_audio_chunk:
                    await self._on_audio_chunk(data)
            else:
                msg = json.loads(data)
                event = msg.get("header", {}).get("event")

                if event == "task-started":
                    logger.info("TTS task started")
                    self._task_started.set()

                elif event == "task-finished":
                    logger.info("TTS task finished")
                    await self.ws.close()
                    break

                elif event == "task-failed":
                    error_msg = msg.get("header", {}).get("error_message", "Unknown Error")
                    logger.error("TTS task failed: %s", error_msg)
                    raise RuntimeError(f"TTS task failed: {error_msg}")

    async def close(self):
        if self.ws:
            await self.ws.close()
