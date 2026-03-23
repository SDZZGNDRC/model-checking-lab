"""
程序图并行组合 (Parallel Composition)

实现多个程序图的并行组合，使用交错语义 (Interleaving Semantics)。

并行组合规则 PG1 ||| PG2:
- 位置空间: Loc = Loc1 × Loc2
- 变量空间: Var = Var1 ∪ Var2
- 迁移规则 (交错语义):
  - PG1 独立迁移: (l1, l2) --a1--> (l1', l2) 
  - PG2 独立迁移: (l1, l2) --a2--> (l1, l2')
- 共享变量假设为原子访问
"""

from typing import Set, Dict, List, Tuple, Optional, Any
from itertools import product

from program_graph import ProgramGraph, Location, Action, PGTransition
from transition_system import TransitionSystem


def parallel_compose(pg1: ProgramGraph, pg2: ProgramGraph, 
                     name: str = "PG1||PG2") -> ProgramGraph:
    """
    并行组合两个程序图 (交错语义)
    
    Args:
        pg1: 第一个程序图
        pg2: 第二个程序图
        name: 组合后程序图的名称
        
    Returns:
        组合后的 ProgramGraph
    """
    composed = ProgramGraph(name)
    
    # 合并变量
    _merge_variables(composed, pg1, pg2)
    
    # 创建组合位置 (Loc1 × Loc2)
    _create_composed_locations(composed, pg1, pg2)
    
    # 添加交错迁移
    _add_interleaved_transitions(composed, pg1, pg2)
    
    return composed


def _merge_variables(composed: ProgramGraph, pg1: ProgramGraph, pg2: ProgramGraph):
    """合并两个程序图的变量"""
    
    # 获取所有变量
    vars1 = pg1.get_variables()
    vars2 = pg2.get_variables()
    init1 = pg1.get_initial_values()
    init2 = pg2.get_initial_values()
    shared1 = pg1.get_shared_variables()
    shared2 = pg2.get_shared_variables()
    
    # 合并共享变量（取并集作为共享）
    all_shared = shared1 | shared2
    
    # 处理 pg1 的变量
    for var, domain in vars1.items():
        is_shared = var in all_shared
        initial = init1.get(var)
        
        # 如果变量也在 pg2 中，合并域
        if var in vars2:
            domain = domain | vars2[var]
            # 对于共享变量，初始值应该一致，使用 pg1 的
        
        composed.declare_variable(var, domain, initial, is_shared)
    
    # 处理只在 pg2 中的变量
    for var, domain in vars2.items():
        if var not in vars1:
            is_shared = var in all_shared
            initial = init2.get(var)
            composed.declare_variable(var, domain, initial, is_shared)


def _create_composed_locations(composed: ProgramGraph, 
                               pg1: ProgramGraph, pg2: ProgramGraph):
    """创建组合位置空间"""
    
    locs1 = pg1.get_locations()
    locs2 = pg2.get_locations()
    
    init1 = pg1.get_initial_location()
    init2 = pg2.get_initial_location()
    
    # 创建所有组合位置
    for loc1 in locs1:
        for loc2 in locs2:
            composed_name = _make_composed_loc_name(loc1, loc2)
            
            # 合并标签
            labels1 = pg1.get_location_labels(loc1)
            labels2 = pg2.get_location_labels(loc2)
            combined_labels = labels1 | labels2
            
            composed.add_location(composed_name, combined_labels if combined_labels else None)
    
    # 设置初始位置
    if init1 and init2:
        init_composed = _make_composed_loc_name(init1, init2)
        composed.set_initial_location(init_composed)


def _make_composed_loc_name(loc1: Location, loc2: Location) -> str:
    """生成组合位置名称"""
    return f"({loc1.name},{loc2.name})"


def _parse_composed_loc_name(name: str) -> Tuple[str, str]:
    """解析组合位置名称"""
    # 移除括号
    content = name[1:-1]
    # 找到分隔符（第一个逗号）
    parts = content.split(",", 1)
    return parts[0], parts[1]


def _add_interleaved_transitions(composed: ProgramGraph, 
                                  pg1: ProgramGraph, pg2: ProgramGraph):
    """添加交错迁移"""
    
    locs1 = pg1.get_locations()
    locs2 = pg2.get_locations()
    
    # 对每个组合位置
    for loc1 in locs1:
        for loc2 in locs2:
            source_name = _make_composed_loc_name(loc1, loc2)
            
            # PG1 的迁移 (保持 loc2 不变)
            for trans in pg1.get_transitions(loc1):
                target_name = _make_composed_loc_name(trans.target, loc2)
                
                # 创建带前缀的动作名
                action = Action(
                    name=f"P1:{trans.action.name}",
                    effect=trans.action.effect.copy(),
                    guard=trans.action.guard
                )
                
                composed.add_transition(source_name, target_name, action, trans.guard)
            
            # PG2 的迁移 (保持 loc1 不变)
            for trans in pg2.get_transitions(loc2):
                target_name = _make_composed_loc_name(loc1, trans.target)
                
                # 创建带前缀的动作名
                action = Action(
                    name=f"P2:{trans.action.name}",
                    effect=trans.action.effect.copy(),
                    guard=trans.action.guard
                )
                
                composed.add_transition(source_name, target_name, action, trans.guard)


def compose_all(programs: List[ProgramGraph], name: str = "Combined") -> ProgramGraph:
    """
    组合多个程序图
    
    Args:
        programs: 程序图列表
        name: 组合后的名称
        
    Returns:
        组合后的 ProgramGraph
    """
    if not programs:
        return ProgramGraph(name)
    
    if len(programs) == 1:
        return programs[0]
    
    result = programs[0]
    for i, pg in enumerate(programs[1:], 2):
        result = parallel_compose(result, pg, f"{name}_{i}")
    
    return result


