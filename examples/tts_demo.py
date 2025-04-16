import pyaudio
import os
import asyncio
import dotenv
from src.dashscope_realtime import DashScopeRealtimeTTS

dotenv.load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 请替换为你自己的 API Key


class AudioPlayer:
    def __init__(self, sample_rate=22050):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=sample_rate,
                                  output=True)

    def play_chunk(self, chunk: bytes):
        self.stream.write(chunk)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


async def main():
    player = AudioPlayer()

    client = DashScopeRealtimeTTS(api_key=API_KEY, send_audio=player.play_chunk)
    client.on_end = lambda: print("✅ 播报完成")
    client.on_error = lambda err: print(f"❌ 错误: {err}")

    await client.connect()

    print("🟢 第一句开始播放...")
    await client.say(" 你好，我是你")
    await client.say("的语音助手。")
    await client.say("欢迎体验实")
    await client.say("时语音合成服务。")

    await asyncio.sleep(1)  # 模拟播放了几秒钟

    print("🛑 中断播放...")
    await client.interrupt()

    print("🟡 第二句开始播放（重启后的）...")
    await client.say("你刚刚中断了播报，现在重新开始。这个功能很强大。")
    await client.finish()
    await client.wait_done()

    print("✅ 所有播报任务完成")
    player.close()


if __name__ == '__main__':
    asyncio.run(main())
