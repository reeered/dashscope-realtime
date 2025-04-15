# 文件结构：src/dashscope_realtime/asr.py

import asyncio
import websockets
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
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


class DashScopeASRClient:
    def __init__(self, api_key: str, config: DashScopeASRConfig = DashScopeASRConfig()):
        self.api_key = api_key
        self.config = config
        self.ws = None
        self.task_id = uuid.uuid4().hex[:32]
        self.on_partial = None
        self.on_final = None
        self.on_error = None
        self.on_sentence_end = None

    async def connect(self):
        self.ws = await websockets.connect(
            "wss://dashscope.aliyuncs.com/api-ws/v1/inference/",
            additional_headers={"Authorization": f"bearer {self.api_key}"}
        )
        await self._send_run_task()
        asyncio.create_task(self._recv())

    async def disconnect(self):
        if self.ws:
            await self.ws.close()

    async def send_audio(self, data: bytes):
        if not self.ws:
            print("ASR ws closed, reconnecting...")
            await self.disconnect()
            await self.connect()
            await self._send_run_task()
        await self.ws.send(data)

    async def finish(self):
        if self.ws:
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
        parameters = {
            "sample_rate": self.config.sample_rate,
            "format": self.config.format,
            "disfluency_removal_enabled": self.config.disfluency_removal_enabled,
            "language_hints": self.config.language_hints,
            "semantic_punctuation_enabled": self.config.semantic_punctuation_enabled,
            "max_sentence_silence": self.config.max_sentence_silence,
            "punctuation_prediction_enabled": self.config.punctuation_prediction_enabled,
            "heartbeat": self.config.heartbeat,
            "inverse_text_normalization_enabled": self.config.inverse_text_normalization_enabled
        }
        if self.config.vocabulary_id:
            parameters["vocabulary_id"] = self.config.vocabulary_id
        if self.config.phrase_id:
            parameters["phrase_id"] = self.config.phrase_id

        await self.ws.send(json.dumps({
            "header": {"action": "run-task", "task_id": self.task_id, "streaming": "duplex"},
            "payload": {"task_group": "audio", "task": "asr", "function": "recognition", "model": self.config.model,
                        "parameters": parameters, "input": {}}
        }))

    async def _recv(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                event = data["header"].get("event")
                if event == "result-generated":
                    text = data["payload"]["output"]["sentence"]["text"]
                    sentence_end = data["payload"]["output"]["sentence"]["sentence_end"]
                    if self.on_partial:
                        self.on_partial(text)
                    if self.on_sentence_end and sentence_end:
                        self.on_sentence_end(text)
                elif event == "task-finished":
                    if self.on_final:
                        self.on_final("done")
                elif event == "task-failed":
                    if self.on_error:
                        self.on_error(data)
        except Exception as e:
            if self.on_error:
                self.on_error(e)
