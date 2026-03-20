"""
实验三测试文件

测试内容：
1. NFA 基本功能测试
2. 从正则表达式构建 NFA 测试
3. TS 与 NFA 乘积构造测试
4. 安全属性验证测试
5. 交通灯示例测试
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

import unittest
from transition_system import TransitionSystem, State
from nfa import NFA, NFAState, RegexToNFA, build_nfa_from_regex
from safety_verifier import (
    ProductConstruction, 
    SafetyVerifier,
    SafetyCheckResult,
    build_bad_prefix_nfa_red_must_follow_yellow,
    build_bad_prefix_nfa_no_consecutive_red,
    check_safety_property,
    check_safety_property_regex
)
from traffic_light_example import (
    create_traffic_light_ts_correct,
    create_traffic_light_ts_violation,
    create_extended_traffic_light_ts
)


class TestNFA(unittest.TestCase):
    """NFA 基础功能测试"""
    
    def test_nfa_creation(self):
        """测试 NFA 创建"""
        nfa = NFA()
        self.assertEqual(len(nfa.get_all_states()), 0)
        self.assertEqual(len(nfa.get_initial_states()), 0)
        self.assertEqual(len(nfa.get_accept_states()), 0)
    
    def test_add_states(self):
        """测试添加状态"""
        nfa = NFA()
        s1 = nfa.add_state("q0", is_initial=True)
        s2 = nfa.add_state("q1", is_accept=True)
        
        self.assertEqual(len(nfa.get_all_states()), 2)
        self.assertIn(s1, nfa.get_initial_states())
        self.assertIn(s2, nfa.get_accept_states())
    
    def test_add_transitions(self):
        """测试添加转移"""
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1", is_accept=True)
        nfa.add_transition("q0", "q1", "a")
        
        q0 = nfa.get_state("q0")
        transitions = nfa.get_transitions(q0)
        self.assertEqual(len(transitions), 1)
        
        target, symbol = transitions[0]
        self.assertEqual(target.name, "q1")
        self.assertEqual(symbol, "a")
    
    def test_epsilon_closure(self):
        """测试 ε-闭包计算"""
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1")
        nfa.add_state("q2")
        
        # q0 --ε--> q1 --ε--> q2
        nfa.add_transition("q0", "q1", None)
        nfa.add_transition("q1", "q2", None)
        
        q0 = nfa.get_state("q0")
        closure = nfa.epsilon_closure({q0})
        
        self.assertEqual(len(closure), 3)
        self.assertIn(nfa.get_state("q0"), closure)
        self.assertIn(nfa.get_state("q1"), closure)
        self.assertIn(nfa.get_state("q2"), closure)
    
    def test_nfa_accepts(self):
        """测试 NFA 接受单词"""
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1")
        nfa.add_state("q2", is_accept=True)
        
        # 构造 NFA 接受 "ab"
        nfa.add_transition("q0", "q1", "a")
        nfa.add_transition("q1", "q2", "b")
        
        self.assertTrue(nfa.accepts(["a", "b"]))
        self.assertFalse(nfa.accepts(["a"]))
        self.assertFalse(nfa.accepts(["b"]))
        self.assertFalse(nfa.accepts(["a", "b", "c"]))
    
    def test_nfa_with_epsilon(self):
        """测试带 ε-转移的 NFA"""
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1")
        nfa.add_state("q2", is_accept=True)
        
        # q0 --ε--> q1 --a--> q2
        nfa.add_transition("q0", "q1", None)
        nfa.add_transition("q1", "q2", "a")
        
        self.assertTrue(nfa.accepts(["a"]))


class TestRegexToNFA(unittest.TestCase):
    """正则表达式到 NFA 转换测试"""
    
    def test_atom(self):
        """测试原子命题"""
        builder = RegexToNFA()
        nfa = builder.parse_and_build("a")
        
        # 调试：打印 NFA 结构
        # nfa.print_structure()
        
        self.assertTrue(nfa.accepts(["a"]))
        self.assertFalse(nfa.accepts(["b"]))
    
    def test_concatenation(self):
        """测试连接"""
        builder = RegexToNFA()
        # 使用空格分隔的原子命题表示连接
        nfa = builder.parse_and_build("a b")
        
        self.assertTrue(nfa.accepts(["a", "b"]))
        self.assertFalse(nfa.accepts(["a"]))
        self.assertFalse(nfa.accepts(["b"]))
    
    def test_union(self):
        """测试选择"""
        builder = RegexToNFA()
        nfa = builder.parse_and_build("a|b")
        
        self.assertTrue(nfa.accepts(["a"]))
        self.assertTrue(nfa.accepts(["b"]))
        self.assertFalse(nfa.accepts(["c"]))
    
    def test_kleene_star(self):
        """测试 Kleene 星"""
        builder = RegexToNFA()
        nfa = builder.parse_and_build("a*")
        
        self.assertTrue(nfa.accepts([]))  # 空串
        self.assertTrue(nfa.accepts(["a"]))
        self.assertTrue(nfa.accepts(["a", "a"]))
        self.assertTrue(nfa.accepts(["a", "a", "a"]))
    
    def test_complex_regex(self):
        """测试复杂正则表达式"""
        builder = RegexToNFA()
        # (a b)*  - 零个或多个 "a b" 序列
        nfa = builder.parse_and_build("(a b)*")
        
        self.assertTrue(nfa.accepts([]))
        self.assertTrue(nfa.accepts(["a", "b"]))
        self.assertTrue(nfa.accepts(["a", "b", "a", "b"]))
        self.assertFalse(nfa.accepts(["a"]))
        self.assertFalse(nfa.accepts(["b"]))
    
    def test_traffic_light_regex(self):
        """测试交通灯相关正则"""
        builder = RegexToNFA()
        # red yellow
        nfa = builder.parse_and_build("red yellow")
        
        self.assertTrue(nfa.accepts(["red", "yellow"]))
        self.assertFalse(nfa.accepts(["red", "green"]))


class TestProductConstruction(unittest.TestCase):
    """乘积构造测试"""
    
    def test_product_basic(self):
        """测试基本乘积构造"""
        # 创建简单 TS
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})
        ts.add_initial_state("s0")
        ts.add_transition("s0", "s1")
        
        # 创建简单 NFA（接受 "b"）
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1", is_accept=True)
        nfa.add_transition("q0", "q1", "b")
        
        product = ProductConstruction(ts, nfa)
        initial_states = product.get_initial_states()
        
        self.assertEqual(len(initial_states), 1)
    
    def test_product_reachability(self):
        """测试乘积图可达性"""
        # TS: s0 --a--> s1
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_state("s1", {"b"})
        ts.add_initial_state("s0")
        ts.add_transition("s0", "s1")
        
        # NFA: q0 --b--> q1 (accept)
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1", is_accept=True)
        nfa.add_transition("q0", "q1", "b")
        
        product = ProductConstruction(ts, nfa)
        states, transitions = product.construct()
        
        # 应该有 2 个乘积状态：(s0,q0) 和 (s1,q1)
        self.assertEqual(len(states), 2)


class TestSafetyVerifier(unittest.TestCase):
    """安全属性验证测试"""
    
    def test_property_holds(self):
        """测试属性成立的情况"""
        ts = create_traffic_light_ts_correct()
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "red 后必须紧跟 yellow")
        
        self.assertTrue(result.holds)
        self.assertIsNone(result.counterexample)
    
    def test_property_violated(self):
        """测试属性被违反的情况"""
        ts = create_traffic_light_ts_violation()
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "red 后必须紧跟 yellow")
        
        self.assertFalse(result.holds)
        self.assertIsNotNone(result.counterexample)
        self.assertGreater(len(result.counterexample), 0)
    
    def test_counterexample_path(self):
        """测试反例路径生成"""
        ts = create_traffic_light_ts_violation()
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "test")
        
        if not result.holds:
            # 反例路径应该包含 red 状态
            path_names = [s.name for s in result.counterexample]
            self.assertIn("red", path_names)
    
    def test_no_consecutive_red(self):
        """测试不允许连续 red 属性"""
        # 创建 TS 有连续 red: green -> red -> red
        ts = TransitionSystem()
        ts.add_state("s0", {"green"})  # 初始状态，标签 green
        ts.add_state("s1", {"red"})    # 第一个 red
        ts.add_state("s2", {"red"})    # 连续 red（违反）
        ts.add_initial_state("s0")
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s2")
        
        nfa = build_bad_prefix_nfa_no_consecutive_red()
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "不允许连续 red")
        
        self.assertFalse(result.holds)
        self.assertIsNotNone(result.counterexample)


class TestTrafficLightExamples(unittest.TestCase):
    """交通灯示例测试"""
    
    def test_correct_traffic_light(self):
        """测试正确交通灯模型"""
        ts = create_traffic_light_ts_correct()
        
        # 验证可达状态
        reachable = ts.compute_reachable_states()
        self.assertEqual(len(reachable), 4)
        
        # 验证属性
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "red 后必须紧跟 yellow")
        
        self.assertTrue(result.holds)
    
    def test_violation_traffic_light(self):
        """测试违反属性的交通灯模型"""
        ts = create_traffic_light_ts_violation()
        
        # 验证可达状态
        reachable = ts.compute_reachable_states()
        self.assertEqual(len(reachable), 3)
        
        # 验证属性被违反
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "red 后必须紧跟 yellow")
        
        self.assertFalse(result.holds)
        self.assertIsNotNone(result.counterexample)
    
    def test_extended_traffic_light(self):
        """测试扩展交通灯模型"""
        ts = create_extended_traffic_light_ts()
        
        # 验证可达状态
        reachable = ts.compute_reachable_states()
        self.assertGreaterEqual(len(reachable), 4)
        
        # 验证属性
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "red 后必须紧跟 yellow")
        
        self.assertTrue(result.holds)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 创建 TS
        ts = TransitionSystem()
        ts.add_state("green", {"green"})
        ts.add_state("yellow", {"yellow"})
        ts.add_state("red", {"red"})
        ts.add_initial_state("green")
        ts.add_transition("green", "yellow")
        ts.add_transition("yellow", "red")
        ts.add_transition("red", "green")
        
        # 2. 创建 NFA（接受 "red green" 作为坏前缀）
        nfa = NFA()
        nfa.add_state("q0", is_initial=True)
        nfa.add_state("q1")
        nfa.add_state("q2", is_accept=True)
        
        nfa.add_transition("q0", "q0", "green")
        nfa.add_transition("q0", "q0", "yellow")
        nfa.add_transition("q0", "q1", "red")
        nfa.add_transition("q1", "q2", "green")
        nfa.add_transition("q2", "q2", "green")
        nfa.add_transition("q2", "q2", "yellow")
        nfa.add_transition("q2", "q2", "red")
        
        # 3. 验证
        verifier = SafetyVerifier(ts)
        result = verifier.verify(nfa, "red 后不能直接 green")
        
        # 应该检测到违反
        self.assertFalse(result.holds)
        self.assertIsNotNone(result.counterexample)
    
    def test_convenience_functions(self):
        """测试便捷函数"""
        ts = create_traffic_light_ts_correct()
        nfa = build_bad_prefix_nfa_red_must_follow_yellow()
        
        result = check_safety_property(ts, nfa, "test")
        self.assertTrue(result.holds)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestNFA))
    suite.addTests(loader.loadTestsFromTestCase(TestRegexToNFA))
    suite.addTests(loader.loadTestsFromTestCase(TestProductConstruction))
    suite.addTests(loader.loadTestsFromTestCase(TestSafetyVerifier))
    suite.addTests(loader.loadTestsFromTestCase(TestTrafficLightExamples))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
