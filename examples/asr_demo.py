import dotenv
import os
import asyncio
from src.dashscope_realtime import DashScopeASRClient

dotenv.load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 替换成你的api key
AUDIO_FILE = "asr_example.wav"  # 替换成你的音频路径，要求16000Hz wav格式


async def main():
    asr = DashScopeASRClient(api_key=API_KEY)

    asr.on_partial = lambda text: print(f"[Partial] {text}")
    asr.on_final = lambda text: print(f"[Final] {text}")
    asr.on_error = lambda err: print(f"[Error] {err}")

    await asr.connect()

    with open(AUDIO_FILE, 'rb') as f:
        while chunk := f.read(3200):  # 按官方建议大小发送
            await asr.send_audio(chunk)
            await asyncio.sleep(0.1)  # 节奏感流式模拟

    await asyncio.sleep(1)  # 等待结束响应
    await asr.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
