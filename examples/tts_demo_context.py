import asyncio
import os
from src.dashscope_realtime import DashScopeRealtimeTTS
import dotenv

dotenv.load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 请替换为你自己的 API Key


async def main():
    async with DashScopeRealtimeTTS(api_key=API_KEY) as tts:
        tts.on_audio_chunk = lambda chunk: print(f"Got audio chunk: {len(chunk)} bytes")
        tts.on_end = lambda: print("TTS Finished")
        tts.on_error = lambda e: print(f"TTS Error: {e}")

        await tts.say("你好，我是语音合成测试。")
        await tts.finish()
        await asyncio.sleep(1)


asyncio.run(main())
