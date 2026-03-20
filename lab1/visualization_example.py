"""
Transition System 可视化示例

本示例展示如何使用 ts_visualizer 模块可视化迁移系统。
"""

import sys
from pathlib import Path

# 添加 lab1 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from transition_system import TransitionSystem
from ts_visualizer import TSVisualizer

# 可视化输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visualization"


def example1_simple_ts():
    """示例1: 简单的迁移系统可视化"""
    print("=" * 60)
    print("示例1: 简单迁移系统")
    print("=" * 60)
    
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("start", {"init"})
    ts.add_state("process", {"running"})
    ts.add_state("check", {"running", "verify"})
    ts.add_state("success", {"done"})
    ts.add_state("error", {"failed"})
    
    # 设置初始状态
    ts.add_initial_state("start")
    
    # 添加迁移
    ts.add_transition("start", "process", "begin")
    ts.add_transition("process", "check", "validate")
    ts.add_transition("check", "success", "ok")
    ts.add_transition("check", "error", "fail")
    ts.add_transition("error", "start", "retry")
    
    # ASCII 可视化
    print("\n1. ASCII 可视化:")
    ts.visualize_ascii()
    
    # DOT 格式
    print("\n2. DOT 格式 (Graphviz):")
    print(ts.visualize_dot())
    
    # 保存 DOT 文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "example1_simple.dot")
    
    # 保存 HTML 文件
    ts.visualize_html(OUTPUT_DIR / "example1_simple.html")
    
    print("\n文件已生成:")
    print(f"  - {OUTPUT_DIR / 'example1_simple.dot'}")
    print(f"  - {OUTPUT_DIR / 'example1_simple.html'}")
    
    return ts


def example2_peterson_visualization():
    """示例2: Peterson 算法的可视化"""
    print("\n" + "=" * 60)
    print("示例2: Peterson 互斥算法 (简化模型)")
    print("=" * 60)
    
    # 导入简化版 Peterson 模型
    from peterson_example import create_simplified_peterson
    
    ts = create_simplified_peterson()
    
    # ASCII 可视化
    print("\n1. ASCII 可视化:")
    ts.visualize_ascii()
    
    # 高亮显示关键状态（两个进程都在临界区的状态 - 应该不存在）
    reachable = ts.compute_reachable_states()
    critical_states = {s for s in reachable if s.has_label("crit0") or s.has_label("crit1")}
    
    # DOT 格式（高亮临界区状态）
    print("\n2. DOT 格式 (高亮临界区状态):")
    dot = ts.visualize_dot(highlight_states=critical_states)
    print(dot)
    
    # 保存文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "example2_peterson.dot", highlight_states=critical_states)
    ts.visualize_html(OUTPUT_DIR / "example2_peterson.html")
    
    print("\n文件已生成:")
    print(f"  - {OUTPUT_DIR / 'example2_peterson.dot'}")
    print(f"  - {OUTPUT_DIR / 'example2_peterson.html'}")
    
    return ts


def example3_highlight_path():
    """示例3: 高亮显示路径"""
    print("\n" + "=" * 60)
    print("示例3: 高亮显示路径")
    print("=" * 60)
    
    ts = TransitionSystem()
    
    # 构建一个线性状态序列
    states = ["s0", "s1", "s2", "s3", "s4"]
    for s in states:
        ts.add_state(s)
    ts.add_initial_state("s0")
    
    for i in range(len(states) - 1):
        ts.add_transition(states[i], states[i+1], f"step{i}")
    
    # 添加一些分支
    ts.add_transition("s2", "s5", "branch")
    ts.add_state("s5", {"alt_end"})
    
    # 查找从 s0 到 s4 的路径
    s0 = ts.get_state("s0")
    s4 = ts.get_state("s4")
    path = ts.find_path(s0, s4)
    
    print(f"\n找到路径: {' -> '.join(s.name for s in path)}")
    
    print("\nDOT 格式 (高亮路径):")
    dot = ts.visualize_dot(highlight_path=path)
    print(dot)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "example3_path.dot", highlight_path=path)
    ts.visualize_html(OUTPUT_DIR / "example3_path.html")
    
    print("\n文件已生成:")
    print(f"  - {OUTPUT_DIR / 'example3_path.dot'}")
    print(f"  - {OUTPUT_DIR / 'example3_path.html'}")
    
    return ts


