"""
实验三：NFA (非确定性有限自动机) 实现

本模块实现 NFA 的数据结构和模拟运行，支持：
- NFA 状态、转移、初始/接受状态的管理
- 从简化正则表达式构建 NFA
- NFA 的模拟运行（包括 ε-闭包计算）

为实验三的正则安全属性验证提供基础支持。
"""

from typing import Set, Dict, List, Tuple, Optional, FrozenSet
from dataclasses import dataclass, field
from collections import deque


@dataclass(frozen=True)
class NFAState:
    """
    NFA 状态类 - 不可变对象，可作为字典键使用
    
    状态由名称唯一标识
    """
    name: str
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NFAState):
            return False
        return self.name == other.name
    
    def __repr__(self) -> str:
        return f"NFAState({self.name})"


@dataclass
class NFATransition:
    """
    NFA 迁移类
    
    表示从源状态到目标状态的一个迁移，带有符号标签
    符号可以是原子命题或 ε（空转移）
    """
    source: NFAState
    target: NFAState
    symbol: Optional[str]  # None 表示 ε-转移
    
    def __repr__(self) -> str:
        if self.symbol is None:
            return f"{self.source.name} --ε--> {self.target.name}"
        return f"{self.source.name} --{self.symbol}--> {self.target.name}"


