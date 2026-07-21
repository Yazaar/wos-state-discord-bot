import asyncio, uuid, typing


__task_stack: dict[str, asyncio.Task] = {}

def queue_task(coro: typing.Coroutine):
    taskId = new_uuid()
    def on_done(doneTask: asyncio.Task) -> None:
        try: __task_stack.pop(taskId)
        except Exception: pass

        try: doneTask.result()
        except Exception: pass

    task = asyncio.create_task(coro)
    __task_stack[taskId] = task
    task.add_done_callback(on_done)
    return task

def new_uuid() -> str:
    return uuid.uuid4().hex
