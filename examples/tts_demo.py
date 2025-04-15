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

    client = DashScopeRealtimeTTS(api_key=API_KEY)
    client.on_audio_chunk = lambda chunk: player.play_chunk(chunk)
    client.on_end = lambda: print("✅ 播报完成")
    client.on_error = lambda err: print(f"❌ 错误: {err}")

    await client.connect()

    await client.say(" 你好，我是你")
    await client.say("的语音助手。")
    await client.say("欢迎体验实")
    await client.say("时语音合成服务。")
    await client.finish()

    await asyncio.sleep(1)
    await client.disconnect()
    player.close()


if __name__ == '__main__':
    asyncio.run(main())
