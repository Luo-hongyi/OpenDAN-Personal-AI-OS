import os
import sys
import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

directory = os.path.dirname(__file__)
sys.path.append(directory + '/../src')
from aios.agent.llm_process import AgentMessageProcess
from aios.agent.agent_memory import AgentMemory
from aios.agent.llm_context import LLMProcessContext,GlobaToolsLibrary, SimpleLLMContext

from aios.proto.compute_task import LLMPrompt, LLMResult, ComputeTaskResult, ComputeTaskResultCode
from aios.proto.agent_msg import AgentMsg, AgentMsgType

from aios.frame.compute_kernel import ComputeKernel

from component.openai_node.open_ai_node import OpenAI_ComputeNode


print("package loaded")

# initialize the OpenAI compute node
node = OpenAI_ComputeNode()

# start the compute kernel and process the test message in a single event loop
kernel = ComputeKernel()

# Mock Agent Memory
memory = AgentMemory(agent_id="test_agent", base_dir="./tmp")

# Mock Agent Message
msg = AgentMsg()
msg.body = "test message"
msg.topic = "test"
msg.sender = "test_sender"
input = {}
input["msg"] = msg

# creat a test process
test_process = AgentMessageProcess()
test_process.model_name = "switch_llm"
test_process.memory = memory
test_process.llm_context = SimpleLLMContext()
test_process.timeout = 60

async def main():
	kernel.add_compute_node(node)
	await kernel.start()
	print("Kernel started")
	await test_process.process(input)
if __name__ == "__main__":
	asyncio.run(main())