"""
程序图 (Program Graph) 实现

程序图是对程序控制流的抽象表示，形式化定义为：
PG = (Loc, Act, Effect, →, Loc0, g0)
- Loc: 位置集合（程序点）
- Act: 动作集合（语句）
- Effect: Act × Eval(Var) → Eval(Var) 效果函数
- →: 带守卫条件的迁移关系
- Loc0: 初始位置
- g0: 初始条件

本模块支持将程序图展开为 Transition System，便于模型检查。
"""

from typing import Set, Dict, List, Tuple, Optional, Any, FrozenSet, Callable
from dataclasses import dataclass, field
from itertools import product
import copy

from transition_system import TransitionSystem


@dataclass(frozen=True)
class Location:
    """
    程序位置（程序点）
    
    表示程序执行过程中的一个控制点。
    """
    name: str
    
    def __repr__(self) -> str:
        return f"Loc({self.name})"
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Location):
            return False
        return self.name == other.name


@dataclass
class Action:
    """
    动作（语句）
    
    表示程序中的一条可执行语句。
    
    Attributes:
        name: 动作的标识名称
        effect: 效果函数，字典形式表示变量赋值 {var_name: expression_str}
        guard: 守卫条件（字符串形式的布尔表达式）
    """
    name: str
    effect: Dict[str, str] = field(default_factory=dict)
    guard: str = "True"
    
    def __repr__(self) -> str:
        if self.guard != "True":
            return f"[{self.guard}] {self.name}"
        return self.name
    
    def involves_variables(self, variables: Set[str]) -> bool:
        """检查该动作是否涉及指定的变量"""
        # 检查效果中是否修改了这些变量
        for var in self.effect:
            if var in variables:
                return True
        # 检查守卫条件中是否使用了这些变量
        for var in variables:
            if var in self.guard:
                return True
        # 检查效果表达式中是否使用了这些变量
        for expr in self.effect.values():
            for var in variables:
                if var in str(expr):
                    return True
        return False


@dataclass
class PGTransition:
    """
    程序图迁移
    
    表示从源位置到目标位置的一条迁移，带有守卫条件和动作。
    """
    source: Location
    guard: str
    action: Action
    target: Location
    
    def __repr__(self) -> str:
        if self.guard != "True":
            return f"{self.source.name} --[{self.guard}] {self.action.name}--> {self.target.name}"
        return f"{self.source.name} --{self.action.name}--> {self.target.name}"


