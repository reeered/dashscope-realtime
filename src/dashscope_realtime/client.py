import asyncio
from typing import Callable, Union, Optional

from .asr import DashScopeRealtimeASR
from .tts import DashScopeRealtimeTTS
from .event import EventEmitter


class RealtimeEvent:
    ASR_PARTIAL = "asr.partial"
    ASR_FINAL = "asr.final"
    ASR_SENTENCE_END = "asr.sentence_end"
    TTS_AUDIO = "tts.audio"
    TTS_END = "tts.end"
    READY = "ready"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class RealtimeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.asr = DashScopeRealtimeASR(api_key=api_key)
        self.tts = DashScopeRealtimeTTS(api_key=api_key)
        self.events = EventEmitter()
        self._start_lock = asyncio.Lock()
        self._tts_playing = False
        self._playback_queue = asyncio.Queue()
        self._playback_task: Optional[asyncio.Task] = None
        self._playback_ending = asyncio.Event()

        # ASR callbacks
        self.asr.on_partial = lambda text: asyncio.create_task(
            self._emit_async(RealtimeEvent.ASR_PARTIAL, text))
        self.asr.on_final = lambda text: self.events.emit(RealtimeEvent.ASR_FINAL, text)
        self.asr.on_error = lambda err: self.events.emit(RealtimeEvent.ERROR, err)
        self.asr.on_sentence_end = lambda text: asyncio.create_task(self._on_sentence_end(text))

        # TTS callbacks
        self.tts.on_audio_chunk = lambda chunk: self.events.emit(RealtimeEvent.TTS_AUDIO, chunk)
        self.tts.on_end = lambda: self.events.emit(RealtimeEvent.TTS_END)
        self.tts.on_error = lambda err: self.events.emit(RealtimeEvent.ERROR, err)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        async with self._start_lock:
            await self.asr.connect()
            await self.tts.connect()
            self._playback_task = asyncio.create_task(self._playback_loop())
            self.events.emit(RealtimeEvent.READY)

    async def stop(self):
        await asyncio.gather(
            self.asr.disconnect(),
            self.tts.disconnect(),
            return_exceptions=True
        )
        if self._playback_task:
            self._playback_task.cancel()

    def on(self, event_name: str, callback: Callable[[Union[str, bytes, Exception]], None]):
        self.events.on(event_name, callback)

    async def wait_for(self, event_name: str):
        return await self.events.wait_for(event_name)

    def is_tts_playing(self) -> bool:
        return self._tts_playing

    def reset(self):
        self._tts_playing = False
        self._playback_ending.clear()
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
        self._playback_queue = asyncio.Queue()

    async def send_audio_chunk(self, audio: bytes):
        await self.asr.send_audio(audio)

    async def call_voice(self, text: str):
        await self._playback_queue.put(text)

    async def end_voice(self):
        self._playback_ending.set()

    async def interrupt(self):
        self.reset()
        while not self._playback_queue.empty():
            self._playback_queue.get_nowait()
        await self.tts.interrupt()
        self.events.emit(RealtimeEvent.INTERRUPTED)

    async def _playback_loop(self):
        while True:
            text = await self._playback_queue.get()
            try:
                self._tts_playing = True
                await self.tts.say(text)
            except Exception as e:
                self.events.emit(RealtimeEvent.ERROR, e)
            self._playback_queue.task_done()

            # 播放结束判断逻辑
            if self._playback_queue.empty() and self._playback_ending.is_set():
                await self.tts.finish()
                self._tts_playing = False
                self._playback_ending.clear()
                self.events.emit(RealtimeEvent.TTS_END)

    async def _emit_async(self, event_name: str, payload: Union[str, bytes]):
        self.events.emit(event_name, payload)

    async def _on_sentence_end(self, text: str):
        self.events.emit(RealtimeEvent.ASR_SENTENCE_END, text)
        await self.call_voice(text)
        # 可选：你也可以手动调用 end_voice() 在某些标点后自动结束
