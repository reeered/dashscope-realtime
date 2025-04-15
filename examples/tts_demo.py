import pyaudio
import os
import asyncio
import dotenv
from src.dashscope_realtime.tts import DashScopeRealtimeTTS

dotenv.load_dotenv()


class AudioPlayer:
    def __init__(self, sample_rate=16000):
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
    texts = [
        "床前明月光，",
        "疑是地上霜。",
        "举头望明月，",
        "低头思故乡。"
    ]

    async def handle_audio_chunk(chunk):
        print("chunk received", len(chunk))
        player.play_chunk(chunk)

    player = AudioPlayer()

    async with DashScopeRealtimeTTS(api_key=os.getenv("DASHSCOPE_API_KEY")) as tts:
        await tts.connect(on_audio_chunk=handle_audio_chunk)
        for text in texts:
            await tts.send_text(text)
            await asyncio.sleep(0.1)
        await tts.finish()

    player.close()


if __name__ == '__main__':
    asyncio.run(main())
