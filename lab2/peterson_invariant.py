"""
实验二：Peterson 算法不变性检查示例

本模块演示如何使用不变性检查器验证 Peterson 互斥算法的性质：
1. 验证互斥性质：¬(crit0 ∧ crit1) - 两个进程不能同时在临界区
2. 人为引入错误，验证检查器能正确检测并生成反例

基于实验一的 Peterson 算法模型。
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from transition_system import TransitionSystem
from propositional_formula import parse_formula
from invariant_checker import InvariantChecker, InvariantCheckResult, check_invariant
from peterson_example import create_simplified_peterson, PetersonTS


def verify_mutual_exclusion(ts: TransitionSystem, verbose: bool = True) -> InvariantCheckResult:
    """
    验证 Peterson 算法的互斥性质
    
    性质：¬(crit0 ∧ crit1) - 两个进程不能同时在临界区
    
    Args:
        ts: Peterson 算法的 Transition System
        verbose: 是否打印详细信息
        
    Returns:
        InvariantCheckResult 对象
    """
    formula_str = "¬(crit0 ∧ crit1)"
    
    if verbose:
        print("\n" + "=" * 60)
        print("验证互斥性质")
        print("=" * 60)
        print(f"公式: {formula_str}")
        print("含义: 两个进程不能同时在临界区")
        print("-" * 60)
    
    result = check_invariant(ts, formula_str, method="bfs")
    
    if verbose:
        if result.holds:
            print(f"✓ 验证通过！")
            print(f"  检查了 {result.checked_states} 个可达状态")
            print(f"  没有发现违反互斥性质的状态")
        else:
            print(f"✗ 验证失败！")
            print(f"  发现违反状态: {result.violated_state}")
            print(f"  反例路径:")
            path_str = " -> ".join(s.name for s in result.counterexample)
            print(f"    {path_str}")
            print(f"\n  路径上的状态标签:")
            for i, state in enumerate(result.counterexample):
                labels = set(state.labels)
                label_str = ", ".join(sorted(labels)) if labels else "(无标签)"
                print(f"    {i}: {state.name} [{label_str}]")
    
    return result


def verify_single_process_in_critical(ts: TransitionSystem, verbose: bool = True) -> InvariantCheckResult:
    """
    验证：如果进程 0 在等待，那么进程 1 不能在临界区（或反之）
    
    这是一个更复杂的性质，用于演示公式嵌套。
    
    Args:
        ts: Peterson 算法的 Transition System
        verbose: 是否打印详细信息
        
    Returns:
        InvariantCheckResult 对象
    """
    # 性质：wait0 → ¬crit1 （如果进程0在等待，则进程1不在临界区）
    formula_str = "(¬wait0 ∨ ¬crit1)"  # 等价于 wait0 → ¬crit1
    
    if verbose:
        print("\n" + "=" * 60)
        print("验证：进程 0 等待时，进程 1 不在临界区")
        print("=" * 60)
        print(f"公式: {formula_str}")
        print("含义: wait0 → ¬crit1 (如果进程0在等待，则进程1不在临界区)")
        print("-" * 60)
    
    result = check_invariant(ts, formula_str, method="bfs")
    
    if verbose:
        if result.holds:
            print(f"✓ 验证通过！")
            print(f"  检查了 {result.checked_states} 个可达状态")
        else:
            print(f"✗ 验证失败！")
            print(f"  发现违反状态: {result.violated_state}")
            path_str = " -> ".join(s.name for s in result.counterexample)
            print(f"  反例路径: {path_str}")
    
    return result


def create_buggy_peterson() -> TransitionSystem:
    """
    创建一个有 bug 的 Peterson 算法模型
    
    通过修改迁移关系，使得两个进程可以同时进入临界区，
    用于测试不变性检查器能否正确检测违反。
    """
    ts = TransitionSystem()
    
    # 状态定义 (l0, l1, turn)
    states = [
        ("s0", "n,n,0", set()),           # 初始状态
        ("s1", "n,w,0", {"wait1"}),       # p1 请求
        ("s2", "w,n,1", {"wait0"}),       # p0 请求
        ("s3", "w,w,0", {"wait0", "wait1"}),  # 都请求，turn=0
        ("s4", "w,w,1", {"wait0", "wait1"}),  # 都请求，turn=1
        ("s5", "c,n,1", {"crit0"}),       # p0 进入临界区
        ("s6", "n,c,0", {"crit1"}),       # p1 进入临界区
        ("s7", "c,w,1", {"crit0", "wait1"}),  # p0 在临界区，p1 等待
        ("s8", "w,c,0", {"wait0", "crit1"}),  # p1 在临界区，p0 等待
        ("s9", "c,c,0", {"crit0", "crit1"}),  # BUG: 两个进程同时在临界区！
        ("s10", "c,c,1", {"crit0", "crit1"}), # BUG: 两个进程同时在临界区！
    ]
    
    for name, desc, labels in states:
        ts.add_state(name, labels)
    
    # 设置初始状态
    ts.add_initial_state("s0")
    
    # 添加正常迁移
    transitions = [
        ("s0", "s2", "p0_request"),
        ("s0", "s1", "p1_request"),
        ("s1", "s6", "p1_enter"),
        ("s1", "s4", "p0_request"),
        ("s2", "s5", "p0_enter"),
        ("s2", "s4", "p1_request"),
        ("s4", "s7", "p0_enter"),
        ("s5", "s0", "p0_exit"),
        ("s6", "s0", "p1_exit"),
        ("s7", "s1", "p0_exit"),
        ("s8", "s2", "p1_exit"),
        # BUG 迁移：允许在违反条件时进入临界区
        ("s7", "s9", "p1_enter_bug"),   # p0 在临界区时 p1 也进入
        ("s8", "s10", "p0_enter_bug"),  # p1 在临界区时 p0 也进入
    ]
    
    for src, dst, action in transitions:
        ts.add_transition(src, dst, action)
    
    return ts


def demonstrate_counterexample():
    """
    演示反例生成功能
    
    使用有 bug 的模型，展示不变性检查器如何检测违反并生成反例路径。
    """
    print("\n" + "=" * 60)
    print("演示：反例生成")
    print("=" * 60)
    print("使用一个有 bug 的 Peterson 模型")
    print("Bug：允许两个进程同时进入临界区")
    
    ts = create_buggy_peterson()
    
    # 打印可达状态图
    ts.print_reachable_graph()
    
    # 验证互斥性质
    result = verify_mutual_exclusion(ts, verbose=True)
    
    return result


def compare_bfs_dfs():
    """
    比较 BFS 和 DFS 两种遍历方法
    
    在有 bug 的模型上，展示两种方法都能找到违反，但反例路径可能不同。
    """
    print("\n" + "=" * 60)
    print("比较 BFS 和 DFS 遍历方法")
    print("=" * 60)
    
    ts = create_buggy_peterson()
    formula_str = "¬(crit0 ∧ crit1)"
    
    checker = InvariantChecker(ts)
    
    # BFS
    print("\n--- BFS 遍历 ---")
    result_bfs = checker.check_string(formula_str, method="bfs")
    print(f"检查状态数: {result_bfs.checked_states}")
    print(f"反例路径长度: {len(result_bfs.counterexample) if result_bfs.counterexample else 'N/A'}")
    if result_bfs.counterexample:
        path_str = " -> ".join(s.name for s in result_bfs.counterexample)
        print(f"反例路径: {path_str}")
    
    # DFS
    print("\n--- DFS 遍历 ---")
    result_dfs = checker.check_string(formula_str, method="dfs")
    print(f"检查状态数: {result_dfs.checked_states}")
    print(f"反例路径长度: {len(result_dfs.counterexample) if result_dfs.counterexample else 'N/A'}")
    if result_dfs.counterexample:
        path_str = " -> ".join(s.name for s in result_dfs.counterexample)
        print(f"反例路径: {path_str}")


def test_formula_parsing():
    """
    测试公式解析功能
    
    展示支持的公式语法。
    """
    print("\n" + "=" * 60)
    print("公式解析测试")
    print("=" * 60)
    
    test_formulas = [
        "crit0",
        "¬crit0",
        "crit0 ∧ crit1",
        "crit0 ∨ crit1",
        "¬(crit0 ∧ crit1)",
        "(¬crit0) ∨ (¬crit1)",
        "wait0 ∧ ¬crit1",
        "(wait0 ∨ wait1) ∧ ¬(crit0 ∧ crit1)",
    ]
    
    test_labels = [
        {"crit0"},
        {"crit1"},
        {"crit0", "crit1"},
        {"wait0"},
        {"wait0", "crit1"},
        set(),
    ]
    
    for formula_str in test_formulas:
        print(f"\n公式: {formula_str}")
        try:
            formula = parse_formula(formula_str)
            print(f"  解析结果: {formula}")
            print(f"  原子命题: {formula.get_atoms()}")
            print("  求值结果:")
            for labels in test_labels:
                result = formula.evaluate(labels)
                label_str = ", ".join(sorted(labels)) if labels else "∅"
                print(f"    {{{label_str}}} -> {result}")
        except Exception as e:
            print(f"  错误: {e}")


def run_all_demonstrations():
    """运行所有演示"""
    print("=" * 60)
    print("实验二：不变性检查演示")
    print("=" * 60)
    
    # 1. 测试公式解析
    test_formula_parsing()
    
    # 2. 验证简化版 Peterson 模型
    print("\n" + "=" * 60)
    print("简化版 Peterson 模型验证")
    print("=" * 60)
    ts_simplified = create_simplified_peterson()
    ts_simplified.print_reachable_graph()
    result1 = verify_mutual_exclusion(ts_simplified)
    assert result1.holds, "简化版模型应满足互斥性质"
    
    # 3. 验证完整版 Peterson 模型
    print("\n" + "=" * 60)
    print("完整版 Peterson 模型验证")
    print("=" * 60)
    peterson = PetersonTS()
    ts_full = peterson.get_ts()
    stats = ts_full.get_statistics()
    print(f"总状态数: {stats['total_states']}")
    print(f"可达状态数: {stats['reachable_states']}")
    print(f"可达迁移数: {stats['reachable_transitions']}")
    result2 = verify_mutual_exclusion(ts_full)
    assert result2.holds, "完整版模型应满足互斥性质"
    
    # 4. 验证其他性质
    verify_single_process_in_critical(ts_simplified)
    
    # 5. 演示反例生成
    result3 = demonstrate_counterexample()
    assert not result3.holds, "有 bug 的模型应违反互斥性质"
    assert result3.counterexample is not None, "应生成反例路径"
    
    # 6. 比较 BFS 和 DFS
    compare_bfs_dfs()
    
    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_demonstrations()
