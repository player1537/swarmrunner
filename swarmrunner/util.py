"""

"""

from __future__ import annotations
from functools import wraps, partial
from eliot._action import TaskLevel
from eliot import start_task, Action


def continue_task_from_header(action_type=None, *, header='X-Eliot-Task', **fields: Dict[str, Callable[None, Any]]):
        def wrapper(func):
                @wraps(func)
                def inner_func(self, *args, **kwargs):
                        task_id = self.headers[header]
                        if task_id is None:
                                with start_task(action_type=action_type):
                                        return func(self, *args, **kwargs)

                        if isinstance(task_id, bytes):
                                task_id = task_id.decode('ascii')
                        uuid, task_level = task_id.split('@')
                        action = Action(None, uuid, TaskLevel.fromString(task_level), action_type if action_type is not None else 'eliot:remote_task')
                        action._start({ k: v() for k, v in fields.items() })
                        with action:
                                return func(self, *args, **kwargs)

                return inner_func
        return wrapper


