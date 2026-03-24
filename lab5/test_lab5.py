"""
实验五：CTL 模型检查单元测试

本模块包含对 CTL 公式表示、解析和模型检查算法的全面测试。
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

import unittest
from typing import Set

from transition_system import TransitionSystem, State
from ctl_formula import (
    CTLFormula, CTLOp, atom, neg, conj, disj, implies,
    ex, ax, ef, af, eg, ag, eu, au,
    ctl_true, ctl_false, parse_ctl
)
from ctl_model_checker import CTLModelChecker, CTLCheckResult


class TestCTLFormula(unittest.TestCase):
    """测试 CTL 公式的表示和构造"""
    
    def test_atom_construction(self):
        """测试原子命题构造"""
        f = atom("p")
        self.assertEqual(f.op, CTLOp.ATOM)
        self.assertEqual(f.atom, "p")
    
    def test_negation(self):
        """测试否定"""
        f = neg(atom("p"))
        self.assertEqual(f.op, CTLOp.NOT)
        self.assertEqual(f.left.op, CTLOp.ATOM)
    
    def test_conjunction(self):
        """测试合取"""
        f = conj(atom("p"), atom("q"))
        self.assertEqual(f.op, CTLOp.AND)
        self.assertEqual(f.left.atom, "p")
        self.assertEqual(f.right.atom, "q")
    
    def test_disjunction(self):
        """测试析取"""
        f = disj(atom("p"), atom("q"))
        self.assertEqual(f.op, CTLOp.OR)
        self.assertEqual(f.left.atom, "p")
        self.assertEqual(f.right.atom, "q")
    
    def test_implies(self):
        """测试蕴含"""
        f = implies(atom("p"), atom("q"))
        self.assertEqual(f.op, CTLOp.IMPLIES)
    
    def test_temporal_operators(self):
        """测试时序算子"""
        p = atom("p")
        
        ex_f = ex(p)
        self.assertEqual(ex_f.op, CTLOp.EX)
        
        ax_f = ax(p)
        self.assertEqual(ax_f.op, CTLOp.AX)
        
        ef_f = ef(p)
        self.assertEqual(ef_f.op, CTLOp.EF)
        
        af_f = af(p)
        self.assertEqual(af_f.op, CTLOp.AF)
        
        eg_f = eg(p)
        self.assertEqual(eg_f.op, CTLOp.EG)
        
        ag_f = ag(p)
        self.assertEqual(ag_f.op, CTLOp.AG)
    
    def test_until_operators(self):
        """测试 Until 算子"""
        p = atom("p")
        q = atom("q")
        
        eu_f = eu(p, q)
        self.assertEqual(eu_f.op, CTLOp.EU)
        self.assertEqual(eu_f.left.atom, "p")
        self.assertEqual(eu_f.right.atom, "q")
        
        au_f = au(p, q)
        self.assertEqual(au_f.op, CTLOp.AU)
    
    def test_get_atoms(self):
        """测试获取原子命题"""
        f = conj(atom("p"), disj(atom("q"), atom("r")))
        atoms = f.get_atoms()
        self.assertEqual(atoms, {"p", "q", "r"})
    
    def test_string_representation(self):
        """测试字符串表示"""
        f = ag(disj(neg(atom("p")), atom("q")))
        self.assertIn("∀□", str(f))
        self.assertIn("p", str(f))
        self.assertIn("q", str(f))


class TestCTLParser(unittest.TestCase):
    """测试 CTL 公式解析器"""
    
    def test_parse_atom(self):
        """测试解析原子命题"""
        f = parse_ctl("p")
        self.assertEqual(f.op, CTLOp.ATOM)
        self.assertEqual(f.atom, "p")
    
    def test_parse_negation(self):
        """测试解析否定"""
        f = parse_ctl("!p")
        self.assertEqual(f.op, CTLOp.NOT)
        
        f2 = parse_ctl("¬p")
        self.assertEqual(f2.op, CTLOp.NOT)
    
    def test_parse_and(self):
        """测试解析合取"""
        f = parse_ctl("p & q")
        self.assertEqual(f.op, CTLOp.AND)
        
        f2 = parse_ctl("p && q")
        self.assertEqual(f2.op, CTLOp.AND)
    
    def test_parse_or(self):
        """测试解析析取"""
        f = parse_ctl("p | q")
        self.assertEqual(f.op, CTLOp.OR)
    
    def test_parse_implies(self):
        """测试解析蕴含"""
        f = parse_ctl("p -> q")
        self.assertEqual(f.op, CTLOp.IMPLIES)
    
    def test_parse_ex(self):
        """测试解析 EX"""
        f = parse_ctl("EX(p)")
        self.assertEqual(f.op, CTLOp.EX)
    
    def test_parse_eg(self):
        """测试解析 EG"""
        f = parse_ctl("EG(p)")
        self.assertEqual(f.op, CTLOp.EG)
    
    def test_parse_ag(self):
        """测试解析 AG"""
        f = parse_ctl("AG(!p | q)")
        self.assertEqual(f.op, CTLOp.AG)
    
    def test_parse_ef(self):
        """测试解析 EF"""
        f = parse_ctl("EF(target)")
        self.assertEqual(f.op, CTLOp.EF)
    
    def test_parse_af(self):
        """测试解析 AF"""
        f = parse_ctl("AF(p)")
        self.assertEqual(f.op, CTLOp.AF)
    
    def test_parse_complex_formula(self):
        """测试解析复杂公式"""
        # AG(wait -> AF(crit))
        f = parse_ctl("AG(wait -> AF(crit))")
        self.assertEqual(f.op, CTLOp.AG)
        self.assertEqual(f.left.op, CTLOp.IMPLIES)


class TestCTLModelChecker(unittest.TestCase):
    """测试 CTL 模型检查器"""
    
    def create_simple_ts(self) -> TransitionSystem:
        """创建一个简单的测试迁移系统"""
        ts = TransitionSystem()
        
        # 状态：s0 -> s1 -> s2
        # s0: 初始状态，标签 {p}
        # s1: 标签 {q}
        # s2: 标签 {r}
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"q"})
        ts.add_state("s2", {"r"})
        
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s2")
        ts.add_transition("s2", "s2")  # 自环
        
        return ts
    
    def create_branching_ts(self) -> TransitionSystem:
        """创建一个分支结构的迁移系统"""
        ts = TransitionSystem()
        
        #       s0 (初始, p)
        #      /   \
        #    s1(q)  s2(r)
        #    |       |
        #    s3(p)   s4(q)
        
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"q"})
        ts.add_state("s2", {"r"})
        ts.add_state("s3", {"p"})
        ts.add_state("s4", {"q"})
        
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s0", "s2")
        ts.add_transition("s1", "s3")
        ts.add_transition("s2", "s4")
        ts.add_transition("s3", "s3")
        ts.add_transition("s4", "s4")
        
        return ts
    
    def test_check_true(self):
        """测试检查 true"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        result = checker.check(ctl_true())
        self.assertTrue(result.holds)
        self.assertEqual(len(result.satisfying_states), 3)  # 所有可达状态
    
    def test_check_false(self):
        """测试检查 false"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        result = checker.check(ctl_false())
        self.assertFalse(result.holds)
        self.assertEqual(len(result.satisfying_states), 0)
    
    def test_check_atom(self):
        """测试检查原子命题"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        result = checker.check(atom("p"))
        self.assertTrue(result.holds)  # s0 有标签 p
        self.assertEqual(len(result.satisfying_states), 1)
        
        result2 = checker.check(atom("q"))
        self.assertFalse(result2.holds)  # 初始状态没有 q
    
    def test_check_negation(self):
        """测试检查否定"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # !p: s1, s2 满足
        result = checker.check(neg(atom("p")))
        self.assertFalse(result.holds)  # s0 不满足 !p
        self.assertEqual(len(result.satisfying_states), 2)
    
    def test_check_conjunction(self):
        """测试检查合取"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # p & q: 没有状态同时满足
        result = checker.check(conj(atom("p"), atom("q")))
        self.assertFalse(result.holds)
        self.assertEqual(len(result.satisfying_states), 0)
    
    def test_check_disjunction(self):
        """测试检查析取"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # p | q: s0 和 s1 满足
        result = checker.check(disj(atom("p"), atom("q")))
        self.assertTrue(result.holds)
        self.assertEqual(len(result.satisfying_states), 2)
    
    def test_check_ex(self):
        """测试检查 EX"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # EX(q): s0 满足，因为 s0 -> s1 且 s1 有 q
        result = checker.check(ex(atom("q")))
        self.assertTrue(result.holds)
        self.assertIn(ts.get_state("s0"), result.satisfying_states)
    
    def test_check_ax(self):
        """测试检查 AX"""
        ts = self.create_branching_ts()
        checker = CTLModelChecker(ts)
        
        # AX(q): s0 不满足，因为 s0 -> s2 且 s2 没有 q
        result = checker.check(ax(atom("q")))
        self.assertFalse(result.holds)
    
    def test_check_ef(self):
        """测试检查 EF"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # EF(r): 所有状态都满足，因为从 s0 可以到达 s2
        result = checker.check(ef(atom("r")))
        self.assertTrue(result.holds)
        self.assertEqual(len(result.satisfying_states), 3)
    
    def test_check_af(self):
        """测试检查 AF"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # AF(r): 所有状态都满足，因为最终都会到达 s2
        result = checker.check(af(atom("r")))
        self.assertTrue(result.holds)
    
    def test_check_eg(self):
        """测试检查 EG"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # EG(p): 在这个 TS 中没有状态满足，因为 s0 必须走到 s1，而 s1 没有 p
        # EG φ 要求存在一条路径使得 φ 在所有未来状态上成立
        result = checker.check(eg(atom("p")))
        # 没有状态能永远保持 p，因为 s0->s1 且 s1 没有 p
        self.assertFalse(result.holds)
        self.assertEqual(len(result.satisfying_states), 0)
    
    def test_check_ag(self):
        """测试检查 AG"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # AG(p): 不满足，因为 s1 和 s2 没有 p
        result = checker.check(ag(atom("p")))
        self.assertFalse(result.holds)
    
    def test_check_eu(self):
        """测试检查 EU"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # E[p U r]: s0 不满足，因为路径 s0(p) -> s1(q) -> s2(r) 中
        # s1 没有 p，所以不满足 "p 直到 r"
        # 只有 s2 满足（因为 r 立即成立）
        result = checker.check(eu(atom("p"), atom("r")))
        # s2 满足 r，所以满足 E[p U r]
        self.assertIn(ts.get_state("s2"), result.satisfying_states)
    
    def test_check_au(self):
        """测试检查 AU"""
        ts = self.create_simple_ts()
        checker = CTLModelChecker(ts)
        
        # A[p U r]: 检查是否所有路径都满足 p 直到 r
        # 在 s0->s1->s2 路径中，s1 没有 p，所以不满足 "p 直到 r"
        result = checker.check(au(atom("p"), atom("r")))
        # 只有 s2 满足（r 立即成立）
        self.assertIn(ts.get_state("s2"), result.satisfying_states)


class TestPetersonMutualExclusion(unittest.TestCase):
    """测试 Peterson 算法的互斥属性"""
    
    def create_peterson_ts(self) -> TransitionSystem:
        """创建一个简化的 Peterson 算法迁移系统"""
        ts = TransitionSystem()
        
        # 简化状态：(pc0, pc1)
        # pc: 0=非临界区(nc), 1=等待(wait), 2=临界区(crit)
        
        states = [
            ("s00", 0, 0, set()),           # 都在非临界区
            ("s10", 1, 0, {"wait0"}),       # P0等待
            ("s01", 0, 1, {"wait1"}),       # P1等待
            ("s20", 2, 0, {"crit0"}),       # P0临界
            ("s02", 0, 2, {"crit1"}),       # P1临界
            ("s11", 1, 1, {"wait0", "wait1"}),  # 都等待
        ]
        
        for name, pc0, pc1, labels in states:
            ts.add_state(name, labels)
        
        ts.add_initial_state("s00")
        
        # 迁移
        ts.add_transition("s00", "s10", "P0_request")
        ts.add_transition("s00", "s01", "P1_request")
        ts.add_transition("s10", "s20", "P0_enter")
        ts.add_transition("s10", "s11", "P1_request")
        ts.add_transition("s01", "s02", "P1_enter")
        ts.add_transition("s01", "s11", "P0_request")
        ts.add_transition("s20", "s00", "P0_exit")
        ts.add_transition("s02", "s00", "P1_exit")
        ts.add_transition("s11", "s20", "P0_enter")  # P0优先
        ts.add_transition("s11", "s02", "P1_enter")  # P1优先
        
        return ts
    
    def test_mutual_exclusion(self):
        """测试互斥属性：AG(!crit0 | !crit1)"""
        ts = self.create_peterson_ts()
        checker = CTLModelChecker(ts)
        
        # AG(!crit0 | !crit1)
        formula = ag(disj(neg(atom("crit0")), neg(atom("crit1"))))
        result = checker.check(formula)
        
        # 在这个简化模型中，互斥应该满足
        self.assertTrue(result.holds)
    
    def test_reachability(self):
        """测试可达性：EF(crit0)"""
        ts = self.create_peterson_ts()
        checker = CTLModelChecker(ts)
        
        formula = ef(atom("crit0"))
        result = checker.check(formula)
        
        # 应该能从初始状态到达 crit0
        self.assertTrue(result.holds)
    
    def test_safety(self):
        """测试安全性：AG(!(crit0 & crit1))"""
        ts = self.create_peterson_ts()
        checker = CTLModelChecker(ts)
        
        formula = ag(neg(conj(atom("crit0"), atom("crit1"))))
        result = checker.check(formula)
        
        # 不应该有状态同时满足 crit0 和 crit1
        self.assertTrue(result.holds)


class TestFixedPointIteration(unittest.TestCase):
    """测试固定点迭代算法"""
    
    def test_eg_fixed_point(self):
        """测试 EG 的最大固定点计算"""
        ts = TransitionSystem()
        
        # 创建一个循环：s0(p) -> s1(p) -> s0(p)
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"p"})
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s0")
        
        checker = CTLModelChecker(ts)
        
        # EG(p): 所有状态都满足，因为可以永远保持在有 p 的路径上
        result = checker.check(eg(atom("p")))
        self.assertTrue(result.holds)
        self.assertEqual(len(result.satisfying_states), 2)
    
    def test_af_fixed_point(self):
        """测试 AF 的最小固定点计算"""
        ts = TransitionSystem()
        
        # s0 -> s1 -> s2(r)
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"q"})
        ts.add_state("s2", {"r"})
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s2")
        ts.add_transition("s2", "s2")
        
        checker = CTLModelChecker(ts)
        
        # AF(r): 所有状态都满足，因为最终都会到达 s2
        result = checker.check(af(atom("r")))
        self.assertTrue(result.holds)
        self.assertEqual(len(result.satisfying_states), 3)
    
    def test_eu_fixed_point(self):
        """测试 EU 的最小固定点计算"""
        ts = TransitionSystem()
        
        # s0(p) -> s1(p) -> s2(q)
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"p"})
        ts.add_state("s2", {"q"})
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s2")
        ts.add_transition("s2", "s2")
        
        checker = CTLModelChecker(ts)
        
        # E[p U q]: s0, s1, s2 都满足
        result = checker.check(eu(atom("p"), atom("q")))
        self.assertTrue(result.holds)
        self.assertEqual(len(result.satisfying_states), 3)


class TestStringParsingAndChecking(unittest.TestCase):
    """测试字符串解析和检查"""
    
    def test_parse_and_check(self):
        """测试解析字符串并检查"""
        ts = TransitionSystem()
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"q"})
        ts.add_initial_state("s0")
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s1")
        
        checker = CTLModelChecker(ts)
        
        # 从字符串解析并检查
        result = checker.check_string("EF(q)")
        self.assertTrue(result.holds)
        
        result2 = checker.check_string("AG(p)")
        self.assertFalse(result2.holds)


class TestCounterexampleGeneration(unittest.TestCase):
    """测试反例生成"""
    
    def test_counterexample_for_violation(self):
        """测试违反时的反例生成"""
        ts = TransitionSystem()
        ts.add_state("s0", {"p"})
        ts.add_state("s1", {"q"})
        ts.add_state("s2", {"r"})
        ts.add_initial_state("s0")
        
        ts.add_transition("s0", "s1")
        ts.add_transition("s1", "s2")
        
        checker = CTLModelChecker(ts)
        
        # AG(p): 不满足，因为 s1 和 s2 没有 p
        result = checker.check(ag(atom("p")))
        self.assertFalse(result.holds)
        # 反例路径应该存在
        self.assertIsNotNone(result.counterexample_path)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestCTLFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestCTLParser))
    suite.addTests(loader.loadTestsFromTestCase(TestCTLModelChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestPetersonMutualExclusion))
    suite.addTests(loader.loadTestsFromTestCase(TestFixedPointIteration))
    suite.addTests(loader.loadTestsFromTestCase(TestStringParsingAndChecking))
    suite.addTests(loader.loadTestsFromTestCase(TestCounterexampleGeneration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
