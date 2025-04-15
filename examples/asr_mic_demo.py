import asyncio
import pyaudio
import os
from src.dashscope_realtime import DashScopeASRClient
import dotenv
dotenv.load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")

RATE = 16000
CHUNK = 3200  # 推荐大小


class MicInput:
    def __init__(self, rate=16000, chunk=3200):
        self.chunk = chunk
        self.rate = rate
        self.p = pyaudio.PyAudio()
        self.stream = None

    def start(self):
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
        )

    def read_chunk(self):
        return self.stream.read(self.chunk, exception_on_overflow=False)

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()


async def main():
    mic = MicInput(rate=RATE, chunk=CHUNK)
    asr = DashScopeASRClient(api_key=API_KEY)

    asr.on_partial = lambda text: print(f"[Partial] {text}")
    asr.on_final = lambda text: print(f"[Final] {text}")
    asr.on_error = lambda err: print(f"[Error] {err}")
    asr.on_sentence_end = lambda text: print(f"[Sentence End] {text}")

    await asr.connect()
    mic.start()

    print("🎤 开始说话吧，Ctrl+C退出")

    try:
        while True:
            chunk = mic.read_chunk()
            await asr.send_audio(chunk)
            await asyncio.sleep(0.05)
    except KeyboardInterrupt:
        print("🛑 结束")
    finally:
        mic.close()
        await asr.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
