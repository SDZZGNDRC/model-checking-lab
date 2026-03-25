"""
实验七：偏序归约 LTL\X 验证器

本模块实现基于偏序归约的 LTL\X 模型检查，验证简化后的迁移系统
与原系统在 LTL\X 公式上的等价性。

LTL\X 表示不含 next 算子的 LTL，偏序归约保持 LTL\X 公式的真值。
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab4')

from typing import Set, Dict, List, Tuple, Optional
from dataclasses import dataclass

from transition_system import TransitionSystem, State
from nba import NBA
from ltl_model_checker import LTLModelChecker, LTLCheckResult
from action_dependency import ActionDependency
from por_transition_system import PORTransitionSystemBuilder, PORStatistics


@dataclass
class PORLTLResult:
    """
    偏序归约 LTL 验证结果
    
    Attributes:
        full_result: 完整 TS 上的验证结果
        reduced_result: 简化 TS 上的验证结果
        equivalent: 两个结果是否等价
        statistics: 偏序归约统计信息
    """
    full_result: LTLCheckResult
    reduced_result: LTLCheckResult
    equivalent: bool
    statistics: PORStatistics
    
    def __repr__(self) -> str:
        status = "等价" if self.equivalent else "不等价"
        return (f"PORLTLResult(\n"
                f"  状态: {status}\n"
                f"  完整TS结果: {self.full_result.holds}\n"
                f"  简化TS结果: {self.reduced_result.holds}\n"
                f"  状态减少率: {self.statistics.state_reduction_rate:.1%}\n"
                f")")


class PORLTLChecker:
    """
    偏序归约 LTL 模型检查器
    
    对比完整状态空间和简化状态空间的 LTL 验证结果，
    验证偏序归约的正确性。
    """
    
    def __init__(self):
        self._builder = PORTransitionSystemBuilder()
    
    def check_with_comparison(self, pg,
                              dependency_analyzer: ActionDependency,
                              nba_neg_formula: NBA,
                              visible_vars: Set[str],
                              property_description: str = "") -> PORLTLResult:
        """
        检查 LTL 公式，并对比完整展开和偏序归约的结果
        
        Args:
            pg: 程序图
            dependency_analyzer: 动作依赖分析器
            nba_neg_formula: 公式否定的 NBA
            visible_vars: 可见变量集合
            property_description: 属性描述
            
        Returns:
            PORLTLResult 对象
        """
        # 对比展开
        full_ts, reduced_ts, stats = self._builder.compare_with_full_exploration(
            pg, dependency_analyzer, visible_vars
        )
        
        # 在完整 TS 上验证
        checker_full = LTLModelChecker(full_ts)
        result_full = checker_full.check(nba_neg_formula, property_description)
        
        # 在简化 TS 上验证
        checker_reduced = LTLModelChecker(reduced_ts)
        result_reduced = checker_reduced.check(nba_neg_formula, property_description)
        
        # 检查等价性
        equivalent = (result_full.holds == result_reduced.holds)
        
        return PORLTLResult(
            full_result=result_full,
            reduced_result=result_reduced,
            equivalent=equivalent,
            statistics=stats
        )
    
    def verify_por_correctness(self, pg,
                                dependency_analyzer: ActionDependency,
                                test_formulas: List[Tuple[NBA, Set[str], str]]) -> Dict[str, any]:
        """
        验证偏序归约的正确性
        
        对多个 LTL\X 公式验证完整 TS 和简化 TS 的结果是否一致。
        
        Args:
            pg: 程序图
            dependency_analyzer: 动作依赖分析器
            test_formulas: 测试公式列表，每项为 (NBA, 可见变量, 描述)
            
        Returns:
            验证结果字典
        """
        results = []
        all_equivalent = True
        
        for nba, visible_vars, description in test_formulas:
            result = self.check_with_comparison(
                pg, dependency_analyzer, nba, visible_vars, description
            )
            results.append({
                "formula": description,
                "equivalent": result.equivalent,
                "full_holds": result.full_result.holds,
                "reduced_holds": result.reduced_result.holds,
                "state_reduction": result.statistics.state_reduction_rate
            })
            
            if not result.equivalent:
                all_equivalent = False
        
        return {
            "all_equivalent": all_equivalent,
            "results": results
        }


def build_simple_ltl_nba_always(property_name: str) -> NBA:
    """
    构造简单的 "□property"（总是 property）NBA
    
    这是一个简化实现，用于测试。
    实际应该使用 ltl_formula 模块的转换功能。
    """
    nba = NBA()
    
    # q0: 初始+接受状态
    q0 = nba.add_state("q0", is_initial=True, is_accept=True)
    
    # 自环：必须始终满足 property
    nba.add_transition("q0", "q0", property_name)
    
    return nba


def build_simple_ltl_nba_never(property_name: str) -> NBA:
    """
    构造简单的 "□¬property"（永不 property）NBA
    
    用于检查某个属性永远不成立（如互斥）。
    """
    nba = NBA()
    
    # q0: 初始+接受状态（没有读到 property）
    q0 = nba.add_state("q0", is_initial=True, is_accept=True)
    
    # q1: 非接受状态（读到了 property，违反性质）
    q1 = nba.add_state("q1", is_accept=False)
    
    # q0 --property--> q1（违反）
    nba.add_transition("q0", "q1", property_name)
    
    return nba


if __name__ == "__main__":
    print("=" * 60)
    print("偏序归约 LTL\X 验证器测试")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
    from program_graph import ProgramGraph, Action as PGAction
    from action_dependency import Action
    
    # 创建双计数器程序图
    pg = ProgramGraph("TwoCounters")
    pg.declare_variable("count0", {0, 1, 2}, 0, is_shared=False)
    pg.declare_variable("count1", {0, 1, 2}, 0, is_shared=False)
    pg.add_location("start")
    pg.set_initial_location("start")
    pg.add_transition("start", "start", PGAction("inc0", {"count0": "(count0 + 1) % 3"}))
    pg.add_transition("start", "start", PGAction("inc1", {"count1": "(count1 + 1) % 3"}))
    
    # 创建依赖分析器
    analyzer = ActionDependency()
    action0 = Action("inc0", 0, frozenset(), frozenset({"count0"}))
    action1 = Action("inc1", 1, frozenset(), frozenset({"count1"}))
    analyzer.register_actions([action0, action1])
    
    # 测试 LTL 公式：□(count0 < 3)
    print("\n【测试】LTL 公式: □(count0 < 3)")
    
    # 构造 NBA（简化实现）
    nba = build_simple_ltl_nba_always("count0=0")
    
    # 执行验证
    checker = PORLTLChecker()
    visible_vars = {"count0"}
    
    result = checker.check_with_comparison(
        pg, analyzer, nba, visible_vars, "□(count0=0)"
    )
    
    print(f"\n结果: {result}")
    
    if result.equivalent:
        print("\n✓ 偏序归约保持 LTL\X 公式真值！")
    else:
        print("\n✗ 偏序归约未能保持 LTL\X 公式真值！")
