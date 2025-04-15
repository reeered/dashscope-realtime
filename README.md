# dashscope-realtime

DashScope Realtime ASR & TTS Python SDK

## 安装

```bash
pip install dashscope-realtime
```

## 使用示例
### ASR

```python
from dashscope-realtime import DashScopeRealtimeASR

async with DashScopeRealtimeASR(api_key="your-api-key") as asr:
    await asr.send_audio_chunk(b"...")
```

### TTS
```python

from dashscope-realtime import DashScopeRealtimeTTS

async with DashScopeRealtimeTTS(api_key="your-api-key") as tts:
    await tts.send_text("Hello, DashScope!")
    await tts.finish()
```