class ProgramGraph:
    """
    程序图 (Program Graph) 类
    
    形式化定义：PG = (Loc, Act, Effect, →, Loc0, g0)
    
    支持：
    - 添加位置和迁移
    - 声明变量及其取值域
    - 标记共享变量
    - 展开为 Transition System
    """
    
    def __init__(self, name: str = "PG"):
        self.name = name
        
        # 位置集合
        self._locations: Dict[str, Location] = {}
        
        # 初始位置
        self._initial_location: Optional[Location] = None
        
        # 迁移关系: source -> [(guard, action, target)]
        self._transitions: Dict[Location, List[PGTransition]] = {}
        
        # 变量声明: var_name -> domain (可能取值集合)
        self._variables: Dict[str, Set[Any]] = {}
        
        # 初始变量值
        self._initial_values: Dict[str, Any] = {}
        
        # 共享变量集合
        self._shared_vars: Set[str] = set()
        
        # 标签函数: 位置 -> 原子命题集合
        self._location_labels: Dict[Location, Set[str]] = {}
    
    # ==================== 位置管理 ====================
    
    def add_location(self, name: str, labels: Optional[Set[str]] = None) -> Location:
        """
        添加程序位置
        
        Args:
            name: 位置名称
            labels: 该位置关联的原子命题标签
            
        Returns:
            创建的 Location 对象
        """
        if name in self._locations:
            loc = self._locations[name]
        else:
            loc = Location(name)
            self._locations[name] = loc
            self._transitions[loc] = []
        
        if labels:
            if loc not in self._location_labels:
                self._location_labels[loc] = set()
            self._location_labels[loc].update(labels)
        
        return loc
    
    def set_initial_location(self, name: str) -> Location:
        """设置初始位置"""
        loc = self.add_location(name)
        self._initial_location = loc
        return loc
    
    def get_location(self, name: str) -> Optional[Location]:
        """根据名称获取位置"""
        return self._locations.get(name)
    
    def get_locations(self) -> Set[Location]:
        """获取所有位置"""
        return set(self._locations.values())
    
    def get_initial_location(self) -> Optional[Location]:
        """获取初始位置"""
        return self._initial_location
    
    def get_location_labels(self, loc: Location) -> Set[str]:
        """获取位置的标签"""
        return self._location_labels.get(loc, set())
    
    # ==================== 迁移管理 ====================
    
    def add_transition(self, source_name: str, target_name: str,
                       action: Action, guard: str = "True") -> PGTransition:
        """
        添加迁移关系
        
        Args:
            source_name: 源位置名称
            target_name: 目标位置名称
            action: 动作
            guard: 守卫条件
            
        Returns:
            创建的 PGTransition 对象
        """
        source = self.add_location(source_name)
        target = self.add_location(target_name)
        
        transition = PGTransition(source, guard, action, target)
        self._transitions[source].append(transition)
        
        return transition
    
    def get_transitions(self, loc: Location) -> List[PGTransition]:
        """获取从指定位置出发的所有迁移"""
        return self._transitions.get(loc, [])
    
    def get_all_transitions(self) -> List[PGTransition]:
        """获取所有迁移"""
        result = []
        for trans_list in self._transitions.values():
            result.extend(trans_list)
        return result
    
    # ==================== 变量管理 ====================
    
    def declare_variable(self, name: str, domain: Set[Any],
                        initial_value: Any, is_shared: bool = False):
        """
        声明变量
        
        Args:
            name: 变量名
            domain: 取值域
            initial_value: 初始值
            is_shared: 是否为共享变量
        """
        self._variables[name] = set(domain)
        self._initial_values[name] = initial_value
        
        if is_shared:
            self._shared_vars.add(name)
    
    def get_variables(self) -> Dict[str, Set[Any]]:
        """获取所有变量及其取值域"""
        return self._variables.copy()
    
    def get_shared_variables(self) -> Set[str]:
        """获取共享变量集合"""
        return self._shared_vars.copy()
    
    def get_initial_values(self) -> Dict[str, Any]:
        """获取初始变量值"""
        return self._initial_values.copy()
    
    def is_shared_variable(self, name: str) -> bool:
        """检查是否为共享变量"""
        return name in self._shared_vars
    
    # ==================== 展开为 Transition System ====================
    
    def unfold_to_ts(self, include_unreachable: bool = False) -> TransitionSystem:
        """
        将程序图展开为迁移系统
        
        状态空间: S = Loc × Eval(Var)
        - 每个状态 = (位置, 变量赋值)
        - 初始状态 = (Loc0, 初始变量值)
        
        Args:
            include_unreachable: 是否包含不可达状态
            
        Returns:
            展开后的 TransitionSystem
        """
        ts = TransitionSystem()
        
        if self._initial_location is None:
            return ts
        
        # 生成所有可能的变量赋值
        all_valuations = self._generate_all_valuations()
        
        # 创建初始状态
        initial_valuation = tuple(sorted(self._initial_values.items()))
        initial_state_name = self._make_state_name(
            self._initial_location, dict(initial_valuation)
        )
        
        # 使用 BFS 只展开可达状态
        if not include_unreachable:
            self._unfold_reachable(ts, initial_state_name)
        else:
            self._unfold_all(ts, all_valuations)
        
        return ts
    
    def _generate_all_valuations(self) -> List[Dict[str, Any]]:
        """生成所有可能的变量赋值组合"""
        if not self._variables:
            return [{}]
        
        var_names = list(self._variables.keys())
        domains = [list(self._variables[name]) for name in var_names]
        
        valuations = []
        for combo in product(*domains):
            valuation = {var_names[i]: combo[i] for i in range(len(var_names))}
            valuations.append(valuation)
        
        return valuations
    
    def _make_state_name(self, loc: Location, valuation: Dict[str, Any]) -> str:
        """生成状态名称: (位置, 变量赋值)"""
        val_str = ",".join(f"{k}={v}" for k, v in sorted(valuation.items()))
        if val_str:
            return f"({loc.name},{val_str})"
        return f"({loc.name})"
    
    def _parse_state_name(self, state_name: str) -> Tuple[str, Dict[str, Any]]:
        """从状态名称解析位置和变量赋值
        
        状态名称格式: (loc_name,var1=val1,var2=val2,...)
        对于组合位置: ((A,B),var1=val1,...)
        """
        # 移除最外层括号
        content = state_name[1:-1]
        
        # 找到位置名称的结束位置
        # 如果位置名称本身包含括号（组合位置），需要特殊处理
        if content.startswith('('):
            # 组合位置: ((A,B),var=val)
            # 找到匹配的右括号
            depth = 0
            loc_end = 0
            for i, c in enumerate(content):
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        loc_end = i + 1
                        break
            loc_name = content[:loc_end]
            rest = content[loc_end:]
        else:
            # 简单位置: (A,var=val)
            # 找到第一个通带等号的逗号
            first_eq = content.find('=')
            if first_eq == -1:
                # 没有变量
                loc_name = content
                rest = ''
            else:
                # 找到等号前的最后一个逗号
                last_comma = content.rfind(',', 0, first_eq)
                if last_comma == -1:
                    loc_name = content
                    rest = ''
                else:
                    loc_name = content[:last_comma]
                    rest = content[last_comma:]
        
        # 解析变量
        valuation = {}
        if rest:
            # 移除前导逗号
            if rest.startswith(','):
                rest = rest[1:]
            for part in rest.split(','):
                if '=' in part:
                    var, val_str = part.split('=', 1)
                    try:
                        val = eval(val_str)
                    except:
                        val = val_str
                    valuation[var] = val
        
        return loc_name, valuation
    
    def _evaluate_guard(self, guard: str, valuation: Dict[str, Any]) -> bool:
        """在给定变量赋值下求值守卫条件"""
        if guard == "True":
            return True
        if guard == "False":
            return False
        
        try:
            return bool(eval(guard, {"__builtins__": {}}, valuation))
        except:
            return False
    
    def _apply_effect(self, effect: Dict[str, str], 
                      valuation: Dict[str, Any]) -> Dict[str, Any]:
        """应用动作效果，返回新的变量赋值"""
        new_valuation = valuation.copy()
        
        for var, expr in effect.items():
            try:
                new_value = eval(expr, {"__builtins__": {}}, valuation)
                new_valuation[var] = new_value
            except Exception as e:
                # 如果求值失败，保持原值
                pass
        
        return new_valuation
    
    def _get_state_labels(self, loc: Location, valuation: Dict[str, Any]) -> Set[str]:
        """获取状态的原子命题标签"""
        labels = set()
        
        # 添加位置标签
        labels.update(self.get_location_labels(loc))
        
        # 可以根据变量值添加额外标签
        # 例如，如果某个变量有特定值，可以添加对应标签
        
        return labels
    
    def _unfold_reachable(self, ts: TransitionSystem, initial_state_name: str):
        """只展开可达状态（BFS）"""
        from collections import deque
        
        # 解析初始状态
        init_loc_name, init_valuation = self._parse_state_name(initial_state_name)
        init_loc = self.get_location(init_loc_name)
        
        # 添加初始状态
        init_labels = self._get_state_labels(init_loc, init_valuation)
        ts.add_state(initial_state_name, init_labels if init_labels else None)
        ts.add_initial_state(initial_state_name)
        
        # BFS 队列: (状态名称, 位置, 变量赋值)
        queue = deque([(initial_state_name, init_loc, init_valuation)])
        visited = {initial_state_name}
        
        while queue:
            current_state_name, current_loc, current_valuation = queue.popleft()
            
            # 处理当前位置的所有迁移
            for trans in self.get_transitions(current_loc):
                # 检查守卫条件
                if not self._evaluate_guard(trans.guard, current_valuation):
                    continue
                
                # 应用效果函数
                new_valuation = self._apply_effect(trans.action.effect, current_valuation)
                
                # 验证新值在域内
                valid = True
                for var, val in new_valuation.items():
                    if var in self._variables and val not in self._variables[var]:
                        valid = False
                        break
                
                if not valid:
                    continue
                
                # 生成目标状态
                target_state_name = self._make_state_name(trans.target, new_valuation)
                target_labels = self._get_state_labels(trans.target, new_valuation)
                
                # 添加状态（先添加状态，再添加迁移）
                ts.add_state(target_state_name, target_labels if target_labels else None)
                ts.add_transition(current_state_name, target_state_name, trans.action.name)
                
                # 如果是新状态，加入队列
                if target_state_name not in visited:
                    visited.add(target_state_name)
                    queue.append((target_state_name, trans.target, new_valuation))
    
    def _unfold_all(self, ts: TransitionSystem, all_valuations: List[Dict[str, Any]]):
        """展开所有状态（包括不可达状态）"""
        # 创建所有状态
        for loc in self.get_locations():
            for valuation in all_valuations:
                state_name = self._make_state_name(loc, valuation)
                labels = self._get_state_labels(loc, valuation)
                ts.add_state(state_name, labels)
        
        # 设置初始状态
        if self._initial_location:
            initial_state_name = self._make_state_name(
                self._initial_location, self._initial_values
            )
            ts.add_initial_state(initial_state_name)
        
        # 添加所有迁移
        for loc in self.get_locations():
            for valuation in all_valuations:
                source_name = self._make_state_name(loc, valuation)
                
                for trans in self.get_transitions(loc):
                    if not self._evaluate_guard(trans.guard, valuation):
                        continue
                    
                    new_valuation = self._apply_effect(trans.action.effect, valuation)
                    
                    # 验证新值在域内
                    valid = True
                    for var, val in new_valuation.items():
                        if var in self._variables and val not in self._variables[var]:
                            valid = False
                            break
                    
                    if not valid:
                        continue
                    
                    target_name = self._make_state_name(trans.target, new_valuation)
                    ts.add_transition(source_name, target_name, trans.action.name)
    
    # ==================== 工具方法 ====================
    
    def __repr__(self) -> str:
        return (f"ProgramGraph({self.name}, "
                f"locs={len(self._locations)}, "
                f"vars={list(self._variables.keys())})")
    
    def print_info(self):
        """打印程序图信息"""
        print(f"程序图: {self.name}")
        print(f"  位置数: {len(self._locations)}")
        print(f"  初始位置: {self._initial_location}")
        print(f"  变量: {list(self._variables.keys())}")
        print(f"  共享变量: {self._shared_vars}")
        print(f"  迁移数: {len(self.get_all_transitions())}")
        
        print("\n  迁移关系:")
        for trans in self.get_all_transitions():
            print(f"    {trans}")
