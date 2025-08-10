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
from enum import Enum
from typing import List, Dict, Any, Optional, Union

from aios.proto.compute_task_test import ComputeTask, ComputeTaskType, ComputeTaskState, ComputeTaskResult, ComputeTaskResultCode
from aios.frame.compute_node import ComputeNode
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

        self.support_task_types = [] # list of task types that this node can handle
        # node characteristics for testing
        self.ability: float = 10.0
        self.price_per_token: float = 0.0
        self.capacity_concurrent: int = 1
        self.fault_error_rate: float = 0.0
        self.compute_error_rate: float = 0.0
        self.jitter_ms_range = (0, 0)

        # dynamic load indicators
        self.pending_task_count: int = 0
        self.pending_task_total_runtime_ms: float = 0.0
        self.in_flight_task_count: int = 0

    async def initial(self):
        self.start()
        return True

    async def push_task(self, task: ComputeTask, proiority: int = 0):
        logger.info(f"{self.node_id} push task: {task.display()}")
        # stamp assignment and schedule time
        try:
            task.assigned_node_id = self.node_id
            if getattr(task, "scheduled_at", None) is None:
                task.scheduled_at = asyncio.get_event_loop().time()
        except Exception:
            pass
        # update pending metrics
        self.pending_task_count += 1
        try:
            self.pending_task_total_runtime_ms += float(getattr(task, "runtime_ms", 0.0) or 0.0)
        except Exception:
            pass
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
                # timestamps
                now_ts = asyncio.get_event_loop().time()
                if getattr(task, "scheduled_at", None) is None:
                    task.scheduled_at = now_ts
                task.started_at = now_ts

                # simulate fault error first
                if random.random() < self.fault_error_rate:
                    result.result_code = ComputeTaskResultCode.ERROR
                    result.error_str = "node_fault"
                    task.state = ComputeTaskState.ERROR
                    return result

                # compute execution time based on difficulty vs ability (simplified)
                base_ms = float(getattr(task, "runtime_ms", 0.0) or 0.0)
                difficulty = float(getattr(task, "difficulty", 0.0) or 0.0)
                ability = float(self.ability or 0.0)
                # runtime_ms directly corresponds to sleep time
                exec_ms = base_ms
                await asyncio.sleep(exec_ms / 1000.0)

                # compute error probability (LLM wrong answer)
                if random.random() < self.compute_error_rate:
                    result.result_code = ComputeTaskResultCode.OK
                    result.compute_error = True
                    result.quality_score = 0.0
                    task.state = ComputeTaskState.DONE
                else:
                    # success
                    task.state = ComputeTaskState.DONE
                    result.result_code = ComputeTaskResultCode.OK
                    result.compute_error = False

                # fill metrics
                task.finished_at = asyncio.get_event_loop().time()
                
                # quality & cost
                quality_score = max(0.0, 10.0 - max(0.0, difficulty - ability))
                result.quality_score = quality_score
                input_tokens = int(getattr(task, "input_tokens", 0) or 0)
                result.cost = float(self.price_per_token or 0.0) * float(input_tokens)

                # format result_str for logging
                result_str_parts = []
                result_str_parts.append(f"quality:{quality_score:.2f}")
                result_str_parts.append(f"cost:{result.cost:.6f}")
                result_str_parts.append(f"exec_time:{exec_ms:.0f}ms")
                
                if task.started_at is not None and task.scheduled_at is not None:
                    queue_wait_ms = max(0.0, (task.started_at - task.scheduled_at) * 1000.0)
                    if queue_wait_ms > 0:
                        result_str_parts.append(f"queue_wait:{queue_wait_ms:.0f}ms")
                
                if result.compute_error:
                    result_str_parts.append("compute_error:true")
                
                result.result_str = " | ".join(result_str_parts)
                result.worker_id = self.node_id
                
                # Return the result for supported task types
                return result

            except Exception as e:
                logger.error(f"{self.node_id} node run {task.task_type} task error: {e}")
                task.state = ComputeTaskState.ERROR
                task.error_str = str(e)
                result.error_str = str(e)
                return result

        # Default response for unsupported task types
        logger.info("A node response: finished")
        task.state = ComputeTaskState.DONE
        result.result_code = ComputeTaskResultCode.OK
        result.worker_id = self.node_id
        result.result_str = "finished"
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
        logger.info(f"task type: {task.task_type}, support task types: {self.support_task_types}")
        if task.task_type in self.support_task_types:
            return True
        return False

    def is_local(self) -> bool:
        return False
