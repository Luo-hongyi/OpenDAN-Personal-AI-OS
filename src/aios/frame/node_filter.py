from dataclasses import dataclass
from typing import Optional, Set, Dict, DefaultDict
from collections import defaultdict

from .compute_node import ComputeNode
from ..proto.compute_task_test import ComputeTask, ComputeTaskType


@dataclass
class CandidateQuery:
    task_type: Optional[ComputeTaskType] = None
    model_in: Optional[Set[str]] = None  # acceptable model names


class NodeFilter:
    """O(1) filtering using pre-built indexes."""
    
    def __init__(self):
        # Index: task_type -> set of node_ids
        self._task_type_index: DefaultDict[ComputeTaskType, Set[str]] = defaultdict(set)
        # Index: model_name -> set of node_ids  
        self._model_index: DefaultDict[str, Set[str]] = defaultdict(set)
        # All registered node IDs
        self._all_nodes: Set[str] = set()
        # Node lookup for metadata
        self._node_lookup: Dict[str, ComputeNode] = {}
    
    def register_node(self, node: ComputeNode) -> None:
        """Register a node and update indexes."""
        node_id = node.node_id
        self._all_nodes.add(node_id)
        self._node_lookup[node_id] = node
        
        # Index by task types
        support_types = getattr(node, "support_task_types", []) or []
        for task_type in support_types:
            self._task_type_index[task_type].add(node_id)
        
        # Index by model
        model_name = getattr(node, "model_name", None)
        if model_name:
            self._model_index[model_name].add(node_id)
    
    def deregister_node(self, node_id: str) -> None:
        """Remove a node and update indexes."""
        if node_id not in self._all_nodes:
            return
            
        node = self._node_lookup.pop(node_id, None)
        self._all_nodes.discard(node_id)
        
        if node:
            # Remove from task type index
            support_types = getattr(node, "support_task_types", []) or []
            for task_type in support_types:
                self._task_type_index[task_type].discard(node_id)
                # Clean up empty sets
                if not self._task_type_index[task_type]:
                    del self._task_type_index[task_type]
            
            # Remove from model index
            model_name = getattr(node, "model_name", None)
            if model_name and model_name in self._model_index:
                self._model_index[model_name].discard(node_id)
                if not self._model_index[model_name]:
                    del self._model_index[model_name]
    
    def filter_node_ids(self, task: Optional[ComputeTask] = None, query: Optional[CandidateQuery] = None) -> Set[str]:
        """O(1) filtering using pre-built indexes."""
        q = query or self._build_query_from_task(task)
        
        # Start with all nodes
        result = self._all_nodes.copy()
        
        # Task type filter: O(1) set intersection
        if q.task_type is not None:
            if q.task_type not in self._task_type_index:
                return set()  # No nodes support this task type
            result &= self._task_type_index[q.task_type]
            if not result:
                return set()
        
        # Model filter: O(1) set intersection
        if q.model_in:
            model_nodes = set()
            for model in q.model_in:
                if model in self._model_index:
                    model_nodes |= self._model_index[model]
            result &= model_nodes
            if not result:
                return set()
        
        return result
    
    def _build_query_from_task(self, task: ComputeTask) -> CandidateQuery:
        """Build query from task parameters."""
        model_name = None
        try:
            model_name = task.params.get("model_name") if hasattr(task, "params") else None
        except Exception:
            model_name = None
        return CandidateQuery(
            task_type=task.task_type,
            model_in={model_name} if model_name else None,
        )
    
    def get_nodes_by_task_type(self, task_type: ComputeTaskType) -> Set[str]:
        """Get all nodes supporting a specific task type."""
        return self._task_type_index.get(task_type, set()).copy()
    
    def get_nodes_by_model(self, model_name: str) -> Set[str]:
        """Get all nodes with a specific model."""
        return self._model_index.get(model_name, set()).copy()
    
    def get_all_nodes(self) -> Set[str]:
        """Get all registered node IDs."""
        return self._all_nodes.copy()
    
    def get_node(self, node_id: str) -> Optional[ComputeNode]:
        """Get a node instance by ID."""
        return self._node_lookup.get(node_id)
