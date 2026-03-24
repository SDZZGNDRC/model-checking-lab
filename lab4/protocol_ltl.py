"""
实验四：通信协议 LTL 验证示例

本模块演示如何使用 LTL 模型检查验证通信协议。

验证的属性：
1. □(send → ♦ack)（发送后最终收到确认）- 响应属性
2. □♦send（无限经常发送）- 活性属性

包含两个版本的协议模型：
- 正常版本：满足所有 LTL 属性
- 错误版本：可能发送但不收到确认，违反响应属性
"""

import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from transition_system import TransitionSystem, State
from nba import NBA
from ltl_formula import (
    atom, neg, globally, eventually, implies,
    always_eventually, implies_eventually, ltl_to_nba
)
from ltl_model_checker import LTLModelChecker, check_ltl_property
from nba import NBA

# 导入 NFAVisualizer 用于 NBA 可视化（NBA 与 NFA 结构兼容）
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab3')
from nfa_visualizer import NFAVisualizer

# 可视化输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visualization"


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
    
    print(f"  DOT 文件: {dot_path}")
    print(f"  HTML 文件: {html_path}")
    
    return dot_path, html_path


def visualize_nba_with_details(nba: NBA, filename_prefix: str, title: str):
    """
    可视化 NBA 并生成多种格式
    
    Args:
        nba: 要可视化的 NBA
        filename_prefix: 文件名前缀
        title: 可视化标题
    """
    viz = NFAVisualizer(nba)
    
    # 保存 DOT 格式
    dot_path = OUTPUT_DIR / f"{filename_prefix}.dot"
    viz.save_dot(str(dot_path))
    
    # 保存 HTML 格式
    html_path = OUTPUT_DIR / f"{filename_prefix}.html"
    viz.save_html(str(html_path), title=title)
    
    # 打印 ASCII 可视化
    print(f"\n【{title} - ASCII 结构图】")
    viz.print_ascii()
    
    print(f"  DOT 文件: {dot_path}")
    print(f"  HTML 文件: {html_path}")
    
    return dot_path, html_path


def create_protocol_ts_correct() -> TransitionSystem:
    """
    创建正确的通信协议 Transition System
    
    状态序列：
    - idle（空闲）
    - send（发送）
    - wait_ack（等待确认）
    - ack_received（收到确认）-> 回到 idle
    
    确保每次发送后最终收到确认
    """
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("idle", {"idle"})
    ts.add_state("send", {"send"})
    ts.add_state("wait_ack", {"wait_ack"})
    ts.add_state("ack_received", {"ack"})
    
    # 设置初始状态
    ts.add_initial_state("idle")
    
    # 添加迁移
    ts.add_transition("idle", "send", "start_send")
    ts.add_transition("send", "wait_ack", "send_msg")
    ts.add_transition("wait_ack", "ack_received", "recv_ack")
    ts.add_transition("ack_received", "idle", "process_done")
    
    # 注意：为了简化模型检查，我们不添加重传机制
    # 这样可以确保每次 send 后必然到达 ack
    
    return ts


def create_protocol_ts_violation() -> TransitionSystem:
    """
    创建违反 LTL 属性的通信协议
    
    错误：发送后可能永远等待确认（丢包）
    违反属性：□(send → ♦ack)
    """
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("idle", {"idle"})
    ts.add_state("send", {"send"})
    ts.add_state("wait_ack", {"wait_ack"})
    ts.add_state("ack_received", {"ack"})
    
    # 设置初始状态
    ts.add_initial_state("idle")
    
    # 添加迁移
    ts.add_transition("idle", "send", "start_send")
    ts.add_transition("send", "wait_ack", "send_msg")
    
    # 错误：wait_ack 可以自环（丢包，永远等待）
    ts.add_transition("wait_ack", "wait_ack", "packet_lost")
    
    # 也可能正常收到确认
    ts.add_transition("wait_ack", "ack_received", "recv_ack")
    ts.add_transition("ack_received", "idle", "process_done")
    
    return ts


def create_protocol_ts_no_ack() -> TransitionSystem:
    """
    创建永远收不到确认的协议
    
    用于测试 □(send → ♦ack) 的失败情况
    """
    ts = TransitionSystem()
    
    # 添加状态（没有 ack_received）
    ts.add_state("idle", {"idle"})
    ts.add_state("send", {"send"})
    ts.add_state("wait_ack", {"wait_ack"})
    
    # 设置初始状态
    ts.add_initial_state("idle")
    
    # 添加迁移（永远不到 ack）
    ts.add_transition("idle", "send", "start_send")
    ts.add_transition("send", "wait_ack", "send_msg")
    ts.add_transition("wait_ack", "wait_ack", "wait")  # 永远等待
    
    return ts


