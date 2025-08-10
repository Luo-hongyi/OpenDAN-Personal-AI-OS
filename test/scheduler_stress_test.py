import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
import os
import sys
import asyncio
import random
import time
from typing import List, Dict
from collections import defaultdict

directory = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(directory, "..", "src")))

from aios.proto.compute_task_test import ComputeTask, ComputeTaskType, LLMPrompt
from aios.frame.compute_kernel import ComputeKernel
from component.test_node.test_node import TestComputeNode
from aios.storage.storage import AIStorage

print("package loaded")

# Configuration parameters
NUM_NODES = 16  # Number of nodes, based on CPU core count
BATCH_SIZE = 20  # Number of tasks per batch
NUM_BATCHES = 10  # Total number of batches
BATCH_INTERVAL = 1.0  # Batch interval (seconds)

# Task parameter configurations with priority
TASK_CONFIGS = [
    # (runtime_ms, difficulty, input_tokens, priority, description)
    (100, 3.0, 100, 0, "Simple Task"),
    (200, 5.0, 200, 1, "Medium Priority Task"),
    (500, 7.0, 500, 2, "High Priority Task"),
    (1000, 9.0, 1000, 3, "Critical Priority Task"),
    (50, 2.0, 50, 0, "Quick Task"),
]

# Node configurations
NODE_CONFIGS = [
    # (ability, price_per_token, fault_error_rate, compute_error_rate, description)
    (10.0, 0.000001, 0.001, 0.01, "High Performance Node"),
    (8.0, 0.000002, 0.005, 0.02, "Medium Performance Node"),
    (6.0, 0.000003, 0.01, 0.03, "Low Performance Node"),
]

