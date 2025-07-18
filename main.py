#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git对象拯救工具 - 命令行版本 
使用3种分析器：全体分组器、种子分组器、组内版本比较器
"""

import argparse
import datetime
import os
import sys
import logging
from pathlib import Path
from typing import List
import time
from src.git_extractor import GitObjectExtractor, create_time_range_from_2am, create_custom_time_range
from src.ai_analyzer import AIAnalyzer
from src.version_analyzer import (
    BatchGroupingAnalyzer, 
    IterativeGroupingAnalyzer, 
    VersionComparisonAnalyzer,
    VersionGroup,
    FileVersion,
    load_analysis_report,
    extract_file_versions,
    save_json_report
)
from src.version_organizer import RefactoredVersionOrganizer
from src.config_manager import get_config_manager
from src.base_workflow import BaseWorkflow
import json

# 设置日志记录
logger = logging.getLogger(__name__)

def create_parser():
    """创建命令行参数解析器"""
    config_manager = get_config_manager()
    
    # 获取配置
    available_models = config_manager.get_available_models()
    default_model = config_manager.get_default_model()
    analysis_config = config_manager.get_analysis_config()
    output_config = config_manager.get_output_config()
    
    parser = argparse.ArgumentParser(description="Git对象拯救工具 (重构版)")
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 通用参数组
    common_group = argparse.ArgumentParser(add_help=False)
    common_group.add_argument("--ai-model", default=default_model, 
                             choices=available_models, help="AI模型")
    common_group.add_argument("--api-key", help="API密钥 (优先级: 命令行 > 环境变量 > 配置文件)")
    common_group.add_argument("--max-workers", type=int, default=analysis_config["max_workers"], 
                             help="并发数")
    common_group.add_argument("--config-file", default="config.ini", help="配置文件路径")
    
    # 输出目录参数组
    output_group = argparse.ArgumentParser(add_help=False)
    output_group.add_argument("--extract-output", default=output_config["extract_output"], 
                     help="提取输出目录")
    output_group.add_argument("--analyze-output", default=output_config["analyze_output"], 
                     help="AI分析输出目录")
    output_group.add_argument("--grouped-output", default=output_config["grouped_output"], 
                     help="版本分组输出目录")
    output_group.add_argument("--organized-output", default=output_config["organized_output"], 
                     help="版本组织输出目录")
    
    # 时间范围参数组
    time_group = argparse.ArgumentParser(add_help=False)
    time_group.add_argument("--start-time", help="开始时间 (格式: YYYY-MM-DD HH:MM)")
    time_group.add_argument("--end-time", help="结束时间 (格式: YYYY-MM-DD HH:MM)")
    
    # extract 子命令
    extract_parser = subparsers.add_parser('extract', help='从Git对象提取文件', 
                                          parents=[common_group, output_group, time_group])
    extract_parser.add_argument("--git-dir", required=True, help="Git目录路径 (.git目录)")
    
    # analyze 子命令
    analyze_parser = subparsers.add_parser('analyze', help='对已提取文件做AI分析', 
                                          parents=[common_group, output_group])
    analyze_parser.add_argument("--input-dir", default="extracted_objects", 
                               help="输入目录 (默认: extracted_objects)")
    
    # group 子命令
    group_parser = subparsers.add_parser('group', help='基于分析结果做版本分组', 
                                    parents=[common_group, output_group])
    group_parser.add_argument("--input-dir", default="analyzed_files", 
                         help="输入目录 (默认: analyzed_files)")

    # compare 子命令
    compare_parser = subparsers.add_parser('compare', help='对分组结果做版本比较并组织文件', 
                                      parents=[common_group, output_group])
    compare_parser.add_argument("--input-dir", default="grouped_files", 
                           help="输入目录 (默认: grouped_files)")
    
    # full 子命令 - 完整流程
    full_parser = subparsers.add_parser('full', help='执行完整流程: extract→analyze→group→compare', 
                                       parents=[common_group, output_group, time_group])
    full_parser.add_argument("--git-dir", help="Git目录路径 (.git目录，可选，如果不提供则从中间文件开始)")
    full_parser.add_argument("--fast", action="store_true", 
                            help="快速模式：使用一次性分组而非迭代分组，后续可以并行比较")
    
    # iterate 子命令 - 迭代模式
    iterate_parser = subparsers.add_parser('iterate', help='对analyzed_files执行迭代式版本分析', 
                                          parents=[common_group, output_group])
    iterate_parser.add_argument("--input-dir", default="analyzed_files", 
                               help="输入目录 (默认: analyzed_files)")
    
    # config 子命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_parser.add_argument('save', nargs='?', help='保存当前配置到指定文件')
    
    return parser

class GitRescuerWorkflow(BaseWorkflow):
    """Git对象拯救工作流"""
    
    def __init__(self, config_file: str = "config.ini"):
        super().__init__(config_file)
        #self.batch_grouping_analyzer = None
        #self.iterative_grouping_analyzer = None
        #self.version_comparison_analyzer = None
    
    def setup_analyzers(self, ai_model: str, api_key: str, max_workers: int):
        """设置分析器
        Args:
            ai_model: 使用的AI模型
            api_key: API 密钥
            max_workers: 并发数
        """
        self.max_workers = max_workers
        self.batch_grouping_analyzer = BatchGroupingAnalyzer(ai_model, api_key, max_workers)
        self.iterative_grouping_analyzer = IterativeGroupingAnalyzer(ai_model, api_key, max_workers)
        self.version_comparison_analyzer = VersionComparisonAnalyzer(ai_model, api_key, max_workers)
        self.version_organizer = RefactoredVersionOrganizer(self.output_config)
    
    def extract_objects(self, git_dir: str, extract_output: str, start_time: datetime.datetime, end_time: datetime.datetime):
        """提取Git对象"""
        print("=== 第一步：提取Git对象 ===")
        extractor = GitObjectExtractor(git_dir, extract_output)
        extract_results = extractor.extract_objects(start_time, end_time)
        print(f"提取完成！处理了 {extract_results['processed_count']} 个对象，保存了 {extract_results['saved_count']} 个文件")
        print()
        return extract_results
    
    def analyze_files(self, extract_output: str, analyze_output: str, ai_model: str, api_key: str, max_workers: int):
        """AI分析文件"""
        print("=== 第二步：AI分析 ===")
        ai_config = self.config_manager.get_ai_config(ai_model)
        analyzer = AIAnalyzer(ai_config_key=ai_model, custom_api_key=api_key)
        analyzer.max_workers = max_workers
        analyzer.max_content_length = self.analysis_config["max_content_length"]
        analyzer.temperature = self.analysis_config["temperature"]
        
        analyze_results = analyzer.analyze_directory(extract_output, analyze_output)
        print(f"AI分析完成！分析了 {analyze_results['analysis_info']['total_files']} 个文件，保存了 {analyze_results['analysis_info']['saved_count']} 个有价值文件")
        print()
        return analyze_results
    
    def group_versions(self, analyze_output: str, grouped_output: str):
        """版本分组 - 使用全体分组器"""
        print("=== 第三步：版本分组 ===")
        
        # 加载分析报告
        report_path = os.path.join(analyze_output, "analysis_report.json")
        if not os.path.exists(report_path):
            print(f"错误: 分析报告不存在: {report_path}")
            print("请先执行AI分析步骤")
            return None
        
        report_data = load_analysis_report(report_path)
        versions = extract_file_versions(report_data, analyze_output)
        
        print(f"加载了 {len(versions)} 个文件版本")
        
        # 使用全体分组器进行分组
        files_info = self.batch_grouping_analyzer.build_files_info(
            versions, self.batch_grouping_analyzer.ai_analyzer.batch_grouping_preview_length
        )
        
        # 执行批量分组
        use_stream = True  # 使用流式输出避免超时
        logger.debug(f"批量分组使用流式输出模式")
        
        groups = self.batch_grouping_analyzer.analyze(
            files_info=files_info, 
            versions=versions,
            use_stream=use_stream
        )
        
        # 保存分组结果
        output_path = Path(grouped_output)
        output_path.mkdir(exist_ok=True)
        
        # 保存分组结果（不包含详细分析）
        group_results = {
            "analysis_info": {
                "total_files": len(versions),
                "processed_groups": len(groups),
                "mode": "grouping_only"
            },
            "version_groups": []
        }
        
        # 按分组复制文件到子目录
        if self.output_config.get("create_group_directories", True):
            print("按分组复制文件...")
            for i, group in enumerate(groups):
                # 过滤掉不安全的字符，确保目录名有效
                safe_base_name = "".join(c for c in group.base_name if c.isalnum() or c in "._- ")
                safe_base_name = safe_base_name.strip()
                if not safe_base_name:
                    safe_base_name = f"group_{i+1:03d}"
                
                group_name = f"group_{i+1:03d}_{safe_base_name}"
                group_dir = output_path / group_name
                group_dir.mkdir(exist_ok=True)
                
                # 复制组内文件
                for j, version in enumerate(group.versions):
                    source_file = Path(analyze_output) / version.suggested_filename
                    if source_file.exists():
                        target_file = group_dir / version.suggested_filename
                        import shutil
                        shutil.copy2(source_file, target_file)
                        print(f"  复制: {version.suggested_filename} -> {group_name}/")
        else:
            print("跳过按分组复制文件（已禁用）")
        
        for i, group in enumerate(groups):
            # 使用相同的安全名称逻辑
            safe_base_name = "".join(c for c in group.base_name if c.isalnum() or c in "._- ")
            safe_base_name = safe_base_name.strip()
            if not safe_base_name:
                safe_base_name = f"group_{i+1:03d}"
            
            group_name = f"group_{i+1:03d}_{safe_base_name}"
            
            group_data = {
                "base_name": group.base_name,
                "group_dir": group_name,
                "reasoning": group.reasoning,
                "versions_count": len(group.versions),
                "versions": [
                    {
                        "filename": v.ai_name,
                        "hash": v.original_hash,
                        "suggested_filename": v.suggested_filename,
                        "file_type": v.file_type,
                        "ai_analysis": v.ai_analysis,
                    }
                    for v in group.versions
                ]
            }
            group_results["version_groups"].append(group_data)
        
        # 保存分组结果
        group_file = output_path / "version_groups.json"
        save_json_report(group_results, str(group_file))
        
        print(f"版本分组完成！处理了 {len(groups)} 个版本组")
        print(f"分组结果已保存到: {group_file}")
        print(f"文件已按分组复制到子目录")
        print()
        return group_results
    
    def compare_versions(self, grouped_output: str, organized_output: str):
        """版本比较并组织文件 - 使用组内版本比较器"""
        print("=== 第四步：版本比较并组织 ===")
        
        # 加载分组结果
        group_file = os.path.join(grouped_output, "version_groups.json")
        if not os.path.exists(group_file):
            print(f"错误: 分组结果不存在: {group_file}")
            print("请先执行版本分组步骤")
            return None
        
        group_results = self.load_json_report(group_file)
        
        # 重新加载文件版本信息（从analyzed_files）
        report_path = os.path.join("analyzed_files", "analysis_report.json")
        report_data = load_analysis_report(report_path)
        all_versions = extract_file_versions(report_data, "analyzed_files")
        
        # 根据分组结果重新构建版本组
        groups = []
        for group_data in group_results["version_groups"]:
            group_versions = []
            for version_info in group_data["versions"]:
                # 根据哈希找到对应的版本对象
                for version in all_versions:
                    if version.original_hash == version_info["hash"]:
                        group_versions.append(version)
                        break
            
            if group_versions:
                group = VersionGroup(
                    base_name=group_data["base_name"],
                    versions=group_versions
                )
                groups.append(group)
        
        print(f"加载了 {len(groups)} 个版本组")
        
        # 并行对每个组进行版本比较
        def analyze_group(group, group_index):
            """分析单个版本组"""
            print(f"开始比较版本组 {group_index+1}/{len(groups)}: {group.base_name}")
            
            try:
                # 使用组内版本比较器
                files_info = self.version_comparison_analyzer.build_files_info(
                    group.versions, self.version_comparison_analyzer.ai_analyzer.version_analysis_preview_length
                )
                
                analysis_result = self.version_comparison_analyzer.analyze(
                    files_info=files_info, 
                    versions=group.versions,
                    use_stream=True
                )
                
                print(f"完成版本组 {group_index+1}/{len(groups)}: {group.base_name}")
                return group_index, analysis_result
                
            except Exception as e:
                print(f"版本组 {group_index+1}/{len(groups)} 分析失败: {e}")
                return group_index, None
        
        # 使用线程池并行执行
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print(f"开始并行版本比较，使用 {self.max_workers} 个并发线程...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_group = {
                executor.submit(analyze_group, group, i): i 
                for i, group in enumerate(groups)
            }
            
            # 收集结果
            for future in as_completed(future_to_group):
                group_index, analysis_result = future.result()
                if analysis_result:
                    groups[group_index].analysis_result = analysis_result
                    groups[group_index].sorted_versions = analysis_result.get("sorted_versions", groups[group_index].versions)
                else:
                    # 分析失败，使用默认排序
                    groups[group_index].sorted_versions = groups[group_index].versions
        
        print("并行版本比较完成！")
        
        # 收集误判文件
        misjudged_files = []
        for group in groups:
            if group.analysis_result:
                file_analysis_list = group.analysis_result.get("file_analysis_list", [])
                for file_analysis in file_analysis_list:
                    if file_analysis.get("misjudged", False):
                        file_analysis["file"].misjudged = True
                        if file_analysis["file"] not in misjudged_files:
                            misjudged_files.append(file_analysis["file"])
        
        # 生成最终结果
        version_results = {
            "analysis_info": {
                "total_files": group_results["analysis_info"]["total_files"],
                "processed_groups": len(groups),
                "mode": "grouping_and_comparison",
                "misjudged_files_count": len(misjudged_files),
            },
            "version_groups": [],
            "misjudged_files": [
                {
                    "filename": v.ai_name,
                    "hash": v.original_hash,
                    "suggested_filename": v.suggested_filename,
                    "file_type": v.file_type,
                }
                for v in misjudged_files
            ],
        }
        
        for group in groups:
            sorted_versions = group.sorted_versions or group.versions
            analysis_result = group.analysis_result or {}
            
            group_data = {
                "base_name": group.base_name,
                "versions_count": len(group.versions),
                "sorted_versions": [
                    {
                        "filename": v.ai_name,
                        "hash": v.original_hash,
                        "suggested_filename": v.suggested_filename,
                        "misjudged": v.misjudged,
                    }
                    for v in sorted_versions
                ],
                "analysis": analysis_result.get("analysis", ""),
                "confidence": analysis_result.get("confidence", 0.5),
                "notes": analysis_result.get("notes", ""),
                "group_misjudged": analysis_result.get("group_misjudged", False),
            }
            version_results["version_groups"].append(group_data)
        
        # 保存最终结果到organized_output目录
        result_file = Path(organized_output) / "version_analysis_report.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        save_json_report(version_results, str(result_file))
        
        print(f"版本比较完成！处理了 {len(groups)} 个版本组")
        print(f"发现 {len(misjudged_files)} 个误判文件")
        print(f"结果已保存到: {result_file}")
        
        # 直接组织文件
        print("=== 第五步：版本组织 ===")
        organize_results = self.version_organizer.organize_versions(organized_output, organized_output)
        
        if organize_results.get("organized", False):
            print("版本组织完成！")
        else:
            print(f"版本组织跳过: {organize_results.get('reason', '未知原因')}")
        print()
        
        return version_results
    
    def iterative_analysis(self, analyze_output: str, organized_output: str):
        """迭代模式分析 - 使用种子分组器和组内版本比较器"""
        print("=== 迭代模式：从analyzed_files直接分析 ===")
        
        # 直接从analyzed_files加载
        report_path = os.path.join(analyze_output, "analysis_report.json")
        if not os.path.exists(report_path):
            print(f"错误: 分析报告不存在: {report_path}")
            return None
        
        report_data = load_analysis_report(report_path)
        versions = extract_file_versions(report_data, analyze_output)
        
        print(f"加载了 {len(versions)} 个文件版本")
        
        # 执行迭代式版本分析
        output_path = Path(organized_output)
        output_path.mkdir(exist_ok=True)

        remaining_versions = versions.copy()
        processed_groups: List[VersionGroup] = []
        misjudged_files: List[FileVersion] = []
        iteration = 1

        while remaining_versions:
            print(f"=== 迭代 {iteration} ===")
            print(f"剩余文件数量: {len(remaining_versions)}")

            seed_file = remaining_versions[0]
            print(f"选择种子文件: {seed_file.ai_name}")

            # 使用种子分组器查找相似文件
            candidate_files = []
            for version in remaining_versions:
                if version.original_hash != seed_file.original_hash:
                    candidate_files.append(version)

            if candidate_files:
                # 构建候选文件信息
                candidate_files_info = self.iterative_grouping_analyzer.build_files_info(
                    candidate_files, self.iterative_grouping_analyzer.ai_analyzer.iterative_similarity_preview_length
                )
                
                # 使用种子分组器查找相似文件
                similar_files = self.iterative_grouping_analyzer.analyze(
                    target_version=seed_file,
                    candidate_files=candidate_files_info,
                    candidate_versions=candidate_files,
                    use_stream=True
                )

                if similar_files:
                    group_versions = [seed_file] + similar_files
                    group = VersionGroup(
                        base_name=self._normalize_filename(seed_file.ai_name),
                        versions=group_versions,
                    )

                    # 使用组内版本比较器分析版本组
                    if len(group_versions) > 1:
                        files_info = self.version_comparison_analyzer.build_files_info(
                            group_versions, self.version_comparison_analyzer.ai_analyzer.version_analysis_preview_length
                        )
                        
                        analysis_result = self.version_comparison_analyzer.analyze(
                            files_info=files_info, 
                            versions=group_versions,
                            use_stream=True
                        )
                        group.analysis_result = analysis_result
                        group.sorted_versions = analysis_result.get("sorted_versions", group_versions)
                        
                        # 检查误判文件
                        file_analysis_list = analysis_result.get("file_analysis_list", [])
                        for file_analysis in file_analysis_list:
                            if file_analysis.get("misjudged", False):
                                file_analysis["file"].misjudged = True
                                if file_analysis["file"] not in misjudged_files:
                                    misjudged_files.append(file_analysis["file"])

                    processed_groups.append(group)

                    processed_hashes = {v.original_hash for v in group_versions}
                    remaining_versions = [v for v in remaining_versions if v.original_hash not in processed_hashes]
                else:
                    # 未找到相似文件，创建单文件组
                    single_group = VersionGroup(
                        base_name=self._normalize_filename(seed_file.ai_name),
                        versions=[seed_file],
                    )
                    processed_groups.append(single_group)
                    remaining_versions.pop(0)
                    print("未找到相似文件，为其创建单文件版本组")
            else:
                # 没有候选文件，创建单文件组
                single_group = VersionGroup(
                    base_name=self._normalize_filename(seed_file.ai_name),
                    versions=[seed_file],
                )
                processed_groups.append(single_group)
                remaining_versions.pop(0)
                print("没有候选文件，为其创建单文件版本组")

            iteration += 1

            if iteration > 10:
                print("达到最大迭代次数限制")
                break

        if remaining_versions:
            print(f"为剩余的 {len(remaining_versions)} 个文件创建单文件版本组")
            for v in remaining_versions:
                single_group = VersionGroup(
                    base_name=self._normalize_filename(v.ai_name),
                    versions=[v],
                )
                processed_groups.append(single_group)
            remaining_versions = []

        # 生成结果
        result = {
            "analysis_info": {
                "total_files": len(versions),
                "processed_groups": len(processed_groups),
                "remaining_files": len(remaining_versions),
                "misjudged_files_count": len(misjudged_files),
            },
            "version_groups": [],
            "misjudged_files": [
                {
                    "filename": v.ai_name,
                    "hash": v.original_hash,
                    "suggested_filename": v.suggested_filename,
                    "file_type": v.file_type,
                }
                for v in misjudged_files
            ],
        }

        for group in processed_groups:
            group_data = {
                "base_name": group.base_name,
                "versions_count": len(group.versions),
                "sorted_versions": [
                    {
                        "filename": v.ai_name,
                        "hash": v.original_hash,
                        "suggested_filename": v.suggested_filename,
                        "misjudged": v.misjudged,
                    }
                    for v in (group.sorted_versions or group.versions)
                ],
                "analysis": (group.analysis_result or {}).get("analysis", ""),
                "confidence": (group.analysis_result or {}).get("confidence", 0.5),
                "notes": (group.analysis_result or {}).get("notes", ""),
                "group_misjudged": (group.analysis_result or {}).get("group_misjudged", False),
                "reasoning": group.reasoning,
            }
            result["version_groups"].append(group_data)

        # 保存到文件
        result_file = output_path / "version_analysis_report.json"
        save_json_report(result, str(result_file))

        print(f"\n迭代模式分析完成！总耗时: {time.time() - time.time():.2f}秒")
        print(f"处理了 {len(processed_groups)} 个版本组")
        print(f"剩余 {len(remaining_versions)} 个未分组文件")
        print(f"发现 {len(misjudged_files)} 个误判文件")
        print(f"结果已保存到: {result_file}")
        
        return result
    
    def _normalize_filename(self, filename: str) -> str:
        """标准化文件名"""
        import re
        name = os.path.splitext(filename)[0]
        patterns = [
            r"[-_]\d+$",
            r"[-_]v?\d+\.\d+",
            r"[-_]copy$",
            r"[-_]backup$",
            r"[-_]\w{8}$",  # 移除8位哈希后缀
        ]
        for pattern in patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        return name.strip().lower()
    
    def execute(self, **kwargs) -> dict:
        """执行完整工作流"""
        # 这里可以实现完整的工作流逻辑
        return {"status": "workflow_executed"}

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    # 初始化工作流
    config_file = getattr(args, 'config_file', 'config.ini')
    workflow = GitRescuerWorkflow(config_file)
    
    # 验证参数
    if args.command == 'extract':
        if not args.git_dir:
            print("错误: extract命令需要指定Git目录")
            sys.exit(1)
        try:
            workflow.validate_git_directory(args.git_dir)
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
    
    elif args.command == 'full':
        if not args.git_dir and not args.fast:
            print("错误: full命令需要指定Git目录或使用--fast选项")
            sys.exit(1)
        if args.git_dir:
            try:
                workflow.validate_git_directory(args.git_dir)
            except ValueError as e:
                print(f"错误: {e}")
                sys.exit(1)
    
    elif args.command == 'iterate':
        if not hasattr(args, 'input_dir') or not args.input_dir:
            print("错误: iterate命令需要指定输入目录")
            sys.exit(1)
    
    elif args.command == 'group':
        if not hasattr(args, 'input_dir') or not args.input_dir:
            print("错误: group命令需要指定输入目录")
            sys.exit(1)
    
    elif args.command == 'compare':
        if not hasattr(args, 'input_dir') or not args.input_dir:
            print("错误: compare命令需要指定输入目录")
            sys.exit(1)
    
    # 获取时间范围
    start_time = None
    end_time = None
    
    # 只有extract和full命令需要时间范围
    if args.command in ['extract', 'full']:
        if args.start_time and args.end_time:
            try:
                start_time = datetime.datetime.strptime(args.start_time, "%Y-%m-%d %H:%M")
                end_time = datetime.datetime.strptime(args.end_time, "%Y-%m-%d %H:%M")
            except ValueError as e:
                print(f"错误: 时间格式错误: {e}")
                sys.exit(1)
        elif args.command == 'full' and not args.fast:
            # 默认：当天2点到现在
            now = datetime.datetime.now()
            today_2am = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if now < today_2am:
                start_time = today_2am - datetime.timedelta(days=1)
            else:
                start_time = today_2am
            end_time = now
        else:
            # 其他情况设为默认值
            start_time = datetime.datetime(2000, 1, 1)
            end_time = datetime.datetime.now()

    # 获取API密钥
    ai_model = getattr(args, 'ai_model', 'moonshot')
    api_key = getattr(args, 'api_key', '')
    api_key = workflow.get_api_key(ai_model, api_key)
    if not api_key:
        print(f"错误: 未设置API密钥")
        print(f"请使用以下方式之一设置API密钥:")
        print(f"1. 命令行参数: --api-key your-key")
        print(f"2. 环境变量: 设置对应的环境变量")
        print(f"3. 配置文件: 在 {args.config_file} 中设置")
        print(f"   当前模型: {args.ai_model}")
        sys.exit(1)
    
    # 设置分析器
    max_workers = getattr(args, 'max_workers', 50)
    
    workflow.setup_analyzers(ai_model, api_key, max_workers)
    
    print("=== Git对象拯救工具 ===")
    print(f"配置文件: {config_file}")
    print(f"执行命令: {getattr(args, 'command', 'None')}")
    
    # 显示输入源信息
    if getattr(args, 'command', '') in ['extract', 'full'] and getattr(args, 'git_dir', None):
        git_dir = args.git_dir
        print(f"输入源: Git目录 {git_dir}")
        print(f"Git对象目录: {os.path.join(git_dir, 'objects')}")
        if start_time and end_time:
            print(f"时间范围: {start_time} 到 {end_time}")
    elif getattr(args, 'command', '') in ['analyze', 'group', 'compare', 'iterate']:
        input_dir = getattr(args, 'input_dir', 'analyzed_files')
        print(f"输入源: {input_dir}")
    
    print(f"AI模型: {ai_model}")
    print("模式: 3种分析器架构")
    
    # 获取输出目录配置
    extract_output = getattr(args, 'extract_output', 'extracted_objects')
    analyze_output = getattr(args, 'analyze_output', 'analyzed_files')
    grouped_output = getattr(args, 'grouped_output', 'grouped_files')
    organized_output = getattr(args, 'organized_output', 'organized_files')
    
    print(f"提取输出目录: {extract_output}")
    print(f"AI分析输出目录: {analyze_output}")
    print(f"版本分组输出目录: {grouped_output}")
    print(f"版本组织输出目录: {organized_output}")
    print()
    
    if start_time is None:
        start_time = datetime.datetime(2000, 1, 1)
    if end_time is None:
        end_time = datetime.datetime.now()

    try:
        # 根据子命令执行相应操作
        command = getattr(args, 'command', None)
        
        if command == 'extract':
            git_dir = args.git_dir
            workflow.extract_objects(git_dir, extract_output, start_time, end_time)
            
        elif command == 'analyze':
            input_dir = getattr(args, 'input_dir', 'extracted_objects')
            if not os.path.exists(input_dir):
                print(f"错误: {input_dir}目录不存在")
                sys.exit(1)
            workflow.analyze_files(input_dir, analyze_output, ai_model, api_key, max_workers)
            
        elif command == 'group':
            input_dir = getattr(args, 'input_dir', 'analyzed_files')
            if not os.path.exists(input_dir):
                print(f"错误: {input_dir}目录不存在")
                sys.exit(1)
            workflow.group_versions(input_dir, grouped_output)
            
        elif command == 'compare':
            input_dir = getattr(args, 'input_dir', 'grouped_files')
            if not os.path.exists(input_dir):
                print(f"错误: {input_dir}目录不存在")
                sys.exit(1)
            workflow.compare_versions(input_dir, organized_output)
            
        elif command == 'iterate':
            input_dir = getattr(args, 'input_dir', 'analyzed_files')
            if not os.path.exists(input_dir):
                print(f"错误: {input_dir}目录不存在")
                sys.exit(1)
            workflow.iterative_analysis(input_dir, organized_output)
            
        elif command == 'full':
            git_dir = getattr(args, 'git_dir', None)
            if git_dir:
                # 有Git目录，执行完整流程
                print("检测到Git目录，执行完整流程...")
                
                # 1. 提取Git对象
                workflow.extract_objects(git_dir, extract_output, start_time, end_time)
                
                # 2. AI分析
                workflow.analyze_files(extract_output, analyze_output, ai_model, api_key, max_workers)
                
                # 3. 版本分组
                workflow.group_versions(analyze_output, grouped_output)
                
                # 4. 版本比较并组织
                workflow.compare_versions(grouped_output, organized_output)
                
            else:
                # 没有Git目录，从中间文件开始
                print("未检测到Git目录，从中间文件开始...")
                
                # 检查analyzed_files是否存在
                if not os.path.exists(analyze_output):
                    print(f"错误: {analyze_output}目录不存在，无法继续")
                    sys.exit(1)
                
                # 从analyzed_files开始执行后续步骤
                workflow.group_versions(analyze_output, grouped_output)
                workflow.compare_versions(grouped_output, organized_output)
        
        elif command == 'config':
            save_path = getattr(args, 'save', None)
            if save_path:
                # 保存配置
                config_manager = get_config_manager()
                # 获取当前配置数据
                config_data = {
                    "ai_models": {"default_model": config_manager.get_default_model()},
                    "analysis": config_manager.get_analysis_config(),
                    "output": config_manager.get_output_config(),
                    "file_extensions": config_manager.get_file_extensions()
                }
                config_manager.save_config_to_file(save_path, config_data)
                print(f"配置已保存到: {save_path}")
            else:
                print("配置管理命令")
                print("用法: python main.py config save <配置文件路径>")
        
        else:
            print("请指定要执行的命令")
            print("可用命令: extract, analyze, group, compare, full, iterate, config")
            print("使用 --help 查看详细帮助")
            sys.exit(1)
        
        print("=== 操作完成 ===")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 