"""TaskNode + PlanGraph 测试 (47+ 用例) —— 纯数据结构和算法，完全离线可测。"""

import pytest
from agents.plan_graph import TaskNode, PlanGraph


# ════════════════════ TaskNode ════════════════════

class TestTaskNode:
    def test_tasknode_creation_with_all_fields(self):
        node = TaskNode(id="1", description="搜索数据", dependencies=["0"])
        assert node.id == "1"
        assert node.description == "搜索数据"
        assert node.dependencies == ["0"]

    def test_tasknode_default_status_is_pending(self):
        node = TaskNode(id="1", description="test", dependencies=[])
        assert node.status == "pending"

    def test_tasknode_default_result_is_none(self):
        node = TaskNode(id="1", description="test", dependencies=[])
        assert node.result is None

    def test_tasknode_default_feedback_is_none(self):
        node = TaskNode(id="1", description="test", dependencies=[])
        assert node.feedback is None

    def test_tasknode_default_attempts_zero(self):
        node = TaskNode(id="1", description="test", dependencies=[])
        assert node.attempts == 0

    def test_tasknode_default_max_attempts_is_2(self):
        node = TaskNode(id="1", description="test", dependencies=[])
        assert node.max_attempts == 2

    def test_tasknode_default_alternative_descriptions_empty(self):
        node = TaskNode(id="1", description="test", dependencies=[])
        assert node.alternative_descriptions == []


# ════════════════════ PlanGraph.from_plan ════════════════════

class TestPlanGraphFromPlan:
    def test_from_plan_empty_list_creates_no_nodes(self):
        g = PlanGraph()
        g.from_plan([])
        assert len(g.nodes) == 0

    def test_from_plan_single_node_no_dependencies(self):
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "任务", "depends_on": []}])
        assert len(g.nodes) == 1
        assert g.nodes["1"].description == "任务"

    def test_from_plan_multiple_nodes_with_dependencies(self):
        g = PlanGraph()
        plan = [
            {"id": "1", "description": "A", "depends_on": []},
            {"id": "2", "description": "B", "depends_on": ["1"]},
        ]
        g.from_plan(plan)
        assert len(g.nodes) == 2
        assert g.nodes["2"].dependencies == ["1"]

    def test_from_plan_nodes_have_dependencies_attribute(self):
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "A", "depends_on": ["x"]}])
        assert g.nodes["1"].dependencies == ["x"]

    def test_from_plan_item_without_depends_on_defaults_to_empty(self):
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "A"}])
        assert g.nodes["1"].dependencies == []


# ════════════════════ get_ready_tasks ════════════════════

