import asyncio
from .asr import DashScopeRealtimeASR
from .tts import DashScopeRealtimeTTS
from .event import EventEmitter


class RealtimeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.asr = DashScopeRealtimeASR(api_key=api_key)
        self.tts = DashScopeRealtimeTTS(api_key=api_key)
        self.events = EventEmitter()
        self._start_lock = asyncio.Lock()

        self.asr.on_partial = lambda text: asyncio.create_task(self._handle_partial(text))
        self.asr.on_final = lambda text: self.events.emit("asr.final", text)
        self.asr.on_error = lambda err: self.events.emit("error", err)
        self.asr.on_sentence_end = lambda text: self.events.emit("asr.sentence_end", text)

        self.tts.on_audio_chunk = lambda chunk: self.events.emit("tts.audio", chunk)
        self.tts.on_end = lambda: self._on_tts_end()
        self.tts.on_error = lambda err: self.events.emit("error", err)

    async def _handle_partial(self, text: str):
        self.events.emit("asr.partial", text)

    async def _on_tts_end(self):
        self._tts_playing = False
        self.events.emit("tts.end")

    async def start(self):
        async with self._start_lock:
            await self.asr.connect()
            await self.tts.connect()
            self.events.emit("ready")

    async def stop(self):
        await asyncio.gather(
            self.asr.disconnect(),
            self.tts.disconnect(),
            return_exceptions=True
        )

    async def send_audio_chunk(self, audio: bytes):
        await self.asr.send_audio(audio)

    async def say(self, text: str):
        await self.tts.say(text)

    def on(self, event_name: str, callback):
        self.events.on(event_name, callback)

    async def wait_for(self, event_name: str):
        return await self.events.wait_for(event_name)
