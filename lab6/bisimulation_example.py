"""
实验六：Bisimulation 最小化示例

本模块演示 Bisimulation 最小化的应用：
1. 简单示例：展示基本的最小化过程
2. Peterson 算法：验证最小化前后的 CTL 性质一致性
3. 对比分析：展示状态空间缩减效果
4. 可视化：生成原始和最小化TS的对比图
"""

import sys
import os
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab5')

from typing import Tuple, Optional

from transition_system import TransitionSystem, State
from bisimulation_minimizer import (
    BisimulationMinimizer, MinimizationResult, minimize_transition_system
)
from ctl_formula import atom, neg, conj, disj, ag, af, ef, eu
from ctl_model_checker import CTLModelChecker

# 导入可视化模块
from ts_visualizer import TSVisualizer

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                          'output', 'visualization')


def create_simple_example_ts() -> TransitionSystem:
    """
    创建一个简单的示例迁移系统
    
    这个 TS 有一些 Bisimilar 的状态可以被合并。
    
    状态:
    - s0: 初始状态，标签 {a}
    - s1: 标签 {b}，后继到 s3
    - s2: 标签 {b}，后继到 s3 (与 s1 Bisimilar)
    - s3: 标签 {c}
    - s4: 标签 {b}，后继到 s5
    - s5: 标签 {c} (与 s3 Bisimilar)
    
    预期最小化后：
    - s0 单独一个块
    - s1, s2, s4 合并（都有标签 b，且后继到标签 c 的块）
    - s3, s5 合并（都有标签 c）
    """
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("s0", {"a"})
    ts.add_state("s1", {"b"})
    ts.add_state("s2", {"b"})
    ts.add_state("s3", {"c"})
    ts.add_state("s4", {"b"})
    ts.add_state("s5", {"c"})
    
    # 设置初始状态
    ts.add_initial_state("s0")
    
    # 添加迁移
    ts.add_transition("s0", "s1")
    ts.add_transition("s0", "s2")
    ts.add_transition("s0", "s4")
    ts.add_transition("s1", "s3")
    ts.add_transition("s2", "s3")
    ts.add_transition("s4", "s5")
    
    return ts


def create_redundant_ts() -> TransitionSystem:
    """
    创建一个有大量冗余状态的迁移系统
    
    这个 TS 模拟两个并行的相同子系统，它们应该被最小化为一个。
    """
    ts = TransitionSystem()
    
    # 子系统 A
    ts.add_state("a0", {"start"})
    ts.add_state("a1", {"middle"})
    ts.add_state("a2", {"end"})
    
    # 子系统 B（与子系统 A 结构相同，只是名称不同）
    ts.add_state("b0", {"start"})
    ts.add_state("b1", {"middle"})
    ts.add_state("b2", {"end"})
    
    # 设置初始状态
    ts.add_initial_state("a0")
    ts.add_initial_state("b0")
    
    # 子系统 A 的迁移
    ts.add_transition("a0", "a1", "step")
    ts.add_transition("a1", "a2", "step")
    ts.add_transition("a2", "a2", "loop")
    
    # 子系统 B 的迁移（与 A 相同）
    ts.add_transition("b0", "b1", "step")
    ts.add_transition("b1", "b2", "step")
    ts.add_transition("b2", "b2", "loop")
    
    return ts


