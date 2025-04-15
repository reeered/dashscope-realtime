# DashScope Realtime

> 🚀 Async Python SDK for DashScope Realtime ASR (Speech Recognition) & TTS (Speech Synthesis)

<p align="center">
    <img src="https://img.shields.io/pypi/v/dashscope-realtime?color=%2300b3a4&logo=pypi" />
    <img src="https://img.shields.io/pypi/pyversions/dashscope-realtime.svg?logo=python" />
    <img src="https://img.shields.io/github/license/mikuh/dashscope-realtime.svg?color=blue" />
</p>

---

## 简介

DashScope Realtime 是一个支持异步 WebSocket 的 Python SDK，适配阿里 DashScope 的实时流式语音识别（ASR）和流式语音合成（TTS）能力。

---

## 为什么开发这个项目？

阿里云官方提供的DashScope Python SDK 是同步 WebSocket 实现，存在以下问题：

- 不支持 async / await

- 回调不在同一事件循环，无法直接使用 async 上下文

- 与 OpenAI API 生态的开源项目（如 FastAPI、Chainlit）不兼容

为了解决这些问题，本项目基于 DashScope WebSocket API，重新实现了异步版本的 ASR（语音识别）与 TTS（语音合成）SDK，具备：

- 纯异步 API 设计

- 支持流式音频输入输出

- 支持上下文无感知切换

- 更易接入 OpenAI API 风格的开源项目

---

## 安装

```bash
pip install dashscope-realtime
```

---

## 快速上手

### 实时语音识别（ASR）

```python
from dashscope_realtime import DashScopeRealtimeASR

async with DashScopeRealtimeASR(api_key="your-api-key") as asr:
    await asr.send_audio(b"...")  # 发送音频片段
```

---

### 实时语音合成（TTS）

```python
from dashscope_realtime import DashScopeRealtimeTTS

async with DashScopeRealtimeTTS(api_key="your-api-key") as tts:
    await tts.say("Hello, DashScope!")  # 发送文本
    await tts.finish()  # 完成任务
```

---

## 特性

- ✅ 全异步设计（async / await）
- ✅ ASR 支持流式音频输入
- ✅ TTS 支持流式音频输出
- ✅ 自动重连 & 错误处理
- ✅ 接口风格对齐 OpenAI Realtime
- ✅ 方便集成任意异步 Python 项目

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

> Made with ❤️ by mikuh

