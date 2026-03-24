"""
实验六：Bisimulation 最小化单元测试

测试内容：
1. 初始分区创建
2. 分区细化算法
3. 最小化 TS 构造
4. CTL 等价性验证
5. 边界情况处理
6. 可视化功能
"""

import sys
import os
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab5')

import unittest
from typing import Set

from transition_system import TransitionSystem, State
from bisimulation_minimizer import (
    BisimulationMinimizer, Block, MinimizationResult, minimize_transition_system
)
from ctl_formula import atom, neg, conj, disj, ag, af, ef, eu, ex
from ctl_model_checker import CTLModelChecker
from ts_visualizer import TSVisualizer

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                          'output', 'visualization')


def save_ts_visualization(ts: TransitionSystem, name: str, output_dir: str = OUTPUT_DIR):
    """保存迁移系统可视化"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成DOT文件
    dot_path = os.path.join(output_dir, f"{name}.dot")
    ts.save_dot(dot_path)
    
    # 生成HTML文件
    html_path = os.path.join(output_dir, f"{name}.html")
    ts.visualize_html(html_path)
    
    return dot_path, html_path


class TestBisimulationMinimizer(unittest.TestCase):
    """测试 Bisimulation 最小化器"""
    
    def create_simple_ts(self) -> TransitionSystem:
        """创建一个简单的测试 TS"""
        ts = TransitionSystem()
        
        # s0 -> s1, s2; s1 -> s3; s2 -> s3
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})
        ts.add_state("s2", {"b"})
        ts.add_state("s3", {"c"})
        
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s0", "s2")
        ts.add_transition("s1", "s3")
        ts.add_transition("s2", "s3")
        
        return ts
    
    def create_bisimilar_pair_ts(self) -> TransitionSystem:
        """创建有两个 Bisimilar 状态的 TS"""
        ts = TransitionSystem()
        
        # s1 和 s2 是 Bisimilar 的（相同标签，相同后继）
        ts.add_state("s0", {"start"})
        ts.add_state("s1", {"middle"})
        ts.add_state("s2", {"middle"})  # 与 s1 Bisimilar
        ts.add_state("s3", {"end"})
        
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s0", "s2")
        ts.add_transition("s1", "s3")
        ts.add_transition("s2", "s3")
        
        return ts
    
    def create_chain_ts(self) -> TransitionSystem:
        """创建链式 TS"""
        ts = TransitionSystem()
        
        for i in range(5):
            ts.add_state(f"s{i}", {f"label_{i}"})
        
        ts.add_initial_state("s0")
        
        for i in range(4):
            ts.add_transition(f"s{i}", f"s{i+1}")
        
        return ts
    
    def test_initial_partition(self):
        """测试初始分区创建"""
        ts = self.create_simple_ts()
        minimizer = BisimulationMinimizer(ts)
        
        partition = minimizer._create_initial_partition()
        
        # 应该有 3 个块（按标签 a, b, c 分组）
        self.assertEqual(len(partition), 3)
        
        # 检查每个块的大小
        block_sizes = [len(block.states) for block in partition]
        self.assertIn(1, block_sizes)  # a 标签只有 s0
        self.assertIn(2, block_sizes)  # b 标签有 s1, s2
        self.assertIn(1, block_sizes)  # c 标签只有 s3
    
    def test_partition_refinement(self):
        """测试分区细化"""
        ts = self.create_bisimilar_pair_ts()
        minimizer = BisimulationMinimizer(ts)
        
        # 创建初始分区
        initial_partition = minimizer._create_initial_partition()
        
        # 细化分区
        final_partition = minimizer._refine_partition(initial_partition)
        
        # s1 和 s2 应该被分到同一个块
        block_map = minimizer._build_block_map(final_partition)
        
        s1 = ts.get_state("s1")
        s2 = ts.get_state("s2")
        
        self.assertEqual(block_map[s1], block_map[s2])
    
    def test_minimization_result(self):
        """测试最小化结果"""
        ts = self.create_bisimilar_pair_ts()
        result = minimize_transition_system(ts)
        
        # 原始状态数: 4
        self.assertEqual(result.original_state_count, 4)
        
        # 最小化后状态数: 3 (s1 和 s2 合并)
        self.assertEqual(result.minimized_state_count, 3)
        
        # 缩减比例应该是 25%
        self.assertAlmostEqual(result.reduction_ratio, 0.25, places=2)
        
        # 生成可视化文件
        save_ts_visualization(ts, "test_lab6_original")
        save_ts_visualization(result.minimized_ts, "test_lab6_minimized")
    
    def test_minimized_ts_structure(self):
        """测试最小化 TS 的结构"""
        ts = self.create_simple_ts()
        result = minimize_transition_system(ts)
        
        minimized_ts = result.minimized_ts
        
        # 检查最小化 TS 的基本属性
        self.assertGreater(len(minimized_ts.get_all_states()), 0)
        self.assertGreater(len(minimized_ts.get_initial_states()), 0)
        
        # 检查所有状态都有标签
        for state in minimized_ts.get_all_states():
            self.assertIsNotNone(state.labels)
    
    def test_minimized_ts_transitions(self):
        """测试最小化 TS 的迁移关系"""
        ts = self.create_bisimilar_pair_ts()
        result = minimize_transition_system(ts)
        
        minimized_ts = result.minimized_ts
        
        # 检查迁移关系
        stats = minimized_ts.get_statistics()
        self.assertGreater(stats['reachable_transitions'], 0)
    
    def test_empty_ts(self):
        """测试空 TS"""
        ts = TransitionSystem()
        
        result = minimize_transition_system(ts)
        
        self.assertEqual(result.original_state_count, 0)
        self.assertEqual(result.minimized_state_count, 0)
        self.assertEqual(result.reduction_ratio, 0.0)
    
    def test_single_state_ts(self):
        """测试单状态 TS"""
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_initial_state("s0")
        
        result = minimize_transition_system(ts)
        
        self.assertEqual(result.original_state_count, 1)
        self.assertEqual(result.minimized_state_count, 1)
        self.assertEqual(result.reduction_ratio, 0.0)
    
    def test_no_reachable_states(self):
        """测试没有可达状态的 TS"""
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})
        # 没有初始状态，所以没有可达状态
        
        result = minimize_transition_system(ts)
        
        self.assertEqual(result.original_state_count, 0)
        self.assertEqual(result.minimized_state_count, 0)


class TestCTLEquivalence(unittest.TestCase):
    """测试 CTL 等价性"""
    
    def create_test_ts(self) -> TransitionSystem:
        """创建测试 TS"""
        ts = TransitionSystem()
        
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})
        ts.add_state("s2", {"b"})
        ts.add_state("s3", {"c"})
        
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s0", "s2")
        ts.add_transition("s1", "s3")
        ts.add_transition("s2", "s3")
        
        return ts
    
    def test_ctl_equivalence_simple(self):
        """测试简单 TS 的 CTL 等价性"""
        ts = self.create_test_ts()
        result = minimize_transition_system(ts)
        minimized_ts = result.minimized_ts
        
        # 定义测试公式
        formulas = [
            ef(atom("c")),  # 最终能到达 c
            ag(disj(atom("a"), disj(atom("b"), atom("c")))),  # 总是 a 或 b 或 c
        ]
        
        checker_orig = CTLModelChecker(ts)
        checker_min = CTLModelChecker(minimized_ts)
        
        for formula in formulas:
            result_orig = checker_orig.check(formula)
            result_min = checker_min.check(formula)
            
            # 检查结果应该一致
            self.assertEqual(
                result_orig.holds, 
                result_min.holds,
                f"公式 {formula} 在原始 TS 和最小化 TS 上的结果不一致"
            )
    
    def test_ctl_ex_operator(self):
        """测试 EX 算子"""
        ts = self.create_test_ts()
        result = minimize_transition_system(ts)
        minimized_ts = result.minimized_ts
        
        # EX(b): 存在下一步是 b
        formula = ex(atom("b"))
        
        checker_orig = CTLModelChecker(ts)
        checker_min = CTLModelChecker(minimized_ts)
        
        result_orig = checker_orig.check(formula)
        result_min = checker_min.check(formula)
        
        self.assertEqual(result_orig.holds, result_min.holds)
    
    def test_ctl_eu_operator(self):
        """测试 EU 算子"""
        ts = self.create_test_ts()
        result = minimize_transition_system(ts)
        minimized_ts = result.minimized_ts
        
        # E[a U c]: 存在路径从 a 到 c
        formula = eu(atom("a"), atom("c"))
        
        checker_orig = CTLModelChecker(ts)
        checker_min = CTLModelChecker(minimized_ts)
        
        result_orig = checker_orig.check(formula)
        result_min = checker_min.check(formula)
        
        self.assertEqual(result_orig.holds, result_min.holds)


class TestBisimulationClasses(unittest.TestCase):
    """测试 Bisimulation 等价类计算"""
    
    def test_compute_bisimulation_classes(self):
        """测试计算 Bisimulation 等价类"""
        ts = TransitionSystem()
        
        # 创建两个 Bisimilar 的子系统
        for prefix in ["a", "b"]:
            ts.add_state(f"{prefix}0", {"start"})
            ts.add_state(f"{prefix}1", {"middle"})
            ts.add_state(f"{prefix}2", {"end"})
            
            ts.add_initial_state(f"{prefix}0")
            
            ts.add_transition(f"{prefix}0", f"{prefix}1")
            ts.add_transition(f"{prefix}1", f"{prefix}2")
        
        minimizer = BisimulationMinimizer(ts)
        classes = minimizer.compute_bisimulation_classes()
        
        # 应该有 3 个等价类（start, middle, end）
        self.assertEqual(len(classes), 3)
        
        # 每个等价类应该包含 2 个状态
        for class_id, states in classes.items():
            self.assertEqual(len(states), 2)


class TestVisualization(unittest.TestCase):
    """测试可视化功能"""
    
    def create_test_ts(self) -> TransitionSystem:
        """创建测试 TS"""
        ts = TransitionSystem()
        
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})
        ts.add_state("s2", {"b"})  # 与 s1 Bisimilar
        ts.add_state("s3", {"c"})
        
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s0", "s2")
        ts.add_transition("s1", "s3")
        ts.add_transition("s2", "s3")
        
        return ts
    
    def test_ts_dot_generation(self):
        """测试 TS 的 DOT 生成"""
        ts = self.create_test_ts()
        
        # 测试 DOT 生成
        dot = ts.visualize_dot()
        self.assertIn("digraph", dot)
        self.assertIn("s0", dot)
        self.assertIn("s1", dot)
    
    def test_minimizer_partition_visualization(self):
        """测试最小化器的分区可视化"""
        ts = self.create_test_ts()
        minimizer = BisimulationMinimizer(ts)
        
        # 测试分区可视化
        output_path = os.path.join(OUTPUT_DIR, "test_partition_viz.html")
        result_path = minimizer.visualize_partition(output_path)
        
        self.assertTrue(os.path.exists(result_path))
        self.assertTrue(os.path.exists(result_path.replace('.html', '.dot')))
    
    def test_ascii_visualization(self):
        """测试 ASCII 可视化"""
        ts = self.create_test_ts()
        
        # 测试 ASCII 可视化不抛出异常
        try:
            ts.visualize_ascii()
        except Exception as e:
            self.fail(f"visualize_ascii() 抛出异常: {e}")
    
    def test_html_visualization(self):
        """测试 HTML 可视化生成"""
        ts = self.create_test_ts()
        
        output_path = os.path.join(OUTPUT_DIR, "test_ts_viz.html")
        ts.visualize_html(output_path)
        
        self.assertTrue(os.path.exists(output_path))
        
        # 检查文件内容
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("<html>", content.lower())
            # 检查是否包含Graphviz相关的脚本
            self.assertTrue("viz.js" in content or "d3-graphviz" in content or "graphviz" in content.lower())


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def test_self_loop(self):
        """测试自环"""
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_initial_state("s0")
        ts.add_transition("s0", "s0")  # 自环
        
        result = minimize_transition_system(ts)
        
        self.assertEqual(result.minimized_state_count, 1)
        
        # 检查自环是否保留
        minimized_ts = result.minimized_ts
        state = list(minimized_ts.get_all_states())[0]
        successors = minimized_ts.get_successors(state)
        self.assertEqual(len(successors), 1)
        self.assertEqual(list(successors)[0], state)
    
    def test_multiple_initial_states(self):
        """测试多个初始状态"""
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"a"})  # 与 s0 相同标签
        ts.add_state("s2", {"b"})
        
        ts.add_initial_state("s0")
        ts.add_initial_state("s1")
        
        ts.add_transition("s0", "s2")
        ts.add_transition("s1", "s2")
        
        result = minimize_transition_system(ts)
        
        # s0 和 s1 应该合并
        self.assertEqual(result.minimized_state_count, 2)
        
        # 检查初始状态
        minimized_ts = result.minimized_ts
        self.assertEqual(len(minimized_ts.get_initial_states()), 1)
    
    def test_disconnected_states(self):
        """测试不连通的状态"""
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})  # 不连通
        
        ts.add_initial_state("s0")
        
        # 只有 s0 有迁移
        ts.add_transition("s0", "s0")
        
        result = minimize_transition_system(ts)
        
        # 只有可达状态会被考虑
        self.assertEqual(result.original_state_count, 1)
        self.assertEqual(result.minimized_state_count, 1)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestBisimulationMinimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestCTLEquivalence))
    suite.addTests(loader.loadTestsFromTestCase(TestBisimulationClasses))
    suite.addTests(loader.loadTestsFromTestCase(TestVisualization))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)