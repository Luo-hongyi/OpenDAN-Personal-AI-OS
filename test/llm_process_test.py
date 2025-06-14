import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

directory = os.path.dirname(__file__)
sys.path.append(directory + '/../src')
from aios.agent.llm_process import AgentMessageProcess, AgentSelfThinking
from aios.proto.compute_task import LLMPrompt, LLMResult, ComputeTaskResult, ComputeTaskResultCode
from aios.proto.agent_msg import AgentMsg, AgentMsgType
print("package loaded")



