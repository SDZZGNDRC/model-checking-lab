"""
Peterson 互斥算法的 Transition System 模型

Peterson 算法是一个经典的并发互斥算法，用于协调两个进程对临界区的访问。
本模块将其建模为 Transition System，用于验证互斥性质。

算法伪代码：
```
# 共享变量
turn = 0  # 轮到哪个进程
flag = [False, False]  # 进程是否想进入临界区

# 进程 i (i = 0 或 1)
while True:
    # 非临界区 (noncrit)
    flag[i] = True
    turn = 1 - i
    while flag[1-i] and turn == 1-i:
        pass  # 等待
    # 临界区 (crit)
    flag[i] = False
```

状态表示：(l0, l1, turn, flag0, flag1)
- l0: 进程 0 的位置 (noncrit, wait, crit)
- l1: 进程 1 的位置 (noncrit, wait, crit)
- turn: 0 或 1
- flag0: True 或 False
- flag1: True 或 False
"""

from transition_system import TransitionSystem, State


class PetersonTS:
    """
    Peterson 互斥算法的 Transition System 构造器
    """
    
    def __init__(self):
        self.ts = TransitionSystem()
        self._build_ts()
    
    def _state_name(self, loc0: str, loc1: str, turn: int, flag0: bool, flag1: bool) -> str:
        """生成状态名称"""
        f0 = "T" if flag0 else "F"
        f1 = "T" if flag1 else "F"
        return f"({loc0},{loc1},{turn},{f0},{f1})"
    
    def _add_state_with_labels(self, loc0: str, loc1: str, turn: int, flag0: bool, flag1: bool):
        """添加带标签的状态"""
        name = self._state_name(loc0, loc1, turn, flag0, flag1)
        
        # 构建标签集合
        labels = set()
        if loc0 == "crit":
            labels.add("crit0")
        if loc1 == "crit":
            labels.add("crit1")
        if loc0 == "wait":
            labels.add("wait0")
        if loc1 == "wait":
            labels.add("wait1")
        
        return self.ts.add_state(name, labels)
    
    def _build_ts(self):
        """
        构建 Peterson 算法的完整 Transition System
        
        每个进程有三个位置：
        - noncrit: 非临界区
        - wait: 等待进入临界区
        - crit: 临界区
        """
        # 遍历所有可能的状态组合
        locations = ["noncrit", "wait", "crit"]
        
        for loc0 in locations:
            for loc1 in locations:
                for turn in [0, 1]:
                    for flag0 in [False, True]:
                        for flag1 in [False, True]:
                            self._add_state_with_labels(loc0, loc1, turn, flag0, flag1)
        
        # 添加迁移关系
        for loc0 in locations:
            for loc1 in locations:
                for turn in [0, 1]:
                    for flag0 in [False, True]:
                        for flag1 in [False, True]:
                            self._add_transitions_for_state(loc0, loc1, turn, flag0, flag1)
        
        # 设置初始状态：两个进程都在非临界区，turn=0，flag 都为 False
        self.ts.add_initial_state(self._state_name("noncrit", "noncrit", 0, False, False))
    
    def _add_transitions_for_state(self, loc0: str, loc1: str, turn: int, flag0: bool, flag1: bool):
        """为给定状态添加所有可能的迁移"""
        current = self._state_name(loc0, loc1, turn, flag0, flag1)
        
        # 进程 0 的迁移
        if loc0 == "noncrit":
            # noncrit -> wait: 设置 flag[0]=True, turn=1
            next_state = self._state_name("wait", loc1, 1, True, flag1)
            self.ts.add_transition(current, next_state, "p0_request")
        
        elif loc0 == "wait":
            # wait -> crit: 当 flag[1]=False 或 turn=0 时
            if not flag1 or turn == 0:
                next_state = self._state_name("crit", loc1, turn, flag0, flag1)
                self.ts.add_transition(current, next_state, "p0_enter")
            # wait -> wait: 自旋等待（可选，用于建模忙等待）
            # 这里我们省略自旋等待，直接允许进入
        
        elif loc0 == "crit":
            # crit -> noncrit: 设置 flag[0]=False
            next_state = self._state_name("noncrit", loc1, turn, False, flag1)
            self.ts.add_transition(current, next_state, "p0_exit")
        
        # 进程 1 的迁移
        if loc1 == "noncrit":
            # noncrit -> wait: 设置 flag[1]=True, turn=0
            next_state = self._state_name(loc0, "wait", 0, flag0, True)
            self.ts.add_transition(current, next_state, "p1_request")
        
        elif loc1 == "wait":
            # wait -> crit: 当 flag[0]=False 或 turn=1 时
            if not flag0 or turn == 1:
                next_state = self._state_name(loc0, "crit", turn, flag0, flag1)
                self.ts.add_transition(current, next_state, "p1_enter")
        
        elif loc1 == "crit":
            # crit -> noncrit: 设置 flag[1]=False
            next_state = self._state_name(loc0, "noncrit", turn, flag0, False)
            self.ts.add_transition(current, next_state, "p1_exit")
    
    def get_ts(self) -> TransitionSystem:
        """获取构建好的 Transition System"""
        return self.ts


