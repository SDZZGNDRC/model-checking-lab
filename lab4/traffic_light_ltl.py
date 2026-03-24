"""
实验四：交通灯 LTL 验证示例

本模块演示如何使用 LTL 模型检查验证交通灯系统。

验证的属性：
1. □♦green（无限经常绿灯）- 活性属性
2. □(red → ♦green)（红灯后最终绿灯）- 响应属性

包含两个版本的交通灯模型：
- 正常版本：满足所有 LTL 属性
- 错误版本：可能永远停留在红灯，违反活性属性
"""

import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from transition_system import TransitionSystem, State
from nba import NBA
from ltl_formula import (
    atom, neg, globally, eventually, implies, conj,
    always_eventually, implies_eventually, ltl_to_nba
)
from ltl_model_checker import LTLModelChecker, check_ltl_property

# 可视化输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visualization"


def create_traffic_light_ts_correct() -> TransitionSystem:
    """
    创建正确的交通灯 Transition System
    
    状态序列：green -> yellow -> red -> yellow -> green -> ...
    确保无限经常变绿（满足 □♦green）
    """
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("green", {"green"})
    ts.add_state("yellow_to_red", {"yellow"})   # yellow 在 red 之前
    ts.add_state("red", {"red"})
    ts.add_state("yellow_to_green", {"yellow"}) # yellow 在 green 之前
    
    # 设置初始状态
    ts.add_initial_state("green")
    
    # 添加迁移：green -> yellow -> red -> yellow -> green
    ts.add_transition("green", "yellow_to_red", "to_yellow")
    ts.add_transition("yellow_to_red", "red", "to_red")
    ts.add_transition("red", "yellow_to_green", "to_yellow")
    ts.add_transition("yellow_to_green", "green", "to_green")
    
    return ts


def create_traffic_light_ts_violation() -> TransitionSystem:
    """
    创建违反 LTL 属性的交通灯 Transition System
    
    状态序列：green -> yellow -> red -> red -> red -> ...
    错误：进入 red 后可能永远停留在 red，违反 □♦green
    """
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("green", {"green"})
    ts.add_state("yellow", {"yellow"})
    ts.add_state("red", {"red"})
    
    # 设置初始状态
    ts.add_initial_state("green")
    
    # 添加迁移（有错误）
    ts.add_transition("green", "yellow", "to_yellow")
    ts.add_transition("yellow", "red", "to_red")
    # 错误：red 可以自环，永远不到 green
    ts.add_transition("red", "red", "stay_red")
    # 也可能变绿（非确定性）
    ts.add_transition("red", "green", "to_green")
    
    return ts


def create_traffic_light_ts_no_green() -> TransitionSystem:
    """
    创建永远不到绿灯的交通灯
    
    用于测试 □♦green 的失败情况
    """
    ts = TransitionSystem()
    
    # 只有 red 和 yellow 状态
    ts.add_state("yellow", {"yellow"})
    ts.add_state("red", {"red"})
    
    # 设置初始状态
    ts.add_initial_state("red")
    
    # red 和 yellow 循环，永远不到 green
    ts.add_transition("red", "yellow", "to_yellow")
    ts.add_transition("yellow", "red", "to_red")
    
    return ts


