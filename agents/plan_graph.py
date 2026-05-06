from typing import List, Optional, Dict


class TaskNode:
    def __init__(self, id: str, description: str, dependencies: List[str]):
        self.id = id
        self.description = description
        self.dependencies = dependencies
        self.status = "pending"  # pending, running, done, failed
        self.result: Optional[str] = None
        self.feedback: Optional[str] = None
        self.attempts = 0
        self.max_attempts = 2
        self.alternative_descriptions: List[str] = []


class PlanGraph:
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}

    def from_plan(self, plan: List[dict]):
        """从 Planner JSON 构建节点"""
        for item in plan:
            node = TaskNode(
                id=item["id"],
                description=item["description"],
                dependencies=item.get("depends_on", [])
            )
            self.nodes[node.id] = node

    # ── 状态管理 ──

    def mark_running(self, node_id: str):
        self.nodes[node_id].status = "running"

    def mark_done(self, node_id: str, result: str):
        node = self.nodes[node_id]
        node.status = "done"
        node.result = result

    def mark_failed(self, node_id: str, feedback: str):
        node = self.nodes[node_id]
        node.status = "failed"
        node.feedback = feedback
        node.attempts += 1

    # ── 查询方法 ──

    def get_node(self, node_id: str) -> TaskNode:
        return self.nodes[node_id]

    def get_nodes_by_status(self, status: str) -> List[TaskNode]:
        return [n for n in self.nodes.values() if n.status == status]

    def get_failed_nodes(self) -> List[TaskNode]:
        return self.get_nodes_by_status("failed")

    def get_done_nodes(self) -> List[TaskNode]:
        return self.get_nodes_by_status("done")

    def get_pending_nodes(self) -> List[TaskNode]:
        return self.get_nodes_by_status("pending")

    def get_ready_tasks(self) -> List[TaskNode]:
        """返回当前所有依赖已满足且 pending 的任务"""
        ready = []
        for node in self.nodes.values():
            if node.status != "pending":
                continue
            deps_done = all(
                self.nodes[dep].status == "done"
                for dep in node.dependencies
                if dep in self.nodes
            )
            if deps_done:
                ready.append(node)
        return ready

    def all_done(self) -> bool:
        return all(nd.status == "done" for nd in self.nodes.values())

    def reset_failed(self):
        """将失败任务的依赖重置（用于回溯）"""
        for node in self.nodes.values():
            if node.status == "failed":
                node.status = "pending"

    # ── 进度展示 ──

    def progress_summary(self) -> str:
        done = len(self.get_done_nodes())
        failed = len(self.get_failed_nodes())
        running = len(self.get_nodes_by_status("running"))
        pending = len(self.get_pending_nodes())
        total = len(self.nodes)
        lines = [f"进度: {done}/{total} 完成, {running} 运行中, {pending} 待处理, {failed} 失败"]
        status_order = {"running": "[运行]", "failed": "[失败]", "pending": "[待定]", "done": "[完成]"}
        for status, label in status_order.items():
            for node in self.get_nodes_by_status(status):
                extra = f" -> {node.feedback[:40]}" if node.feedback else ""
                lines.append(f"  {label} {node.id}: {node.description[:50]}{extra}")
        return "\n".join(lines)

    # ── 校验 ──

    def validate(self) -> List[str]:
        """检测循环依赖和孤立引用，返回错误列表（空表示合法）"""
        errors = []
        node_ids = set(self.nodes.keys())
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in node_ids:
                    errors.append(f"任务 '{node_id}' 依赖了不存在的任务 '{dep_id}'")

        if errors:
            return errors

        # DFS 循环检测
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in node_ids}

        def dfs(nid):
            color[nid] = GRAY
            for dep_id in self.nodes[nid].dependencies:
                if color[dep_id] == GRAY:
                    errors.append(f"检测到循环依赖，涉及任务 '{nid}' 和 '{dep_id}'")
                    return
                if color[dep_id] == WHITE:
                    dfs(dep_id)
            color[nid] = BLACK

        for nid in node_ids:
            if color[nid] == WHITE:
                dfs(nid)

        return errors

    # ── 计划合并 ──

    def merge_replan(self, new_plan: List[dict]):
        """合并重规划结果：保留已完成节点，替换/新增待定节点，删除不在新计划中的未完成节点"""
        new_ids = {item["id"] for item in new_plan}
        # 删除不在新计划中的未完成节点
        for node_id in list(self.nodes.keys()):
            if node_id not in new_ids and self.nodes[node_id].status != "done":
                del self.nodes[node_id]
        # 更新或新增节点
        for item in new_plan:
            if item["id"] in self.nodes and self.nodes[item["id"]].status == "done":
                continue  # 保留已完成的
            node = TaskNode(
                id=item["id"],
                description=item["description"],
                dependencies=item.get("depends_on", [])
            )
            self.nodes[node.id] = node

    # ── 回溯 ──

    def has_alternatives(self, node_id: str) -> bool:
        return len(self.nodes[node_id].alternative_descriptions) > 0

    def try_alternative(self, node_id: str) -> Optional[str]:
        """弹出替代描述，重置节点为 pending，返回新描述；无替代时返回 None"""
        node = self.nodes[node_id]
        if not node.alternative_descriptions:
            return None
        new_desc = node.alternative_descriptions.pop(0)
        node.description = new_desc
        node.status = "pending"
        node.attempts = 0
        node.feedback = None
        return new_desc
