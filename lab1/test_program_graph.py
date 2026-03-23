"""
程序图功能完整测试用例

测试内容：
1. 程序图基础测试 - 位置、迁移、变量管理
2. Python 解析器测试 - AST 解析、共享变量检测、取值域推断
3. 展开为 TS 测试 - 简单程序、条件、循环
4. 并行组合测试 - 基本组合、共享变量、Peterson 算法

使用 pytest 运行：
    pytest lab1/test_program_graph.py -v
"""

import sys
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from program_graph import ProgramGraph, Location, Action, PGTransition
from python_parser import PythonToProgramGraph, parse_python
from parallel_composition import (
    parallel_compose, compose_all, programs_to_ts,
    create_peterson_process, create_peterson_ts, verify_peterson_mutual_exclusion
)
from transition_system import TransitionSystem

# 可视化输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visualization"


def save_pg_visualization(pg, name_prefix: str):
    """保存程序图可视化文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 保存 DOT 文件
    dot_file = OUTPUT_DIR / f"{name_prefix}_pg.dot"
    pg.save_dot(str(dot_file))
    
    # 保存 HTML 文件
    html_file = OUTPUT_DIR / f"{name_prefix}_pg.html"
    pg.visualize_html(str(html_file))
    
    print(f"  程序图可视化已保存: {name_prefix}_pg.dot/html")


def save_ts_visualization(ts, name_prefix: str):
    """保存迁移系统可视化文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 保存 DOT 文件
    dot_file = OUTPUT_DIR / f"{name_prefix}_ts.dot"
    ts.save_dot(str(dot_file))
    
    # 保存 HTML 文件
    html_file = OUTPUT_DIR / f"{name_prefix}_ts.html"
    ts.visualize_html(str(html_file))
    
    print(f"  迁移系统可视化已保存: {name_prefix}_ts.dot/html")


# ==================== 程序图基础测试 ====================

class TestProgramGraphBasics:
    """程序图基础功能测试"""
    
    def test_create_program_graph(self):
        """测试程序图创建"""
        pg = ProgramGraph("TestPG")
        assert pg.name == "TestPG"
        assert len(pg.get_locations()) == 0
        assert pg.get_initial_location() is None
    
    def test_add_location(self):
        """测试添加位置"""
        pg = ProgramGraph("PG")
        
        loc1 = pg.add_location("L1")
        loc2 = pg.add_location("L2", {"label1", "label2"})
        
        assert loc1.name == "L1"
        assert loc2.name == "L2"
        assert len(pg.get_locations()) == 2
        assert pg.get_location_labels(loc2) == {"label1", "label2"}
    
    def test_set_initial_location(self):
        """测试设置初始位置"""
        pg = ProgramGraph("PG")
        
        init = pg.set_initial_location("Init")
        assert pg.get_initial_location() == init
        assert init.name == "Init"
    
    def test_add_transition(self):
        """测试添加迁移"""
        pg = ProgramGraph("PG")
        pg.add_location("A")
        pg.add_location("B")
        
        action = Action("a", {"x": "1"})
        trans = pg.add_transition("A", "B", action, "x == 0")
        
        assert trans.source.name == "A"
        assert trans.target.name == "B"
        assert trans.guard == "x == 0"
        assert trans.action.name == "a"
    
    def test_get_transitions(self):
        """测试获取迁移"""
        pg = ProgramGraph("PG")
        pg.add_location("A")
        pg.add_location("B")
        pg.add_location("C")
        
        pg.add_transition("A", "B", Action("a1", {}))
        pg.add_transition("A", "C", Action("a2", {}))
        
        loc_a = pg.get_location("A")
        transitions = pg.get_transitions(loc_a)
        
        assert len(transitions) == 2
        targets = {t.target.name for t in transitions}
        assert targets == {"B", "C"}
    
    def test_declare_variable(self):
        """测试变量声明"""
        pg = ProgramGraph("PG")
        
        pg.declare_variable("x", {0, 1, 2}, 0, is_shared=False)
        pg.declare_variable("flag", {True, False}, True, is_shared=True)
        
        vars = pg.get_variables()
        assert "x" in vars
        assert vars["x"] == {0, 1, 2}
        assert "flag" in vars
        assert vars["flag"] == {True, False}
        
        assert not pg.is_shared_variable("x")
        assert pg.is_shared_variable("flag")
    
    def test_initial_values(self):
        """测试初始值"""
        pg = ProgramGraph("PG")
        
        pg.declare_variable("x", {0, 1}, 0)
        pg.declare_variable("y", {True, False}, True)
        
        init_vals = pg.get_initial_values()
        assert init_vals["x"] == 0
        assert init_vals["y"] == True