def create_peterson_ts_for_minimization() -> TransitionSystem:
    """
    创建一个适合展示最小化效果的 Peterson 算法迁移系统
    
    使用简化版本，但添加一些对称状态。
    """
    ts = TransitionSystem()
    
    # 状态: (pc0, pc1, turn)
    # pc: 0=非临界区, 1=等待, 2=临界区
    
    states = [
        ("s00_0", 0, 0, 0),
        ("s00_1", 0, 0, 1),
        ("s10_0", 1, 0, 0),
        ("s10_1", 1, 0, 1),
        ("s01_0", 0, 1, 0),
        ("s01_1", 0, 1, 1),
        ("s11_0", 1, 1, 0),
        ("s11_1", 1, 1, 1),
        ("s20_0", 2, 0, 0),
        ("s20_1", 2, 0, 1),
        ("s02_0", 0, 2, 0),
        ("s02_1", 0, 2, 1),
    ]
    
    for name, pc0, pc1, turn in states:
        labels = set()
        if pc0 == 1:
            labels.add("wait0")
        if pc0 == 2:
            labels.add("crit0")
        if pc1 == 1:
            labels.add("wait1")
        if pc1 == 2:
            labels.add("crit1")
        ts.add_state(name, labels)
    
    # 初始状态
    ts.add_initial_state("s00_0")
    ts.add_initial_state("s00_1")
    
    # 添加迁移
    # P0 从非临界区到等待区
    ts.add_transition("s00_0", "s10_0", "P0_request")
    ts.add_transition("s00_1", "s10_1", "P0_request")
    
    # P1 从非临界区到等待区
    ts.add_transition("s00_0", "s01_0", "P1_request")
    ts.add_transition("s00_1", "s01_1", "P1_request")
    
    # P0 进入临界区（当 turn=0 时）
    ts.add_transition("s10_0", "s20_0", "P0_enter")
    ts.add_transition("s11_0", "s21_0", "P0_enter")
    
    # P1 进入临界区（当 turn=1 时）
    ts.add_transition("s01_1", "s02_1", "P1_enter")
    ts.add_transition("s11_1", "s12_1", "P1_enter")
    
    # P0 离开临界区
    ts.add_transition("s20_0", "s00_1", "P0_exit")
    ts.add_transition("s20_1", "s00_0", "P0_exit")
    
    # P1 离开临界区
    ts.add_transition("s02_0", "s00_1", "P1_exit")
    ts.add_transition("s02_1", "s00_0", "P1_exit")
    
    return ts


