import os
import sys

# Ensure src is on sys.path
directory = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(directory, "..", "src")))

import unittest
from unittest.mock import Mock

from aios.frame.node_filter import NodeFilter, CandidateQuery
from aios.proto.compute_task_test import ComputeTask, ComputeTaskType


class MockNode:
    def __init__(self, node_id: str, task_types, model_name=None):
        self.node_id = node_id
        self.support_task_types = task_types
        self.model_name = model_name


class TestNodeFilter(unittest.TestCase):
    
    def setUp(self):
        self.filter = NodeFilter()
        self.node1 = MockNode("n1", [ComputeTaskType.LLM_COMPLETION], "gpt-4")
        self.node2 = MockNode("n2", [ComputeTaskType.TEXT_EMBEDDING], "ada-002")
        self.node3 = MockNode("n3", [ComputeTaskType.LLM_COMPLETION, ComputeTaskType.TEXT_EMBEDDING], "gpt-4")
    
    def test_basic_functionality(self):
        # 注册节点
        self.filter.register_node(self.node1)
        self.filter.register_node(self.node2)
        self.filter.register_node(self.node3)
        
        # 测试过滤
        candidates = self.filter.filter_node_ids(
            query=CandidateQuery(task_type=ComputeTaskType.LLM_COMPLETION)
        )
        self.assertEqual(candidates, {"n1", "n3"})
        
        # 测试模型过滤
        candidates = self.filter.filter_node_ids(
            query=CandidateQuery(model_in={"gpt-4"})
        )
        self.assertEqual(candidates, {"n1", "n3"})
        
        # 测试组合过滤
        candidates = self.filter.filter_node_ids(
            query=CandidateQuery(
                task_type=ComputeTaskType.LLM_COMPLETION,
                model_in={"gpt-4"}
            )
        )
        self.assertEqual(candidates, {"n1", "n3"})
    
    def test_deregister(self):
        self.filter.register_node(self.node1)
        self.filter.register_node(self.node2)
        
        self.filter.deregister_node("n1")
        candidates = self.filter.filter_node_ids(
            query=CandidateQuery(task_type=ComputeTaskType.LLM_COMPLETION)
        )
        self.assertEqual(candidates, set())


if __name__ == "__main__":
    unittest.main()
