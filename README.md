# Git对象恢复与分析工具

一个简单易用的Git对象提取和分析工具，帮你从`.git`目录中恢复文件并智能分析。

## 🎯 主要功能

- **文件恢复**：从`.git/objects`中提取所有文件内容
- **智能筛选**：使用AI模型自动识别有价值的文件（这一步不一定要ai，但是未实现非ai的识别）
- **版本整理**：AI推测同一文件的版本历史并整理
- 图形和命令行，长文件处理

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 图形界面
```bash
python run_gui.py
```

**注意**：GUI界面会调用命令行工具，所有执行过程的输出将显示在系统终端中，方便实时查看进度和调试。

### 命令行使用

#### 一键处理（推荐）
```bash
# 使用默认时间范围（当天2点到现在）
python main.py full --git-dir "D:\repo\.git" 

# 指定时间范围
python main.py full --git-dir "D:\repo\.git" --start-time "2024-07-15 02:00" --end-time "2024-12-31 23:59" 

# 快速模式（一次性分组 + 并行比较）
python main.py full --git-dir "D:\repo\.git" --fast 
```

#### 分步处理
```bash
# 只提取文件
python main.py extract --git-dir "D:\repo\.git" --start-time "2024-07-15 02:00"

# 只做AI分析
python main.py analyze 

# 只做版本分组
python main.py group 

# 只做版本比较并组织
python main.py compare 

# 迭代模式（对analyzed_files执行迭代式版本分析）
python main.py iterate 
```

## 📋 命令说明

### 子命令

- **`extract`** - 从Git对象提取文件
  - 必需参数：`--git-dir`
  - 可选参数：`--start-time`, `--end-time`

- **`analyze`** - 对已提取文件做AI分析
  - 可选参数：`--input-dir` (默认: extracted_objects)

- **`group`** - 基于分析结果做版本分组
  - 可选参数：`--input-dir` (默认: analyzed_files)

- **`compare`** - 对分组结果做版本比较并组织文件
  - 可选参数：`--input-dir` (默认: grouped_files)

- **`full`** - 执行完整流程: extract→analyze→group→compare
  - 可选参数：`--git-dir`, `--fast` (快速模式)

- **`iterate`** - 对analyzed_files执行迭代式版本分析
  - 可选参数：`--input-dir` (默认: analyzed_files)

- **`config`** - 配置管理
  - 用法：`python main.py config save <配置文件路径>`

### 通用参数

- `--ai-model` - AI模型 (默认: moonshot)
- `--api-key` - API密钥
- `--max-workers` - 并发数 (默认: 50)
- `--config-file` - 配置文件路径 (默认: config.ini)

### 输出目录参数

- `--extract-output` - 提取输出目录 (默认: extracted_objects)
- `--analyze-output` - AI分析输出目录 (默认: analyzed_files)
- `--grouped-output` - 版本分组输出目录 (默认: grouped_files)
- `--organized-output` - 版本组织输出目录 (默认: organized_files)

## 🖥️ GUI界面说明

GUI界面提供了以下功能：

### 单步骤操作
- **提取对象** - 执行 `extract` 命令
- **AI分析** - 执行 `analyze` 命令  
- **版本分组** - 执行 `group` 命令
- **版本比较并组织** - 执行 `compare` 命令
- **迭代式版本分析** - 执行 `iterate` 命令

### 一键操作
- **快速型一键** - 执行 `full --fast` 命令
- **标准型一键** - 执行 `full` 命令

### 实时输出
- GUI会调用命令行工具，所有执行过程的输出将显示在系统终端中
- 可以在终端中实时查看进度、错误信息和调试输出
- GUI日志区域会显示命令执行状态和结果

## ⚙️ 配置说明

### 时间参数
- **不指定时间**：默认使用"当天凌晨2点到现在"
- **只指定开始时间**：终点自动设为"现在"
- **只指定结束时间**：起点设为2000年1月1日
- **同时指定**：严格按用户指定的时间范围

时间格式：`YYYY-MM-DD HH:MM`，例如：`2024-07-15 02:00`

### AI模型配置
在`config.ini`中配置你的AI模型：
```ini
[ai_models]
moonshot = https://api.moonshot.cn/v1
openai = https://api.openai.com/v1
```

### 输出目录
- `extracted_objects/` - 提取的原始文件
- `analyzed_files/` - AI筛选后的有价值文件
- `grouped_files/` - 版本分组结果
- `organized_files/` - 最终整理的文件

## 📁 输出文件说明

### 提取结果
```
extracted_objects/
├─ <object-id>.txt       # 每个Git对象的文件内容
└─ extraction_log.json   # 提取过程日志
```

### AI分析结果
```
analyzed_files/
├─ valuable_<n>.txt      # AI认为有价值的文件
└─ analysis_report.json  # 分析报告和理由
```

### 版本分组结果
```
grouped_files/
├─ version_groups.json   # 版本分组报告
└─ group_001_组名/      # 分组目录（默认启用）
    ├─ file1_hash.txt
    ├─ file2_hash.txt
    └─ ...
```

### 版本整理结果
```
organized_files/
├─ <文件名> /           # 分组的目录
│  ├─ <文件名>                    # 最新版本文件
│  ├─ <文件名> 版本分析报告.json   # 该文件的版本分析报告
│  └─ old/                       # 历史版本目录
│     ├─ <文件名>_<hash>.md      # 历史版本文件
│     └─ ...
└─ version_analysis_report.json  # 整体版本分析报告
```

## 🔧 高级配置

### 并发控制
```bash
python main.py full --git-dir "D:\repo\.git" --max-workers 3 --ai-model moonshot
```

### 模式选择
```bash
# 稳定模式（默认）：迭代分组 + 串行比较
python main.py full --git-dir "D:\repo\.git" --ai-model moonshot

# 快速模式：一次性分组 + 并行比较
python main.py full --git-dir "D:\repo\.git" --fast --ai-model moonshot

# 迭代模式：对analyzed_files执行迭代式版本分析
python main.py iterate --input-dir "analyzed_files" --ai-model moonshot
```

**Q: 快速模式和稳定模式有什么区别？**
A: 快速模式使用一次性分组，速度更快但可能不够准确；稳定模式使用迭代分组，更准确但更慢


## 📄 许可证
代码由ai生成，主要功能基本能用，可能有不少小问题和不必要的冗余