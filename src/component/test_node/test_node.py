import asyncio
import openai
from openai import AsyncOpenAI
import os
import asyncio
from asyncio import Queue
import logging
import json
import aiohttp
import base64
import requests
from openai._types import NOT_GIVEN
import random

from aios import ComputeTask, ComputeTaskResult, ComputeTaskState, ComputeTaskType,ComputeTaskResultCode,ComputeNode,AIStorage,UserConfig
from aios import image_utils

logger = logging.getLogger(__name__)


class TestComputeNode(ComputeNode):
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TestComputeNode()
        return cls._instance

    @classmethod
    def declare_user_config(cls):
        pass

    def __init__(self) -> None:
        super().__init__()

        self.is_start = False
        self.node_id = "test_node"
        self.task_queue = Queue()

        self.support_task_types = []
        self.mock_running_time = {} # taks_type -> running_time in seconds
        self.mock_error_rate = {}  # task_type -> error rate
        self.mock_task_load = {}  # task_type -> load
        self.ability = 10 # the ability to handel the task, the larger the number, a task can ba handle better
        self.current_load = 0 # the current load of the node, the larger the number, the more busy the node is

    async def initial(self):
        self.start()
        return True

    async def push_task(self, task: ComputeTask, proiority: int = 0):
        logger.info(f"{self.node_id} push task: {task.display()}")
        self.current_load += self.mock_task_load.get(task.task_type)
        self.task_queue.put_nowait(task)

    async def remove_task(self, task_id: str):
        pass

    def message_to_dict(self, message)->dict:
        result = message.dict()
        return result

    async def _run_task(self, task: ComputeTask):
        task.state = ComputeTaskState.RUNNING

        result = ComputeTaskResult()
        result.result_code = ComputeTaskResultCode.ERROR
        result.set_from_task(task)

        model_name = task.params["model_name"]
        input = task.task_type
        logger.info(f"call {model_name} input: {input}")

        if task.task_type in self.support_task_types:
            try:   
                await asyncio.sleep(self.mock_running_time.get(task.task_type))  # simulate running time

                # randomly throw an error to test error handling
                if random.random() < self.mock_error_rate.get(task.task_type):
                    raise ValueError("Random error occurred")

            except Exception as e:
                logger.error(f"{self.node_id} node run {task.task_type} task error: {e}")
                task.state = ComputeTaskState.ERROR
                task.error_str = str(e)
                result.error_str = str(e)
                self.current_load -= self.mock_task_load.get(task.task_type)
                return result

        logger.info("A node response: finished")
        task.state = ComputeTaskState.DONE
        result.result_code = ComputeTaskResultCode.OK
        result.worker_id = self.node_id
        result.result_str = "finished"
        self.current_load -= self.mock_task_load.get(task.task_type)
        return result


    def start(self):
        if self.is_start is True:
            return
        self.is_start = True

        async def _run_task_loop():
            while True:
                task = await self.task_queue.get()
                logger.info(f"openai_node get task: {task.display()}")
                result = await self._run_task(task)
                if result is not None:
                    task.result = result
                    task.state = ComputeTaskState.DONE

        asyncio.create_task(_run_task_loop())

    def display(self) -> str:
        return f"{self.node_id}"

    def get_task_state(self, task_id: str):
        pass

    def get_capacity(self):
        pass

    def is_support(self, task: ComputeTask) -> bool:
        if task.task_type in self.support_task_types:
            return True
        return False

    def is_local(self) -> bool:
        return False
