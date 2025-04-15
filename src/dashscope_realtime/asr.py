import asyncio
import json
import uuid
from typing import Optional, Callable, Awaitable

from websockets.asyncio.client import connect
from .config import DASHSCOPE_WS_URL, ASRConfig, logger


class DashScopeRealtimeASR:
    def __init__(
        self,
        api_key: str,
        config: ASRConfig = ASRConfig(),
        url: str = DASHSCOPE_WS_URL,
    ):
        self.api_key = api_key
        self.config = config
        self.url = url

        self.task_id = uuid.uuid4().hex
        self.ws = None
        self.result_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self.on_speech_end: Optional[Callable[[str], Awaitable[None]]] = None
        self._receive_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.finish()

    async def connect(self):
        self.ws = await connect(
            self.url,
            additional_headers={
                "Authorization": f"bearer {self.api_key}",
                "X-DashScope-DataInspection": "enable",
            },
        )
        await self._send_run_task()
        self._receive_task = asyncio.create_task(self._receive())

    async def _send_run_task(self):
        message = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": self.config.model,
                "parameters": {
                    "sample_rate": self.config.sample_rate,
                    "format": self.config.audio_format,
                    "semantic_punctuation_enabled": True,
                },
                "input": {},
            },
        }
        await self.ws.send(json.dumps(message))

    async def send_audio_chunk(self, data: bytes):
        if not self.ws:
            raise RuntimeError("WebSocket not connected")
        await self.ws.send(data)

    async def finish(self):
        if not self.ws:
            return
        message = {
            "header": {
                "action": "finish-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {
                "input": {},
            },
        }
        await self.ws.send(json.dumps(message))
        await self._receive_task
        await self.ws.close()

    async def _receive(self):
        async for message in self.ws:
            data = json.loads(message)
            event = data.get("header", {}).get("event")

            if event == "task-started":
                logger.info("ASR task started")

            elif event == "result-generated":
                sentence = data["payload"]["output"]["sentence"]
                text = sentence["text"]
                is_final = sentence.get("sentence_end", False)

                logger.info("ASR Result: %s (final=%s)", text, is_final)

                if self.result_callback:
                    await self.result_callback(text)

                if is_final and self.on_speech_end:
                    await self.on_speech_end(text)

            elif event == "task-finished":
                logger.info("ASR task finished")
                break

            elif event == "task-failed":
                error_msg = data["header"].get("error_message", "Unknown Error")
                logger.error("ASR task failed: %s", error_msg)
                break
