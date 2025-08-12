import random
from typing import Dict, List, Optional, Set, Iterable

from .compute_node import ComputeNode
from ..proto.compute_task_test import ComputeTask, ComputeTaskPriority, ComputeTaskType


class ComputeNodePool:
    """Node pool manager with two priority bands (HIGH/LOW) and basic listing.

    Responsibilities (pool-only, no final selection):
    - Maintain pools ("high", "low") and node membership
    - Route tasks to a pool based on priority (enum or legacy int)
    - Return all nodes in the routed pool (no filtering, no sorting)
    """

    HIGH_POOL = "high"
    LOW_POOL = "low"

    def __init__(self) -> None:
        self._pools: Dict[str, Set[str]] = {
            self.HIGH_POOL: set(),
            self.LOW_POOL: set(),
        }
        self._nodes: Dict[str, ComputeNode] = {}

    # ---------- Node membership management ----------
    def register_node(self, node: ComputeNode, pool: Optional[str] = None) -> None:
        self._nodes[node.node_id] = node
        if pool is None:
            # Default: register into LOW pool; callers can explicitly assign HIGH
            self._pools[self.LOW_POOL].add(node.node_id)
        else:
            self._ensure_pool(pool)
            self._pools[pool].add(node.node_id)

    def deregister_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            del self._nodes[node_id]
        for pool_nodes in self._pools.values():
            pool_nodes.discard(node_id)

    def assign_node_to_pool(self, node_id: str, pool: str) -> None:
        self._ensure_pool(pool)
        if node_id in self._nodes:
            self._pools[pool].add(node_id)

    def remove_node_from_pool(self, node_id: str, pool: str) -> None:
        self._ensure_pool(pool)
        self._pools[pool].discard(node_id)

    def _ensure_pool(self, pool: str) -> None:
        if pool not in self._pools:
            self._pools[pool] = set()

    def _coerce_priority_level(self, priority_value) -> ComputeTaskPriority:
        """Normalize priority to HIGH/LOW band.
        
        Accepts enum, string, or legacy int. For ints, map 0 -> LOW, 1 -> HIGH.
        """
        if isinstance(priority_value, ComputeTaskPriority):
            return priority_value
        if isinstance(priority_value, str):
            if priority_value.lower() in ["high", "1", "true"]:
                return ComputeTaskPriority.HIGH
            return ComputeTaskPriority.LOW
        try:
            # legacy mapping: 0 => LOW, 1 => HIGH
            iv = int(priority_value)
            return ComputeTaskPriority.HIGH if iv == 1 else ComputeTaskPriority.LOW
        except Exception:
            return ComputeTaskPriority.LOW

    # ---------- Routing & node listing ----------
    def route_pool(self, task: ComputeTask) -> str:
        level = self._coerce_priority_level(task.priority)
        if level == ComputeTaskPriority.HIGH:
            return self.HIGH_POOL
        return self.LOW_POOL

    def list_ids_by_task(self, pool: str, task_type: ComputeTaskType) -> List[str]:
        """List node IDs in a pool that support the given task type.
        
        This remains available for callers that want additional filtering outside the pool.
        """
        self._ensure_pool(pool)
        result = []
        for nid in self._pools.get(pool, set()):
            node = self._nodes.get(nid)
            if not node:
                continue
            support_types = getattr(node, "support_task_types", []) or []
            if task_type in support_types:
                result.append(nid)
        return result

    def get_pool_nodes(self, pool: str) -> List[ComputeNode]:
        """Return all nodes in the given pool (no filtering, no sorting)."""
        self._ensure_pool(pool)
        return [self._nodes[nid] for nid in self._pools.get(pool, set()) if nid in self._nodes]

    def get_candidates(self, task: ComputeTask, limit: int = 32) -> List[ComputeNode]:
        """Return all nodes in the routed pool (no filtering, no sorting)."""
        pool = self.route_pool(task)
        return self.get_pool_nodes(pool)

    def get_ability_level_name(self, level: int) -> str:
        """Get the ability level name for a given level.
        
        Kept for compatibility with external callers/tests if needed.
        """
        level_names = {1: "swift", 2: "outline", 3: "plan", 4: "reason", 5: "code"}
        return level_names.get(level, f"unknown-{level}")