def example4_extended_ts():
    """示例4: 扩展迁移系统可视化"""
    print("\n" + "=" * 60)
    print("示例4: 扩展迁移系统")
    print("=" * 60)
    
    ts = TransitionSystem()
    
    # 创建一个循环状态机
    ts.add_state("idle", {"ready"})
    ts.add_state("working", {"busy"})
    ts.add_state("paused", {"ready"})
    
    ts.add_initial_state("idle")
    
    ts.add_transition("idle", "working", "start")
    ts.add_transition("working", "paused", "pause")
    ts.add_transition("paused", "working", "resume")
    ts.add_transition("working", "idle", "finish")
    ts.add_transition("paused", "idle", "cancel")
    
    # 使用 TransitionSystem 对象上的可视化方法
    print("\n1. ASCII 可视化:")
    ts.visualize_ascii()
    
    print("\n2. DOT 格式:")
    print(ts.visualize_dot())
    
    # 保存各种格式
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "example4_extended.dot")
    ts.visualize_html(OUTPUT_DIR / "example4_extended.html")
    
    print("\n文件已生成:")
    print(f"  - {OUTPUT_DIR / 'example4_extended.dot'}")
    print(f"  - {OUTPUT_DIR / 'example4_extended.html'}")
    
    return ts


def example5_traffic_light():
    """示例5: 交通信号灯状态机可视化"""
    print("\n" + "=" * 60)
    print("示例5: 交通信号灯状态机")
    print("=" * 60)
    
    ts = TransitionSystem()
    
    # 定义交通信号灯状态
    ts.add_state("red", {"stop"})
    ts.add_state("red_yellow", {"prepare_go"})
    ts.add_state("green", {"go"})
    ts.add_state("yellow", {"prepare_stop"})
    
    ts.add_initial_state("red")
    
    # 定义状态转换
    ts.add_transition("red", "red_yellow", "timer")
    ts.add_transition("red_yellow", "green", "timer")
    ts.add_transition("green", "yellow", "timer")
    ts.add_transition("yellow", "red", "timer")
    
    # 可视化
    print("\n交通信号灯状态机:")
    ts.visualize_ascii()
    
    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "example5_traffic.dot")
    ts.visualize_html(OUTPUT_DIR / "example5_traffic.html")
    
    print("\n文件已生成:")
    print(f"  - {OUTPUT_DIR / 'example5_traffic.dot'}")
    print(f"  - {OUTPUT_DIR / 'example5_traffic.html'}")
    
    return ts


if __name__ == "__main__":
    print("Transition System 可视化示例")
    print("=" * 60)
    print("\n本示例展示多种可视化方式:")
    print("  1. ASCII 艺术可视化")
    print("  2. Graphviz DOT 格式")
    print("  3. HTML/SVG 交互式可视化")
    print("  4. 状态高亮和路径高亮")
    print("  5. 扩展方法集成")
    print()
    
    # 运行所有示例
    example1_simple_ts()
    example2_peterson_visualization()
    example3_highlight_path()
    example4_extended_ts()
    example5_traffic_light()
    
    print("\n" + "=" * 60)
    print("所有示例完成!")
    print("=" * 60)
    print(f"\n生成的可视化文件 (位于 {OUTPUT_DIR}):")
    print("  DOT 文件可以用 Graphviz 渲染:")
    print("    dot -Tpng example1_simple.dot -o example1_simple.png")
    print("  HTML 文件可以直接在浏览器中打开查看")
    print("\n注意: 如果需要 Matplotlib 可视化，请安装:")
    print("  pip install matplotlib networkx")
