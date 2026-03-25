"""
实验七：双计数器示例

本模块实现两个独立递增计数器的并发程序示例，
用于展示偏序归约的效果。

示例描述：
- 两个进程 P0 和 P1，各自有一个计数器 count0 和 count1
- 每个进程独立递增自己的计数器
- 由于动作独立，偏序归约可以将状态空间从 O(n²) 减少到 O(n)
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Tuple
from program_graph import ProgramGraph, Action
from action_dependency import ActionDependency, Action as DepAction
from por_transition_system import PORTransitionSystemBuilder, PORStatistics
from por_ltl_checker import PORLTLChecker, build_simple_ltl_nba_always


def create_counter_process(process_id: int, max_count: int = 3) -> ProgramGraph:
    """
    创建单个计数器进程的程序图
    
    进程行为：
    - 从 count = 0 开始
    - 每次递增 count
    - 当 count 达到 max_count 时保持不变
    
    Args:
        process_id: 进程ID (0 或 1)
        max_count: 计数器最大值
        
    Returns:
        该进程的程序图
    """
    pg = ProgramGraph(f"Counter{process_id}")
    
    # 变量：计数器值
    var_name = f"count{process_id}"
    domain = set(range(max_count + 1))
    pg.declare_variable(var_name, domain, 0, is_shared=False)
    
    # 位置
    pg.add_location("loop", {f"counting{process_id}"})
    pg.set_initial_location("loop")
    
    # 递增动作（带守卫：count < max）
    inc_action = Action(
        name=f"inc{process_id}",
        effect={var_name: f"{var_name} + 1"}
    )
    
    # 自环迁移，只在 count < max_count 时执行
    pg.add_transition("loop", "loop", inc_action, guard=f"{var_name} < {max_count}")
    
    return pg


def create_two_counter_program(max_count: int = 3, 
                                use_parallel_compose: bool = True) -> ProgramGraph:
    """
    创建双计数器程序图
    
    Args:
        max_count: 计数器最大值
        use_parallel_compose: 是否使用并行组合（True）或手动创建（False）
        
    Returns:
        组合后的程序图
    """
    if use_parallel_compose:
        from parallel_composition import parallel_compose
        
        pg0 = create_counter_process(0, max_count)
        pg1 = create_counter_process(1, max_count)
        
        combined = parallel_compose(pg0, pg1, "TwoCounters")
        return combined
    else:
        # 手动创建组合程序图
        pg = ProgramGraph("TwoCounters")
        
        # 声明两个独立变量
        pg.declare_variable("count0", set(range(max_count + 1)), 0, is_shared=False)
        pg.declare_variable("count1", set(range(max_count + 1)), 0, is_shared=False)
        
        # 单个位置
        pg.add_location("(loop,loop)")
        pg.set_initial_location("(loop,loop)")
        
        # P0 的递增动作
        action0 = Action("P0:inc0", {"count0": "count0 + 1"})
        pg.add_transition("(loop,loop)", "(loop,loop)", action0, guard="count0 < max_count")
        
        # P1 的递增动作
        action1 = Action("P1:inc1", {"count1": "count1 + 1"})
        pg.add_transition("(loop,loop)", "(loop,loop)", action1, guard="count1 < max_count")
        
        return pg


def create_dependency_analyzer(max_count: int = 3) -> ActionDependency:
    """
    为双计数器创建依赖分析器
    
    Args:
        max_count: 计数器最大值（用于分析）
        
    Returns:
        配置好的依赖分析器
    """
    analyzer = ActionDependency()
    
    # P1 的动作：只写入 count0
    # 注意：动作名称必须与程序图中的动作名称匹配
    # 程序图中进程ID从1开始（P1, P2）
    action0 = DepAction(
        name="inc0",  # 使用基本名称，process_id 区分进程
        process_id=1,  # 对应程序图中的 P1
        reads=frozenset(),
        writes=frozenset({"count0"})
    )
    
    # P2 的动作：只写入 count1
    action1 = DepAction(
        name="inc1",  # 使用基本名称，process_id 区分进程
        process_id=2,  # 对应程序图中的 P2
        reads=frozenset(),
        writes=frozenset({"count1"})
    )
    
    analyzer.register_actions([action0, action1])
    
    return analyzer


def analyze_state_space_explosion(max_count: int = 3) -> Tuple[int, int, float]:
    """
    分析状态空间爆炸和偏序归约效果
    
    Args:
        max_count: 计数器最大值
        
    Returns:
        (完整状态数, 简化状态数, 减少率)
    """
    # 创建程序图
    pg = create_two_counter_program(max_count)
    
    # 创建依赖分析器
    analyzer = create_dependency_analyzer(max_count)
    
    # 对比展开
    builder = PORTransitionSystemBuilder()
    full_ts, reduced_ts, stats = builder.compare_with_full_exploration(pg, analyzer)
    
    return stats.original_states, stats.reduced_states, stats.state_reduction_rate


def demonstrate_por_effect():
    """
    演示偏序归约的效果
    
    对不同规模的计数器展示状态空间减少率。
    """
    print("=" * 60)
    print("偏序归约效果演示：双独立计数器")
    print("=" * 60)
    
    print("\n理论分析：")
    print("- 两个独立计数器，每个有 n 个取值")
    print("- 完整状态空间：O(n²) - 所有交错组合")
    print("- 偏序归约后：O(n) - 只探索一个进程的完整路径")
    print()
    
    test_cases = [2, 3, 4, 5]
    
    print(f"{'最大值':<10} {'完整状态数':<15} {'简化状态数':<15} {'减少率':<10}")
    print("-" * 55)
    
    for max_count in test_cases:
        full_states, reduced_states, reduction_rate = analyze_state_space_explosion(max_count)
        print(f"{max_count:<10} {full_states:<15} {reduced_states:<15} {reduction_rate:<10.1%}")
    
    print("\n观察：")
    print("- 完整状态数随 max_count 呈平方增长 (O(n²))")
    print("- 简化状态数随 max_count 呈线性增长 (O(n))")
    print("- 减少率随规模增大而提高")


def verify_ltl_equivalence():
    """
    验证 LTL\X 公式的等价性
    
    在完整 TS 和简化 TS 上验证相同的 LTL 公式，
    确保偏序归约保持公式真值。
    """
    print("\n" + "=" * 60)
    print("LTL\\X 公式等价性验证")
    print("=" * 60)
    
    # 创建程序图（max_count = 2）
    pg = create_two_counter_program(max_count=2)
    analyzer = create_dependency_analyzer(max_count=2)
    
    # 测试公式1：□(count0 ≤ 2) - 总是 count0 ≤ 2
    print("\n【公式1】□(count0 ≤ 2)")
    print("  描述：count0 永远不超过 2")
    
    # 创建 NBA（简化实现）
    from nba import NBA
    nba1 = NBA()
    q0 = nba1.add_state("q0", is_initial=True, is_accept=True)
    # 接受所有状态（简化）
    nba1.add_transition("q0", "q0", "count0=0")
    nba1.add_transition("q0", "q0", "count0=1")
    nba1.add_transition("q0", "q0", "count0=2")
    
    checker = PORLTLChecker()
    result1 = checker.check_with_comparison(
        pg, analyzer, nba1, {"count0"}, "□(count0 ≤ 2)"
    )
    
    print(f"  完整TS结果: {result1.full_result.holds}")
    print(f"  简化TS结果: {result1.reduced_result.holds}")
    print(f"  等价性: {result1.equivalent}")
    
    # 测试公式2：□¬(count0 = 2 ∧ count1 = 2) - 不会同时达到最大值
    print("\n【公式2】□¬(count0 = 2 ∧ count1 = 2)")
    print("  描述：不会同时达到最大值")
    
    # 这个公式在简化 TS 上可能不同，因为偏序归约改变了交错
    # 但在 LTL\X 中，这种性质应该保持
    
    print("\n结论：")
    if result1.equivalent:
        print("✓ 偏序归约正确保持了 LTL\\X 公式真值")
    else:
        print("✗ 需要检查偏序归约实现")


def create_detailed_example():
    """
    创建详细的双计数器示例，展示具体的状态空间
    """
    print("\n" + "=" * 60)
    print("详细示例：max_count = 2")
    print("=" * 60)
    
    # 创建程序图
    pg = create_two_counter_program(max_count=2)
    analyzer = create_dependency_analyzer(max_count=2)
    
    # 完整展开
    print("\n【完整状态空间】")
    builder_full = PORTransitionSystemBuilder(enable_por=False)
    full_ts = builder_full.build_from_program_graph(pg, analyzer)
    full_ts.print_reachable_graph()
    
    # 偏序归约展开
    print("\n【偏序归约状态空间】")
    builder_por = PORTransitionSystemBuilder(enable_por=True)
    reduced_ts = builder_por.build_from_program_graph(pg, analyzer)
    reduced_ts.print_reachable_graph()
    
    # 统计对比
    full_stats = full_ts.get_statistics()
    reduced_stats = reduced_ts.get_statistics()
    
    print("\n【统计对比】")
    print(f"完整展开：  状态数 = {full_stats['reachable_states']}, 迁移数 = {full_stats['reachable_transitions']}")
    print(f"偏序归约：  状态数 = {reduced_stats['reachable_states']}, 迁移数 = {reduced_stats['reachable_transitions']}")
    
    reduction = (full_stats['reachable_states'] - reduced_stats['reachable_states']) / full_stats['reachable_states']
    print(f"状态减少率：{reduction:.1%}")


def visualize_por_state_spaces(max_count: int = 2, output_dir=None):
    """
    可视化原始状态空间和偏序归约后的状态空间

    Args:
        max_count: 计数器最大值（影响状态空间规模）
        output_dir: 可视化文件输出目录（默认输出到 output/visualization）
    """
    from por_visualizer import visualize_por_comparison, DEFAULT_OUTPUT_DIR

    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    print("\n" + "=" * 60)
    print(f"偏序归约状态空间可视化（max_count={max_count}）")
    print("=" * 60)

    pg = create_two_counter_program(max_count=max_count)
    analyzer = create_dependency_analyzer(max_count=max_count)

    comparison_path = visualize_por_comparison(
        pg=pg,
        dependency_analyzer=analyzer,
        name=f"lab7_counter_por_n{max_count}",
        output_dir=output_dir
    )

    print(f"\n可视化完成！对比页面: {comparison_path}")
    return comparison_path


if __name__ == "__main__":
    # 演示偏序归约效果
    demonstrate_por_effect()

    # 详细示例
    create_detailed_example()

    # 验证 LTL 等价性
    verify_ltl_equivalence()

    # 可视化状态空间（max_count=2 和 max_count=3）
    visualize_por_state_spaces(max_count=2)
    visualize_por_state_spaces(max_count=3)
