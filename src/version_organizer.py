#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的版本组织器
使用新的报告生成器
"""

import json
import shutil
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from .base_workflow import BaseWorkflow
from .report_generator import VersionAnalysisReportGenerator


class RefactoredVersionOrganizer(BaseWorkflow):
    """重构后的版本组织器"""
    
    def __init__(self, output_config: Dict[str, Any]):
        """
        初始化重构后的版本组织器
        
        Args:
            output_config: 输出配置
        """
        super().__init__()
        self.create_version_structure = output_config.get("create_version_structure", True)
        self.report_generator = VersionAnalysisReportGenerator()
    
    def organize_versions(self, version_analysis_dir: str, target_base_dir: str) -> Dict[str, Any]:
        """
        根据版本分析结果组织文件
        从organized_output目录读取version_analysis_report.json
        """
        if not self.create_version_structure:
            print("版本结构组织功能已禁用")
            return {"organized": False, "reason": "功能已禁用"}
        
        # 检查version_analysis_report.json是否存在于version_analysis_dir中
        version_report_path = Path(version_analysis_dir) / "version_analysis_report.json"
        if not version_report_path.exists():
            print(f"版本分析报告不存在: {version_report_path}")
            return {"organized": False, "reason": "版本分析报告不存在"}
        
        version_report = self.load_json_report(str(version_report_path))
        
        # 创建目标目录
        target_base = Path(target_base_dir)
        target_base.mkdir(parents=True, exist_ok=True)
        
        print(f"开始组织版本文件...")
        print(f"目标目录: {target_base}")
        print()
        
        organized_groups = 0
        newest_files = 0
        old_files = 0
        misjudged_files = 0
        
        # 处理每个版本组
        for group in version_report.get("version_groups", []):
            base_name = group["base_name"]
            sorted_versions = group["sorted_versions"]
            analysis = group.get("analysis", "")
            confidence = group.get("confidence", 0.5)
            notes = group.get("notes", "")
            group_misjudged = group.get("group_misjudged", False)
            
            print(f"处理版本组: {base_name}")
            
            if not sorted_versions:
                print(f"  跳过：没有版本文件")
                continue
            
            # 检查是否有误判文件
            has_misjudged = any(v.get("misjudged", False) for v in sorted_versions)
            
            if group_misjudged or has_misjudged:
                # 误判的版本组，复制到误判文件夹
                misjudged_dir = target_base / "误判文件夹"
                misjudged_dir.mkdir(exist_ok=True)
                
                # 为误判组创建子目录
                misjudged_group_dir = misjudged_dir / base_name
                misjudged_group_dir.mkdir(exist_ok=True)
                
                # 复制所有文件到误判文件夹
                for i, version in enumerate(sorted_versions):
                    version_label = f"v{i+1}" if i < len(sorted_versions) - 1 else "newest"
                    file_path = self._copy_version_file(version, misjudged_group_dir, version_label)
                    if file_path:
                        misjudged_files += 1
                
                # 创建误判分析报告
                self._create_misjudged_analysis_report(misjudged_group_dir, base_name, sorted_versions, analysis, confidence, notes, group_misjudged)
                
                print(f"  误判组：复制 {len(sorted_versions)} 个文件到误判文件夹")
            else:
                # 正常版本组，按原逻辑处理
                # 为每个文件创建独立的目录，使用清理后的基础名称
                safe_base_name = "".join(c for c in base_name if c.isalnum() or c in "._- ")
                safe_base_name = safe_base_name.strip()
                if not safe_base_name:
                    safe_base_name = f"file_group_{organized_groups+1}"
                
                file_dir = target_base / safe_base_name
                file_dir.mkdir(exist_ok=True)
                
                # 创建old目录
                old_dir = file_dir / "old"
                old_dir.mkdir(exist_ok=True)
                
                # 最新版本（列表中的最后一个）
                newest_version = sorted_versions[-1]
                old_versions = sorted_versions[:-1]
                
                # 复制最新版本到文件目录根目录
                newest_file_path = self._copy_version_file(newest_version, file_dir, "newest")
                if newest_file_path:
                    newest_files += 1
                
                # 复制旧版本到old目录
                for i, old_version in enumerate(old_versions):
                    old_file_path = self._copy_version_file(old_version, old_dir, "old")
                    if old_file_path:
                        old_files += 1
                
                # 创建版本分析报告
                self._create_version_analysis_report(file_dir, safe_base_name, sorted_versions, analysis, confidence, notes)
                
                organized_groups += 1
                print(f"  处理完成：1个最新版本，{len(old_versions)}个旧版本")
        
        # 处理独立的误判文件（不在任何版本组中的）
        independent_misjudged = version_report.get("misjudged_files", [])
        if independent_misjudged:
            misjudged_dir = target_base / "误判文件夹"
            misjudged_dir.mkdir(exist_ok=True)
            
            independent_dir = misjudged_dir / "独立误判文件"
            independent_dir.mkdir(exist_ok=True)
            
            for misjudged_file in independent_misjudged:
                file_path = self._copy_version_file(misjudged_file, independent_dir, "independent")
                if file_path:
                    misjudged_files += 1
            
            print(f"处理了 {len(independent_misjudged)} 个独立误判文件")
        
        # # 生成组织报告
        # organization_report = {
        #     "organization_info": {
        #         "target_base_dir": str(target_base),
        #         "organized_groups": organized_groups,
        #         "newest_files": newest_files,
        #         "old_files": old_files,
        #         "misjudged_files": misjudged_files,
        #         "total_files": newest_files + old_files + misjudged_files
        #     },
        #     "directory_structure": "每个文件独立目录，包含最新版本、old目录和版本分析报告；误判文件统一放在误判文件夹中"
        # }
        
        # # 保存组织报告
        # report_file = target_base / "organization_report.json"
        # self.save_json_report(organization_report, str(report_file))
        
        print(f"\n版本组织完成！")
        print(f"处理了 {organized_groups} 个版本组")
        print(f"最新版本文件: {newest_files} 个")
        print(f"旧版本文件: {old_files} 个")
        print(f"被标记为误判的文件: {misjudged_files} 个")
        # print(f"组织报告已保存到: {report_file}")
        
        return {
            "organized": True,
            # "report": organization_report,
            # "report_file": str(report_file)
        }
    
    def _copy_version_file(self, version_info: Dict[str, str], target_dir: Path, 
                          version_label: str) -> Optional[Path]:
        """
        复制版本文件到目标目录
        
        Args:
            version_info: 版本信息
            target_dir: 目标目录
            version_label: 版本标签
            
        Returns:
            复制的文件路径，如果失败返回None
        """
        suggested_filename = version_info["suggested_filename"]
        
        # 构建源文件路径
        source_filename = suggested_filename
        
        # 在analyzed_files目录中查找文件
        possible_sources = [
            Path("analyzed_files") / source_filename,
            Path("analyzed_files") / version_info["filename"],
        ]
        
        source_file = None
        for possible_source in possible_sources:
            if possible_source.exists():
                source_file = possible_source
                break
        
        if not source_file:
            print(f"    警告: 未找到源文件 {source_filename}")
            return None
        
        # 构建目标文件名
        if version_label == "newest":
            # 最新版本保持原始文件名（去掉hash后缀）
            name_part, ext_part = os.path.splitext(suggested_filename)
            # 移除hash后缀（最后8位字符）
            if len(name_part) > 8 and name_part[-9] == '_':
                clean_name = name_part[:-9]
            else:
                clean_name = name_part
            target_filename = f"{clean_name}{ext_part}"
        else:
            # 旧版本保持suggested_filename
            target_filename = suggested_filename
        
        target_file = target_dir / target_filename
        
        try:
            shutil.copy2(source_file, target_file)
            print(f"    复制: {source_file.name} -> {target_filename}")
            return target_file
        except Exception as e:
            print(f"    错误: 复制文件失败 {source_file} -> {target_file}: {e}")
            return None
    
    def _create_version_analysis_report(self, file_dir: Path, base_name: str, 
                                      sorted_versions: List[Dict], analysis: str, 
                                      confidence: float, notes: str):
        """
        创建版本分析报告
        
        Args:
            file_dir: 文件目录
            base_name: 基础文件名
            sorted_versions: 排序后的版本列表
            analysis: 版本分析结果
            confidence: 置信度
            notes: 注意事项
        """
        # 创建JSON格式的详细报告
        json_report = {
            "base_name": base_name,
            "version_count": len(sorted_versions),
            "confidence": confidence,
            "sorted_versions": [
                {
                    "filename": v["filename"],
                    "hash": v["hash"],
                    "suggested_filename": v["suggested_filename"],
                    "file_type": v.get("file_type", "unknown"),
                    "analysis": v.get("analysis", "")
                }
                for v in sorted_versions
            ],
            "analysis": analysis,
            "notes": notes,
            "directory_structure": {
                "newest_version": "最新版本文件（去掉hash后缀）",
                "old_versions_dir": "old/",
                "report_file": f"{base_name}版本分析报告.json"
            }
        }
        
        json_report_file = file_dir / f"{base_name}版本分析报告.json"
        self.save_json_report(json_report, str(json_report_file))
        
        print(f"    创建版本分析报告: {json_report_file.name}")
    
    def _create_misjudged_analysis_report(self, file_dir: Path, base_name: str, 
                                        sorted_versions: List[Dict], analysis: str, 
                                        confidence: float, notes: str, group_misjudged: bool):
        """
        创建误判分析报告
        
        Args:
            file_dir: 文件目录
            base_name: 基础文件名
            sorted_versions: 排序后的版本列表
            analysis: 版本分析结果
            confidence: 置信度
            notes: 注意事项
            group_misjudged: 整个组是否被误判
        """
        # 使用报告生成器创建误判分析报告
        report_content = self.report_generator.create_misjudged_analysis_report(
            base_name, sorted_versions, analysis, confidence, notes, group_misjudged
        )
        
        # 保存Markdown报告
        report_file = file_dir / f"{base_name}_误判分析报告.md"
        self.report_generator.save_markdown_report(report_content, report_file)
        
        # 同时保存JSON格式的详细报告
        json_report = {
            "base_name": base_name,
            "version_count": len(sorted_versions),
            "confidence": confidence,
            "sorted_versions": sorted_versions,
            "analysis": analysis,
            "notes": notes,
            "group_misjudged": group_misjudged,
            "misjudged_files": [v for v in sorted_versions if v.get("misjudged", False)],
            "directory_structure": {
                "report_file": f"{base_name}_误判分析报告.md"
            }
        }
        
        json_report_file = file_dir / f"{base_name}_误判分析报告.json"
        self.report_generator.save_json_report(json_report, json_report_file)
        
        print(f"    创建误判分析报告: {report_file.name}")
    
    def create_directory_structure_only(self, target_base_dir: str) -> Dict[str, str]:
        """
        仅创建目录结构，不复制文件
        
        Args:
            target_base_dir: 目标基础目录
            
        Returns:
            创建的目录信息
        """
        target_base = Path(target_base_dir)
        target_base.mkdir(parents=True, exist_ok=True)
        
        return {
            "base_dir": str(target_base),
            "structure": "每个文件独立目录，包含最新版本、old目录和版本分析报告"
        }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行版本组织工作流"""
        version_analysis_dir = kwargs.get("version_analysis_dir", "version_analysis")
        target_base_dir = kwargs.get("target_base_dir", "organized_files")
        
        return self.organize_versions(version_analysis_dir, target_base_dir) 