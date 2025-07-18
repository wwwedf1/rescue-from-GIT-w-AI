#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器
提取公共的报告生成逻辑
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class ReportGenerator:
    """报告生成器基类"""
    
    def __init__(self):
        """初始化报告生成器"""
        pass
    
    def create_markdown_report(self, title: str, sections: List[Dict]) -> str:
        """
        创建Markdown格式报告
        
        Args:
            title: 报告标题
            sections: 报告章节列表，每个章节包含title和content
            
        Returns:
            Markdown格式的报告内容
        """
        report_content = f"# {title}\n\n"
        
        for section in sections:
            section_title = section.get("title", "")
            section_content = section.get("content", "")
            
            if section_title:
                report_content += f"## {section_title}\n\n"
            
            if section_content:
                report_content += f"{section_content}\n\n"
        
        # 添加页脚
        report_content += "---\n*此报告由Git对象拯救工具自动生成*\n"
        
        return report_content
    
    def save_markdown_report(self, content: str, file_path: Path) -> None:
        """
        保存Markdown报告
        
        Args:
            content: 报告内容
            file_path: 文件路径
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def save_json_report(self, data: Dict, file_path: Path) -> None:
        """
        保存JSON报告
        
        Args:
            data: 报告数据
            file_path: 文件路径
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class VersionAnalysisReportGenerator(ReportGenerator):
    """版本分析报告生成器"""
    
    def create_version_analysis_report(self, base_name: str, sorted_versions: List[Dict], 
                                     analysis: str, confidence: float, notes: str) -> str:
        """
        创建版本分析报告
        
        Args:
            base_name: 基础文件名
            sorted_versions: 排序后的版本列表
            analysis: 版本分析结果
            confidence: 置信度
            notes: 注意事项
            
        Returns:
            Markdown格式的报告内容
        """
        sections = [
            {
                "title": "文件信息",
                "content": f"""- **基础文件名**: {base_name}
- **版本数量**: {len(sorted_versions)}
- **分析置信度**: {confidence:.2f}"""
            },
            {
                "title": "版本排序（从旧到新）",
                "content": self._build_version_list(sorted_versions)
            }
        ]
        
        if analysis and analysis.strip():
            sections.append({
                "title": "版本分析理由",
                "content": analysis
            })
        else:
            sections.append({
                "title": "版本分析理由",
                "content": "*AI分析结果为空，可能是单文件版本组或分析失败*"
            })
        
        if notes and notes.strip():
            sections.append({
                "title": "注意事项",
                "content": notes
            })
        
        if len(sorted_versions) > 1:
            sections.append({
                "title": "排序依据",
                "content": f"""AI根据以下因素对版本进行排序：
- 文件名相似性和变化规律
- 内容结构和功能变化
- Git冲突标记和修改痕迹
- 代码注释和版本标识
- 整体架构和依赖关系

置信度 {confidence:.2f} 表示AI对排序结果的信心程度。"""
            })
        
        sections.append({
            "title": "目录结构",
            "content": self._build_directory_structure(base_name)
        })
        
        return self.create_markdown_report(f"{base_name} 版本分析报告", sections)
    
    def create_misjudged_analysis_report(self, base_name: str, sorted_versions: List[Dict],
                                       analysis: str, confidence: float, notes: str, 
                                       group_misjudged: bool) -> str:
        """
        创建误判分析报告
        
        Args:
            base_name: 基础文件名
            sorted_versions: 排序后的版本列表
            analysis: 版本分析结果
            confidence: 置信度
            notes: 注意事项
            group_misjudged: 整个组是否被误判
            
        Returns:
            Markdown格式的报告内容
        """
        sections = [
            {
                "title": "误判信息",
                "content": f"""- **基础文件名**: {base_name}
- **版本数量**: {len(sorted_versions)}
- **分析置信度**: {confidence:.2f}
- **误判类型**: {'整个版本组误判' if group_misjudged else '部分文件误判'}"""
            },
            {
                "title": "误判说明",
                "content": """此版本组被AI标记为误判，可能的原因包括：
- 文件内容差异过大，不是同一文件的不同版本
- 文件类型不匹配
- 功能或结构差异显著
- 其他AI无法确定的关系"""
            },
            {
                "title": "文件列表",
                "content": self._build_misjudged_file_list(sorted_versions)
            }
        ]
        
        if analysis and analysis.strip():
            sections.append({
                "title": "AI分析结果",
                "content": analysis
            })
        else:
            sections.append({
                "title": "AI分析结果",
                "content": "*AI分析结果为空*"
            })
        
        if notes and notes.strip():
            sections.append({
                "title": "注意事项",
                "content": notes
            })
        
        sections.append({
            "title": "人工检查建议",
            "content": """请人工检查以下内容：
1. 这些文件是否真的是同一文件的不同版本？
2. 文件间的差异是否合理？
3. 是否需要重新分组或调整？"""
        })
        
        sections.append({
            "title": "目录结构",
            "content": self._build_misjudged_directory_structure(base_name)
        })
        
        return self.create_markdown_report(f"{base_name} 误判分析报告", sections)
    
    def _build_version_list(self, sorted_versions: List[Dict]) -> str:
        """构建版本列表"""
        content = ""
        for i, version in enumerate(sorted_versions, 1):
            status = "最新版本" if i == len(sorted_versions) else f"旧版本 {i}"
            content += f"""
### 版本 {i}: {version['filename']}
- **原始文件名**: {version['suggested_filename']}
- **Git对象**: {version['hash']}
- **状态**: {status}
"""
        return content
    
    def _build_misjudged_file_list(self, sorted_versions: List[Dict]) -> str:
        """构建误判文件列表"""
        content = ""
        for i, version in enumerate(sorted_versions, 1):
            misjudged_status = "误判" if version.get("misjudged", False) else "正常"
            content += f"""
### 文件 {i}: {version['filename']}
- **原始文件名**: {version['suggested_filename']}
- **Git对象**: {version['hash']}
- **误判状态**: {misjudged_status}
"""
        return content
    
    def _build_directory_structure(self, base_name: str) -> str:
        """构建目录结构说明"""
        return f"""```
{base_name}/
├── old/
│   ├── {base_name}_v1.txt
│   ├── {base_name}_v2.txt
│   └── ...
├── {base_name}_最新版本.txt
└── {base_name}_版本分析报告.md
```"""
    
    def _build_misjudged_directory_structure(self, base_name: str) -> str:
        """构建误判目录结构说明"""
        return f"""```
误判文件夹/{base_name}/
├── {base_name}_v1.txt
├── {base_name}_v2.txt
├── ...
├── {base_name}_newest.txt
└── {base_name}_误判分析报告.md
```""" 