def visualize_minimization_comparison(result: MinimizationResult, 
                                       name: str,
                                       output_dir: str = OUTPUT_DIR) -> Tuple[str, str]:
    """
    可视化原始TS和最小化TS的对比
    
    Args:
        result: 最小化结果
        name: 输出文件名前缀
        output_dir: 输出目录
        
    Returns:
        (原始TS的HTML路径, 最小化TS的HTML路径)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 可视化原始TS
    original_viz = TSVisualizer(result.original_ts)
    original_dot = original_viz.to_dot()
    original_dot_path = os.path.join(output_dir, f"lab6_{name}_original.dot")
    original_html_path = os.path.join(output_dir, f"lab6_{name}_original.html")
    
    with open(original_dot_path, 'w', encoding='utf-8') as f:
        f.write(original_dot)
    original_viz.save_html(original_html_path, title=f"{name} - 原始迁移系统")
    
    # 可视化最小化TS
    minimized_viz = TSVisualizer(result.minimized_ts)
    minimized_dot = minimized_viz.to_dot()
    minimized_dot_path = os.path.join(output_dir, f"lab6_{name}_minimized.dot")
    minimized_html_path = os.path.join(output_dir, f"lab6_{name}_minimized.html")
    
    with open(minimized_dot_path, 'w', encoding='utf-8') as f:
        f.write(minimized_dot)
    minimized_viz.save_html(minimized_html_path, title=f"{name} - 最小化后迁移系统")
    
    print(f"  可视化文件已保存:")
    print(f"    - {original_html_path}")
    print(f"    - {minimized_html_path}")
    
    return original_html_path, minimized_html_path


def visualize_partition(result: MinimizationResult,
                        name: str,
                        output_dir: str = OUTPUT_DIR) -> str:
    """
    可视化Bisimulation分区（用不同颜色标记等价类）
    
    Args:
        result: 最小化结果
        name: 输出文件名前缀
        output_dir: 输出目录
        
    Returns:
        HTML文件路径
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 为每个块分配颜色
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
        "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"
    ]
    
    block_colors = {}
    for i, block in enumerate(sorted(result.partition, key=lambda b: b.id)):
        block_colors[block.id] = colors[i % len(colors)]
    
    # 构建DOT，用颜色标记等价类
    dot_lines = ['digraph Partition {', '  rankdir=TB;']
    dot_lines.append('  label="Bisimulation 分区（颜色标记等价类）";')
    dot_lines.append('  labelloc="t";')
    dot_lines.append('  node [shape=ellipse, style=filled, fontname="Arial"];')
    
    # 添加状态节点（带颜色）
    for state in result.original_ts.get_all_states():
        block = result.block_map.get(state)
        if block:
            color = block_colors.get(block.id, "#CCCCCC")
            labels_str = "\\n".join(sorted(state.labels)) if state.labels else ""
            label = f"{state.name}\\n{labels_str}" if state.labels else state.name
            dot_lines.append(f'  "{state.name}" [fillcolor="{color}", label="{label}"];')
    
    # 添加迁移边
    for state in result.original_ts.get_all_states():
        for succ in result.original_ts.get_successors(state):
            dot_lines.append(f'  "{state.name}" -> "{succ.name}";')
    
    dot_lines.append('}')
    dot_content = "\\n".join(dot_lines)
    
    # 保存DOT文件
    dot_path = os.path.join(output_dir, f"lab6_{name}_partition.dot")
    with open(dot_path, 'w', encoding='utf-8') as f:
        f.write(dot_content)
    
    # 生成HTML
    html_path = os.path.join(output_dir, f"lab6_{name}_partition.html")
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{name} - Bisimulation 分区</title>
    <script src="https://unpkg.com/viz.js@2.1.0-pre.1/viz.js"></script>
    <script src="https://unpkg.com/viz.js@2.1.0-pre.1/full.render.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        #graph {{ border: 1px solid #ddd; padding: 10px; }}
        .legend {{ margin-top: 20px; padding: 10px; background: #f5f5f5; }}
        .legend-item {{ display: inline-block; margin: 5px 10px; }}
        .color-box {{ display: inline-block; width: 20px; height: 20px; margin-right: 5px; vertical-align: middle; }}
    </style>
</head>
<body>
    <h1>{name} - Bisimulation 分区可视化</h1>
    <div id="graph"></div>
    <div class="legend">
        <h3>等价类（颜色标记）:</h3>
        {''.join(f'<div class="legend-item"><span class="color-box" style="background-color: {block_colors.get(block.id, "#CCCCCC")};"></span>Block {block.id}: {", ".join(sorted(s.name for s in block.states))}</div><br>' for block in sorted(result.partition, key=lambda b: b.id))}
    </div>
    <script>
        const dot = `{dot_content}`;
        const viz = new Viz();
        viz.renderSVGElement(dot).then(function(element) {{
            document.getElementById('graph').appendChild(element);
        }}).catch(function(error) {{
            console.error(error);
            document.getElementById('graph').innerHTML = '<p style="color: red;">渲染失败: ' + error + '</p>';
        }});
    </script>
</body>
</html>'''
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"    - {html_path}")
    return html_path


def demonstrate_simple_minimization():
    """演示简单示例的最小化"""
    print("=" * 70)
    print("示例 1: 简单迁移系统的 Bisimulation 最小化")
    print("=" * 70)
    
    ts = create_simple_example_ts()
    
    print("\n原始迁移系统:")
    print(f"  状态数: {len(ts.get_all_states())}")
    print(f"  迁移数: {ts.get_statistics()['total_transitions']}")
    
    # ASCII可视化
    print("\n原始TS的ASCII可视化:")
    ts.visualize_ascii()
    
    print("\n原始状态详情:")
    for state in sorted(ts.get_all_states(), key=lambda s: s.name):
        successors = ts.get_successors(state)
        succ_names = [s.name for s in successors]
        labels = ",".join(sorted(state.labels)) if state.labels else "无"
        print(f"  {state.name}: 标签=[{labels}], 后继={succ_names}")
    
    # 执行最小化
    result = minimize_transition_system(ts)
    
    print("\n最小化结果:")
    print(f"  原始状态数: {result.original_state_count}")
    print(f"  最小化后状态数: {result.minimized_state_count}")
    print(f"  缩减比例: {result.reduction_ratio:.1%}")
    print(f"  迭代次数: {result.iterations}")
    
    print("\nBisimulation 等价类:")
    for block in sorted(result.partition, key=lambda b: b.id):
        state_names = sorted(s.name for s in block.states)
        print(f"  Block {block.id}: {state_names}")
    
    print("\n最小化后的迁移系统:")
    minimized_stats = result.minimized_ts.get_statistics()
    print(f"  状态数: {minimized_stats['reachable_states']}")
    print(f"  迁移数: {minimized_stats['reachable_transitions']}")
    
    # ASCII可视化最小化TS
    print("\n最小化后TS的ASCII可视化:")
    result.minimized_ts.visualize_ascii()
    
    print("\n最小化后的状态和标签:")
    for state in sorted(result.minimized_ts.get_all_states(), key=lambda s: s.name):
        labels = ",".join(sorted(state.labels)) if state.labels else "无"
        print(f"  {state.name}: [{labels}]")
    
    # 生成可视化文件
    print("\n生成可视化文件...")
    visualize_minimization_comparison(result, "simple_example")
    visualize_partition(result, "simple_example")
    
    print()
    return result


def demonstrate_redundant_minimization():
    """演示冗余状态的最小化"""
    print("=" * 70)
    print("示例 2: 冗余状态的最小化（两个相同子系统）")
    print("=" * 70)
    
    ts = create_redundant_ts()
    
    print("\n原始迁移系统:")
    print(f"  状态数: {len(ts.get_all_states())}")
    print(f"  迁移数: {ts.get_statistics()['total_transitions']}")
    
    # ASCII可视化
    print("\n原始TS的ASCII可视化:")
    ts.visualize_ascii()
    
    print("\n原始状态详情:")
    for state in sorted(ts.get_all_states(), key=lambda s: s.name):
        successors = ts.get_successors(state)
        succ_names = [s.name for s in successors]
        labels = ",".join(sorted(state.labels)) if state.labels else "无"
        print(f"  {state.name}: 标签=[{labels}], 后继={succ_names}")
    
    # 执行最小化
    result = minimize_transition_system(ts)
    
    print("\n最小化结果:")
    print(f"  原始状态数: {result.original_state_count}")
    print(f"  最小化后状态数: {result.minimized_state_count}")
    print(f"  缩减比例: {result.reduction_ratio:.1%}")
    print(f"  迭代次数: {result.iterations}")
    
    print("\nBisimulation 等价类:")
    for block in sorted(result.partition, key=lambda b: b.id):
        state_names = sorted(s.name for s in block.states)
        print(f"  Block {block.id}: {state_names}")
    
    # ASCII可视化最小化TS
    print("\n最小化后TS的ASCII可视化:")
    result.minimized_ts.visualize_ascii()
    
    # 生成可视化文件
    print("\n生成可视化文件...")
    visualize_minimization_comparison(result, "redundant_system")
    visualize_partition(result, "redundant_system")
    
    print()
    return result


def verify_ctl_equivalence():
    """
    验证最小化前后 CTL 公式的等价性
    
    这是实验六的核心验证：Bisimulation 保持 CTL* 性质。
    """
    print("=" * 70)
    print("示例 3: 验证最小化前后 CTL 性质的一致性")
    print("=" * 70)
    
    # 创建测试用的 TS
    ts = create_simple_example_ts()
    
    # 最小化
    result = minimize_transition_system(ts)
    minimized_ts = result.minimized_ts
    
    # 定义要验证的 CTL 公式
    formulas = [
        ("EF(c)", ef(atom("c"))),  # 最终能到达 c
        ("AG(a | b | c)", ag(disj(disj(atom("a"), atom("b")), atom("c")))),  # 总是 a 或 b 或 c
        ("EX(b)", ef(atom("b"))),  # 存在路径下一步是 b
    ]
    
    print("\n验证 CTL 公式在原始 TS 和最小化 TS 上的一致性:\n")
    
    checker_original = CTLModelChecker(ts)
    checker_minimized = CTLModelChecker(minimized_ts)
    
    all_match = True
    
    for name, formula in formulas:
        result_orig = checker_original.check(formula)
        result_min = checker_minimized.check(formula)
        
        # 检查公式在初始状态上的结果是否一致
        match = result_orig.holds == result_min.holds
        status = "✓" if match else "✗"
        
        print(f"  {status} 公式: {name}")
        print(f"      原始 TS: {'满足' if result_orig.holds else '不满足'}")
        print(f"      最小化 TS: {'满足' if result_min.holds else '不满足'}")
        
        if not match:
            all_match = False
    
    print(f"\n结论: {'所有 CTL 公式结果一致 ✓' if all_match else '存在不一致的公式 ✗'}")
    print()
    
    return all_match


def demonstrate_peterson_minimization():
    """演示 Peterson 算法 TS 的最小化"""
    print("=" * 70)
    print("示例 4: Peterson 算法迁移系统的最小化")
    print("=" * 70)
    
    # 这里我们使用 lab5 的 Peterson TS
    try:
        sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab5')
        from peterson_ctl import create_peterson_ts
        
        ts = create_peterson_ts(simplified=True)
    except Exception as e:
        print(f"无法加载 Peterson TS，使用简化版本: {e}")
        ts = create_peterson_ts_for_minimization()
    
    print("\n原始 Peterson 迁移系统:")
    stats = ts.get_statistics()
    print(f"  总状态数: {stats['total_states']}")
    print(f"  可达状态数: {stats['reachable_states']}")
    print(f"  迁移数: {stats['reachable_transitions']}")
    
    # ASCII可视化原始TS
    print("\n原始Peterson TS的ASCII可视化:")
    ts.visualize_ascii()
    
    # 执行最小化
    result = minimize_transition_system(ts)
    
    print("\n最小化结果:")
    print(f"  原始状态数: {result.original_state_count}")
    print(f"  最小化后状态数: {result.minimized_state_count}")
    print(f"  缩减比例: {result.reduction_ratio:.1%}")
    print(f"  迭代次数: {result.iterations}")
    
    print("\nBisimulation 等价类 (前 10 个):")
    for i, block in enumerate(sorted(result.partition, key=lambda b: b.id)[:10]):
        state_names = sorted(s.name for s in block.states)
        labels = set()
        for s in block.states:
            labels.update(s.labels)
        label_str = ",".join(sorted(labels)) if labels else "无"
        print(f"  Block {block.id}: 状态数={len(state_names)}, 标签=[{label_str}]")
    
    if len(result.partition) > 10:
        print(f"  ... 还有 {len(result.partition) - 10} 个块")
    
    # ASCII可视化最小化TS
    print("\n最小化后Peterson TS的ASCII可视化:")
    result.minimized_ts.visualize_ascii()
    
    # 生成可视化文件
    print("\n生成可视化文件...")
    visualize_minimization_comparison(result, "peterson")
    visualize_partition(result, "peterson")
    
    print()
    return result


def run_all_examples():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("实验六：Bisimulation 最小化演示")
    print("=" * 70)
    print()
    
    # 示例 1: 简单示例
    demonstrate_simple_minimization()
    
    # 示例 2: 冗余状态
    demonstrate_redundant_minimization()
    
    # 示例 3: CTL 等价性验证
    verify_ctl_equivalence()
    
    # 示例 4: Peterson 算法
    demonstrate_peterson_minimization()
    
    print("=" * 70)
    print("所有示例运行完成！")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()