def programs_to_ts(programs: List[ProgramGraph]) -> TransitionSystem:
    """
    将多个程序图并行组合后展开为迁移系统
    
    这是一个便捷函数，组合了并行组合和展开操作。
    
    Args:
        programs: 程序图列表
        
    Returns:
        展开后的 TransitionSystem
    """
    if not programs:
        return TransitionSystem()
    
    combined = compose_all(programs)
    return combined.unfold_to_ts()


# ==================== Peterson 算法示例 ====================

def create_peterson_process(process_id: int) -> ProgramGraph:
    """
    创建 Peterson 算法的单个进程程序图
    
    Peterson 算法伪代码 (进程 i):
    ```
    # noncrit: 非临界区
    flag[i] = True
    turn = 1 - i
    # wait: 等待
    while flag[1-i] and turn == 1-i:
        pass
    # crit: 临界区
    flag[i] = False
    # 回到 noncrit
    ```
    
    Args:
        process_id: 进程 ID (0 或 1)
        
    Returns:
        该进程的 ProgramGraph
    """
    pg = ProgramGraph(f"P{process_id}")
    
    # 定义位置
    pg.add_location("noncrit", {f"noncrit{process_id}"})
    pg.add_location("set_flag")
    pg.add_location("set_turn")
    pg.add_location("wait", {f"wait{process_id}"})
    pg.add_location("crit", {f"crit{process_id}"})
    pg.set_initial_location("noncrit")
    
    # 变量定义
    my_flag = f"flag{process_id}"
    other_flag = f"flag{1-process_id}"
    my_turn = 1 - process_id  # 设置 turn 为对方的 ID
    
    # 声明变量 - 两个进程都需要知道所有共享变量
    pg.declare_variable("flag0", {True, False}, False, is_shared=True)
    pg.declare_variable("flag1", {True, False}, False, is_shared=True)
    pg.declare_variable("turn", {0, 1}, 0, is_shared=True)
    
    # 迁移定义
    
    # noncrit -> set_flag: flag[i] = True
    action1 = Action(f"{my_flag}=True", {my_flag: "True"})
    pg.add_transition("noncrit", "set_flag", action1)
    
    # set_flag -> set_turn: turn = 1-i
    action2 = Action(f"turn={my_turn}", {"turn": str(my_turn)})
    pg.add_transition("set_flag", "set_turn", action2)
    
    # set_turn -> wait
    action3 = Action("to_wait", {})
    pg.add_transition("set_turn", "wait", action3)
    
    # wait -> crit: 当 not(flag[1-i] and turn == 1-i)
    # 即 flag[1-i] == False or turn != 1-i
    guard_enter = f"(not {other_flag}) or (turn != {my_turn})"
    action4 = Action("enter_crit", {})
    pg.add_transition("wait", "crit", action4, guard_enter)
    
    # wait -> wait: 自旋等待（用于建模忙等待）
    guard_spin = f"{other_flag} and (turn == {my_turn})"
    action_spin = Action("spin", {})
    pg.add_transition("wait", "wait", action_spin, guard_spin)
    
    # crit -> noncrit: flag[i] = False
    action5 = Action(f"{my_flag}=False", {my_flag: "False"})
    pg.add_transition("crit", "noncrit", action5)
    
    return pg


def create_peterson_ts() -> TransitionSystem:
    """
    创建 Peterson 互斥算法的完整迁移系统
    
    Returns:
        Peterson 算法的 TransitionSystem
    """
    # 创建两个进程的程序图
    p0 = create_peterson_process(0)
    p1 = create_peterson_process(1)
    
    # 并行组合
    combined = parallel_compose(p0, p1, "Peterson")
    
    # 展开为迁移系统
    return combined.unfold_to_ts()


def verify_peterson_mutual_exclusion() -> bool:
    """
    验证 Peterson 算法的互斥性质
    
    性质：不存在两个进程同时在临界区的状态
    ¬(crit0 ∧ crit1)
    
    Returns:
        True 如果满足互斥性质，False 否则
    """
    ts = create_peterson_ts()
    reachable = ts.compute_reachable_states()
    
    violations = []
    for state in reachable:
        if state.has_label("crit0") and state.has_label("crit1"):
            violations.append(state)
    
    if violations:
        print(f"发现 {len(violations)} 个违反互斥性质的状态:")
        for v in violations:
            print(f"  {v}")
        return False
    
    print("互斥性质验证通过！")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("并行组合测试")
    print("=" * 60)
    
    # 测试简单并行组合
    print("\n【简单并行组合测试】")
    
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
    
    composed = parallel_compose(pg1, pg2)
    composed.print_info()
    
    print("\n展开为 TS:")
    ts = composed.unfold_to_ts()
    ts.print_reachable_graph()
    
    # 测试 Peterson 算法
    print("\n" + "=" * 60)
    print("【Peterson 互斥算法测试】")
    print("=" * 60)
    
    p0 = create_peterson_process(0)
    print("\n进程 P0:")
    p0.print_info()
    
    p1 = create_peterson_process(1)
    print("\n进程 P1:")
    p1.print_info()
    
    print("\n并行组合后:")
    peterson = parallel_compose(p0, p1, "Peterson")
    peterson.print_info()
    
    print("\n验证互斥性质:")
    verify_peterson_mutual_exclusion()
