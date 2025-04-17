import logging

# WebSocket URL
DASHSCOPE_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"

logger = logging.getLogger("dashscope_realtime")
logger.setLevel(logging.INFO)
