import asyncio
import os
import pyaudio
import queue
from src.dashscope_realtime import RealtimeClient
import dotenv

dotenv.load_dotenv()
API_KEY = os.getenv("DASHSCOPE_API_KEY")
RATE = 16000
CHUNK = 3200


class AudioInputStream:
    def __init__(self, rate=16000, chunk=3200):
        self.chunk = chunk
        self.rate = rate
        self.q = queue.Queue()
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False

    def start(self):
        self.running = True
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=self.callback,
        )
        self.stream.start_stream()

    def callback(self, in_data, frame_count, time_info, status):
        if self.running:
            self.q.put(in_data)
        return None, pyaudio.paContinue

    def read_chunk(self):
        try:
            return self.q.get(timeout=0.1)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()


class AudioPlayer:
    def __init__(self, rate=16000):
        self.rate = rate
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=rate,
            output=True
        )
        self.lock = asyncio.Lock()
        self.interrupted = False

    async def play(self, chunk: bytes):
        async with self.lock:
            if not self.interrupted:
                self.stream.write(chunk)

    async def interrupt(self):
        async with self.lock:
            self.interrupted = True
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()


async def voice_loop():
    global sentence_end_task

    client = RealtimeClient(api_key=API_KEY)
    mic = AudioInputStream(rate=RATE, chunk=CHUNK)
    player = AudioPlayer(rate=RATE)
    current_speech = []

    async def handle_partial(text):
        print(f"[Partial] {text}")

    async def handle_final(_):
        text = ''.join(current_speech).strip()
        print(f"[Final] {text}")
        if text:
            await client.say(f"[你刚才说的是：]{text}")
        current_speech.clear()

    async def handle_audio(chunk):
        await player.play(chunk)

    async def handle_on_sentence_end(text):
        try:
            print(f"[完整的话是：] {text}")
            await client.tts.interrupt()
            for line in ["窗前明月光", "疑似地上霜", "举头望明月", "低头思故乡"]:
                await client.say(line)
            await client.tts.finish()
            await client.start()
        except asyncio.CancelledError:
            print("⚠️ 播报任务被取消")

    # 注册事件
    client.on("asr.partial", lambda text: asyncio.create_task(handle_partial(text)))
    client.on("asr.final", lambda _: asyncio.create_task(handle_final(_)))
    client.on("tts.audio", lambda chunk: asyncio.create_task(handle_audio(chunk)))
    client.on("tts.end", lambda: print("🎧 播报结束"))
    client.on("asr.sentence_end", lambda text: asyncio.create_task(handle_on_sentence_end(text)))

    await client.start()
    mic.start()

    print("你可以开始说话了...")

    try:
        while True:
            chunk = mic.read_chunk()
            if chunk:
                await client.send_audio_chunk(chunk)
            await asyncio.sleep(0.01)
    except KeyboardInterrupt:
        print("🛑 退出")
    finally:
        mic.stop()
        await client.stop()


if __name__ == "__main__":
    asyncio.run(voice_loop())
