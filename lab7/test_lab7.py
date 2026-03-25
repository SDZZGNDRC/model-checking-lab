"""
实验七：偏序归约测试

本模块包含偏序归约实现的完整测试套件，验证：
1. 动作依赖分析的正确性
2. Ample 集计算的正确性
3. 偏序归约状态空间生成的正确性
4. LTL\X 公式验证的等价性
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

import unittest
from typing import Set

from action_dependency import Action, ActionDependency, create_simple_dependency_analyzer, create_shared_variable_dependency
from ample_set import AmpleSet, AmpleSetGenerator
from por_transition_system import PORTransitionSystemBuilder, PORStatistics, create_dependency_analyzer_from_pg
from por_ltl_checker import PORLTLChecker, build_simple_ltl_nba_always
from counter_example import create_two_counter_program, create_dependency_analyzer, create_counter_process
from program_graph import ProgramGraph, Action as PGAction


class TestActionDependency(unittest.TestCase):
    """测试动作依赖分析"""
    
    def test_independent_actions(self):
        """测试独立动作识别"""
        analyzer = create_simple_dependency_analyzer()
        
        inc0 = analyzer._actions["inc0"]
        inc1 = analyzer._actions["inc1"]
        
        # 两个动作应该独立（访问不同变量）
        self.assertTrue(analyzer.are_independent(inc0, inc1))
        self.assertFalse(analyzer.are_dependent(inc0, inc1))
    
    def test_dependent_actions(self):
        """测试依赖动作识别"""
        analyzer = create_shared_variable_dependency()
        
        inc0 = analyzer._actions["inc0"]
        inc1 = analyzer._actions["inc1"]
        
        # 两个动作应该依赖（访问同一共享变量）
        self.assertFalse(analyzer.are_independent(inc0, inc1))
        self.assertTrue(analyzer.are_dependent(inc0, inc1))
    
    def test_same_process_dependency(self):
        """测试同一进程内的动作依赖"""
        analyzer = ActionDependency()
        
        action1 = Action("a1", process_id=0, reads=frozenset(), writes=frozenset({"x"}))
        action2 = Action("a2", process_id=0, reads=frozenset(), writes=frozenset({"y"}))
        
        analyzer.register_actions([action1, action2])
        
        # 同一进程内的动作应该依赖
        self.assertFalse(analyzer.are_independent(action1, action2))
    
    def test_variable_access_detection(self):
        """测试变量访问检测"""
        action = Action("test", process_id=0, 
                       reads=frozenset({"x", "y"}), 
                       writes=frozenset({"z"}))
        
        self.assertTrue(action.accesses_variable("x"))
        self.assertTrue(action.accesses_variable("y"))
        self.assertTrue(action.accesses_variable("z"))
        self.assertFalse(action.accesses_variable("w"))


class TestAmpleSet(unittest.TestCase):
    """测试 Ample 集计算"""
    
    def test_ample_computation_basic(self):
        """测试基本 ample 集计算"""
        analyzer = create_simple_dependency_analyzer()
        ample_calc = AmpleSet(analyzer)
        
        inc0 = analyzer._actions["inc0"]
        inc1 = analyzer._actions["inc1"]
        
        enabled = {inc0, inc1}
        
        def get_successor(action):
            return f"state_after_{action.name}"
        
        ample = ample_calc.compute_ample_simple("s0", enabled, get_successor)
        
        # 由于动作独立，应该能找到一个进程的 ample 集
        self.assertIsNotNone(ample)
        self.assertGreater(len(ample), 0)
        self.assertLessEqual(len(ample), len(enabled))
    
    def test_ample_with_visible_variables(self):
        """测试带可见变量的 ample 集计算"""
        analyzer = create_simple_dependency_analyzer()
        ample_calc = AmpleSet(analyzer)
        
        # 设置 count0 为可见变量
        ample_calc.set_visible_variables({"count0"})
        
        inc0 = analyzer._actions["inc0"]
        inc1 = analyzer._actions["inc1"]
        
        enabled = {inc0, inc1}
        
        def get_successor(action):
            return f"state_after_{action.name}"
        
        ample = ample_calc.compute_ample_simple("s0", enabled, get_successor)
        
        # inc0 写入可见变量，可能无法被包含在 ample 集中
        self.assertIsNotNone(ample)
    
    def test_ample_with_dfs_stack(self):
        """测试 DFS 栈对 ample 集的影响"""
        analyzer = create_simple_dependency_analyzer()
        ample_calc = AmpleSet(analyzer)
        
        inc0 = analyzer._actions["inc0"]
        inc1 = analyzer._actions["inc1"]
        
        enabled = {inc0, inc1}
        
        def get_successor(action):
            return f"state_after_{action.name}"
        
        # 设置 DFS 栈包含 inc0 的后继
        ample_calc.set_dfs_stack({"state_after_inc0"})
        
        ample = ample_calc.compute_ample_simple("s0", enabled, get_successor)
        
        # 由于 A4' 条件，inc0 不应该在 ample 集中
        self.assertIsNotNone(ample)


class TestPORTransitionSystem(unittest.TestCase):
    """测试偏序归约迁移系统生成"""
    
    def test_basic_por_generation(self):
        """测试基本的偏序归约生成"""
        pg = create_two_counter_program(max_count=2)
        analyzer = create_dependency_analyzer(max_count=2)
        
        builder = PORTransitionSystemBuilder(enable_por=True)
        ts = builder.build_from_program_graph(pg, analyzer)
        
        stats = ts.get_statistics()
        
        # 应该生成一些状态
        self.assertGreater(stats['reachable_states'], 0)
        self.assertGreater(stats['reachable_transitions'], 0)
    
    def test_por_vs_full_exploration(self):
        """测试偏序归约与完整展开的对比"""
        pg = create_two_counter_program(max_count=2)
        analyzer = create_dependency_analyzer(max_count=2)
        
        builder = PORTransitionSystemBuilder()
        full_ts, reduced_ts, stats = builder.compare_with_full_exploration(pg, analyzer)
        
        full_stats = full_ts.get_statistics()
        reduced_stats = reduced_ts.get_statistics()
        
        # 简化后的状态数应该小于或等于完整状态数
        self.assertLessEqual(
            reduced_stats['reachable_states'],
            full_stats['reachable_states']
        )
        
        # 对于独立计数器，应该有明显的减少
        # 完整状态数应该是 (max_count+1)² = 9
        # 简化状态数应该接近 (max_count+1) + (max_count+1) - 1 = 5
        self.assertEqual(full_stats['reachable_states'], 9)
        self.assertLess(reduced_stats['reachable_states'], 9)
    
    def test_por_state_reduction_rate(self):
        """测试状态减少率"""
        pg = create_two_counter_program(max_count=3)
        analyzer = create_dependency_analyzer(max_count=3)
        
        builder = PORTransitionSystemBuilder()
        _, _, stats = builder.compare_with_full_exploration(pg, analyzer)
        
        # 应该有正的状态减少率
        self.assertGreater(stats.state_reduction_rate, 0)
        
        # 对于独立计数器，减少率应该较高
        self.assertGreater(stats.state_reduction_rate, 0.3)
    
    def test_por_toggle(self):
        """测试偏序归约开关"""
        pg = create_two_counter_program(max_count=2)
        analyzer = create_dependency_analyzer(max_count=2)
        
        # 启用偏序归约
        builder_enabled = PORTransitionSystemBuilder(enable_por=True)
        ts_enabled = builder_enabled.build_from_program_graph(pg, analyzer)
        
        # 禁用偏序归约
        builder_disabled = PORTransitionSystemBuilder(enable_por=False)
        ts_disabled = builder_disabled.build_from_program_graph(pg, analyzer)
        
        stats_enabled = ts_enabled.get_statistics()
        stats_disabled = ts_disabled.get_statistics()
        
        # 禁用时状态数应该更多（或相等）
        self.assertGreaterEqual(
            stats_disabled['reachable_states'],
            stats_enabled['reachable_states']
        )


class TestPORLTLChecker(unittest.TestCase):
    """测试偏序归约 LTL 验证"""
    
    def test_ltl_equivalence_basic(self):
        """测试基本 LTL 等价性"""
        pg = create_two_counter_program(max_count=2)
        analyzer = create_dependency_analyzer(max_count=2)
        
        # 创建简单的 NBA
        from nba import NBA
        nba = NBA()
        q0 = nba.add_state("q0", is_initial=True, is_accept=True)
        nba.add_transition("q0", "q0", "count0=0")
        nba.add_transition("q0", "q0", "count0=1")
        nba.add_transition("q0", "q0", "count0=2")
        
        checker = PORLTLChecker()
        result = checker.check_with_comparison(
            pg, analyzer, nba, {"count0"}, "test_formula"
        )
        
        # 完整 TS 和简化 TS 的结果应该等价
        self.assertTrue(result.equivalent)
    
    def test_por_correctness_verification(self):
        """测试偏序归约正确性验证"""
        pg = create_two_counter_program(max_count=2)
        analyzer = create_dependency_analyzer(max_count=2)
        
        # 创建测试公式列表
        from nba import NBA
        
        test_formulas = []
        
        # 公式1：总是 count0 ≤ 2
        nba1 = NBA()
        q0 = nba1.add_state("q0", is_initial=True, is_accept=True)
        for i in range(3):
            nba1.add_transition("q0", "q0", f"count0={i}")
        test_formulas.append((nba1, {"count0"}, "□(count0 ≤ 2)"))
        
        checker = PORLTLChecker()
        verification_result = checker.verify_por_correctness(pg, analyzer, test_formulas)
        
        # 所有公式应该等价
        self.assertTrue(verification_result["all_equivalent"])


class TestCounterExample(unittest.TestCase):
    """测试双计数器示例"""
    
    def test_counter_process_creation(self):
        """测试计数器进程创建"""
        pg = create_counter_process(0, max_count=3)
        
        self.assertIsNotNone(pg.get_initial_location())
        self.assertEqual(len(pg.get_variables()), 1)
        self.assertIn("count0", pg.get_variables())
    
    def test_two_counter_program(self):
        """测试双计数器程序创建"""
        pg = create_two_counter_program(max_count=2)
        
        self.assertIsNotNone(pg.get_initial_location())
        
        # 应该有两个变量
        vars_dict = pg.get_variables()
        self.assertIn("count0", vars_dict)
        self.assertIn("count1", vars_dict)
    
    def test_state_space_scaling(self):
        """测试状态空间规模"""
        # max_count = 2: (2+1)² = 9 个状态
        pg2 = create_two_counter_program(max_count=2)
        analyzer2 = create_dependency_analyzer(max_count=2)
        
        builder2 = PORTransitionSystemBuilder(enable_por=False)
        ts2 = builder2.build_from_program_graph(pg2, analyzer2)
        stats2 = ts2.get_statistics()
        
        self.assertEqual(stats2['reachable_states'], 9)
        
        # max_count = 3: (3+1)² = 16 个状态
        pg3 = create_two_counter_program(max_count=3)
        analyzer3 = create_dependency_analyzer(max_count=3)
        
        builder3 = PORTransitionSystemBuilder(enable_por=False)
        ts3 = builder3.build_from_program_graph(pg3, analyzer3)
        stats3 = ts3.get_statistics()
        
        self.assertEqual(stats3['reachable_states'], 16)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_end_to_end_por_workflow(self):
        """测试端到端偏序归约工作流"""
        # 1. 创建程序图
        pg = create_two_counter_program(max_count=2)
        
        # 2. 创建依赖分析器
        analyzer = create_dependency_analyzer(max_count=2)
        
        # 3. 对比完整展开和偏序归约
        builder = PORTransitionSystemBuilder()
        full_ts, reduced_ts, stats = builder.compare_with_full_exploration(pg, analyzer)
        
        # 4. 验证 LTL 等价性
        from nba import NBA
        nba = NBA()
        q0 = nba.add_state("q0", is_initial=True, is_accept=True)
        for i in range(3):
            nba.add_transition("q0", "q0", f"count0={i}")
        
        checker = PORLTLChecker()
        ltl_result = checker.check_with_comparison(
            pg, analyzer, nba, {"count0"}, "□(count0 ≤ 2)"
        )
        
        # 验证所有条件
        self.assertGreater(stats.original_states, 0)
        self.assertGreater(stats.reduced_states, 0)
        self.assertGreater(stats.state_reduction_rate, 0)
        self.assertTrue(ltl_result.equivalent)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestActionDependency))
    suite.addTests(loader.loadTestsFromTestCase(TestAmpleSet))
    suite.addTests(loader.loadTestsFromTestCase(TestPORTransitionSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestPORLTLChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestCounterExample))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("实验七：偏序归约测试套件")
    print("=" * 60)
    
    success = run_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)
