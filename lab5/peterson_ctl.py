"""
实验五：Peterson 算法的 CTL 验证示例

本模块使用 CTL 模型检查验证 Peterson 互斥算法的性质：
1. 互斥性：∀□(¬crit₁ ∨ ¬crit₂)
2. 无饥饿：∀□(wait₁ → ∀◇crit₁)

基于实验一和实验二的 Peterson 算法实现。
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab2')

from typing import Tuple, Optional

from transition_system import TransitionSystem, State
from ctl_formula import (
    CTLFormula, atom, neg, conj, disj, implies,
    ag, af, ef, eg, ex, eu, mutual_exclusion, no_starvation
)
from ctl_model_checker import CTLModelChecker, CTLCheckResult


def create_peterson_ts(simplified: bool = False) -> TransitionSystem:
    """
    创建 Peterson 算法的迁移系统
    
    状态变量：
    - pc0, pc1: 进程 0 和 1 的程序计数器
    - turn: 轮到哪个进程 (0 或 1)
    - b0, b1: 进程 0 和 1 的兴趣标志
    
    Args:
        simplified: 如果为 True，创建简化版本（状态更少）
        
    Returns:
        Peterson 算法的 Transition System
    """
    ts = TransitionSystem()
    
    if simplified:
        # 简化版本：只关注关键状态
        # 状态: (pc0, pc1, turn, b0, b1)
        # pc: 0=非临界区, 1=等待, 2=临界区
        
        states = [
            # (pc0, pc1, turn) 格式，b0=(pc0>0), b1=(pc1>0)
            ("s00_0", 0, 0, 0),   # 都在非临界区，turn=0
            ("s00_1", 0, 0, 1),   # 都在非临界区，turn=1
            ("s10_0", 1, 0, 0),   # P0等待，P1非临界，turn=0
            ("s10_1", 1, 0, 1),   # P0等待，P1非临界，turn=1
            ("s01_0", 0, 1, 0),   # P0非临界，P1等待，turn=0
            ("s01_1", 0, 1, 1),   # P0非临界，P1等待，turn=1
            ("s11_0", 1, 1, 0),   # 都等待，turn=0
            ("s11_1", 1, 1, 1),   # 都等待，turn=1
            ("s20_0", 2, 0, 0),   # P0临界，P1非临界，turn=0
            ("s20_1", 2, 0, 1),   # P0临界，P1非临界，turn=1
            ("s02_0", 0, 2, 0),   # P0非临界，P1临界，turn=0
            ("s02_1", 0, 2, 1),   # P0非临界，P1临界，turn=1
        ]
        
        # 添加状态并设置标签
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
            if pc0 > 0:
                labels.add("b0")
            if pc1 > 0:
                labels.add("b1")
            ts.add_state(name, labels)
        
        # 设置初始状态
        ts.add_initial_state("s00_0")
        ts.add_initial_state("s00_1")
        
        # 添加迁移（简化版：基于 Peterson 算法逻辑）
        # P0 从非临界区到等待区
        ts.add_transition("s00_0", "s10_0", "P0_request")
        ts.add_transition("s00_1", "s10_1", "P0_request")
        ts.add_transition("s02_0", "s12_0", "P0_request")  # P1在临界区，P0请求
        ts.add_transition("s02_1", "s12_1", "P0_request")
        
        # P1 从非临界区到等待区
        ts.add_transition("s00_0", "s01_0", "P1_request")
        ts.add_transition("s00_1", "s01_1", "P1_request")
        ts.add_transition("s20_0", "s21_0", "P1_request")  # P0在临界区，P1请求
        ts.add_transition("s20_1", "s21_1", "P1_request")
        
        # 添加更多迁移...
        # P0 从等待区进入临界区（当 turn=0 或 !b1）
        ts.add_transition("s10_0", "s20_0", "P0_enter")
        ts.add_transition("s11_0", "s21_0", "P0_enter")  # turn=0，P0优先
        
        # P1 从等待区进入临界区（当 turn=1 或 !b0）
        ts.add_transition("s01_1", "s02_1", "P1_enter")
        ts.add_transition("s11_1", "s12_1", "P1_enter")  # turn=1，P1优先
        
        # P0 离开临界区
        ts.add_transition("s20_0", "s00_1", "P0_exit")  # turn设为1
        ts.add_transition("s20_1", "s00_0", "P0_exit")  # turn设为0
        
        # P1 离开临界区
        ts.add_transition("s02_0", "s00_1", "P1_exit")
        ts.add_transition("s02_1", "s00_0", "P1_exit")
        
    else:
        # 完整版本
        _create_full_peterson_ts(ts)
    
    return ts


def _create_full_peterson_ts(ts: TransitionSystem):
    """创建完整的 Peterson 算法迁移系统"""
    # 状态空间：(pc0, pc1, turn, b0, b1)
    # pc: 0=nc, 1=wait, 2=crit
    
    for pc0 in range(3):
        for pc1 in range(3):
            for turn in [0, 1]:
                b0 = 1 if pc0 > 0 else 0
                b1 = 1 if pc1 > 0 else 0
                
                name = f"s{pc0}{pc1}_{turn}"
                labels = set()
                
                if pc0 == 1:
                    labels.add("wait0")
                if pc0 == 2:
                    labels.add("crit0")
                if pc1 == 1:
                    labels.add("wait1")
                if pc1 == 2:
                    labels.add("crit1")
                if b0:
                    labels.add("b0")
                if b1:
                    labels.add("b1")
                
                ts.add_state(name, labels)
    
    # 初始状态
    ts.add_initial_state("s00_0")
    ts.add_initial_state("s00_1")
    
    # 添加所有可能的迁移
    for pc0 in range(3):
        for pc1 in range(3):
            for turn in [0, 1]:
                state = f"s{pc0}{pc1}_{turn}"
                b0 = 1 if pc0 > 0 else 0
                b1 = 1 if pc1 > 0 else 0
                
                # P0 的迁移
                if pc0 == 0:
                    # 请求进入
                    ts.add_transition(state, f"s1{pc1}_{turn}", "P0_request")
                elif pc0 == 1:
                    # 尝试进入临界区
                    if turn == 0 or b1 == 0:
                        ts.add_transition(state, f"s2{pc1}_{turn}", "P0_enter")
                elif pc0 == 2:
                    # 离开临界区
                    new_turn = 1
                    ts.add_transition(state, f"s0{pc1}_{new_turn}", "P0_exit")
                
                # P1 的迁移
                if pc1 == 0:
                    # 请求进入
                    ts.add_transition(state, f"s{pc0}1_{turn}", "P1_request")
                elif pc1 == 1:
                    # 尝试进入临界区
                    if turn == 1 or b0 == 0:
                        ts.add_transition(state, f"s{pc0}2_{turn}", "P1_enter")
                elif pc1 == 2:
                    # 离开临界区
                    new_turn = 0
                    ts.add_transition(state, f"s{pc0}0_{new_turn}", "P1_exit")


def check_peterson_mutual_exclusion(ts: TransitionSystem) -> CTLCheckResult:
    """
    检查 Peterson 算法的互斥属性
    
    公式：∀□(¬crit₁ ∨ ¬crit₂)
    即：所有路径上所有状态都不满足 crit1 和 crit2 同时成立
    
    Args:
        ts: Peterson 算法的 Transition System
        
    Returns:
        CTLCheckResult 对象
    """
    print("=" * 60)
    print("检查 Peterson 算法的互斥属性")
    print("公式: ∀□(¬crit₁ ∨ ¬crit₂)")
    print("=" * 60)
    
    checker = CTLModelChecker(ts)
    
    # 构建公式：AG(!crit1 | !crit2)
    formula = ag(disj(neg(atom("crit1")), neg(atom("crit2"))))
    
    result = checker.check(formula)
    
    print(f"\n结果: {'✓ 满足' if result.holds else '✗ 不满足'}")
    print(f"满足公式的状态数: {len(result.satisfying_states)}")
    print(f"固定点迭代次数: {result.iterations}")
    
    if not result.holds:
        print(f"\n反例路径:")
        if result.counterexample_path:
            path_str = " -> ".join(s.name for s in result.counterexample_path)
            print(f"  {path_str}")
            
            # 显示路径上每个状态的标签
            print("\n路径状态详情:")
            for state in result.counterexample_path:
                labels = ", ".join(sorted(state.labels)) if state.labels else "无"
                print(f"  {state.name}: [{labels}]")
    
    print()
    return result


def check_peterson_no_starvation(ts: TransitionSystem, 
                                  process_id: int = 0) -> CTLCheckResult:
    """
    检查 Peterson 算法的无饥饿属性
    
    公式：∀□(waitᵢ → ∀◇critᵢ)
    即：所有路径上，如果进程 i 处于 wait 状态，则最终一定能进入 crit 状态
    
    Args:
        ts: Peterson 算法的 Transition System
        process_id: 进程 ID (0 或 1)
        
    Returns:
        CTLCheckResult 对象
    """
    print("=" * 60)
    print(f"检查 Peterson 算法进程 {process_id} 的无饥饿属性")
    print(f"公式: ∀□(wait{process_id} → ∀◇crit{process_id})")
    print("=" * 60)
    
    checker = CTLModelChecker(ts)
    
    # 构建公式：AG(wait_i -> AF(crit_i))
    wait_atom = atom(f"wait{process_id}")
    crit_atom = atom(f"crit{process_id}")
    formula = ag(implies(wait_atom, af(crit_atom)))
    
    result = checker.check(formula)
    
    print(f"\n结果: {'✓ 满足' if result.holds else '✗ 不满足'}")
    print(f"满足公式的状态数: {len(result.satisfying_states)}")
    print(f"固定点迭代次数: {result.iterations}")
    
    if not result.holds:
        print(f"\n反例路径:")
        if result.counterexample_path:
            path_str = " -> ".join(s.name for s in result.counterexample_path)
            print(f"  {path_str}")
            
            print("\n路径状态详情:")
            for state in result.counterexample_path:
                labels = ", ".join(sorted(state.labels)) if state.labels else "无"
                print(f"  {state.name}: [{labels}]")
    
    print()
    return result


def check_peterson_reachability(ts: TransitionSystem, 
                                 target: str = "crit0") -> CTLCheckResult:
    """
    检查可达性属性
    
    公式：∃◇target
    即：存在一条路径能到达目标状态
    
    Args:
        ts: Transition System
        target: 目标状态标签
        
    Returns:
        CTLCheckResult 对象
    """
    print("=" * 60)
    print(f"检查可达性属性")
    print(f"公式: ∃◇{target}")
    print("=" * 60)
    
    checker = CTLModelChecker(ts)
    
    # 构建公式：EF(target)
    formula = ef(atom(target))
    
    result = checker.check(formula)
    
    print(f"\n结果: {'✓ 满足' if result.holds else '✗ 不满足'}")
    print(f"满足公式的状态数: {len(result.satisfying_states)}")
    print(f"固定点迭代次数: {result.iterations}")
    
    if result.holds:
        print(f"\n从初始状态可以到达带有 '{target}' 标签的状态")
        print("满足状态:", [s.name for s in result.satisfying_states])
    
    print()
    return result


def check_peterson_safety(ts: TransitionSystem) -> CTLCheckResult:
    """
    检查安全性属性（所有状态都满足某种不变式）
    
    公式：∀□(¬(crit₀ ∧ crit₁))
    即：永远不会同时进入临界区
    
    Args:
        ts: Transition System
        
    Returns:
        CTLCheckResult 对象
    """
    print("=" * 60)
    print("检查安全性属性")
    print("公式: ∀□(¬(crit₀ ∧ crit₁))")
    print("=" * 60)
    
    checker = CTLModelChecker(ts)
    
    # 构建公式：AG(!(crit0 & crit1))
    formula = ag(neg(conj(atom("crit0"), atom("crit1"))))
    
    result = checker.check(formula)
    
    print(f"\n结果: {'✓ 满足' if result.holds else '✗ 不满足'}")
    print(f"满足公式的状态数: {len(result.satisfying_states)}")
    print(f"固定点迭代次数: {result.iterations}")
    
    print()
    return result


def demonstrate_eu_computation(ts: TransitionSystem):
    """
    演示 EU 算子的计算过程
    
    计算 E[wait0 U crit0] 的满足集，并与手工计算结果对比
    """
    print("=" * 60)
    print("演示 EU 算子计算: E[wait0 U crit0]")
    print("=" * 60)
    
    checker = CTLModelChecker(ts)
    
    # 构建公式：E[wait0 U crit0]
    formula = eu(atom("wait0"), atom("crit0"))
    
    result = checker.check(formula)
    
    print(f"\n满足 E[wait0 U crit0] 的状态:")
    for state in sorted(result.satisfying_states, key=lambda s: s.name):
        labels = ", ".join(sorted(state.labels)) if state.labels else "无"
        print(f"  {state.name}: [{labels}]")
    
    print(f"\n固定点迭代次数: {result.iterations}")
    
    # 解释
    print("\n解释:")
    print("  E[wait0 U crit0] 表示：存在一条路径，")
    print("  从当前状态开始，沿着 wait0 状态前进，")
    print("  最终到达 crit0 状态。")
    print()


def run_all_checks():
    """运行所有 Peterson 算法的 CTL 验证"""
    print("\n" + "=" * 60)
    print("Peterson 算法 CTL 模型检查")
    print("=" * 60 + "\n")
    
    # 创建 Peterson 算法的迁移系统（简化版）
    print("创建 Peterson 算法的迁移系统（简化版）...\n")
    ts = create_peterson_ts(simplified=True)
    
    # 打印迁移系统信息
    stats = ts.get_statistics()
    print(f"迁移系统统计:")
    print(f"  总状态数: {stats['total_states']}")
    print(f"  可达状态数: {stats['reachable_states']}")
    print(f"  初始状态数: {stats['initial_states']}")
    print(f"  迁移数: {stats['reachable_transitions']}")
    print()
    
    # 1. 检查互斥属性
    result_mutex = check_peterson_mutual_exclusion(ts)
    
    # 2. 检查无饥饿属性（进程 0）
    result_starvation_0 = check_peterson_no_starvation(ts, process_id=0)
    
    # 3. 检查无饥饿属性（进程 1）
    result_starvation_1 = check_peterson_no_starvation(ts, process_id=1)
    
    # 4. 检查可达性
    result_reach = check_peterson_reachability(ts, target="crit0")
    
    # 5. 检查安全性
    result_safety = check_peterson_safety(ts)
    
    # 6. 演示 EU 计算
    demonstrate_eu_computation(ts)
    
    # 总结
    print("=" * 60)
    print("验证结果总结")
    print("=" * 60)
    print(f"1. 互斥性 (AG(!crit1 | !crit2)): {'✓' if result_mutex.holds else '✗'}")
    print(f"2. 无饥饿性 P0 (AG(wait0 -> AF(crit0))): {'✓' if result_starvation_0.holds else '✗'}")
    print(f"3. 无饥饿性 P1 (AG(wait1 -> AF(crit1))): {'✓' if result_starvation_1.holds else '✗'}")
    print(f"4. 可达性 (EF(crit0)): {'✓' if result_reach.holds else '✗'}")
    print(f"5. 安全性 (AG(!(crit0 & crit1))): {'✓' if result_safety.holds else '✗'}")
    print("=" * 60)


if __name__ == "__main__":
    run_all_checks()
