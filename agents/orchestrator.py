from agents.message import Message


class Orchestrator:
    def __init__(self, planner, executor, critic, memory_manager):
        self.name = "orchestrator"
        self.planner = planner
        self.executor = executor
        self.critic = critic
        self.memory = memory_manager

    def run_sequential(self, task: str, max_retries=2):
        # 1. 规划：通过 Message 与 Planner 通信
        plan_msg = Message(
            type="task",
            sender=self.name,
            receiver=self.planner.name,
            payload=task,
        )
        plan_response = self.planner.handle_message(plan_msg)
        plan = plan_response.payload
        print(f"[Orchestrator] 计划: {plan}")

        results = {}
        final_output = task
        for subtask in plan:
            subtask_description = subtask["description"]
            for attempt in range(max_retries + 1):
                # 2. 执行当前子任务（考虑依赖）
                exec_msg = Message(
                    type="task",
                    sender=self.name,
                    receiver=self.executor.name,
                    payload={"subtask": subtask, "previous_results": results},
                )
                exec_response = self.executor.handle_message(exec_msg)
                result = exec_response.payload

                # 3. 评审
                critic_msg = Message(
                    type="task",
                    sender=self.name,
                    receiver=self.critic.name,
                    payload={"task": subtask_description, "result": result},
                )
                critic_response = self.critic.handle_message(critic_msg)
                passed = critic_response.payload["passed"]
                feedback = critic_response.payload["feedback"]

                if passed:
                    results[subtask["id"]] = result
                    print(f"[Orchestrator] 子任务 {subtask['id']} 通过")
                    break
                else:
                    print(f"[Orchestrator] 子任务 {subtask['id']} 未通过，反馈：{feedback}")
                    # 将反馈写入 subtask 副本，不修改原始 plan
                    subtask = {**subtask, "description": f"{subtask_description}\n注意：上次失败，反馈：{feedback}"}
                    self.memory.add_reflection_insight(task, feedback)
            else:
                # 超过最大重试，保存最后一次结果并继续
                results[subtask["id"]] = result

        # 汇总所有子任务结果
        all_results = "\n".join(
            [f"{sub['description']}: {results.get(sub['id'], '未完成')}" for sub in plan]
        )
        final_output = f"任务完成，汇总如下：\n{all_results}"
        return final_output
