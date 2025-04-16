import asyncio
from src.dashscope_realtime import RealtimeClient, RealtimeEvent
import pyaudio
import queue
import dotenv
import os

dotenv.load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 替换成你的api key


class AudioInputStream:
    def __init__(self, rate=22050, chunk=3200):
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
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()


async def main():
    client = RealtimeClient(api_key=API_KEY)
    mic = AudioInputStream()

    async with client:
        # 注册事件处理器
        client.on(RealtimeEvent.READY, lambda: print("🟢 语音系统就绪"))
        client.on(RealtimeEvent.ASR_PARTIAL, lambda text: print(f"[Partial] {text}"))
        client.on(RealtimeEvent.ASR_SENTENCE_END, lambda text: print(f"[✅ 识别完毕]：{text}"))
        client.on(RealtimeEvent.TTS_AUDIO, lambda chunk: print(f"[🔊 播放音频] {len(chunk)} bytes"))
        client.on(RealtimeEvent.TTS_END, lambda: print("🔈 播报结束"))
        client.on(RealtimeEvent.INTERRUPTED, lambda: print("⛔️ 播放被打断"))
        client.on(RealtimeEvent.ERROR, lambda err: print(f"[❌ 错误] {err}"))

        mic.start()
        print("🎙️ 开始说话...")

        try:
            while True:
                chunk = mic.read_chunk()
                if chunk:
                    # 每一帧音频都发送给 ASR
                    await client.send_audio_chunk(chunk)
                await asyncio.sleep(0.01)  # 限制频率
        except KeyboardInterrupt:
            print("🛑 停止录音")
        finally:
            mic.stop()


if __name__ == "__main__":
    asyncio.run(main())