def demo_traffic_light_ltl():
    """演示交通灯 LTL 属性验证"""
    
    print("=" * 70)
    print("实验四：LTL 模型检查 - 交通灯示例")
    print("=" * 70)
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # ====== 测试 1：正确的交通灯 ======
    print("\n【测试 1】正确的交通灯模型")
    print("-" * 50)
    
    ts_correct = create_traffic_light_ts_correct()
    ts_correct.print_reachable_graph()
    
    # 验证属性：□♦green（无限经常绿灯）
    print("\n验证属性：'□♦green'（无限经常绿灯）")
    print("构造 NBA 用于否定公式...")
    
    # 公式：□♦green
    # 否定：¬(□♦green) ≡ ♦□¬green（最终永远非绿）
    # 我们需要构造一个 NBA 接受所有永远不到 green 的运行
    
    # 手动构造否定公式的 NBA
    # 接受条件：运行永远访问 ¬green 的状态
    nba_neg_always_eventually_green = NBA()
    q0 = nba_neg_always_eventually_green.add_state("q0", is_initial=True, is_accept=True)
    # 只要读到的不是 green，就保持在接受状态
    nba_neg_always_eventually_green.add_transition("q0", "q0", "red")
    nba_neg_always_eventually_green.add_transition("q0", "q0", "yellow")
    # 读到 green 则进入非接受状态（死状态）
    q1 = nba_neg_always_eventually_green.add_state("q1")
    nba_neg_always_eventually_green.add_transition("q0", "q1", "green")
    nba_neg_always_eventually_green.add_transition("q1", "q1", "green")
    nba_neg_always_eventually_green.add_transition("q1", "q1", "red")
    nba_neg_always_eventually_green.add_transition("q1", "q1", "yellow")
    
    print("NBA 结构（否定公式）：")
    nba_neg_always_eventually_green.print_structure()
    
    checker = LTLModelChecker(ts_correct)
    result1 = checker.check(nba_neg_always_eventually_green, "□♦green")
    
    print(f"\n  结果: {result1}")
    if result1.holds:
        print("  ✓ 属性成立！（无限经常绿灯）")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result1.counterexample)}")
        if result1.counterexample_loop:
            print(f"  循环部分: {' -> '.join(s.name for s in result1.counterexample_loop)}")
    
    # ====== 测试 2：违反属性的交通灯 ======
    print("\n" + "=" * 70)
    print("【测试 2】违反属性的交通灯模型（可能永远停留在红灯）")
    print("-" * 50)
    
    ts_violation = create_traffic_light_ts_violation()
    ts_violation.print_reachable_graph()
    
    print("\n验证属性：'□♦green'（无限经常绿灯）")
    
    checker2 = LTLModelChecker(ts_violation)
    result2 = checker2.check(nba_neg_always_eventually_green, "□♦green")
    
    print(f"\n  结果: {result2}")
    if result2.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径前缀: {' -> '.join(s.name for s in result2.counterexample)}")
        if result2.counterexample_loop:
            print(f"  循环部分: {' -> '.join(s.name for s in result2.counterexample_loop)}")
            print("  这意味着系统可以永远停留在红灯！")
    
    # ====== 测试 3：永远不到绿灯的交通灯 ======
    print("\n" + "=" * 70)
    print("【测试 3】永远不到绿灯的交通灯模型")
    print("-" * 50)
    
    ts_no_green = create_traffic_light_ts_no_green()
    ts_no_green.print_reachable_graph()
    
    print("\n验证属性：'□♦green'（无限经常绿灯）")
    
    checker3 = LTLModelChecker(ts_no_green)
    result3 = checker3.check(nba_neg_always_eventually_green, "□♦green")
    
    print(f"\n  结果: {result3}")
    if result3.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result3.counterexample)}")
        if result3.counterexample_loop:
            print(f"  循环部分: {' -> '.join(s.name for s in result3.counterexample_loop)}")
    
    # ====== 测试 4：响应属性 □(red → ♦green) ======
    print("\n" + "=" * 70)
    print("【测试 4】响应属性：□(red → ♦green)")
    print("        （每当红灯亮，最终会变绿灯）")
    print("-" * 50)
    
    # 构造否定公式的 NBA：¬□(red → ♦green) ≡ ♦(red ∧ □¬green)
    # 即：存在某个时刻，红灯亮且从此永远不到绿灯
    nba_neg_response = NBA()
    q0 = nba_neg_response.add_state("q0", is_initial=True, is_accept=True)
    q1 = nba_neg_response.add_state("q1")  # 刚读到 red
    q2 = nba_neg_response.add_state("q2", is_accept=True)  # 永远不到 green
    
    # q0：等待 red
    nba_neg_response.add_transition("q0", "q0", "green")
    nba_neg_response.add_transition("q0", "q0", "yellow")
    nba_neg_response.add_transition("q0", "q1", "red")
    
    # q1：刚读到 red，检查下一个是否是 green
    nba_neg_response.add_transition("q1", "q2", "red")  # red 后还是 red，违反
    nba_neg_response.add_transition("q1", "q2", "yellow")  # red 后是 yellow，检查后续
    nba_neg_response.add_transition("q1", "q0", "green")  # red 后是 green，满足
    
    # q2：接受状态（违反属性）
    nba_neg_response.add_transition("q2", "q2", "red")
    nba_neg_response.add_transition("q2", "q2", "yellow")
    
    print("\n验证正确交通灯...")
    result4a = checker.check(nba_neg_response, "□(red → ♦green)")
    print(f"  结果: {'✓ 通过' if result4a.holds else '✗ 失败'}")
    if not result4a.holds:
        print(f"  反例: {' -> '.join(s.name for s in result4a.counterexample)}")
    
    print("\n验证违反属性的交通灯...")
    result4b = checker2.check(nba_neg_response, "□(red → ♦green)")
    print(f"  结果: {'✓ 通过' if result4b.holds else '✗ 失败'}")
    if not result4b.holds:
        print(f"  反例: {' -> '.join(s.name for s in result4b.counterexample)}")
        if result4b.counterexample_loop:
            print(f"  循环: {' -> '.join(s.name for s in result4b.counterexample_loop)}")
    
    # ====== 总结 ======
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    print(f"1. 正确交通灯 (□♦green):     {'✓ 通过' if result1.holds else '✗ 失败'}")
    print(f"2. 可能永远红灯 (□♦green):   {'✓ 通过' if result2.holds else '✗ 检测到违反'}")
    print(f"3. 永远不到绿灯 (□♦green):   {'✓ 通过' if result3.holds else '✗ 检测到违反'}")
    print(f"4. 正确交通灯 (□(red→♦green)): {'✓ 通过' if result4a.holds else '✗ 失败'}")
    print(f"5. 可能永远红灯 (□(red→♦green)): {'✓ 通过' if result4b.holds else '✗ 检测到违反'}")
    print("\n实验四交通灯示例完成！")


if __name__ == "__main__":
    demo_traffic_light_ltl()