class TaskStatistics:
    """Statistics collector for task completion analysis"""
    
    def __init__(self):
        self.tasks = []
        self.quality_scores = []
        self.latency_scores = []
        self.cost_scores = []
        self.overall_scores = []
        self.priority_stats = defaultdict(list)
        
    def calculate_quality_score(self, difficulty: float, ability: float) -> float:
        """Calculate quality score based on task difficulty vs node ability"""
        return max(0, 10 - max(0, difficulty - ability))
    
    def calculate_latency_threshold(self, priority: int) -> float:
        """Calculate latency threshold based on priority (higher priority = more sensitive)"""
        base_threshold = 1000  # 1 second for priority 0
        if priority == 0:
            return base_threshold
        elif priority == 1:
            return base_threshold / 2  # 500ms
        elif priority == 2:
            return base_threshold / 5  # 200ms
        elif priority == 3:
            return base_threshold / 10  # 100ms
        else:
            return base_threshold / (priority + 1)
    
    def calculate_latency_score(self, queue_wait_ms: float, priority: int) -> float:
        """Calculate latency score based on queue wait time and priority"""
        threshold = self.calculate_latency_threshold(priority)
        return max(0, 10 - (queue_wait_ms / threshold))
    
    def calculate_cost_score(self, cost: float) -> float:
        """Calculate cost score (lower cost = higher score)"""
        return max(0, 10 - (cost / 0.01))  # 0.01 cost = 0 score
    
    def add_task_result(self, task: ComputeTask, result, node_ability: float):
        """Add a completed task result to statistics"""
        # Extract task parameters
        difficulty = getattr(task, 'difficulty', 0.0)
        priority = getattr(task, 'priority', 0)
        input_tokens = getattr(task, 'input_tokens', 0)
        
        # Calculate scores
        quality_score = self.calculate_quality_score(difficulty, node_ability)
        cost_score = self.calculate_cost_score(result.cost)
        
        # Calculate queue wait time
        queue_wait_ms = 0.0
        if hasattr(task, 'started_at') and hasattr(task, 'scheduled_at'):
            if task.started_at is not None and task.scheduled_at is not None:
                queue_wait_ms = max(0.0, (task.started_at - task.scheduled_at) * 1000.0)
        
        latency_score = self.calculate_latency_score(queue_wait_ms, priority)
        overall_score = (quality_score + latency_score + cost_score) / 3
        
        # Store results
        task_result = {
            'task_id': task.task_id,
            'priority': priority,
            'difficulty': difficulty,
            'queue_wait_ms': queue_wait_ms,
            'quality_score': quality_score,
            'latency_score': latency_score,
            'cost_score': cost_score,
            'overall_score': overall_score,
            'cost': result.cost,
            'node_ability': node_ability,
        }
        
        self.tasks.append(task_result)
        self.quality_scores.append(quality_score)
        self.latency_scores.append(latency_score)
        self.cost_scores.append(cost_score)
        self.overall_scores.append(overall_score)
        self.priority_stats[priority].append(task_result)
    
    def generate_report(self) -> str:
        """Generate comprehensive statistics report"""
        if not self.tasks:
            return "No tasks completed for statistics"
        
        report = []
        report.append("=== Task Completion Statistics ===")
        report.append(f"Total Tasks: {len(self.tasks)}")
        
        # Quality metrics
        avg_quality = sum(self.quality_scores) / len(self.quality_scores)
        min_quality = min(self.quality_scores)
        max_quality = max(self.quality_scores)
        report.append(f"\nQuality Metrics:")
        report.append(f"- Average Quality Score: {avg_quality:.2f}")
        report.append(f"- Min/Max Quality: {min_quality:.1f} / {max_quality:.1f}")
        
        # Latency metrics
        avg_latency = sum(self.latency_scores) / len(self.latency_scores)
        avg_queue_wait = sum(t['queue_wait_ms'] for t in self.tasks) / len(self.tasks)
        max_queue_wait = max(t['queue_wait_ms'] for t in self.tasks)
        report.append(f"\nLatency Metrics:")
        report.append(f"- Average Latency Score: {avg_latency:.2f}")
        report.append(f"- Average Queue Wait: {avg_queue_wait:.2f}s")
        report.append(f"- Max Queue Wait: {max_queue_wait:.2f}s")
        
        # Priority-based latency analysis
        if len(self.priority_stats) > 1:
            report.append(f"- Priority-based Analysis:")
            for priority in sorted(self.priority_stats.keys()):
                priority_tasks = self.priority_stats[priority]
                avg_score = sum(t['latency_score'] for t in priority_tasks) / len(priority_tasks)
                avg_wait = sum(t['queue_wait_ms'] for t in priority_tasks) / len(priority_tasks)
                report.append(f"  * Priority {priority}: Avg Score {avg_score:.1f}, Avg Wait {avg_wait:.1f}s")
        
        # Cost metrics
        avg_cost_score = sum(self.cost_scores) / len(self.cost_scores)
        total_cost = sum(t['cost'] for t in self.tasks)
        avg_cost_per_task = total_cost / len(self.tasks)
        report.append(f"\nCost Metrics:")
        report.append(f"- Average Cost Score: {avg_cost_score:.2f}")
        report.append(f"- Total Cost: {total_cost:.6f}")
        report.append(f"- Average Cost per Task: {avg_cost_per_task:.6f}")
        
        # Overall performance
        avg_overall = sum(self.overall_scores) / len(self.overall_scores)
        report.append(f"\nOverall Performance:")
        report.append(f"- Average Overall Score: {avg_overall:.2f}")
        
        return "\n".join(report)

# Mock AIStorage
storage = AIStorage.get_instance()
storage.user_config.set_value("llm_code_models",["o3","gpt-4o","gpt-3.5-turbo"])
storage.user_config.sort_llm_models_by_cost("llm_code_models")

def create_test_nodes():
    """Create test nodes"""
    nodes = []
    support_task_types = [ComputeTaskType.LLM_COMPLETION]
    
    for i in range(NUM_NODES):
        node = TestComputeNode()
        node.support_task_types = support_task_types
        node.node_id = f"test_node_{i+1}"
        
        # Randomly select node configuration
        config = random.choice(NODE_CONFIGS)
        node.ability = config[0]
        node.price_per_token = config[1]
        node.fault_error_rate = config[2]
        node.compute_error_rate = config[3]
        
        nodes.append(node)
        print(f"Created node {node.node_id}: ability={node.ability}, price={node.price_per_token}, fault_rate={node.fault_error_rate}, compute_rate={node.compute_error_rate}")
    
    return nodes

