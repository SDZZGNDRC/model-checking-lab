"""
实验三：交通灯示例

本模块演示如何使用正则安全属性验证来检查交通灯系统。

示例属性：
1. "red 后必须紧跟 yellow" - 正常交通灯行为
2. "不允许连续两个 red" - 安全属性

包含两个版本的交通灯模型：
- 正常版本：满足所有安全属性
- 错误版本：red 后直接变 green，违反属性
"""

import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from transition_system import TransitionSystem, State
from nfa import NFA, build_nfa_from_regex
from safety_verifier import (
    SafetyVerifier, 
    build_bad_prefix_nfa_red_must_follow_yellow,
    build_bad_prefix_nfa_no_consecutive_red
)
from nfa_visualizer import NFAVisualizer

# 可视化输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visualization"


def create_traffic_light_ts() -> TransitionSystem:
    """
    创建正常交通灯 Transition System
    
    状态序列：green -> yellow -> red -> green -> ...
    这是一个循环，确保 red 后总是 yellow
    """
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("green", {"green"})
    ts.add_state("yellow", {"yellow"})
    ts.add_state("red", {"red"})
    
    # 设置初始状态
    ts.add_initial_state("green")
    
    # 添加迁移
    ts.add_transition("green", "yellow", "to_yellow")
    ts.add_transition("yellow", "red", "to_red")
    ts.add_transition("red", "green", "to_green")  # 正常：red -> green
    
    return ts


def create_traffic_light_ts_correct() -> TransitionSystem:
    """
    创建正确的交通灯 Transition System
    
    状态序列：green -> yellow -> red -> yellow -> green -> ...
    确保 red 后总是紧跟 yellow
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
    ts.add_transition("red", "yellow_to_green", "to_yellow")  # red 后紧跟 yellow
    ts.add_transition("yellow_to_green", "green", "to_green")
    
    return ts


def create_traffic_light_ts_violation() -> TransitionSystem:
    """
    创建违反属性的交通灯 Transition System
    
    状态序列：green -> yellow -> red -> green -> ...
    错误：red 后直接变 green，没有 yellow
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
    ts.add_transition("red", "green", "to_green")  # 错误：red 直接到 green
    
    return ts


def create_extended_traffic_light_ts() -> TransitionSystem:
    """
    创建扩展的交通灯模型（带行人按钮）
    
    正常序列：green -> yellow -> red -> yellow -> green
    当在 green 时按下按钮：green -> yellow -> red（快速切换）
    """
    ts = TransitionSystem()
    
    # 正常状态
    ts.add_state("green", {"green"})
    ts.add_state("yellow_normal", {"yellow"})
    ts.add_state("red", {"red"})
    ts.add_state("yellow_after_red", {"yellow"})
    
    # 按钮按下后的快速状态
    ts.add_state("green_button", {"green"})
    ts.add_state("yellow_fast", {"yellow"})
    
    # 初始状态
    ts.add_initial_state("green")
    
    # 正常迁移
    ts.add_transition("green", "yellow_normal", "timeout")
    ts.add_transition("yellow_normal", "red", "to_red")
    ts.add_transition("red", "yellow_after_red", "to_yellow")
    ts.add_transition("yellow_after_red", "green", "to_green")
    
    # 按钮按下迁移
    ts.add_transition("green", "green_button", "button_press")
    ts.add_transition("green_button", "yellow_fast", "to_yellow")
    ts.add_transition("yellow_fast", "red", "to_red")
    
    return ts


def visualize_nfa_with_details(nfa: NFA, filename_prefix: str, title: str):
    """
    可视化 NFA 并生成多种格式
    
    Args:
        nfa: 要可视化的 NFA
        filename_prefix: 文件名前缀
        title: 可视化标题
    """
    viz = NFAVisualizer(nfa)
    
    # 保存 DOT 格式
    dot_path = OUTPUT_DIR / f"{filename_prefix}.dot"
    viz.save_dot(str(dot_path))
    
    # 保存 HTML 格式
    html_path = OUTPUT_DIR / f"{filename_prefix}.html"
    viz.save_html(str(html_path), title=title)
    
    # 打印 ASCII 可视化
    print(f"\n【{title} - ASCII 结构图】")
    viz.print_ascii()
    
    return dot_path, html_path


def visualize_ts_with_details(ts: TransitionSystem, filename_prefix: str, 
                               title: str, highlight_path: list = None):
    """
    可视化 Transition System 并生成多种格式
    
    Args:
        ts: 要可视化的 Transition System
        filename_prefix: 文件名前缀
        title: 可视化标题
        highlight_path: 要高亮显示的路径（状态列表）
    """
    from ts_visualizer import TSVisualizer
    
    viz = TSVisualizer(ts)
    
    # 保存 DOT 格式（支持路径高亮）
    dot_path = OUTPUT_DIR / f"{filename_prefix}.dot"
    if highlight_path:
        viz.save_dot(str(dot_path), highlight_path=highlight_path)
    else:
        viz.save_dot(str(dot_path))
    
    # 保存 HTML 格式
    html_path = OUTPUT_DIR / f"{filename_prefix}.html"
    viz.save_html(str(html_path), title=title)
    
    # 打印 ASCII 可视化
    print(f"\n【{title} - ASCII 结构图】")
    viz.print_ascii()
    
    return dot_path, html_path