class NFA:
    """
    非确定性有限自动机 (NFA) 类
    
    形式化定义：A = (Q, Σ, δ, Q₀, F)
    - Q: 状态集合
    - Σ: 字母表（原子命题集合）
    - δ: Q × (Σ ∪ {ε}) → 2^Q: 转移函数
    - Q₀ ⊆ Q: 初始状态集合
    - F ⊆ Q: 接受状态集合
    
    使用邻接表存储转移关系，支持高效的遍历和查询。
    """
    
    def __init__(self):
        # 所有状态集合
        self._states: Dict[str, NFAState] = {}
        # 初始状态集合
        self._initial_states: Set[NFAState] = set()
        # 接受状态集合
        self._accept_states: Set[NFAState] = set()
        # 转移关系：状态 -> [(目标状态, 符号)]
        self._transitions: Dict[NFAState, List[Tuple[NFAState, Optional[str]]]] = {}
        # 字母表
        self._alphabet: Set[str] = set()
    
    # ==================== 状态管理 ====================
    
    def add_state(self, name: str, is_initial: bool = False, 
                  is_accept: bool = False) -> NFAState:
        """
        添加新状态
        
        Args:
            name: 状态名称（唯一标识）
            is_initial: 是否为初始状态
            is_accept: 是否为接受状态
            
        Returns:
            创建的状态对象
        """
        if name in self._states:
            state = self._states[name]
        else:
            state = NFAState(name)
            self._states[name] = state
            self._transitions[state] = []
        
        if is_initial:
            self._initial_states.add(state)
        if is_accept:
            self._accept_states.add(state)
        
        return state
    
    def get_state(self, name: str) -> Optional[NFAState]:
        """根据名称获取状态"""
        return self._states.get(name)
    
    def get_all_states(self) -> Set[NFAState]:
        """获取所有状态"""
        return set(self._states.values())
    
    def get_initial_states(self) -> Set[NFAState]:
        """获取所有初始状态"""
        return self._initial_states.copy()
    
    def get_accept_states(self) -> Set[NFAState]:
        """获取所有接受状态"""
        return self._accept_states.copy()
    
    def set_accept_state(self, state: NFAState):
        """设置接受状态"""
        self._accept_states.add(state)
    
    # ==================== 迁移管理 ====================
    
    def add_transition(self, source_name: str, target_name: str, 
                       symbol: Optional[str] = None):
        """
        添加迁移关系
        
        Args:
            source_name: 源状态名称
            target_name: 目标状态名称
            symbol: 符号标签（None 表示 ε-转移）
        """
        source = self.add_state(source_name)
        target = self.add_state(target_name)
        
        self._transitions[source].append((target, symbol))
        
        if symbol is not None:
            self._alphabet.add(symbol)
    
    def get_transitions(self, state: NFAState) -> List[Tuple[NFAState, Optional[str]]]:
        """获取从指定状态出发的所有迁移"""
        return self._transitions.get(state, [])
    
    def get_successors(self, state: NFAState, symbol: Optional[str] = None) -> Set[NFAState]:
        """
        获取状态在给定符号下的所有后继状态
        
        Args:
            state: 源状态
            symbol: 符号（None 表示获取所有 ε-转移目标）
            
        Returns:
            后继状态集合
        """
        successors = set()
        for target, sym in self._transitions.get(state, []):
            if sym == symbol:
                successors.add(target)
        return successors
    
    # ==================== ε-闭包计算 ====================
    
    def epsilon_closure(self, states: Set[NFAState]) -> Set[NFAState]:
        """
        计算状态的 ε-闭包
        
        ε-闭包是指从给定状态集合通过 ε-转移可以到达的所有状态集合
        
        Args:
            states: 初始状态集合
            
        Returns:
            ε-闭包（包含初始状态）
        """
        closure = set(states)
        queue = deque(states)
        
        while queue:
            current = queue.popleft()
            # 获取所有 ε-转移目标
            for target, symbol in self._transitions.get(current, []):
                if symbol is None and target not in closure:
                    closure.add(target)
                    queue.append(target)
        
        return closure
    
    def epsilon_closure_single(self, state: NFAState) -> Set[NFAState]:
        """计算单个状态的 ε-闭包"""
        return self.epsilon_closure({state})
    
    # ==================== NFA 模拟运行 ====================
    
    def step(self, states: Set[NFAState], symbol: str) -> Set[NFAState]:
        """
        NFA 单步转移
        
        从当前状态集合读取一个符号后到达的新状态集合
        
        Args:
            states: 当前状态集合
            symbol: 输入符号
            
        Returns:
            转移后的状态集合（已计算 ε-闭包）
        """
        # 先计算当前状态的 ε-闭包
        current_closure = self.epsilon_closure(states)
        
        # 在 ε-闭包上执行符号转移
        next_states: Set[NFAState] = set()
        for state in current_closure:
            for target, sym in self._transitions.get(state, []):
                if sym == symbol:
                    next_states.add(target)
        
        # 返回结果状态的 ε-闭包
        return self.epsilon_closure(next_states)
    
    def accepts(self, word: List[str]) -> bool:
        """
        检查 NFA 是否接受给定单词
        
        Args:
            word: 符号列表（原子命题序列）
            
        Returns:
            是否接受
        """
        # 从初始状态的 ε-闭包开始
        current_states = self.epsilon_closure(self._initial_states)
        
        # 逐个处理符号
        for symbol in word:
            current_states = self.step(current_states, symbol)
            if not current_states:
                return False  # 死状态
        
        # 检查是否有状态在接受状态集合中
        return bool(current_states & self._accept_states)
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, int]:
        """获取 NFA 统计信息"""
        transition_count = sum(len(t) for t in self._transitions.values())
        
        return {
            "states": len(self._states),
            "initial_states": len(self._initial_states),
            "accept_states": len(self._accept_states),
            "transitions": transition_count,
            "alphabet_size": len(self._alphabet)
        }
    
    # ==================== 输入/输出 ====================
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (f"NFA("
                f"states={stats['states']}, "
                f"initial={stats['initial_states']}, "
                f"accept={stats['accept_states']}, "
                f"transitions={stats['transitions']})")
    
    def print_structure(self):
        """打印 NFA 结构"""
        print("=" * 50)
        print("NFA 结构")
        print("=" * 50)
        print(f"\n初始状态: {[s.name for s in self._initial_states]}")
        print(f"接受状态: {[s.name for s in self._accept_states]}")
        print(f"\n状态 ({len(self._states)} 个):")
        for name in sorted(self._states.keys()):
            state = self._states[name]
            markers = []
            if state in self._initial_states:
                markers.append("initial")
            if state in self._accept_states:
                markers.append("accept")
            marker_str = f" [{', '.join(markers)}]" if markers else ""
            print(f"  - {name}{marker_str}")
        
        print(f"\n转移关系:")
        for state in sorted(self._transitions.keys(), key=lambda s: s.name):
            for target, symbol in self._transitions[state]:
                sym_str = symbol if symbol else "ε"
                print(f"  {state.name} --{sym_str}--> {target.name}")
        print("=" * 50)


# ==================== 从正则表达式构建 NFA ====================

