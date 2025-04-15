import asyncio
from collections import defaultdict


class EventEmitter:
    def __init__(self):
        self.handlers = defaultdict(list)

    def on(self, event_name, handler):
        self.handlers[event_name].append(handler)

    def emit(self, event_name, *args, **kwargs):
        for handler in self.handlers[event_name]:
            result = handler(*args, **kwargs)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

    async def wait_for(self, event_name):
        future = asyncio.Future()

        def once(*args, **kwargs):
            if not future.done():
                future.set_result(args[0] if args else None)

        self.on(event_name, once)
        return await future