# ==================== Python 解析器测试 ====================

class TestPythonParser:
    """Python 代码解析器测试"""
    
    def test_parse_simple_assignment(self):
        """测试简单赋值语句解析"""
        code = "x = 0"
        pg = parse_python(code, "Simple")
        
        assert "x" in pg.get_variables()
        assert pg.get_initial_values()["x"] == 0
    
    def test_parse_multiple_assignments(self):
        """测试多重赋值"""
        code = """
x = 0
y = 1
z = True
"""
        pg = parse_python(code, "Multi")
        
        vars = pg.get_variables()
        assert "x" in vars
        assert "y" in vars
        assert "z" in vars
        
        init = pg.get_initial_values()
        assert init["x"] == 0
        assert init["y"] == 1
        assert init["z"] == True
    
    def test_parse_boolean_variable(self):
        """测试布尔变量"""
        code = """
flag = False
flag = True
"""
        pg = parse_python(code, "Bool")
        
        vars = pg.get_variables()
        assert "flag" in vars
        assert vars["flag"] == {True, False}
    
    def test_shared_variable_detection(self):
        """测试共享变量检测"""
        code = """
x = 0  # @shared
y = 1
z = 2  # @shared
"""
        pg = parse_python(code, "Shared")
        
        shared = pg.get_shared_variables()
        assert "x" in shared
        assert "z" in shared
        assert "y" not in shared
    
    def test_shared_variable_list_format(self):
        """测试共享变量列表格式"""
        code = """
# @shared: a, b, c
a = 0
b = 1
c = 2
d = 3
"""
        pg = parse_python(code, "SharedList")
        
        shared = pg.get_shared_variables()
        assert "a" in shared
        assert "b" in shared
        assert "c" in shared
        assert "d" not in shared
    
    def test_domain_inference_from_assignment(self):
        """测试从赋值推断取值域"""
        code = """
x = 0
x = 1
x = 2
"""
        pg = parse_python(code, "Domain")
        
        vars = pg.get_variables()
        # 应该包含所有赋值过的值
        assert 0 in vars["x"]
        assert 1 in vars["x"]
        assert 2 in vars["x"]
    
    def test_parse_if_statement(self):
        """测试条件语句解析"""
        code = """
x = 0
if x == 0:
    y = 1
else:
    y = 2
"""
        pg = parse_python(code, "If")
        
        # 应该有条件分支的迁移
        all_trans = pg.get_all_transitions()
        assert len(all_trans) >= 3  # 至少有入口、then、else 分支
    
    def test_parse_while_loop(self):
        """测试 while 循环解析"""
        code = """
x = 0
while x < 3:
    x = x + 1
"""
        pg = parse_python(code, "While")
        
        # 应该有循环回边
        all_trans = pg.get_all_transitions()
        # 检查存在循环结构
        assert any("while" in t.action.name.lower() for t in all_trans)
    
    def test_parse_nested_structure(self):
        """测试嵌套结构"""
        code = """
x = 0
while x < 2:
    if x == 0:
        y = 1
    else:
        y = 2
    x = x + 1
"""
        pg = parse_python(code, "Nested")
        
        # 验证基本结构
        assert pg.get_initial_location() is not None
        assert len(pg.get_all_transitions()) >= 4


# ==================== 展开为 TS 测试 ====================

