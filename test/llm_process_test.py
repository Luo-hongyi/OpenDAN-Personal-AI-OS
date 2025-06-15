import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

directory = os.path.dirname(__file__)
sys.path.append(directory + '/../src')
from aios.agent.llm_process import AgentMessageProcess
from aios.agent.agent_memory import AgentMemory
from aios.agent.llm_context import LLMProcessContext,GlobaToolsLibrary, SimpleLLMContext

from aios.proto.compute_task import LLMPrompt, LLMResult, ComputeTaskResult, ComputeTaskResultCode
from aios.proto.agent_msg import AgentMsg, AgentMsgType

print("package loaded")

# Mock Agent Memory
memory = AgentMemory(agent_id="test_agent", base_dir="./tmp")

# Mock Agent Message
msg = AgentMsg()
msg.body = "test message"
msg.topic = "test"
input = {}
input["msg"] = msg

# creat a test process
test_process = AgentMessageProcess()
test_process.model_name = "switch_llm"
test_process.memory = memory
test_process.llm_context = SimpleLLMContext()

asyncio.run(test_process.process(input))