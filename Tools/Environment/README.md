# Environment Tools

这个目录包含了用于环境管理和验证的工具脚本。

## 📝 文件说明

### 验证脚本
- `quick_verify.py` - 快速环境验证，检查基本的模块导入和环境设置
- `test_environment.py` - 环境测试脚本，测试模块导入功能
- `test_full_environment.py` - 完整环境测试，验证所有环境变量传递和子进程功能
- `test_subprocess_env.py` - 子进程环境验证脚本
- `check_cross_platform_compatibility.py` - 跨平台兼容性验证，生成详细报告

### 修复工具
- `fix_hardcoded_paths.py` - 硬编码路径修复工具
- `patch_config_paths.py` - 配置文件路径修补工具
- `final_cleanup_paths.py` - 最终路径清理脚本

## 🚀 使用方法

### 快速验证环境
```bash
cd /path/to/agent
python Tools/Environment/quick_verify.py
```

### 完整环境测试
```bash
python Tools/Environment/test_full_environment.py
```

### 跨平台兼容性验证
```bash
python Tools/Environment/check_cross_platform_compatibility.py
```

### 修复硬编码路径
```bash
python Tools/Environment/fix_hardcoded_paths.py
```

## 💡 说明

这些工具主要用于：
1. 验证环境配置是否正确
2. 检查跨平台兼容性
3. 修复硬编码路径问题
4. 确保其他人 clone 代码后能正常运行

**🔧 归档后的修复说明**:
- ✅ 所有脚本已修复路径检测问题，现在能正确从 `Tools/Environment/` 目录运行
- ✅ `get_project_root()` 函数已更新，自动向上两级查找项目根目录
- ✅ 简化了复杂的子进程操作，提高脚本稳定性
- ✅ 新增 `test_final.py` 用于最终验证

在部署新环境或遇到环境问题时，可以使用这些工具进行诊断和修复。