class TestGetReadyTasks:
    def test_get_ready_tasks_empty_graph_returns_empty(self, empty_graph):
        assert empty_graph.get_ready_tasks() == []

    def test_get_ready_tasks_all_pending_no_deps_all_ready(self):
        g = PlanGraph()
        g.from_plan([
            {"id": "1", "description": "A", "depends_on": []},
            {"id": "2", "description": "B", "depends_on": []},
        ])
        ready = g.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_tasks_dependency_not_done_blocks(self, graph_from_plan):
        ready = graph_from_plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "1"

    def test_get_ready_tasks_dependency_done_unblocks(self, graph_from_plan):
        graph_from_plan.mark_done("1", "result-1")
        ready = graph_from_plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "2"

    def test_get_ready_tasks_mixed_status(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_done("2", "r2")
        ready = graph_from_plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "3"

    def test_get_ready_tasks_depends_on_nonexistent_id_skips_check(self):
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "A", "depends_on": ["nonexistent"]}])
        ready = g.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "1"

    def test_get_ready_tasks_done_tasks_excluded(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_done("2", "r2")
        graph_from_plan.mark_done("3", "r3")
        assert graph_from_plan.get_ready_tasks() == []

    def test_get_ready_tasks_running_tasks_excluded(self, graph_from_plan):
        graph_from_plan.mark_running("1")
        ready = graph_from_plan.get_ready_tasks()
        assert all(n.id != "1" for n in ready)

    def test_get_ready_tasks_failed_tasks_excluded(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "error")
        ready = graph_from_plan.get_ready_tasks()
        assert all(n.id != "1" for n in ready)

    def test_get_ready_tasks_chain_dependency(self, graph_from_plan):
        ready_ids = [n.id for n in graph_from_plan.get_ready_tasks()]
        assert ready_ids == ["1"]

    def test_get_ready_tasks_diamond_dependency(self, sample_plan_diamond):
        g = PlanGraph()
        g.from_plan(sample_plan_diamond)
        ready = g.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "1"
        # 完成 1 后，2 和 3 都应就绪
        g.mark_done("1", "r1")
        ready = g.get_ready_tasks()
        assert {n.id for n in ready} == {"2", "3"}


# ════════════════════ validate ════════════════════

class TestValidate:
    def test_validate_empty_graph_returns_empty_errors(self, empty_graph):
        assert empty_graph.validate() == []

    def test_validate_valid_dag_returns_empty_errors(self, graph_from_plan):
        assert graph_from_plan.validate() == []

    def test_validate_missing_dependency_reports_error(self):
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "A", "depends_on": ["99"]}])
        errors = g.validate()
        assert len(errors) == 1
        assert "99" in errors[0]

    def test_validate_self_loop_detected(self):
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "A", "depends_on": ["1"]}])
        errors = g.validate()
        assert len(errors) >= 1

    def test_validate_simple_cycle_detected(self):
        g = PlanGraph()
        g.from_plan([
            {"id": "1", "description": "A", "depends_on": ["2"]},
            {"id": "2", "description": "B", "depends_on": ["1"]},
        ])
        errors = g.validate()
        assert len(errors) >= 1

    def test_validate_complex_cycle_detected(self):
        g = PlanGraph()
        g.from_plan([
            {"id": "1", "description": "A", "depends_on": ["2"]},
            {"id": "2", "description": "B", "depends_on": ["3"]},
            {"id": "3", "description": "C", "depends_on": ["1"]},
        ])
        errors = g.validate()
        assert len(errors) >= 1

    def test_validate_diamond_dependency_is_valid(self, sample_plan_diamond):
        g = PlanGraph()
        g.from_plan(sample_plan_diamond)
        assert g.validate() == []

    def test_validate_multiple_missing_dependencies(self):
        g = PlanGraph()
        g.from_plan([
            {"id": "1", "description": "A", "depends_on": ["x", "y"]},
        ])
        errors = g.validate()
        assert len(errors) >= 1


# ════════════════════ State Transitions ════════════════════

class TestStateTransitions:
    def test_mark_running_changes_status(self, graph_from_plan):
        graph_from_plan.mark_running("1")
        assert graph_from_plan.get_node("1").status == "running"

    def test_mark_done_changes_status_and_sets_result(self, graph_from_plan):
        graph_from_plan.mark_done("1", "完成结果")
        node = graph_from_plan.get_node("1")
        assert node.status == "done"
        assert node.result == "完成结果"

    def test_mark_failed_changes_status_sets_feedback_increments_attempts(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "不够准确")
        node = graph_from_plan.get_node("1")
        assert node.status == "failed"
        assert node.feedback == "不够准确"
        assert node.attempts == 1

    def test_mark_failed_does_not_change_result(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "feedback")
        node = graph_from_plan.get_node("1")
        assert node.result is None

    def test_get_node_returns_correct_node(self, graph_from_plan):
        node = graph_from_plan.get_node("1")
        assert node.id == "1"

    def test_get_node_raises_keyerror_for_missing_id(self, graph_from_plan):
        with pytest.raises(KeyError):
            graph_from_plan.get_node("nonexistent")


# ════════════════════ all_done ════════════════════

