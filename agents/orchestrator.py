from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.message import Message
from agents.plan_graph import PlanGraph


class Orchestrator:
    def __init__(self, planner, executor, critic, memory_manager):
        self.name = "orchestrator"
        self.planner = planner
        self.executor = executor
        self.critic = critic
        self.memory = memory_manager
        self.graph = None

    def run_sequential(self, task: str, max_retries=2):
        """[兼容旧接口] 委托给 run_with_graph（串行模式）。"""
        return self.run_with_graph(task, max_retries=max_retries, parallel=False)

    def run_with_graph(self, task: str, max_retries=2, parallel=False, max_replans=2):
        """基于 DAG 的计划执行引擎：规划 → DAG 调度 → 执行 → 评审 → 重规划/回溯。"""
        # ── 1. 规划阶段 ──
        print(f"[Orchestrator] 正在规划任务: {task}")
        plan_msg = Message(
            type="task", sender=self.name, receiver=self.planner.name, payload=task,
        )
        plan_response = self.planner.handle_message(plan_msg)
        plan = plan_response.payload
        print(f"[Orchestrator] 原始计划: {plan}")

        graph = PlanGraph()
        graph.from_plan(plan)
        self.graph = graph

        errors = graph.validate()
        if errors:
            print(f"[Orchestrator] 计划校验失败: {errors}")
            return f"计划无效，无法执行。错误: {'; '.join(errors)}"

        print(f"[Orchestrator]\n{graph.progress_summary()}")

        # ── 2. 执行循环 ──
        replan_count = 0

        while not graph.all_done():
            ready = graph.get_ready_tasks()

            if not ready:
                failed = graph.get_failed_nodes()
                if failed and replan_count < max_replans:
                    print(f"[Orchestrator] 无就绪任务，触发重规划 (第 {replan_count + 1} 次)")
                    self._trigger_replan(task, failed)
                    replan_count += 1
                    print(f"[Orchestrator]\n{graph.progress_summary()}")
                    continue
                elif failed:
                    print("[Orchestrator] 已达到最大重规划次数，部分任务未能完成")
                else:
                    print("[Orchestrator] 检测到可能的死锁，无法继续")
                break

            # 依赖上下文快照（本批次开始时）
            previous_results = {n.id: n.result for n in graph.get_done_nodes()}

            if parallel and len(ready) > 1:
                self._run_parallel(ready, previous_results, max_retries)
            else:
                for node in ready:
                    self._execute_node(node, previous_results, max_retries)
                    if node.status == "done":
                        previous_results[node.id] = node.result

            # 本轮执行后检测失败 → 回溯 → 必要时 replan
            failed_after = graph.get_failed_nodes()
            for fn in failed_after:
                if self._backtrack(fn):
                    print(f"[Orchestrator] 节点 {fn.id} 已切换到替代路径")

            still_failed = [n for n in failed_after if n.status == "failed"]
            if still_failed and replan_count < max_replans:
                if all(not graph.has_alternatives(n.id) for n in still_failed):
                    replan_count += 1
                    print(f"[Orchestrator] 无可替代路径，触发重规划 (第 {replan_count} 次)")
                    self._trigger_replan(task, still_failed)

            print(f"[Orchestrator]\n{graph.progress_summary()}")

        # ── 3. 汇总结果 ──
        done_nodes = graph.get_done_nodes()
        failed_nodes = graph.get_failed_nodes()

        results_lines = [f"[完成] {n.id}: {n.description[:60]} -> {n.result}" for n in done_nodes]
        if failed_nodes:
            results_lines.append("---")
            results_lines.append("以下任务未能完成:")
            results_lines.extend(
                f"[失败] {n.id}: {n.description[:60]} (原因: {n.feedback or '未知'})"
                for n in failed_nodes
            )
        return "任务完成。\n" + "\n".join(results_lines)

    # ── 私有方法 ──

    def _execute_node(self, node, previous_results, max_retries):
        """执行单个节点，含 Critic 评审和重试循环。"""
        self.graph.mark_running(node.id)

        for attempt in range(max_retries + 1):
            exec_msg = Message(
                type="task", sender=self.name, receiver=self.executor.name,
                payload={
                    "subtask": {
                        "id": node.id,
                        "description": node.description,
                        "depends_on": node.dependencies,
                    },
                    "previous_results": previous_results,
                },
            )
            exec_response = self.executor.handle_message(exec_msg)
            result = exec_response.payload

            critic_msg = Message(
                type="task", sender=self.name, receiver=self.critic.name,
                payload={"task": node.description, "result": result},
            )
            critic_response = self.critic.handle_message(critic_msg)
            passed = critic_response.payload["passed"]
            feedback = critic_response.payload["feedback"]

            if passed:
                self.graph.mark_done(node.id, result)
                print(f"[Orchestrator] 子任务 {node.id} 通过")
                return True
            else:
                print(f"[Orchestrator] 子任务 {node.id} 第 {attempt + 1} 次未通过: {feedback[:80]}")
                self.memory.add_reflection_insight(node.description, feedback)
                if attempt < max_retries:
                    node.description = f"{node.description}\n注意：上次失败，反馈：{feedback}"
                else:
                    self.graph.mark_failed(node.id, feedback)
                    print(f"[Orchestrator] 子任务 {node.id} 已达最大重试次数")
                    return False
        return False

    def _trigger_replan(self, original_task, failed_nodes):
        """调用 Planner.replan() 并合并计划。"""
        new_plan = self.planner.replan(original_task, self.graph, failed_nodes)
        if not new_plan:
            print("[Orchestrator] 重规划返回空，尝试回溯各失败节点")
            for fn in failed_nodes:
                self._backtrack(fn)
            return False
        self.graph.merge_replan(new_plan)
        print("[Orchestrator] 重规划完成，计划已更新")
        return True

    def _backtrack(self, node):
        """尝试用替代描述回溯失败节点。"""
        if self.graph.has_alternatives(node.id):
            new_desc = self.graph.try_alternative(node.id)
            print(f"[Orchestrator] 节点 {node.id} 回溯，新路径: {new_desc[:60]}...")
            return True
        return False

    def _run_parallel(self, ready_nodes, previous_results, max_retries):
        """并行执行一组就绪任务。"""
        with ThreadPoolExecutor(max_workers=len(ready_nodes)) as pool:
            futures = {
                pool.submit(self._execute_node, node, dict(previous_results), max_retries): node
                for node in ready_nodes
            }
            for _ in as_completed(futures):
                pass  # _execute_node 已更新 PlanGraph 状态