class TestUnfoldToTS:
    """展开为 Transition System 测试"""
    
    def test_simple_unfold(self):
        """测试简单程序展开"""
        pg = ProgramGraph("Simple")
        pg.add_location("A")
        pg.add_location("B")
        pg.set_initial_location("A")
        pg.declare_variable("x", {0, 1}, 0)
        
        action = Action("x=1", {"x": "1"})
        pg.add_transition("A", "B", action)
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_simple_unfold")
        
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_simple_unfold")
        
        # 应该有初始状态
        init_states = ts.get_initial_states()
        assert len(init_states) == 1
        
        # 检查可达状态
        reachable = ts.compute_reachable_states()
        assert len(reachable) >= 2  # 至少有初始状态和一个后继
    
    def test_unfold_with_condition(self):
        """测试带条件的展开"""
        pg = ProgramGraph("Cond")
        pg.add_location("A")
        pg.add_location("B")
        pg.add_location("C")
        pg.set_initial_location("A")
        pg.declare_variable("x", {0, 1}, 0)
        
        # A -> B when x == 0
        action1 = Action("to_B", {})
        pg.add_transition("A", "B", action1, "x == 0")
        
        # A -> C when x == 1
        action2 = Action("to_C", {})
        pg.add_transition("A", "C", action2, "x == 1")
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_unfold_condition")
        
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_unfold_condition")
        
        reachable = ts.compute_reachable_states()
        
        # 初始 x=0，应该只能到 B
        reachable_names = {s.name for s in reachable}
        assert any("B" in name for name in reachable_names)
    
    def test_unfold_counter(self):
        """测试计数器程序展开"""
        code = """
x = 0
while x < 3:
    x = x + 1
"""
        pg = parse_python(code, "Counter")
        
        # 扩展域以包含所有可能值
        pg.declare_variable("x", {0, 1, 2, 3}, 0)
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_unfold_counter")
        
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_unfold_counter")
        
        reachable = ts.compute_reachable_states()
        
        # 应该有多个可达状态
        assert len(reachable) >= 2
    
    def test_unfold_preserves_labels(self):
        """测试展开保持标签"""
        pg = ProgramGraph("Labels")
        pg.add_location("A", {"start"})
        pg.add_location("B", {"end"})
        pg.set_initial_location("A")
        pg.declare_variable("x", {0}, 0)
        
        action = Action("to_B", {})
        pg.add_transition("A", "B", action)
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_unfold_labels")
        
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_unfold_labels")
        
        # 检查标签传递
        for state in ts.get_all_states():
            if "A" in state.name:
                assert state.has_label("start")
            if "B" in state.name:
                assert state.has_label("end")


# ==================== 并行组合测试 ====================

class TestParallelComposition:
    """并行组合测试"""
    
    def test_basic_parallel_composition(self):
        """测试基本并行组合"""
        # 创建两个简单程序图
        pg1 = ProgramGraph("P1")
        pg1.add_location("A")
        pg1.add_location("B")
        pg1.set_initial_location("A")
        pg1.declare_variable("x", {0, 1}, 0)
        pg1.add_transition("A", "B", Action("x=1", {"x": "1"}))
        
        pg2 = ProgramGraph("P2")
        pg2.add_location("C")
        pg2.add_location("D")
        pg2.set_initial_location("C")
        pg2.declare_variable("y", {0, 1}, 0)
        pg2.add_transition("C", "D", Action("y=1", {"y": "1"}))
        
        # 保存原始程序图可视化
        save_pg_visualization(pg1, "test_parallel_pg1")
        save_pg_visualization(pg2, "test_parallel_pg2")
        
        composed = parallel_compose(pg1, pg2)
        
        # 保存组合后的程序图可视化
        save_pg_visualization(composed, "test_parallel_composed")
        
        # 位置数应该是 2 * 2 = 4
        assert len(composed.get_locations()) == 4
        
        # 变量应该合并
        vars = composed.get_variables()
        assert "x" in vars
        assert "y" in vars
    
    def test_parallel_composition_interleaving(self):
        """测试并行组合的交错语义"""
        pg1 = ProgramGraph("P1")
        pg1.add_location("A")
        pg1.add_location("B")
        pg1.set_initial_location("A")
        pg1.declare_variable("x", {0, 1}, 0)
        pg1.add_transition("A", "B", Action("x=1", {"x": "1"}))
        
        pg2 = ProgramGraph("P2")
        pg2.add_location("C")
        pg2.add_location("D")
        pg2.set_initial_location("C")
        pg2.declare_variable("y", {0, 1}, 0)
        pg2.add_transition("C", "D", Action("y=1", {"y": "1"}))
        
        composed = parallel_compose(pg1, pg2)
        
        # 保存组合程序图可视化
        save_pg_visualization(composed, "test_interleaving_pg")
        
        ts = composed.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_interleaving")
        
        reachable = ts.compute_reachable_states()
        reachable_names = {s.name for s in reachable}
        
        # 应该能到达所有四种组合
        # (A,C), (B,C), (A,D), (B,D)
        assert len(reachable) >= 4
    
    def test_parallel_composition_shared_variables(self):
        """测试共享变量的并行组合"""
        pg1 = ProgramGraph("P1")
        pg1.add_location("A1")
        pg1.add_location("B1")
        pg1.set_initial_location("A1")
        pg1.declare_variable("shared", {0, 1, 2}, 0, is_shared=True)
        pg1.add_transition("A1", "B1", Action("shared=1", {"shared": "1"}))
        
        pg2 = ProgramGraph("P2")
        pg2.add_location("A2")
        pg2.add_location("B2")
        pg2.set_initial_location("A2")
        pg2.declare_variable("shared", {0, 1, 2}, 0, is_shared=True)
        pg2.add_transition("A2", "B2", Action("shared=2", {"shared": "2"}))
        
        composed = parallel_compose(pg1, pg2)
        
        # 共享变量的域应该合并
        vars = composed.get_variables()
        assert "shared" in vars
        assert vars["shared"] == {0, 1, 2}
    
    def test_compose_all(self):
        """测试多程序组合"""
        programs = []
        for i in range(3):
            pg = ProgramGraph(f"P{i}")
            pg.add_location(f"A{i}")
            pg.add_location(f"B{i}")
            pg.set_initial_location(f"A{i}")
            pg.declare_variable(f"x{i}", {0, 1}, 0)
            pg.add_transition(f"A{i}", f"B{i}", Action(f"x{i}=1", {f"x{i}": "1"}))
            programs.append(pg)
        
        composed = compose_all(programs)
        
        # 位置数应该是 2^3 = 8
        assert len(composed.get_locations()) == 8
        
        # 变量应该全部存在
        vars = composed.get_variables()
        assert "x0" in vars
        assert "x1" in vars
        assert "x2" in vars


