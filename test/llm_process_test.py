import logging
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S",
)
import os
import sys
import asyncio

directory = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(directory, "..", "src")))
from aios.agent.llm_process import AgentMessageProcess
from aios.agent.agent_memory import AgentMemory
from aios.agent.llm_context import LLMProcessContext, GlobaToolsLibrary, SimpleLLMContext

from aios.proto.compute_task import ComputeTaskType
from aios.proto.agent_msg import AgentMsg, AgentMsgType

from aios.frame.compute_kernel import ComputeKernel

from component.openai_node.open_ai_node import OpenAI_ComputeNode
from component.test_node.test_node import TestComputeNode

from aios.storage.storage import AIStorage
print("package loaded")

support_task_type1 = [ComputeTaskType.LLM_COMPLETION]
mock_running_time1 = {ComputeTaskType.LLM_COMPLETION: 1}
mock_error_rate1 = {ComputeTaskType.LLM_COMPLETION: 0.001}


# initialize the OpenAI compute node
# node = OpenAI_ComputeNode.get_instance()
node1 = TestComputeNode()
node1.support_task_types = support_task_type1
node1.mock_running_time = mock_running_time1
node1.mock_error_rate = mock_error_rate1
node1.node_id = "test_node_1"

node2 = TestComputeNode()
node2.support_task_types = support_task_type1
node2.mock_running_time = mock_running_time1
node2.mock_error_rate = mock_error_rate1
node2.node_id = "test_node_2"

node3 = TestComputeNode()
node3.support_task_types = support_task_type1
node3.mock_running_time = mock_running_time1
node3.mock_error_rate = mock_error_rate1
node3.node_id = "test_node_3"

# start the compute kernel and process the test message in a single event loop
kernel = ComputeKernel.get_instance()

# Mock Agent Memory
memory = AgentMemory(agent_id="test_agent", base_dir="./tmp")

# Mock AIStorage
storage = AIStorage.get_instance()
storage.user_config.set_value("llm_code_models",["o3","gpt-4o","gpt-3.5-turbo"])
storage.user_config.sort_llm_models_by_cost("llm_code_models")


async def main():
	# start compute nodes
	node1.start()
	node2.start()
	node3.start()
	logging.info("OpenAI Node started")
	kernel.add_compute_node(node1)
	kernel.add_compute_node(node2)
	kernel.add_compute_node(node3)
	await kernel.start()
	logging.info("Compute Kernel started")
	
	# create 10 separate process instances
	processes = []
	inputs = []
	for i in range(90):
		proc = AgentMessageProcess()
		proc.model_name = "code_llm"
		proc.memory = memory
		proc.llm_context = SimpleLLMContext()
		proc.timeout = 30
		processes.append(proc)

		msg = AgentMsg()
		msg.body = "黑色光是什么"
		msg.topic = "test"
		msg.sender = "test_sender"
		input = {}
		input["msg"] = msg
		inputs.append(input)
	
	# start all 10 processes concurrently
	tasks = [asyncio.create_task(proc.process(input)) for proc, input in zip(processes, inputs)]
	results = await asyncio.gather(*tasks)
	
	# log results for each process
	for idx, res in enumerate(results, start=1):
		logging.info(f"Process {idx} result: {res.resp}")

if __name__ == "__main__":
	asyncio.run(main())