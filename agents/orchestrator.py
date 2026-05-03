from unittest import result


class Orchestrator:
    def __init__(self, planner, executor, critic, memory_manager):
        self.planner = planner
        self.executor = executor
        self.critic = critic
        self.memory = memory_manager
        
    def run_sequential(self, task: str, max_retries=2):
        #1. 规划
        plan = self.planner.plan(task)
        print(f"[Orchestrator] 计划: {plan}")
        
        
        results = {}
        final_output = task
        for subtask in plan:
            #2. 执行当前子任务（考虑依赖）
            for attempt in range(max_retries+1):
                result = self.executor.execute_subtask(subtask,results)
                
                #3. 评审
                passed, feedback = self.critic.evaluate(subtask["description"],result)
                if passed:
                    results[subtask["id"]] = result
                    print(f"[Orchestrator] 子任务 {subtask['id']} 通过")
                    break
                else:
                    print(f"[Orchestrator] 子任务 {subtask['id']} 未通过，反馈：{feedback}")
                    # 将反馈注入到子任务描述中重试
                    subtask["description"] = f"{subtask['description']}\n注意：上次失败，反馈：{feedback}"
                    #记录反思记忆
                    self.memory.add_reflection_insight(task, feedback)
                    
            else:
                # 超过最大重试，保存最后一次结果并继续
                results[subtask["id"]] = result
            
        # 汇总所有子任务结果
        all_results = "\n".join([f"{sub['description']}: {results.get(sub['id'], '未完成')}" for sub in plan])
        final_output = f"任务完成，汇总如下：\n{all_results}"
        return final_output