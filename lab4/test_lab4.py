"""
实验四：LTL 模型检查测试

本模块包含对 LTL 模型检查器的单元测试。
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

import unittest
from transition_system import TransitionSystem
from nba import NBA
from ltl_formula import (
    atom, neg, globally, eventually, implies, conj, disj,
    always_eventually, implies_eventually, ltl_to_nba, LTLToNBA
)
from ltl_model_checker import LTLModelChecker, check_ltl_property


class TestNBA(unittest.TestCase):
    """测试 NBA 类"""
    
    def test_nba_creation(self):
        """测试 NBA 创建"""
        nba = NBA()
        q0 = nba.add_state("q0", is_initial=True, is_accept=True)
        q1 = nba.add_state("q1")
        
        self.assertEqual(len(nba.get_all_states()), 2)
        self.assertEqual(len(nba.get_initial_states()), 1)
        self.assertEqual(len(nba.get_accept_states()), 1)
        self.assertTrue(nba.is_accept_state(q0))
        self.assertFalse(nba.is_accept_state(q1))
    
    def test_nba_transitions(self):
        """测试 NBA 转移"""
        nba = NBA()
        q0 = nba.add_state("q0", is_initial=True)
        q1 = nba.add_state("q1", is_accept=True)
        
        nba.add_transition("q0", "q1", "a")
        nba.add_transition("q1", "q1", "b")
        
        successors = nba.get_successors(q0, "a")
        self.assertEqual(len(successors), 1)
        self.assertIn(q1, successors)
    
    def test_epsilon_closure(self):
        """测试 ε-闭包计算"""
        nba = NBA()
        q0 = nba.add_state("q0", is_initial=True)
        q1 = nba.add_state("q1")
        q2 = nba.add_state("q2")
        
        nba.add_transition("q0", "q1", None)  # ε-转移
        nba.add_transition("q1", "q2", None)  # ε-转移
        
        closure = nba.epsilon_closure({q0})
        self.assertEqual(len(closure), 3)
        self.assertIn(q0, closure)
        self.assertIn(q1, closure)
        self.assertIn(q2, closure)


class TestLTLFormula(unittest.TestCase):
    """测试 LTL 公式类"""
    
    def test_atom_creation(self):
        """测试原子命题创建"""
        f = atom("green")
        self.assertEqual(f.op.name, "ATOM")
        self.assertEqual(f.atom, "green")
    
    def test_globally_eventually(self):
        """测试 □♦ 公式创建"""
        f = always_eventually("green")
        self.assertEqual(f.op.name, "GLOBALLY")
        self.assertEqual(f.left.op.name, "EVENTUALLY")
        self.assertEqual(f.left.left.atom, "green")
    
    def test_implies_eventually(self):
        """测试 □(→♦) 公式创建"""
        f = implies_eventually("send", "ack")
        self.assertEqual(f.op.name, "GLOBALLY")
        self.assertEqual(f.left.op.name, "IMPLIES")
    
    def test_get_atoms(self):
        """测试获取原子命题"""
        f = implies_eventually("send", "ack")
        atoms = f.get_atoms()
        self.assertEqual(atoms, {"send", "ack"})


class TestLTLToNBA(unittest.TestCase):
    """测试 LTL 到 NBA 转换"""
    
    def test_convert_globally_atom(self):
        """测试转换 □atom"""
        converter = LTLToNBA()
        f = globally(atom("green"))
        nba = converter.convert(f, {"green", "red"})
        
        self.assertEqual(len(nba.get_all_states()), 1)
        self.assertEqual(len(nba.get_initial_states()), 1)
        self.assertEqual(len(nba.get_accept_states()), 1)
    
    def test_convert_eventually_atom(self):
        """测试转换 ♦atom"""
        converter = LTLToNBA()
        f = eventually(atom("green"))
        nba = converter.convert(f, {"green", "red"})
        
        self.assertEqual(len(nba.get_all_states()), 2)
        self.assertEqual(len(nba.get_initial_states()), 1)
        self.assertEqual(len(nba.get_accept_states()), 1)


class TestProductConstruction(unittest.TestCase):
    """测试乘积构造"""
    
    def test_product_initial_states(self):
        """测试乘积初始状态"""
        from ltl_model_checker import ProductConstruction
        
        # 创建简单 TS
        ts = TransitionSystem()
        ts.add_state("s0", {"a"})
        ts.add_initial_state("s0")
        
        # 创建简单 NBA
        nba = NBA()
        nba.add_state("q0", is_initial=True, is_accept=True)
        nba.add_transition("q0", "q0", "a")
        
        product = ProductConstruction(ts, nba)
        initial_states = product.get_initial_states()
        
        self.assertEqual(len(initial_states), 1)


class TestLTLModelChecker(unittest.TestCase):
    """测试 LTL 模型检查器"""
    
    def test_simple_always_eventually_pass(self):
        """测试简单 □♦ 属性通过"""
        # 创建循环 TS：green -> red -> green
        ts = TransitionSystem()
        ts.add_state("green", {"green"})
        ts.add_state("red", {"red"})
        ts.add_initial_state("green")
        ts.add_transition("green", "red", "to_red")
        ts.add_transition("red", "green", "to_green")
        
        # 构造否定公式的 NBA：♦□¬green（最终永远非绿）
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True, is_accept=True)
        q1 = nba_neg.add_state("q1")
        nba_neg.add_transition("q0", "q0", "red")
        nba_neg.add_transition("q0", "q1", "green")
        nba_neg.add_transition("q1", "q1", "green")
        nba_neg.add_transition("q1", "q1", "red")
        
        checker = LTLModelChecker(ts)
        result = checker.check(nba_neg, "□♦green")
        
        self.assertTrue(result.holds)
    
    def test_simple_always_eventually_fail(self):
        """测试简单 □♦ 属性失败"""
        # 创建 TS：永远不到 green
        ts = TransitionSystem()
        ts.add_state("red", {"red"})
        ts.add_initial_state("red")
        ts.add_transition("red", "red", "loop")
        
        # 构造否定公式的 NBA
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True, is_accept=True)
        nba_neg.add_transition("q0", "q0", "red")
        
        checker = LTLModelChecker(ts)
        result = checker.check(nba_neg, "□♦green")
        
        self.assertFalse(result.holds)
        self.assertIsNotNone(result.counterexample)
    
    def test_response_property_pass(self):
        """测试响应属性通过"""
        # 创建 TS：send -> wait -> ack -> send
        ts = TransitionSystem()
        ts.add_state("idle", {"idle"})
        ts.add_state("send", {"send"})
        ts.add_state("wait", {"wait"})
        ts.add_state("ack", {"ack"})
        ts.add_initial_state("idle")
        ts.add_transition("idle", "send", "start")
        ts.add_transition("send", "wait", "send_msg")
        ts.add_transition("wait", "ack", "recv")
        ts.add_transition("ack", "idle", "done")
        
        # 构造否定公式的 NBA：♦(send ∧ □¬ack)
        # q0：初始状态，q1：已send等待ack，q2：接受状态（永远不到ack）
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True)
        q1 = nba_neg.add_state("q1")
        q2 = nba_neg.add_state("q2", is_accept=True)
        nba_neg.add_transition("q0", "q0", "idle")
        nba_neg.add_transition("q0", "q0", "wait")
        nba_neg.add_transition("q0", "q0", "ack")
        nba_neg.add_transition("q0", "q1", "send")
        nba_neg.add_transition("q1", "q0", "ack")
        nba_neg.add_transition("q1", "q1", "idle")
        nba_neg.add_transition("q1", "q1", "wait")
        nba_neg.add_transition("q1", "q1", "send")
        nba_neg.add_transition("q1", "q2", "idle")
        nba_neg.add_transition("q1", "q2", "wait")
        nba_neg.add_transition("q2", "q2", "idle")
        nba_neg.add_transition("q2", "q2", "send")
        nba_neg.add_transition("q2", "q2", "wait")
        
        checker = LTLModelChecker(ts)
        result = checker.check(nba_neg, "□(send → ♦ack)")
        
        self.assertTrue(result.holds)
    
    def test_response_property_fail(self):
        """测试响应属性失败"""
        # 创建 TS：send 后可能永远等待
        ts = TransitionSystem()
        ts.add_state("idle", {"idle"})
        ts.add_state("send", {"send"})
        ts.add_state("wait", {"wait"})
        ts.add_initial_state("idle")
        ts.add_transition("idle", "send", "start")
        ts.add_transition("send", "wait", "send_msg")
        ts.add_transition("wait", "wait", "wait_forever")
        
        # 构造否定公式的 NBA
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True)
        q1 = nba_neg.add_state("q1")
        q2 = nba_neg.add_state("q2", is_accept=True)
        nba_neg.add_transition("q0", "q0", "idle")
        nba_neg.add_transition("q0", "q1", "send")
        nba_neg.add_transition("q1", "q1", "wait")
        nba_neg.add_transition("q1", "q1", "idle")
        nba_neg.add_transition("q1", "q1", "send")
        nba_neg.add_transition("q1", "q2", "wait")
        nba_neg.add_transition("q1", "q2", "idle")
        nba_neg.add_transition("q2", "q2", "wait")
        nba_neg.add_transition("q2", "q2", "idle")
        nba_neg.add_transition("q2", "q2", "send")
        
        checker = LTLModelChecker(ts)
        result = checker.check(nba_neg, "□(send → ♦ack)")
        
        self.assertFalse(result.holds)
        self.assertIsNotNone(result.counterexample)


class TestTrafficLightExamples(unittest.TestCase):
    """测试交通灯示例"""
    
    def test_correct_traffic_light(self):
        """测试正确交通灯满足 □♦green"""
        ts = TransitionSystem()
        ts.add_state("green", {"green"})
        ts.add_state("yellow", {"yellow"})
        ts.add_state("red", {"red"})
        ts.add_initial_state("green")
        ts.add_transition("green", "yellow", "to_yellow")
        ts.add_transition("yellow", "red", "to_red")
        ts.add_transition("red", "green", "to_green")
        
        # 否定公式的 NBA
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True, is_accept=True)
        q1 = nba_neg.add_state("q1")
        nba_neg.add_transition("q0", "q0", "red")
        nba_neg.add_transition("q0", "q0", "yellow")
        nba_neg.add_transition("q0", "q1", "green")
        nba_neg.add_transition("q1", "q1", "green")
        nba_neg.add_transition("q1", "q1", "red")
        nba_neg.add_transition("q1", "q1", "yellow")
        
        result = check_ltl_property(ts, nba_neg, "□♦green")
        self.assertTrue(result.holds)
    
    def test_violation_traffic_light(self):
        """测试违规交通灯违反 □♦green"""
        ts = TransitionSystem()
        ts.add_state("green", {"green"})
        ts.add_state("yellow", {"yellow"})
        ts.add_state("red", {"red"})
        ts.add_initial_state("green")
        ts.add_transition("green", "yellow", "to_yellow")
        ts.add_transition("yellow", "red", "to_red")
        ts.add_transition("red", "red", "stay_red")  # 永远红灯
        
        # 否定公式的 NBA
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True, is_accept=True)
        q1 = nba_neg.add_state("q1")
        nba_neg.add_transition("q0", "q0", "red")
        nba_neg.add_transition("q0", "q0", "yellow")
        nba_neg.add_transition("q0", "q1", "green")
        nba_neg.add_transition("q1", "q1", "green")
        nba_neg.add_transition("q1", "q1", "red")
        nba_neg.add_transition("q1", "q1", "yellow")
        
        result = check_ltl_property(ts, nba_neg, "□♦green")
        self.assertFalse(result.holds)


class TestProtocolExamples(unittest.TestCase):
    """测试通信协议示例"""
    
    def test_correct_protocol(self):
        """测试正确协议满足 □(send → ♦ack)"""
        ts = TransitionSystem()
        ts.add_state("idle", {"idle"})
        ts.add_state("send", {"send"})
        ts.add_state("wait", {"wait"})
        ts.add_state("ack", {"ack"})
        ts.add_initial_state("idle")
        ts.add_transition("idle", "send", "start")
        ts.add_transition("send", "wait", "send_msg")
        ts.add_transition("wait", "ack", "recv")
        ts.add_transition("ack", "idle", "done")
        
        # 否定公式的 NBA
        nba_neg = NBA()
        q0 = nba_neg.add_state("q0", is_initial=True)
        q1 = nba_neg.add_state("q1")
        q2 = nba_neg.add_state("q2", is_accept=True)
        nba_neg.add_transition("q0", "q0", "idle")
        nba_neg.add_transition("q0", "q0", "wait")
        nba_neg.add_transition("q0", "q0", "ack")
        nba_neg.add_transition("q0", "q1", "send")
        nba_neg.add_transition("q1", "q0", "ack")
        nba_neg.add_transition("q1", "q2", "idle")
        nba_neg.add_transition("q1", "q2", "wait")
        nba_neg.add_transition("q1", "q2", "send")
        nba_neg.add_transition("q2", "q2", "idle")
        nba_neg.add_transition("q2", "q2", "send")
        nba_neg.add_transition("q2", "q2", "wait")
        
        result = check_ltl_property(ts, nba_neg, "□(send → ♦ack)")
        self.assertTrue(result.holds)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestNBA))
    suite.addTests(loader.loadTestsFromTestCase(TestLTLFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestLTLToNBA))
    suite.addTests(loader.loadTestsFromTestCase(TestProductConstruction))
    suite.addTests(loader.loadTestsFromTestCase(TestLTLModelChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestTrafficLightExamples))
    suite.addTests(loader.loadTestsFromTestCase(TestProtocolExamples))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
