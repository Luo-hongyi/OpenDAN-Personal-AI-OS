import os
import sys

# Ensure src is on sys.path
directory = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(directory, "..", "src")))

from aios.frame.node_pool import ComputeNodePool
from aios.proto.compute_task_test import ComputeTask, ComputeTaskType
from component.test_node.test_node import TestComputeNode


def build_node(
    node_id: str,
    support_types,
    capacity: int = 1,
    in_flight: int = 0,
    pending_ms: float = 0.0,
    price: float = 0.0,
    ability: float = 1.0,
    enable: bool = True,
):
    node = TestComputeNode()
    node.node_id = node_id
    node.support_task_types = list(support_types)
    node.capacity_concurrent = capacity
    node.in_flight_task_count = in_flight
    node.pending_task_total_runtime_ms = pending_ms
    node.price_per_token = price
    node.ability = ability
    node.enable = enable
    return node


def test_high_priority_llm_routes_to_high_pool_and_lists_all_pool_nodes():
    pool = ComputeNodePool()

    n_fast = build_node("n_high_fast", [ComputeTaskType.LLM_COMPLETION], capacity=4, in_flight=0, pending_ms=50, ability=5)
    n_busy = build_node("n_high_busy", [ComputeTaskType.LLM_COMPLETION], capacity=2, in_flight=2, pending_ms=800, ability=5)
    n_low = build_node("n_low_default", [ComputeTaskType.LLM_COMPLETION], capacity=1, in_flight=0, pending_ms=0, ability=3)
    n_other = build_node("n_high_other_type", [ComputeTaskType.TEXT_EMBEDDING], capacity=4, in_flight=0, pending_ms=0, ability=5)

    pool.register_node(n_fast, pool=pool.HIGH_POOL)
    pool.register_node(n_busy, pool=pool.HIGH_POOL)
    pool.register_node(n_low, pool=pool.LOW_POOL)
    pool.register_node(n_other, pool=pool.HIGH_POOL)

    task = ComputeTask()
    task.task_type = ComputeTaskType.LLM_COMPLETION
    task.priority = "high"

    candidates = pool.get_candidates(task, limit=3)
    ids = [c.node_id for c in candidates]

    # Should list all nodes in HIGH pool regardless of task_type; exclude LOW pool nodes
    assert "n_low_default" not in ids
    assert "n_high_fast" in ids
    assert "n_high_busy" in ids
    assert "n_high_other_type" in ids


def test_low_priority_llm_routes_to_low_pool():
    pool = ComputeNodePool()

    n_low = build_node("n_low_llm", [ComputeTaskType.LLM_COMPLETION], capacity=2, in_flight=0, pending_ms=0, ability=2)
    n_high = build_node("n_high_llm", [ComputeTaskType.LLM_COMPLETION], capacity=2, in_flight=0, pending_ms=0, ability=5)

    pool.register_node(n_low, pool=pool.LOW_POOL)
    pool.register_node(n_high, pool=pool.HIGH_POOL)

    task = ComputeTask()
    task.task_type = ComputeTaskType.LLM_COMPLETION
    task.priority = "low"

    candidates = pool.get_candidates(task, limit=2)
    ids = [c.node_id for c in candidates]

    assert "n_low_llm" in ids
    assert "n_high_llm" not in ids


def test_list_ids_by_task_basic_filtering():
    pool = ComputeNodePool()

    # Create nodes with different task types
    llm_node = build_node("n_llm", [ComputeTaskType.LLM_COMPLETION], ability=3)
    emb_node = build_node("n_emb", [ComputeTaskType.TEXT_EMBEDDING], ability=2)
    pool.register_node(llm_node, pool=pool.HIGH_POOL)
    pool.register_node(emb_node, pool=pool.HIGH_POOL)

    # Test list_ids_by_task for LLM_COMPLETION
    llm_ids = pool.list_ids_by_task(pool.HIGH_POOL, ComputeTaskType.LLM_COMPLETION)
    assert "n_llm" in llm_ids
    assert "n_emb" not in llm_ids

    # Test list_ids_by_task for TEXT_EMBEDDING
    emb_ids = pool.list_ids_by_task(pool.HIGH_POOL, ComputeTaskType.TEXT_EMBEDDING)
    assert "n_emb" in emb_ids
    assert "n_llm" not in emb_ids


def test_get_candidates_returns_all_pool_nodes():
    pool = ComputeNodePool()

    llm_node = build_node("n_llm", [ComputeTaskType.LLM_COMPLETION])
    emb_node = build_node("n_emb", [ComputeTaskType.TEXT_EMBEDDING])
    pool.register_node(llm_node, pool=pool.HIGH_POOL)
    pool.register_node(emb_node, pool=pool.HIGH_POOL)

    task = ComputeTask()
    task.task_type = ComputeTaskType.LLM_COMPLETION
    task.priority = "high"

    candidates = pool.get_candidates(task, limit=4)
    ids = [c.node_id for c in candidates]
    assert "n_llm" in ids
    assert "n_emb" in ids


def test_disabled_nodes_still_listed_in_pool():
    pool = ComputeNodePool()

    n_enabled = build_node("n_enabled", [ComputeTaskType.LLM_COMPLETION], enable=True)
    n_disabled = build_node("n_disabled", [ComputeTaskType.LLM_COMPLETION], enable=False)
    pool.register_node(n_enabled, pool=pool.HIGH_POOL)
    pool.register_node(n_disabled, pool=pool.HIGH_POOL)

    task = ComputeTask()
    task.task_type = ComputeTaskType.LLM_COMPLETION
    task.priority = "high"

    candidates = pool.get_candidates(task, limit=4)
    ids = [c.node_id for c in candidates]
    assert "n_enabled" in ids
    assert "n_disabled" in ids


def test_assign_and_remove_node_updates_pools():
    pool = ComputeNodePool()
    n = build_node("n_move", [ComputeTaskType.LLM_COMPLETION])

    # default register to LOW when pool omitted
    pool.register_node(n)

    task_low = ComputeTask()
    task_low.task_type = ComputeTaskType.LLM_COMPLETION
    task_low.priority = "low"
    low_ids = [c.node_id for c in pool.get_candidates(task_low, limit=4)]
    assert "n_move" in low_ids

    # move to HIGH
    pool.assign_node_to_pool("n_move", pool.HIGH_POOL)
    task_high = ComputeTask()
    task_high.task_type = ComputeTaskType.LLM_COMPLETION
    task_high.priority = "high"
    high_ids = [c.node_id for c in pool.get_candidates(task_high, limit=4)]
    assert "n_move" in high_ids

    # remove from HIGH, should disappear from HIGH candidates
    pool.remove_node_from_pool("n_move", pool.HIGH_POOL)
    high_ids_after = [c.node_id for c in pool.get_candidates(task_high, limit=4)]
    assert "n_move" not in high_ids_after


if __name__ == "__main__":
    test_high_priority_llm_routes_to_high_pool_and_lists_all_pool_nodes()
    test_low_priority_llm_routes_to_low_pool()
    test_list_ids_by_task_basic_filtering()
    test_get_candidates_returns_all_pool_nodes()
    test_disabled_nodes_still_listed_in_pool()
    test_assign_and_remove_node_updates_pools()
    print("node_pool tests passed")


