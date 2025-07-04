"""
模块依赖解析工具

处理内部模块之间的依赖关系和启动顺序。
"""
from logging import Logger
from typing import List, Dict, Set, Any, Tuple, Optional
from collections import defaultdict, deque
from ..exceptions import ModuleDependencyError


class DependencyResolver:
    """依赖关系解析器"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)
    
    def add_dependency(self, module: str, depends_on: str):
        """
        添加模块依赖关系
        
        Args:
            module: 依赖者模块
            depends_on: 被依赖的模块
        """
        self.dependencies[module].add(depends_on)
        self.reverse_dependencies[depends_on].add(module)
        self.logger.debug(f"Added dependency: {module} depends on {depends_on}")
    
    def add_dependencies(self, dependencies: Dict[str, List[str]]):
        """
        批量添加依赖关系
        
        Args:
            dependencies: {module: [dependency1, dependency2, ...]}
        """
        for module, deps in dependencies.items():
            for dep in deps:
                self.add_dependency(module, dep)
    
    def remove_dependency(self, module: str, depends_on: str):
        """移除依赖关系"""
        self.dependencies[module].discard(depends_on)
        self.reverse_dependencies[depends_on].discard(module)
        self.logger.debug(f"Removed dependency: {module} no longer depends on {depends_on}")
    
    def get_dependencies(self, module: str) -> Set[str]:
        """获取模块的所有直接依赖"""
        return self.dependencies.get(module, set())
    
    def get_dependents(self, module: str) -> Set[str]:
        """获取依赖于指定模块的所有模块"""
        return self.reverse_dependencies.get(module, set())
    
    def has_circular_dependency(self) -> Tuple[bool, Optional[List[str]]]:
        """
        检查是否存在循环依赖
        
        Returns:
            Tuple[bool, Optional[List[str]]]: (是否有循环依赖, 循环路径)
        """
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            if node in rec_stack:
                # 找到循环，返回循环路径
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dependency in self.dependencies.get(node, set()):
                cycle = dfs(dependency, path[:])
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        # 检查所有模块
        all_modules = set(self.dependencies.keys()) | set(self.reverse_dependencies.keys())
        for module in all_modules:
            if module not in visited:
                cycle = dfs(module, [])
                if cycle:
                    return True, cycle
        
        return False, None
    
    def resolve_startup_order(self, modules: List[str]) -> List[str]:
        """
        解析模块启动顺序（拓扑排序）
        
        Args:
            modules: 要启动的模块列表
            
        Returns:
            按依赖关系排序的模块列表
            
        Raises:
            ModuleDependencyError: 当存在循环依赖时
        """
        # 检查循环依赖
        has_cycle, cycle_path = self.has_circular_dependency()
        if has_cycle and cycle_path:
            raise ModuleDependencyError(
                "CIRCULAR_DEPENDENCY",
                "",
                f"Circular dependency detected: {' -> '.join(cycle_path)}"
            )
        
        # 过滤出实际需要的模块及其依赖
        needed_modules = set(modules)
        for module in modules:
            needed_modules.update(self._get_all_dependencies(module))
        
        # 构建子图
        subgraph = {}
        in_degree = {}
        
        for module in needed_modules:
            subgraph[module] = set()
            in_degree[module] = 0
        
        for module in needed_modules:
            for dep in self.dependencies.get(module, set()):
                if dep in needed_modules:
                    subgraph[dep].add(module)
                    in_degree[module] += 1
        
        # 拓扑排序
        queue = deque([module for module in needed_modules if in_degree[module] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for dependent in subgraph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # 检查是否所有模块都被处理
        if len(result) != len(needed_modules):
            unprocessed = needed_modules - set(result)
            raise ModuleDependencyError(
                "DEPENDENCY_RESOLUTION_FAILED",
                "",
                f"Unable to resolve dependencies for modules: {unprocessed}"
            )
        
        # 只返回原始请求的模块（保持顺序）
        ordered_modules = [module for module in result if module in modules]
        
        self.logger.info(f"Resolved startup order: {ordered_modules}")
        return ordered_modules
    
    def resolve_shutdown_order(self, modules: List[str]) -> List[str]:
        """
        解析模块关闭顺序（启动顺序的逆序）
        
        Args:
            modules: 要关闭的模块列表
            
        Returns:
            按依赖关系排序的模块列表（逆序）
        """
        startup_order = self.resolve_startup_order(modules)
        shutdown_order = list(reversed(startup_order))
        
        self.logger.info(f"Resolved shutdown order: {shutdown_order}")
        return shutdown_order
    
    def _get_all_dependencies(self, module: str) -> Set[str]:
        """递归获取模块的所有依赖（包括间接依赖）"""
        all_deps = set()
        to_visit = deque([module])
        visited = set()
        
        while to_visit:
            current = to_visit.popleft()
            if current in visited:
                continue
            
            visited.add(current)
            deps = self.dependencies.get(current, set())
            all_deps.update(deps)
            to_visit.extend(deps)
        
        return all_deps
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取完整的依赖关系图"""
        return {module: list(deps) for module, deps in self.dependencies.items()}
    
    def clear_dependencies(self):
        """清空所有依赖关系"""
        self.dependencies.clear()
        self.reverse_dependencies.clear()
        self.logger.debug("Cleared all dependencies")