def demo_traffic_light_verification():
    """演示交通灯属性验证"""
    
    print("=" * 70)
    print("实验三：正则安全属性验证 - 交通灯示例")
    print("=" * 70)
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # ====== 测试 1：正确的交通灯 ======
    print("\n【测试 1】正确的交通灯模型")
    print("-" * 50)
    
    ts_correct = create_traffic_light_ts_correct()
    ts_correct.print_reachable_graph()
    
    # 生成详细可视化
    print(f"\n生成可视化文件到 {OUTPUT_DIR}")
    visualize_ts_with_details(
        ts_correct, 
        "lab3_traffic_correct", 
        "正确交通灯模型 - Transition System"
    )
    
    # 验证属性：red 后必须紧跟 yellow
    print("\n验证属性：'red 后必须紧跟 yellow'")
    nfa_red_yellow = build_bad_prefix_nfa_red_must_follow_yellow()
    
    # 可视化坏前缀 NFA
    print("\n【坏前缀 NFA 可视化】")
    visualize_nfa_with_details(
        nfa_red_yellow,
        "lab3_nfa_red_must_follow_yellow",
        "坏前缀 NFA: red后必须紧跟yellow"
    )
    
    verifier = SafetyVerifier(ts_correct)
    result1 = verifier.verify(nfa_red_yellow, "red 后必须紧跟 yellow")
    
    print(f"\n  结果: {result1}")
    if result1.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result1.counterexample)}")
    
    # ====== 测试 2：违反属性的交通灯 ======
    print("\n" + "=" * 70)
    print("【测试 2】违反属性的交通灯模型（red 后直接变 green）")
    print("-" * 50)
    
    ts_violation = create_traffic_light_ts_violation()
    ts_violation.print_reachable_graph()
    
    # 生成可视化（普通版本）
    print(f"\n生成普通可视化文件到 {OUTPUT_DIR}")
    visualize_ts_with_details(
        ts_violation,
        "lab3_traffic_violation",
        "违反属性交通灯模型 - Transition System"
    )
    
    print("\n验证属性：'red 后必须紧跟 yellow'")
    
    verifier2 = SafetyVerifier(ts_violation)
    result2 = verifier2.verify(nfa_red_yellow, "red 后必须紧跟 yellow")
    
    print(f"\n  结果: {result2}")
    if result2.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result2.counterexample)}")
        if result2.counterexample_labels:
            labels_str = " -> ".join(
                str(sorted(labels)) if labels else "{}" 
                for labels in result2.counterexample_labels
            )
            print(f"  标签序列: {labels_str}")
        
        # 生成带反例路径高亮的可视化
        print("\n【生成带反例路径高亮的可视化】")
        visualize_ts_with_details(
            ts_violation,
            "lab3_traffic_violation_counterexample",
            "违反属性交通灯模型 - 反例路径高亮",
            highlight_path=result2.counterexample
        )
    
    # ====== 测试 3：使用正则表达式构建 NFA ======
    print("\n" + "=" * 70)
    print("【测试 3】使用正则表达式构建 NFA")
    print("-" * 50)
    
    # 构造坏前缀的正则表达式：red 后紧跟 green
    # 这表示 "red green" 是坏前缀
    # 正则表达式：.* red green
    # 简化表示：我们构造一个 NFA 来识别 "red green"
    
    print("构造 NFA 识别坏前缀 'red green'...")
    
    # 手动构造 NFA 来识别 "red" 后跟 "green"
    nfa_regex = NFA()
    nfa_regex.add_state("q0", is_initial=True)
    nfa_regex.add_state("q1")
    nfa_regex.add_state("q2", is_accept=True)
    
    # 自环：可以接受任何序列
    nfa_regex.add_transition("q0", "q0", "green")
    nfa_regex.add_transition("q0", "q0", "yellow")
    
    # red -> green 路径
    nfa_regex.add_transition("q0", "q1", "red")
    nfa_regex.add_transition("q1", "q2", "green")
    
    # 接受状态的自环
    nfa_regex.add_transition("q2", "q2", "red")
    nfa_regex.add_transition("q2", "q2", "green")
    nfa_regex.add_transition("q2", "q2", "yellow")
    
    # 可视化手动构造的 NFA
    print("\n【手动构造的坏前缀 NFA 可视化】")
    visualize_nfa_with_details(
        nfa_regex,
        "lab3_nfa_manual_red_green",
        "手动构造 NFA: 识别 red green 坏前缀"
    )
    
    print("\n验证正确交通灯...")
    result3a = verifier.verify(nfa_regex, "不允许 red 后直接 green")
    print(f"  结果: {'✓ 通过' if result3a.holds else '✗ 失败'}")
    
    print("\n验证违反属性的交通灯...")
    result3b = verifier2.verify(nfa_regex, "不允许 red 后直接 green")
    print(f"  结果: {'✓ 通过' if result3b.holds else '✗ 失败'}")
    if not result3b.holds:
        print(f"  反例路径: {' -> '.join(s.name for s in result3b.counterexample)}")
        
        # 生成带反例路径高亮的可视化
        print("\n【生成带反例路径高亮的可视化】")
        visualize_ts_with_details(
            ts_violation,
            "lab3_traffic_violation_counterexample_3b",
            "违反属性交通灯模型 - 测试3反例路径高亮",
            highlight_path=result3b.counterexample
        )
    
    # ====== 测试 4：扩展交通灯模型 ======
    print("\n" + "=" * 70)
    print("【测试 4】扩展交通灯模型（带行人按钮）")
    print("-" * 50)
    
    ts_extended = create_extended_traffic_light_ts()
    ts_extended.print_reachable_graph()
    
    # 生成详细可视化
    print(f"\n生成可视化文件到 {OUTPUT_DIR}")
    visualize_ts_with_details(
        ts_extended,
        "lab3_traffic_extended",
        "扩展交通灯模型（带行人按钮）- Transition System"
    )
    
    print("\n验证属性：'red 后必须紧跟 yellow'")
    verifier3 = SafetyVerifier(ts_extended)
    result4 = verifier3.verify(nfa_red_yellow, "red 后必须紧跟 yellow")
    
    print(f"\n  结果: {result4}")
    if result4.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result4.counterexample)}")
        if result4.counterexample:
            # 生成带反例路径高亮的可视化
            print("\n【生成带反例路径高亮的可视化】")
            visualize_ts_with_details(
                ts_extended,
                "lab3_traffic_extended_counterexample",
                "扩展交通灯模型 - 反例路径高亮",
                highlight_path=result4.counterexample
            )
    
    # ====== 测试 5：对比可视化 ======
    print("\n" + "=" * 70)
    print("【测试 5】对比可视化：正确模型 vs 违反属性模型")
    print("-" * 50)
    
    print("\n生成对比可视化...")
    
    # 创建简单的对比 TS（原始版本，用于对比）
    ts_original = create_traffic_light_ts()
    
    # 对比可视化 - 原始模型
    visualize_ts_with_details(
        ts_original,
        "lab5_traffic_original",
        "原始交通灯模型（red->green）"
    )
    
    # 对比可视化 - 正确模型
    visualize_ts_with_details(
        ts_correct,
        "lab5_traffic_correct",
        "正确交通灯模型（red->yellow->green）"
    )
    
    # 对比可视化 - 违反属性模型
    visualize_ts_with_details(
        ts_violation,
        "lab5_traffic_violation",
        "违反属性交通灯模型（red直接到green）"
    )
    
    # 可视化另一个坏前缀 NFA（不允许连续 red）
    print("\n【另一个坏前缀 NFA：不允许连续 red】")
    nfa_no_consecutive_red = build_bad_prefix_nfa_no_consecutive_red()
    visualize_nfa_with_details(
        nfa_no_consecutive_red,
        "lab5_nfa_no_consecutive_red",
        "坏前缀 NFA: 不允许连续两个red"
    )
    
    # 验证扩展模型是否满足"不允许连续 red"属性
    print("\n验证扩展模型是否满足 '不允许连续 red' 属性...")
    result5 = verifier3.verify(nfa_no_consecutive_red, "不允许连续 red")
    print(f"  结果: {'✓ 通过' if result5.holds else '✗ 失败'}")
    
    # 总结
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    print(f"1. 正确交通灯模型: {'✓ 通过' if result1.holds else '✗ 失败'}")
    print(f"2. 违反属性模型:   {'✓ 通过（检测到违反）' if not result2.holds else '✗ 未检测到'}")
    print(f"3. 扩展模型(属性1): {'✓ 通过' if result4.holds else '✗ 失败'}")
    print(f"4. 扩展模型(属性2): {'✓ 通过' if result5.holds else '✗ 失败'}")
    print("\n生成的可视化文件:")
    print(f"  - {OUTPUT_DIR}/lab3_*.dot (DOT格式)")
    print(f"  - {OUTPUT_DIR}/lab3_*.html (HTML交互式)")
    print(f"  - {OUTPUT_DIR}/lab5_*.dot (DOT格式 - 对比测试)")
    print(f"  - {OUTPUT_DIR}/lab5_*.html (HTML交互式 - 对比测试)")
    print("\n实验三完成！")


if __name__ == "__main__":
    demo_traffic_light_verification()
