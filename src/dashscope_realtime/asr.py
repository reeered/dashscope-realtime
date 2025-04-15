import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Callable

import websockets


@dataclass(frozen=True)
class DashScopeASRConfig:
    model: str = "paraformer-realtime-v2"
    sample_rate: int = 16000
    format: str = "wav"
    vocabulary_id: Optional[str] = None
    phrase_id: Optional[str] = None
    disfluency_removal_enabled: bool = False
    language_hints: List[str] = field(default_factory=lambda: ["zh", "en"])
    semantic_punctuation_enabled: bool = False
    max_sentence_silence: int = 800
    punctuation_prediction_enabled: bool = True
    heartbeat: bool = False
    inverse_text_normalization_enabled: bool = True


class DashScopeRealtimeASR:
    def __init__(
        self,
        api_key: str,
        config: DashScopeASRConfig = DashScopeASRConfig(),
        url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/",
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_sentence_end: Optional[Callable[[str], None]] = None,
    ):
        self.api_key = api_key
        self.config = config
        self.url = url
        self.task_id = uuid.uuid4().hex[:32]
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

        self.on_partial = on_partial
        self.on_final = on_final
        self.on_error = on_error
        self.on_sentence_end = on_sentence_end

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

    async def send_audio(self, data: bytes):
        if not self.ws:
            await self.connect()
        await self.ws.send(data)

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

    async def _send_run_task(self):
        params = self._build_parameters()
        await self.ws.send(json.dumps({
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": self.config.model,
                "parameters": params,
                "input": {}
            }
        }))

    def _build_parameters(self):
        params = {
            "sample_rate": self.config.sample_rate,
            "format": self.config.format,
            "disfluency_removal_enabled": self.config.disfluency_removal_enabled,
            "language_hints": self.config.language_hints,
            "semantic_punctuation_enabled": self.config.semantic_punctuation_enabled,
            "max_sentence_silence": self.config.max_sentence_silence,
            "punctuation_prediction_enabled": self.config.punctuation_prediction_enabled,
            "heartbeat": self.config.heartbeat,
            "inverse_text_normalization_enabled": self.config.inverse_text_normalization_enabled,
        }
        if self.config.vocabulary_id:
            params["vocabulary_id"] = self.config.vocabulary_id
        if self.config.phrase_id:
            params["phrase_id"] = self.config.phrase_id
        return params

    async def _receive_loop(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                header = data.get("header", {})
                event = header.get("event")

                if event == "result-generated":
                    sentence = data["payload"]["output"]["sentence"]
                    text = sentence.get("text", "")
                    if self.on_partial:
                        self.on_partial(text)
                    if self.on_sentence_end and sentence.get("sentence_end"):
                        self.on_sentence_end(text)

                elif event == "task-finished":
                    if self.on_final:
                        self.on_final("done")

                elif event == "task-failed":
                    if self.on_error:
                        self.on_error(RuntimeError(data.get("payload", {}).get("message", "Unknown error")))

        except Exception as e:
            if self.on_error:
                self.on_error(e)