class TestAllDone:
    def test_all_done_empty_graph_returns_true(self, empty_graph):
        assert empty_graph.all_done() is True

    def test_all_done_all_nodes_done_returns_true(self, graph_from_plan):
        for nid in ["1", "2", "3"]:
            graph_from_plan.mark_done(nid, f"r-{nid}")
        assert graph_from_plan.all_done() is True

    def test_all_done_some_pending_returns_false(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        assert graph_from_plan.all_done() is False

    def test_all_done_some_failed_returns_false(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_done("2", "r2")
        graph_from_plan.mark_failed("3", "err")
        assert graph_from_plan.all_done() is False

    def test_all_done_mixed_status_returns_false(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_running("2")
        assert graph_from_plan.all_done() is False


# ════════════════════ merge_replan ════════════════════

class TestMergeReplan:
    def test_merge_replan_preserves_done_nodes(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.merge_replan([
            {"id": "2", "description": "B-new", "depends_on": []},
            {"id": "3", "description": "C-new", "depends_on": ["2"]},
        ])
        assert "1" in graph_from_plan.nodes
        assert graph_from_plan.get_node("1").status == "done"

    def test_merge_replan_removes_non_done_nodes_not_in_new_plan(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.merge_replan([
            {"id": "2", "description": "B-new", "depends_on": []},
        ])
        assert "3" not in graph_from_plan.nodes

    def test_merge_replan_adds_new_nodes(self, graph_from_plan):
        graph_from_plan.merge_replan([
            {"id": "1", "description": "A-new", "depends_on": []},
            {"id": "4", "description": "D", "depends_on": ["1"]},
        ])
        assert "4" in graph_from_plan.nodes
        assert graph_from_plan.get_node("4").description == "D"

    def test_merge_replan_replaces_pending_nodes_with_same_id(self, graph_from_plan):
        graph_from_plan.merge_replan([
            {"id": "1", "description": "A-modified", "depends_on": []},
        ])
        assert graph_from_plan.get_node("1").description == "A-modified"

    def test_merge_replan_does_not_replace_done_nodes_with_same_id(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.merge_replan([
            {"id": "1", "description": "A-modified", "depends_on": []},
        ])
        assert graph_from_plan.get_node("1").description == "搜索相关数据"

    def test_merge_replan_resets_status_of_replaced_nodes(self, graph_from_plan):
        graph_from_plan.mark_running("1")
        graph_from_plan.merge_replan([
            {"id": "1", "description": "A-new", "depends_on": []},
        ])
        assert graph_from_plan.get_node("1").status == "pending"

    def test_merge_replan_full_scenario(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_failed("2", "fail")
        graph_from_plan.merge_replan([
            {"id": "2", "description": "B-retry-another-way", "depends_on": ["1"]},
            {"id": "4", "description": "D-new", "depends_on": ["2"]},
        ])
        assert "1" in graph_from_plan.nodes
        assert graph_from_plan.get_node("1").status == "done"
        assert graph_from_plan.get_node("2").status == "pending"
        assert graph_from_plan.get_node("2").description == "B-retry-another-way"
        assert "3" not in graph_from_plan.nodes
        assert "4" in graph_from_plan.nodes


# ════════════════════ try_alternative ════════════════════

class TestTryAlternative:
    def test_try_alternative_with_alternatives_returns_new_description(self, graph_from_plan):
        node = graph_from_plan.get_node("1")
        node.alternative_descriptions = ["替代方案A"]
        result = graph_from_plan.try_alternative("1")
        assert result == "替代方案A"

    def test_try_alternative_without_alternatives_returns_none(self, graph_from_plan):
        result = graph_from_plan.try_alternative("1")
        assert result is None

    def test_try_alternative_resets_node_to_pending(self, graph_from_plan):
        node = graph_from_plan.get_node("1")
        node.alternative_descriptions = ["替代方案A"]
        node.status = "failed"
        graph_from_plan.try_alternative("1")
        assert graph_from_plan.get_node("1").status == "pending"

    def test_try_alternative_resets_attempts_to_zero(self, graph_from_plan):
        node = graph_from_plan.get_node("1")
        node.alternative_descriptions = ["替代方案A"]
        node.attempts = 5
        graph_from_plan.try_alternative("1")
        assert graph_from_plan.get_node("1").attempts == 0

    def test_try_alternative_clears_feedback(self, graph_from_plan):
        node = graph_from_plan.get_node("1")
        node.alternative_descriptions = ["替代方案A"]
        node.feedback = "old feedback"
        graph_from_plan.try_alternative("1")
        assert graph_from_plan.get_node("1").feedback is None

    def test_try_alternative_consumes_first_alternative(self, graph_from_plan):
        node = graph_from_plan.get_node("1")
        node.alternative_descriptions = ["方案A", "方案B"]
        graph_from_plan.try_alternative("1")
        assert graph_from_plan.get_node("1").alternative_descriptions == ["方案B"]

    def test_has_alternatives_true_when_alternatives_exist(self, graph_from_plan):
        graph_from_plan.get_node("1").alternative_descriptions = ["alt"]
        assert graph_from_plan.has_alternatives("1") is True

    def test_has_alternatives_false_when_no_alternatives(self, graph_from_plan):
        assert graph_from_plan.has_alternatives("1") is False


# ════════════════════ reset_failed ════════════════════

class TestResetFailed:
    def test_reset_failed_changes_failed_to_pending(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "err")
        graph_from_plan.mark_failed("2", "err")
        graph_from_plan.reset_failed()
        assert graph_from_plan.get_node("1").status == "pending"
        assert graph_from_plan.get_node("2").status == "pending"

    def test_reset_failed_does_not_change_done_nodes(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_failed("2", "err")
        graph_from_plan.reset_failed()
        assert graph_from_plan.get_node("1").status == "done"

    def test_reset_failed_does_not_change_running_nodes(self, graph_from_plan):
        graph_from_plan.mark_running("1")
        graph_from_plan.mark_failed("2", "err")
        graph_from_plan.reset_failed()
        assert graph_from_plan.get_node("1").status == "running"


# ════════════════════ progress_summary ════════════════════

class TestProgressSummary:
    def test_progress_summary_contains_correct_counts(self, graph_from_plan):
        summary = graph_from_plan.progress_summary()
        assert "0/3" in summary
        assert "0 运行中" in summary
        assert "3 待处理" in summary

    def test_progress_summary_shows_node_details(self, graph_from_plan):
        summary = graph_from_plan.progress_summary()
        assert "1:" in summary
        assert "2:" in summary
        assert "3:" in summary

    def test_progress_summary_empty_graph(self, empty_graph):
        summary = empty_graph.progress_summary()
        assert "0/0" in summary

    def test_progress_summary_with_failed_nodes_shows_feedback(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "not good enough")
        summary = graph_from_plan.progress_summary()
        assert "not good enough" in summary

    def test_progress_summary_truncates_long_descriptions(self, graph_from_plan):
        graph_from_plan.nodes["1"].description = "x" * 100
        summary = graph_from_plan.progress_summary()
        assert len(graph_from_plan.nodes["1"].description) == 100
        assert ("x" * 50 + "x") not in summary

    def test_progress_summary_truncates_long_feedback(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "f" * 100)
        summary = graph_from_plan.progress_summary()
        assert ("f" * 41) not in summary


# ════════════════════ get_nodes_by_status ════════════════════

class TestGetNodesByStatus:
    def test_get_done_nodes_returns_only_done(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        graph_from_plan.mark_done("2", "r2")
        done = graph_from_plan.get_done_nodes()
        assert len(done) == 2
        assert all(n.status == "done" for n in done)

    def test_get_failed_nodes_returns_only_failed(self, graph_from_plan):
        graph_from_plan.mark_failed("1", "err")
        failed = graph_from_plan.get_failed_nodes()
        assert len(failed) == 1
        assert failed[0].id == "1"

    def test_get_pending_nodes_returns_only_pending(self, graph_from_plan):
        graph_from_plan.mark_done("1", "r1")
        pending = graph_from_plan.get_pending_nodes()
        assert len(pending) == 2
        assert all(n.status == "pending" for n in pending)

    def test_get_done_nodes_empty_when_none_done(self, graph_from_plan):
        assert graph_from_plan.get_done_nodes() == []