def build_nba_neg_always_eventually_send() -> NBA:
    """
    构造否定公式 ¬(□♦send) ≡ ♦□¬send 的 NBA
    
    接受所有最终永远不再发送的运行
    """
    nba = NBA()
    
    # q0：初始+接受状态（等待 send）
    q0 = nba.add_state("q0", is_initial=True, is_accept=True)
    # q1：死状态（已经读到 send）
    q1 = nba.add_state("q1")
    
    # 在 q0：
    # - 没有读到 send，保持在接受状态
    nba.add_transition("q0", "q0", "idle")
    nba.add_transition("q0", "q0", "wait_ack")
    nba.add_transition("q0", "q0", "ack")
    # - 读到 send，进入死状态
    nba.add_transition("q0", "q1", "send")
    
    # 在 q1：自环（死状态）
    nba.add_transition("q1", "q1", "idle")
    nba.add_transition("q1", "q1", "send")
    nba.add_transition("q1", "q1", "wait_ack")
    nba.add_transition("q1", "q1", "ack")
    
    return nba


def build_nba_neg_response_send_ack() -> NBA:
    """
    构造否定公式 ¬□(send → ♦ack) ≡ ♦(send ∧ □¬ack) 的 NBA
    
    接受存在某个 send 后永远不到 ack 的运行
    
    NBA 构造思路：
    - q0：初始状态（监视中）
    - q1：已检测到 send，等待确认是否永远不到 ack
    - q2：接受状态（确认：存在 send 后永远不到 ack）
    """
    nba = NBA()
    
    # q0：初始状态（等待 send）
    q0 = nba.add_state("q0", is_initial=True)
    # q1：已读到 send，正在监视后续是否 ack
    q1 = nba.add_state("q1")
    # q2：接受状态（send 后确认永远不到 ack）
    q2 = nba.add_state("q2", is_accept=True)
    
    # 在 q0：等待 send
    nba.add_transition("q0", "q0", "idle")
    nba.add_transition("q0", "q0", "wait_ack")
    nba.add_transition("q0", "q0", "ack")
    nba.add_transition("q0", "q1", "send")
    
    # 在 q1：已读到 send，检查后续
    # - 如果 ack，义务完成，回到 q0
    nba.add_transition("q1", "q0", "ack")
    # - 如果没有 ack，保持在 q1（继续监视）
    nba.add_transition("q1", "q1", "idle")
    nba.add_transition("q1", "q1", "wait_ack")
    nba.add_transition("q1", "q1", "send")
    # - 如果确定永远不到 ack（进入接受循环）
    # 从 q1 到 q2 表示"确认"send 后永远不到 ack
    # 这需要通过嵌套 DFS 检测 q1 中的循环
    nba.add_transition("q1", "q2", "idle")
    nba.add_transition("q1", "q2", "wait_ack")
    
    # 在 q2：接受状态（永远不到 ack）
    nba.add_transition("q2", "q2", "idle")
    nba.add_transition("q2", "q2", "wait_ack")
    nba.add_transition("q2", "q2", "send")
    
    return nba