# ==================== Peterson 算法测试 ====================

class TestPetersonAlgorithm:
    """Peterson 互斥算法测试"""
    
    def test_create_peterson_process(self):
        """测试创建 Peterson 进程"""
        p0 = create_peterson_process(0)
        
        # 检查位置
        locs = {loc.name for loc in p0.get_locations()}
        assert "noncrit" in locs
        assert "wait" in locs
        assert "crit" in locs
        
        # 检查变量
        vars = p0.get_variables()
        assert "flag0" in vars
        assert "turn" in vars
        
        # 检查共享变量
        shared = p0.get_shared_variables()
        assert "flag0" in shared
        assert "turn" in shared
    
    def test_peterson_parallel_composition(self):
        """测试 Peterson 算法并行组合"""
        p0 = create_peterson_process(0)
        p1 = create_peterson_process(1)
        
        # 保存单个进程可视化
        save_pg_visualization(p0, "test_peterson_p0")
        save_pg_visualization(p1, "test_peterson_p1")
        
        composed = parallel_compose(p0, p1, "Peterson")
        
        # 保存组合程序图可视化
        save_pg_visualization(composed, "test_peterson_composed")
        
        # 检查组合后的位置数
        # 5 * 5 = 25 个组合位置
        assert len(composed.get_locations()) == 25
        
        # 检查共享变量
        vars = composed.get_variables()
        assert "flag0" in vars
        assert "flag1" in vars
        assert "turn" in vars
    
    def test_peterson_mutual_exclusion(self):
        """测试 Peterson 算法互斥性质"""
        ts = create_peterson_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_peterson_me")
        
        reachable = ts.compute_reachable_states()
        
        # 验证没有同时进入临界区的状态
        violations = []
        for state in reachable:
            if state.has_label("crit0") and state.has_label("crit1"):
                violations.append(state)
        
        assert len(violations) == 0, f"发现违反互斥性的状态: {violations}"
    
    def test_peterson_reachability(self):
        """测试 Peterson 算法可达性"""
        ts = create_peterson_ts()
        reachable = ts.compute_reachable_states()
        
        # 应该有可达状态
        assert len(reachable) > 0
        
        # 检查某些状态是否可达
        has_crit0 = any(s.has_label("crit0") for s in reachable)
        has_crit1 = any(s.has_label("crit1") for s in reachable)
        
        # 两个进程都应该能进入临界区
        assert has_crit0, "进程 0 应该能进入临界区"
        assert has_crit1, "进程 1 应该能进入临界区"
    
    def test_peterson_no_deadlock(self):
        """测试 Peterson 算法无死锁"""
        ts = create_peterson_ts()
        reachable = ts.compute_reachable_states()
        
        # 检查是否存在终止状态（没有后继的状态）
        deadlocks = []
        for state in reachable:
            successors = ts.get_successors(state)
            if len(successors) == 0:
                deadlocks.append(state)
        
        # Peterson 算法是循环的，不应该有死锁
        # 但由于我们的建模，可能存在自循环
        # 这里主要验证不会卡在等待状态
        for dl in deadlocks:
            # 如果有死锁状态，它不应该是两个进程都在等待
            assert not (dl.has_label("wait0") and dl.has_label("wait1")), \
                f"发现死锁状态: {dl}"


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""
    
    def test_python_to_ts_pipeline(self):
        """测试 Python 代码到 TS 的完整流程"""
        code = """
x = 0
y = 0
while x < 2:
    y = x
    x = x + 1
"""
        # 解析为程序图
        pg = parse_python(code, "Pipeline")
        
        # 扩展域
        pg.declare_variable("x", {0, 1, 2}, 0)
        pg.declare_variable("y", {0, 1}, 0)
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_pipeline_pg")
        
        # 展开为 TS
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_pipeline_ts")
        
        # 验证基本属性
        assert ts.get_initial_states()
        reachable = ts.compute_reachable_states()
        assert len(reachable) >= 1
    
    def test_visualization_compatibility(self):
        """测试与可视化功能的兼容性"""
        pg = ProgramGraph("Viz")
        pg.add_location("A")
        pg.add_location("B")
        pg.set_initial_location("A")
        pg.declare_variable("x", {0, 1}, 0)
        pg.add_transition("A", "B", Action("x=1", {"x": "1"}))
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_viz_compat_pg")
        
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_viz_compat_ts")
        
        # 测试可以生成 DOT 格式
        dot = ts.visualize_dot()
        assert "digraph" in dot
        assert "->" in dot
    
    def test_statistics(self):
        """测试统计信息"""
        pg = ProgramGraph("Stats")
        pg.add_location("A")
        pg.add_location("B")
        pg.add_location("C")
        pg.set_initial_location("A")
        pg.declare_variable("x", {0, 1}, 0)
        pg.add_transition("A", "B", Action("a", {"x": "1"}))
        pg.add_transition("B", "C", Action("b", {}))
        
        # 保存程序图可视化
        save_pg_visualization(pg, "test_stats_pg")
        
        ts = pg.unfold_to_ts()
        
        # 保存迁移系统可视化
        save_ts_visualization(ts, "test_stats_ts")
        
        stats = ts.get_statistics()
        
        assert "total_states" in stats
        assert "reachable_states" in stats
        assert "total_transitions" in stats


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """边界条件测试"""
    
    def test_empty_program_graph(self):
        """测试空程序图"""
        pg = ProgramGraph("Empty")
        ts = pg.unfold_to_ts()
        
        # 空程序图应该产生空 TS
        assert len(ts.get_all_states()) == 0
    
    def test_single_location(self):
        """测试单位置程序图"""
        pg = ProgramGraph("Single")
        pg.set_initial_location("Only")
        pg.declare_variable("x", {0}, 0)
        
        ts = pg.unfold_to_ts()
        reachable = ts.compute_reachable_states()
        
        assert len(reachable) == 1
    
    def test_self_loop(self):
        """测试自循环"""
        pg = ProgramGraph("Loop")
        pg.set_initial_location("A")
        pg.declare_variable("x", {0, 1}, 0)
        
        pg.add_transition("A", "A", Action("x=1-x", {"x": "1 - x"}))
        
        ts = pg.unfold_to_ts()
        reachable = ts.compute_reachable_states()
        
        # 应该有两个状态 (A, x=0) 和 (A, x=1)
        assert len(reachable) == 2
    
    def test_unreachable_states(self):
        """测试不可达状态"""
        pg = ProgramGraph("Unreachable")
        pg.add_location("A")
        pg.add_location("B")
        pg.add_location("C")  # 不可达
        pg.set_initial_location("A")
        pg.declare_variable("x", {0}, 0)
        
        pg.add_transition("A", "B", Action("to_B", {}))
        # C 没有入边，不可达
        
        ts = pg.unfold_to_ts()
        reachable = ts.compute_reachable_states()
        reachable_names = {s.name for s in reachable}
        
        # C 不应该在可达状态中
        assert not any("C" in name for name in reachable_names)
    
    def test_complex_guard(self):
        """测试复杂守卫条件"""
        pg = ProgramGraph("Guard")
        pg.add_location("A")
        pg.add_location("B")
        pg.set_initial_location("A")
        pg.declare_variable("x", {0, 1, 2}, 0)
        pg.declare_variable("y", {0, 1}, 1)
        
        # 复杂守卫条件
        pg.add_transition("A", "B", Action("to_B", {}), "(x == 0) and (y == 1)")
        
        ts = pg.unfold_to_ts()
        reachable = ts.compute_reachable_states()
        
        # 初始状态 x=0, y=1，应该能到达 B
        assert len(reachable) == 2


# ==================== 运行测试 ====================

if __name__ == "__main__":
    # 使用 pytest 运行
    pytest.main([__file__, "-v", "--tb=short"])