def create_simplified_peterson() -> TransitionSystem:
    """
    创建简化的 Peterson 算法模型（手工构建，用于教学演示）
    
    这个简化版本只包含关键状态，便于手工验证可达状态数。
    """
    ts = TransitionSystem()
    
    # 状态定义 (l0, l1, turn)
    # l0, l1 ∈ {n (noncrit), w (wait), c (crit)}
    # turn ∈ {0, 1}
    
    states = [
        # 格式: (name, labels)
        ("s0", "n,n,0", set()),           # 初始状态
        ("s1", "n,w,0", {"wait1"}),       # p1 请求
        ("s2", "w,n,1", {"wait0"}),       # p0 请求
        ("s3", "w,w,0", {"wait0", "wait1"}),  # 都请求，turn=0
        ("s4", "w,w,1", {"wait0", "wait1"}),  # 都请求，turn=1
        ("s5", "c,n,1", {"crit0"}),       # p0 进入临界区
        ("s6", "n,c,0", {"crit1"}),       # p1 进入临界区
        ("s7", "c,w,1", {"crit0", "wait1"}),  # p0 在临界区，p1 等待
        ("s8", "w,c,0", {"wait0", "crit1"}),  # p1 在临界区，p0 等待
    ]
    
    for name, desc, labels in states:
        ts.add_state(name, labels)
    
    # 设置初始状态
    ts.add_initial_state("s0")
    
    # 添加迁移
    transitions = [
        # 从 s0: (n,n,0)
        ("s0", "s2", "p0_request"),  # p0 请求
        ("s0", "s1", "p1_request"),  # p1 请求
        
        # 从 s1: (n,w,0)
        ("s1", "s6", "p1_enter"),    # p1 可以进入 (turn=0)
        ("s1", "s4", "p0_request"),  # p0 请求
        
        # 从 s2: (w,n,1)
        ("s2", "s5", "p0_enter"),    # p0 可以进入 (turn=1)
        ("s2", "s4", "p1_request"),  # p1 请求
        
        # 从 s3: (w,w,0) - p1 可以进入
        ("s3", "s8", "p1_enter"),
        
        # 从 s4: (w,w,1) - p0 可以进入
        ("s4", "s7", "p0_enter"),
        
        # 从 s5: (c,n,1) - p0 退出
        ("s5", "s0", "p0_exit"),
        
        # 从 s6: (n,c,0) - p1 退出
        ("s6", "s0", "p1_exit"),
        
        # 从 s7: (c,w,1) - p0 退出
        ("s7", "s1", "p0_exit"),
        
        # 从 s8: (w,c,0) - p1 退出
        ("s8", "s2", "p1_exit"),
    ]
    
    for src, dst, action in transitions:
        ts.add_transition(src, dst, action)
    
    return ts


def verify_mutual_exclusion(ts: TransitionSystem) -> bool:
    """
    验证互斥性质：两个进程不能同时在临界区
    
    性质：¬(crit0 ∧ crit1)
    """
    reachable = ts.compute_reachable_states()
    
    print("\n验证互斥性质: ¬(crit0 ∧ crit1)")
    print("-" * 40)
    
    violations = []
    for state in reachable:
        has_crit0 = state.has_label("crit0")
        has_crit1 = state.has_label("crit1")
        
        if has_crit0 and has_crit1:
            violations.append(state)
            print(f"  违反: {state}")
    
    if violations:
        print(f"\n  结果: 失败！发现 {len(violations)} 个违反状态")
        return False
    else:
        print("  结果: 通过！没有违反互斥性质的状态")
        return True


if __name__ == "__main__":
    print("=" * 60)
    print("Peterson 互斥算法 - Transition System 模型")
    print("=" * 60)
    
    # 使用简化模型
    print("\n【简化模型】")
    ts = create_simplified_peterson()
    ts.print_reachable_graph()
    
    stats = ts.get_statistics()
    print(f"\n统计信息:")
    print(f"  总状态数: {stats['total_states']}")
    print(f"  可达状态数: {stats['reachable_states']}")
    print(f"  总迁移数: {stats['total_transitions']}")
    print(f"  可达迁移数: {stats['reachable_transitions']}")
    
    # 验证互斥性质
    verify_mutual_exclusion(ts)
    
    # 使用完整模型
    print("\n" + "=" * 60)
    print("【完整 Peterson 模型】")
    print("=" * 60)
    
    peterson = PetersonTS()
    ts_full = peterson.get_ts()
    ts_full.print_reachable_graph()
    
    stats_full = ts_full.get_statistics()
    print(f"\n统计信息:")
    print(f"  总状态数: {stats_full['total_states']}")
    print(f"  可达状态数: {stats_full['reachable_states']}")
    print(f"  总迁移数: {stats_full['total_transitions']}")
    print(f"  可达迁移数: {stats_full['reachable_transitions']}")
    
    # 验证互斥性质
    verify_mutual_exclusion(ts_full)
