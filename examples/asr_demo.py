import os

import aiofiles
import asyncio
from datetime import datetime
from src.dashscope_realtime.asr import DashScopeRealtimeASR
import dotenv

dotenv.load_dotenv()


async def main():
    async def on_result(text: str):
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')}] Partial:", text)

    async def on_end(text: str):
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')}] Final:", text)

    async with DashScopeRealtimeASR(api_key=os.getenv("DASHSCOPE_API_KEY")) as asr:
        asr.result_callback = on_result
        asr.on_speech_end = on_end
        n = 0
        async with aiofiles.open("asr_example.wav", 'rb') as f:
            while chunk := await f.read(8000):
                n += 1
                await asr.send_audio_chunk(chunk)
                await asyncio.sleep(0.1)
                if n > 4:
                    silence_chunk = b'\x00' * 8000
                    await asr.send_audio_chunk(silence_chunk)
                    await asyncio.sleep(3)
                    break


if __name__ == '__main__':
    asyncio.run(main())