def demo_protocol_ltl():
    """演示通信协议 LTL 属性验证"""
    
    print("=" * 70)
    print("实验四：LTL 模型检查 - 通信协议示例")
    print("=" * 70)
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # ====== 测试 1：正确的协议 ======
    print("\n【测试 1】正确的通信协议模型")
    print("-" * 50)
    
    ts_correct = create_protocol_ts_correct()
    ts_correct.print_reachable_graph()
    
    # 可视化正确的协议 TS
    visualize_ts_with_details(ts_correct, "lab4_protocol_correct_ts", 
                              "通信协议迁移系统（正确版本）")
    
    # 验证属性：□(send → ♦ack)
    print("\n验证属性：'□(send → ♦ack)'（发送后最终收到确认）")
    
    nba_neg_response = build_nba_neg_response_send_ack()
    print("\n否定公式 NBA 结构：")
    nba_neg_response.print_structure()
    
    # 可视化否定公式的 NBA
    visualize_nba_with_details(nba_neg_response, "lab4_nba_neg_response", 
                               "否定公式 NBA: ¬□(send → ♦ack)")
    
    checker = LTLModelChecker(ts_correct)
    result1 = checker.check(nba_neg_response, "□(send → ♦ack)")
    
    print(f"\n  结果: {result1}")
    if result1.holds:
        print("  ✓ 属性成立！（发送后最终收到确认）")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result1.counterexample)}")
        if result1.counterexample_loop:
            print(f"  循环部分: {' -> '.join(s.name for s in result1.counterexample_loop)}")
    
    # ====== 测试 2：违反响应属性的协议 ======
    print("\n" + "=" * 70)
    print("【测试 2】违反响应属性的协议（可能永远等待确认）")
    print("-" * 50)
    
    ts_violation = create_protocol_ts_violation()
    ts_violation.print_reachable_graph()
    
    # 可视化违反响应属性的协议 TS
    visualize_ts_with_details(ts_violation, "lab4_protocol_violation_ts", 
                              "通信协议迁移系统（违反响应属性版本）")
    
    print("\n验证属性：'□(send → ♦ack)'（发送后最终收到确认）")
    
    checker2 = LTLModelChecker(ts_violation)
    result2 = checker2.check(nba_neg_response, "□(send → ♦ack)")
    
    print(f"\n  结果: {result2}")
    if result2.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径前缀: {' -> '.join(s.name for s in result2.counterexample)}")
        if result2.counterexample_loop:
            print(f"  循环部分: {' -> '.join(s.name for s in result2.counterexample_loop)}")
            print("  这意味着协议可以无限发送但不收到确认！")
    
    # ====== 测试 3：永远收不到确认的协议 ======
    print("\n" + "=" * 70)
    print("【测试 3】永远收不到确认的协议模型")
    print("-" * 50)
    
    ts_no_ack = create_protocol_ts_no_ack()
    ts_no_ack.print_reachable_graph()
    
    # 可视化永远收不到确认的协议 TS
    visualize_ts_with_details(ts_no_ack, "lab4_protocol_no_ack_ts", 
                              "通信协议迁移系统（永远无确认版本）")
    
    print("\n验证属性：'□(send → ♦ack)'（发送后最终收到确认）")
    
    checker3 = LTLModelChecker(ts_no_ack)
    result3 = checker3.check(nba_neg_response, "□(send → ♦ack)")
    
    print(f"\n  结果: {result3}")
    if result3.holds:
        print("  ✓ 属性成立！")
    else:
        print("  ✗ 属性被违反！")
        print(f"  反例路径: {' -> '.join(s.name for s in result3.counterexample)}")
        if result3.counterexample_loop:
            print(f"  循环部分: {' -> '.join(s.name for s in result3.counterexample_loop)}")
    
    # ====== 测试 4：活性属性 □♦send ======
    print("\n" + "=" * 70)
    print("【测试 4】活性属性：□♦send（无限经常发送）")
    print("-" * 50)
    
    nba_neg_always_eventually = build_nba_neg_always_eventually_send()
    print("\n否定公式 NBA 结构：")
    nba_neg_always_eventually.print_structure()
    
    # 可视化否定活性公式的 NBA
    visualize_nba_with_details(nba_neg_always_eventually, "lab4_nba_neg_always_eventually", 
                               "否定公式 NBA: ¬□♦send")
    
    print("\n验证正确协议...")
    result4a = checker.check(nba_neg_always_eventually, "□♦send")
    print(f"  结果: {'✓ 通过' if result4a.holds else '✗ 失败'}")
    if not result4a.holds:
        print(f"  反例: {' -> '.join(s.name for s in result4a.counterexample)}")
        if result4a.counterexample_loop:
            print(f"  循环: {' -> '.join(s.name for s in result4a.counterexample_loop)}")
    
    # 创建一个可能永远空闲的协议
    ts_idle = TransitionSystem()
    ts_idle.add_state("idle", {"idle"})
    ts_idle.add_state("send", {"send"})
    ts_idle.add_initial_state("idle")
    ts_idle.add_transition("idle", "send", "start")
    ts_idle.add_transition("send", "idle", "done")
    # 添加自环：可能永远停留在 idle
    ts_idle.add_transition("idle", "idle", "wait")
    
    # 可视化可能永远空闲的协议 TS
    visualize_ts_with_details(ts_idle, "lab4_protocol_idle_ts", 
                              "通信协议迁移系统（可能永远空闲版本）")
    
    print("\n验证可能永远空闲的协议...")
    checker4 = LTLModelChecker(ts_idle)
    result4b = checker4.check(nba_neg_always_eventually, "□♦send")
    print(f"  结果: {'✓ 通过' if result4b.holds else '✗ 检测到违反'}")
    if not result4b.holds:
        print(f"  反例: {' -> '.join(s.name for s in result4b.counterexample)}")
        if result4b.counterexample_loop:
            print(f"  循环: {' -> '.join(s.name for s in result4b.counterexample_loop)}")
            print("  这意味着协议可以永远停留在空闲状态！")
    
    # ====== 总结 ======
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    print(f"1. 正确协议 (□(send→♦ack)):     {'✓ 通过' if result1.holds else '✗ 失败'}")
    print(f"2. 可能丢包协议 (□(send→♦ack)): {'✓ 通过' if result2.holds else '✗ 检测到违反'}")
    print(f"3. 永远无确认 (□(send→♦ack)):   {'✓ 通过' if result3.holds else '✗ 检测到违反'}")
    print(f"4. 正确协议 (□♦send):           {'✓ 通过' if result4a.holds else '✗ 失败'}")
    print(f"5. 可能空闲协议 (□♦send):       {'✓ 通过' if result4b.holds else '✗ 检测到违反'}")
    print("\n实验四通信协议示例完成！")


if __name__ == "__main__":
    demo_protocol_ltl()