def create_task_batch(batch_id: int) -> List[Dict]:
    """Create a batch of tasks"""
    tasks = []
    
    for i in range(BATCH_SIZE):
        # Randomly select task configuration
        config = random.choice(TASK_CONFIGS)
        runtime_ms, difficulty, input_tokens, priority, description = config
        
        # Create LLM Prompt
        prompt = LLMPrompt()
        prompt.append_user_message(f"Batch {batch_id} Task {i+1}: {description}")
        
        # Create ComputeTask
        task = ComputeTask()
        task.set_llm_params(prompt, "text", "default_llm", 1000)
        
        # Set task parameters
        task.runtime_ms = runtime_ms
        task.difficulty = difficulty
        task.input_tokens = input_tokens
        task.priority = priority # Assign priority
        
        tasks.append({
            "task": task,
            "batch_id": batch_id,
            "task_id": i + 1,
            "description": description,
            "runtime_ms": runtime_ms,
            "difficulty": difficulty,
            "input_tokens": input_tokens,
            "priority": priority
        })
    
    return tasks

async def run_batch(batch_tasks: List[Dict], batch_id: int):
    """Run a batch of tasks"""
    print(f"\n=== Starting batch {batch_id} ({len(batch_tasks)} tasks) ===")
    
    # Get compute kernel
    kernel = ComputeKernel.get_instance()
    
    # Execute tasks concurrently
    start_time = time.time()
    tasks = []
    
    for task_info in batch_tasks:
        task = task_info["task"]
        
        # Submit task to kernel
        kernel.run(task)
        
        # Create a coroutine to wait for task completion
        async def wait_task_completion(task, task_info):
            while task.state.value not in [0, 3]:  # DONE or ERROR
                await asyncio.sleep(0.1)
            return task, task_info
        
        tasks.append(wait_task_completion(task, task_info))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"=== Batch {batch_id} completed, time: {elapsed:.2f} seconds ===")
    
    # Statistics
    success_count = len([r for r in results if r[0].state.value == 0])  # DONE
    error_count = len(results) - success_count
    
    print(f"Success: {success_count}, Failed: {error_count}")
    
    # Print some task results examples
    for i, (task, task_info) in enumerate(results[:3]):  # Only show first 3
        if task.result:
            print(f"  Task {i+1}: {task_info['description']} - {task.result.result_str}")
    
    return results

async def main():
    """Main test function"""
    print(f"=== Scheduler Stress Test ===")
    print(f"Number of nodes: {NUM_NODES}")
    print(f"Number of batches: {NUM_BATCHES}")
    print(f"Tasks per batch: {BATCH_SIZE}")
    print(f"Batch interval: {BATCH_INTERVAL} seconds")
    
    # Create test nodes
    nodes = create_test_nodes()
    
    # Start compute kernel
    kernel = ComputeKernel.get_instance()
    
    # Start all nodes
    for node in nodes:
        node.start()
        kernel.add_compute_node(node)
        print(f"Started node: {node.node_id}")
    
    await kernel.start()
    print("Compute kernel started")
    
    # Distribute tasks in batches
    all_results = []
    task_stats = TaskStatistics() # Initialize statistics collector
    
    for batch_id in range(1, NUM_BATCHES + 1):
        # Create tasks for the current batch
        batch_tasks = create_task_batch(batch_id)
        
        # Run the current batch
        batch_results = await run_batch(batch_tasks, batch_id)
        all_results.extend(batch_results)
        
        # Wait for the next batch (except the last one)
        if batch_id < NUM_BATCHES:
            print(f"Waiting {BATCH_INTERVAL} seconds before submitting next batch...")
            await asyncio.sleep(BATCH_INTERVAL)
        
        # Process results for statistics after each batch
        for task, task_info in batch_results:
            # Get node ability from the assigned node
            node_ability = 10.0  # Default ability
            if hasattr(task, 'assigned_node_id') and task.assigned_node_id:
                # Find the node that processed this task
                kernel = ComputeKernel.get_instance()
                # Access the actual node objects from the kernel
                for node_id, node in kernel.compute_nodes.items():
                    if node_id == task.assigned_node_id:
                        node_ability = node.ability
                        break
            
            task_stats.add_task_result(task, task.result, node_ability)
    
    # Final statistics
    print(f"\n=== Test Completed ===")
    print(f"Total tasks: {len(all_results)}")
    
    success_count = len([r for r in all_results if r[0].state.value == 0])  # DONE
    error_count = len(all_results) - success_count
    
    print(f"Total success: {success_count}")
    print(f"Total failed: {error_count}")
    print(f"Success rate: {success_count/len(all_results)*100:.1f}%")
    
    # Generate and print statistics report
    print(task_stats.generate_report())

if __name__ == "__main__":
    asyncio.run(main())
