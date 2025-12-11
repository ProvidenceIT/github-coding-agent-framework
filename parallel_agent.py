"""
Parallel Agent Orchestration
=============================

Run multiple coding agents in parallel with intelligent work distribution.

Features:
- Multi-agent coordination via Linear
- Automatic issue assignment (avoid conflicts)
- Parallel execution with async/await
- Progress aggregation and monitoring
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Set
import json
from datetime import datetime

from agent import run_agent_session
from linear_cache import LinearCache


class ParallelAgentCoordinator:
    """
    Coordinate multiple agents working on different Linear issues simultaneously.

    Strategy:
    1. Query Linear for available Todo issues
    2. Assign issues to agents (avoiding conflicts)
    3. Run agents in parallel with async/await
    4. Monitor progress and aggregate results
    5. Handle failures gracefully
    """

    def __init__(self, project_dir: Path, max_agents: int = 3):
        self.project_dir = project_dir
        self.max_agents = max_agents
        self.cache = LinearCache(project_dir)
        self.active_agents: Dict[str, asyncio.Task] = {}
        self.completed_issues: Set[str] = set()

    async def get_available_issues(self, project_id: str, count: int) -> List[Dict]:
        """
        Get available Todo issues for assignment.

        Returns highest-priority issues that aren't already assigned.
        """
        # In real implementation, this would:
        # 1. Call Linear API to get Todo issues
        # 2. Sort by priority
        # 3. Exclude issues already being worked on
        # 4. Return top N issues

        # Placeholder
        return []

    async def assign_issue_to_agent(self, issue: Dict, agent_id: int):
        """
        Assign an issue to an agent.

        1. Update Linear issue status to "In Progress"
        2. Add comment indicating agent ownership
        3. Track assignment locally
        """
        issue_id = issue['id']
        issue_title = issue.get('title', 'Unknown')

        print(f"🤖 Agent {agent_id}: Assigned to {issue_title} ({issue_id})")

        # In real implementation:
        # - Update issue status via Linear API
        # - Add comment with agent ID and timestamp
        # - Cache assignment to avoid race conditions

        return issue_id

    async def run_agent_on_issue(
        self,
        agent_id: int,
        issue_id: str,
        model: str = "claude-opus-4-5-20251101"
    ) -> Dict:
        """
        Run a single agent focused on one issue.

        Returns:
            Result dict with status and outcome
        """
        print(f"🚀 Agent {agent_id}: Starting work on {issue_id}")

        try:
            # In real implementation, you'd:
            # 1. Create a focused prompt for this specific issue
            # 2. Create a fresh client for this agent
            # 3. Run the agent session with issue context
            # 4. Monitor progress
            # 5. Handle completion or failure

            # Simulate work
            await asyncio.sleep(10)  # Placeholder for actual agent execution

            result = {
                'agent_id': agent_id,
                'issue_id': issue_id,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }

            print(f"✅ Agent {agent_id}: Completed {issue_id}")
            return result

        except Exception as e:
            print(f"❌ Agent {agent_id}: Failed on {issue_id} - {e}")
            return {
                'agent_id': agent_id,
                'issue_id': issue_id,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def run_parallel_agents(
        self,
        project_id: str,
        num_agents: Optional[int] = None,
        model: str = "claude-opus-4-5-20251101"
    ):
        """
        Run multiple agents in parallel.

        Args:
            project_id: Linear project ID
            num_agents: Number of parallel agents (default: self.max_agents)
            model: Claude model to use

        Returns:
            List of results from all agents
        """
        if num_agents is None:
            num_agents = self.max_agents

        print(f"🎯 Starting {num_agents} parallel agents for project {project_id}")

        # Get available issues
        available_issues = await self.get_available_issues(project_id, num_agents)

        if not available_issues:
            print("⚠️  No available issues to work on")
            return []

        # Create agent tasks
        tasks = []
        for i, issue in enumerate(available_issues[:num_agents]):
            issue_id = await self.assign_issue_to_agent(issue, agent_id=i+1)
            task = asyncio.create_task(
                self.run_agent_on_issue(agent_id=i+1, issue_id=issue_id, model=model)
            )
            tasks.append(task)

        # Run all agents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = [r for r in results if isinstance(r, dict) and r.get('status') == 'completed']
        failed = [r for r in results if isinstance(r, dict) and r.get('status') == 'failed']

        print(f"\n📊 Parallel execution complete:")
        print(f"   ✅ Successful: {len(successful)}")
        print(f"   ❌ Failed: {len(failed)}")

        return results


async def run_parallel_demo(project_dir: Path, num_agents: int = 3):
    """
    Demo function to run parallel agents.

    Usage:
        asyncio.run(run_parallel_demo(Path("./my_project"), num_agents=3))
    """
    coordinator = ParallelAgentCoordinator(project_dir, max_agents=num_agents)

    # Load project metadata
    project_json = project_dir / ".linear_project.json"
    if not project_json.exists():
        print("❌ Error: Project not initialized. Run initializer first.")
        return

    with open(project_json, 'r') as f:
        project_data = json.load(f)
        project_id = project_data['project_id']

    # Run parallel agents
    results = await coordinator.run_parallel_agents(project_id, num_agents=num_agents)

    return results


# CLI interface for parallel execution
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parallel_agent.py <project_dir> [num_agents]")
        print("Example: python parallel_agent.py ./my_project 3")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    num_agents = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    print(f"🚀 Launching {num_agents} parallel agents for {project_dir}")
    asyncio.run(run_parallel_demo(project_dir, num_agents))
