import dotenv
import os
import asyncio
from src.dashscope_realtime import DashScopeRealtimeASR

dotenv.load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 替换成你的 api key
AUDIO_FILE = "asr_example.wav"  # 替换成你的音频路径，要求16000Hz wav格式


async def main():
    async with DashScopeRealtimeASR(api_key=API_KEY) as asr:
        asr.on_partial = lambda text: print(f"[Partial] {text}")
        asr.on_final = lambda text: print(f"[Final] {text}")
        asr.on_error = lambda err: print(f"[Error] {err}")

        with open(AUDIO_FILE, 'rb') as f:
            while chunk := f.read(3200):  # 官方建议单次最大 3200 字节
                await asr.send_audio(chunk)
                await asyncio.sleep(0.1)  # 流式效果

        await asr.finish()
        await asyncio.sleep(1)  # 等待结束响应


if __name__ == "__main__":
    asyncio.run(main())
