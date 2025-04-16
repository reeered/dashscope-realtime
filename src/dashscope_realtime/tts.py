import asyncio
import json
import uuid
from dataclasses import dataclass
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
            send_audio: Optional[Callable[[bytes], None]] = None,
            on_end: Optional[Callable[[], None]] = None,
            on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.api_key = api_key
        self.config = config
        self.url = url
        self.task_id = uuid.uuid4().hex[:32]
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

        self.send_audio = send_audio  # 真正发送 chunk 的函数
        self.on_end = on_end
        self.on_error = on_error

        self.done_event: Optional[asyncio.Event] = None
        self._say_lock = asyncio.Lock()
        self._audio_queue: Optional[asyncio.Queue[Optional[bytes]]] = None
        self._play_task: Optional[asyncio.Task] = None

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
        self.done_event = asyncio.Event()
        self._audio_queue = asyncio.Queue()
        await self._send_run_task()
        asyncio.create_task(self._receive_loop())

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def say(self, text: str):
        async with self._say_lock:
            if not self.ws:
                await self.connect()

            # 启动后台播放任务
            if self._play_task is None or self._play_task.done():
                self._play_task = asyncio.create_task(self._start_audio_streamer())

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

    async def wait_done(self):
        if self.done_event:
            await self.done_event.wait()
        if self._play_task:
            await self._play_task

    async def interrupt(self):
        if self._play_task and not self._play_task.done():
            self._play_task.cancel()
            try:
                await self._play_task
            except asyncio.CancelledError:
                pass
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
                    if self._audio_queue:
                        await self._audio_queue.put(msg)
                else:
                    data = json.loads(msg)
                    event = data.get("header", {}).get("event")

                    if event == "task-finished":
                        if self._audio_queue:
                            await self._audio_queue.put(None)  # 播放结束标志
                        if self.on_end:
                            self.on_end()
                        if self.done_event and not self.done_event.is_set():
                            self.done_event.set()

                    elif event == "task-failed":
                        if self.on_error:
                            self.on_error(RuntimeError(data.get("payload", {}).get("message", "Unknown error")))

        except Exception as e:
            if self.on_error:
                self.on_error(e)

    async def _start_audio_streamer(self):
        try:
            while True:
                chunk = await self._audio_queue.get()
                if chunk is None:
                    break
                if self.send_audio:
                    result = self.send_audio(chunk)
                    if asyncio.iscoroutine(result):
                        await result
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.on_error:
                self.on_error(e)