class RegexToNFA:
    """
    从简化正则表达式构建 NFA
    
    支持的正则表达式语法：
    - 原子命题: a, b, red, green 等标识符
    - 连接: ab (a 后跟 b)
    - 选择: a|b (a 或 b)
    - Kleene 星: a* (零个或多个 a)
    - 括号: (a|b)*
    """
    
    def __init__(self):
        self._state_counter = 0
    
    def _new_state_name(self) -> str:
        """生成新状态名称"""
        name = f"q{self._state_counter}"
        self._state_counter += 1
        return name
    
    def build_atom(self, atom: str) -> NFA:
        """
        构建原子命题的 NFA
        
        Returns:
            NFA，包含一个初始状态和一个接受状态
        """
        nfa = NFA()
        initial = nfa.add_state(self._new_state_name(), is_initial=True)
        accept = nfa.add_state(self._new_state_name(), is_accept=True)
        nfa.add_transition(initial.name, accept.name, atom)
        return nfa
    
    def build_concat(self, nfa1: NFA, nfa2: NFA) -> NFA:
        """
        构建两个 NFA 的串联 (NFA1 · NFA2)
        
        将 NFA1 的接受状态通过 ε-转移连接到 NFA2 的初始状态
        """
        result = NFA()
        
        # 合并状态（重命名避免冲突）
        state_map1: Dict[NFAState, NFAState] = {}
        state_map2: Dict[NFAState, NFAState] = {}
        
        for state in nfa1.get_all_states():
            new_name = f"1_{state.name}"
            is_init = state in nfa1.get_initial_states()
            is_accept = state in nfa1.get_accept_states()
            new_state = result.add_state(new_name, is_init, is_accept)
            state_map1[state] = new_state
        
        for state in nfa2.get_all_states():
            new_name = f"2_{state.name}"
            is_init = state in nfa2.get_initial_states()
            is_accept = state in nfa2.get_accept_states()
            new_state = result.add_state(new_name, is_init, is_accept)
            state_map2[state] = new_state
        
        # 复制 NFA1 的转移
        for state in nfa1.get_all_states():
            for target, symbol in nfa1.get_transitions(state):
                result.add_transition(
                    state_map1[state].name,
                    state_map1[target].name,
                    symbol
                )
        
        # 复制 NFA2 的转移
        for state in nfa2.get_all_states():
            for target, symbol in nfa2.get_transitions(state):
                result.add_transition(
                    state_map2[state].name,
                    state_map2[target].name,
                    symbol
                )
        
        # 连接：NFA1 的接受状态 -> NFA2 的初始状态
        for accept1 in nfa1.get_accept_states():
            for init2 in nfa2.get_initial_states():
                result.add_transition(
                    state_map1[accept1].name,
                    state_map2[init2].name,
                    None  # ε-转移
                )
        
        # 清除 NFA1 接受状态的接受标记
        for accept1 in nfa1.get_accept_states():
            result._accept_states.discard(state_map1[accept1])
        
        # 清除 NFA2 初始状态的初始标记
        for init2 in nfa2.get_initial_states():
            result._initial_states.discard(state_map2[init2])
        
        return result
    
    def build_union(self, nfa1: NFA, nfa2: NFA) -> NFA:
        """
        构建两个 NFA 的并集 (NFA1 | NFA2)
        
        添加新的初始状态，通过 ε-转移连接到两个 NFA 的初始状态
        """
        result = NFA()
        
        # 创建新的初始状态
        new_initial = result.add_state(self._new_state_name(), is_initial=True)
        
        # 合并状态
        state_map1: Dict[NFAState, NFAState] = {}
        state_map2: Dict[NFAState, NFAState] = {}
        
        for state in nfa1.get_all_states():
            new_name = f"1_{state.name}"
            is_accept = state in nfa1.get_accept_states()
            new_state = result.add_state(new_name, is_accept=is_accept)
            state_map1[state] = new_state
        
        for state in nfa2.get_all_states():
            new_name = f"2_{state.name}"
            is_accept = state in nfa2.get_accept_states()
            new_state = result.add_state(new_name, is_accept=is_accept)
            state_map2[state] = new_state
        
        # 复制转移
        for state in nfa1.get_all_states():
            for target, symbol in nfa1.get_transitions(state):
                result.add_transition(
                    state_map1[state].name,
                    state_map1[target].name,
                    symbol
                )
        
        for state in nfa2.get_all_states():
            for target, symbol in nfa2.get_transitions(state):
                result.add_transition(
                    state_map2[state].name,
                    state_map2[target].name,
                    symbol
                )
        
        # 新初始状态通过 ε-转移连接到两个 NFA 的初始状态
        for init1 in nfa1.get_initial_states():
            result.add_transition(new_initial.name, state_map1[init1].name, None)
        for init2 in nfa2.get_initial_states():
            result.add_transition(new_initial.name, state_map2[init2].name, None)
        
        return result
    
    def build_star(self, nfa: NFA) -> NFA:
        """
        构建 NFA 的 Kleene 星 (NFA*)
        
        添加新的初始/接受状态，允许零次或多次重复
        """
        result = NFA()
        
        # 创建新的初始/接受状态
        new_initial = result.add_state(self._new_state_name(), 
                                       is_initial=True, is_accept=True)
        
        # 复制原 NFA 状态
        state_map: Dict[NFAState, NFAState] = {}
        for state in nfa.get_all_states():
            new_name = f"s_{state.name}"
            is_accept = state in nfa.get_accept_states()
            new_state = result.add_state(new_name, is_accept=is_accept)
            state_map[state] = new_state
        
        # 复制转移
        for state in nfa.get_all_states():
            for target, symbol in nfa.get_transitions(state):
                result.add_transition(
                    state_map[state].name,
                    state_map[target].name,
                    symbol
                )
        
        # 新初始状态通过 ε-转移连接到原 NFA 的初始状态
        for init in nfa.get_initial_states():
            result.add_transition(new_initial.name, state_map[init].name, None)
        
        # 原 NFA 的接受状态通过 ε-转移连接回原初始状态（循环）
        for accept in nfa.get_accept_states():
            for init in nfa.get_initial_states():
                result.add_transition(
                    state_map[accept].name,
                    state_map[init].name,
                    None
                )
            # 也可以直接到达新的接受状态
            result.add_transition(state_map[accept].name, new_initial.name, None)
        
        return result
    
    def parse_and_build(self, regex: str) -> NFA:
        """
        解析正则表达式并构建 NFA
        
        Args:
            regex: 正则表达式字符串
            
        Returns:
            对应的 NFA
        """
        self._state_counter = 0
        tokens = self._tokenize(regex)
        self._pos = 0
        self._tokens = tokens
        return self._parse_expr()
    
    def _tokenize(self, regex: str) -> List[str]:
        """词法分析：将正则表达式转换为词法单元列表
        
        注意：每个字符被视为独立的原子命题（单字符标识符）
        多字符标识符需要用空格分隔，如 "red yellow"
        """
        tokens = []
        i = 0
        while i < len(regex):
            char = regex[i]
            if char.isspace():
                i += 1
                continue
            elif char in '()|*':
                tokens.append(char)
                i += 1
            elif char.isalpha() or char == '_':
                # 读取完整的标识符（支持多字符原子命题如 "red"）
                j = i
                while j < len(regex) and (regex[j].isalnum() or regex[j] == '_'):
                    j += 1
                tokens.append(regex[i:j])
                i = j
            else:
                raise ValueError(f"非法字符: '{char}'")
        return tokens
    
    def _current(self) -> Optional[str]:
        """获取当前词法单元"""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None
    
    def _advance(self) -> Optional[str]:
        """前进到下一个词法单元"""
        token = self._current()
        self._pos += 1
        return token
    
    def _parse_expr(self) -> NFA:
        """解析表达式（处理 | 运算符）"""
        left = self._parse_concat()
        
        while self._current() == '|':
            self._advance()
            right = self._parse_concat()
            left = self.build_union(left, right)
        
        return left
    
    def _parse_concat(self) -> NFA:
        """解析连接（隐式连接）"""
        atoms = []
        
        while self._current() and self._current() not in ')|':
            atoms.append(self._parse_atom())
        
        if not atoms:
            # 空表达式，返回接受空串的 NFA
            nfa = NFA()
            state = nfa.add_state(self._new_state_name(), 
                                  is_initial=True, is_accept=True)
            return nfa
        
        result = atoms[0]
        for atom in atoms[1:]:
            result = self.build_concat(result, atom)
        
        return result
    
    def _parse_atom(self) -> NFA:
        """解析原子（基本单元）"""
        token = self._current()
        
        if token is None:
            raise ValueError("意外的表达式结束")
        
        if token == '(':
            self._advance()
            nfa = self._parse_expr()
            if self._current() != ')':
                raise ValueError("缺少右括号")
            self._advance()
        elif token.isalnum() or token[0] == '_':
            self._advance()
            nfa = self.build_atom(token)
        else:
            raise ValueError(f"意外的词法单元: '{token}'")
        
        # 处理 Kleene 星
        while self._current() == '*':
            self._advance()
            nfa = self.build_star(nfa)
        
        return nfa


def build_nfa_from_regex(regex: str) -> NFA:
    """
    便捷函数：从正则表达式构建 NFA
    
    Args:
        regex: 正则表达式字符串
        
    Returns:
        对应的 NFA
        
    Examples:
        >>> nfa = build_nfa_from_regex("red yellow*")
        >>> nfa.accepts(["red", "yellow", "yellow"])
        True
    """
    builder = RegexToNFA()
    return builder.parse_and_build(regex)
