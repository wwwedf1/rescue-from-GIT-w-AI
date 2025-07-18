#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的Git对象拯救工具GUI界面
作为配置和调用的入口，调用main.py中的工作流逻辑
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import threading
import os
import subprocess
import sys
from pathlib import Path

from .config_manager import ConfigManager
from .git_extractor import create_time_range_from_2am

class RefactoredGitRescuerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Git对象拯救工具")
        self.root.geometry("1000x900")  # 增加宽度，减少高度
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 语言设置
        self.current_language = "zh"  # 默认中文
        self.texts = self.get_texts()
        
        # 存储UI元素引用，用于语言切换
        self.ui_elements = {}
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="5")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重 - 使用两列布局
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)  # 左侧配置区域
        self.main_frame.columnconfigure(1, weight=2)  # 右侧操作区域
        
        self.create_widgets()
        
    def get_texts(self):
        """获取界面文本"""
        if self.current_language == "zh":
            return {
                "title": "Git对象拯救工具",
                "path_config": "路径配置",
                "git_dir": "Git目录 (.git):",
                "path_hint": "提示: 可以直接选择.git目录，或选择包含.git子目录的仓库根目录",
                "git_dir_optional": "Git目录 (.git) [可选]:",
                "time_config": "时间范围配置",
                "from_2am": "从凌晨2点开始",
                "custom_time": "自定义时间范围",
                "start_time": "开始时间:",
                "end_time": "结束时间:",
                "ai_config": "AI模型配置",
                "ai_model": "AI模型:",
                "api_key": "API密钥:",
                "max_workers": "并发数:",
                "output_config": "输出配置",
                "extract_output": "提取输出目录:",
                "analyze_output": "AI分析输出目录:",
                "grouped_output": "版本分组输出目录:",
                "organized_output": "版本组织输出目录:",
                "action_buttons": "操作按钮",
                "single_step_buttons": "单步骤操作",
                "one_click_buttons": "一键操作",
                "extract_objects": "提取对象",
                "analyze_files": "AI分析",
                "group_parallel": "版本分组",
                "compare_and_organize": "版本比较并组织",
                "stable_group_to_organize": "迭代式版本分析",
                "fast_one_click": "快速型一键",
                "standard_one_click": "标准型一键",
                "clear_log": "清空日志",
                "language": "语言",
                "log_section": "执行日志",
                "browse": "浏览",
                "select_git_dir": "选择Git目录 (.git) 或仓库根目录",
                "select_extract_dir": "选择提取输出目录",
                "select_analyze_dir": "选择AI分析输出目录",
                "select_grouped_dir": "选择版本分组输出目录",
                "select_organized_dir": "选择版本组织输出目录",
                "error": "错误",
                "info": "提示",
                "git_dir_not_exist": "指定的Git目录不存在",
                "invalid_git_dir": "指定的路径不是有效的Git目录",
                "git_dir_hint": "请选择.git目录，或包含.git子目录的仓库根目录",
                "api_key_required": "请输入API密钥",
                "time_format_error": "时间格式错误",
                "extract_success": "提取完成！处理了 {processed} 个对象，保存了 {saved} 个文件",
                "extract_failed": "提取失败",
                "analyze_success": "AI分析完成！分析了 {total} 个文件，保存了 {saved} 个有价值文件",
                "analyze_failed": "AI分析失败",
                "group_success": "分组完成！处理了 {groups} 个版本组",
                "group_failed": "分组失败",
                "compare_organize_success": "组内比较并组织完成！处理了 {groups} 个版本组",
                "compare_organize_failed": "组内比较并组织失败",
                "stable_success": "稳定型分组到组织完成！处理了 {groups} 个版本组",
                "stable_failed": "稳定型分组到组织失败",
                "fast_one_click_success": "快速型一键完成！",
                "fast_one_click_failed": "快速型一键失败",
                "standard_one_click_success": "标准型一键完成！",
                "standard_one_click_failed": "标准型一键失败",
                "complete": "完成",
                "git_dir_required_for_extract": "提取Git对象需要指定Git目录",
                "no_git_dir_warning": "未指定Git目录，将使用中间文件作为输入源",
                "command_executing": "正在执行命令（输出将显示在系统终端中）...",
                "command_completed": "命令执行完成",
                "command_failed": "命令执行失败"
            }
        else:
            return {
                "title": "Git Object Rescuer Tool (Refactored)",
                "path_config": "Path Configuration",
                "git_dir": "Git Directory (.git):",
                "path_hint": "Hint: You can directly select the .git directory, or select the repository root directory containing the .git subdirectory",
                "git_dir_optional": "Git Directory (.git) [Optional]:",
                "time_config": "Time Range Configuration",
                "from_2am": "Start from 2 AM",
                "custom_time": "Custom Time Range",
                "start_time": "Start Time:",
                "end_time": "End Time:",
                "ai_config": "AI Model Configuration",
                "ai_model": "AI Model:",
                "api_key": "API Key:",
                "max_workers": "Max Workers:",
                "output_config": "Output Configuration",
                "extract_output": "Extract Output Directory:",
                "analyze_output": "AI Analysis Output Directory:",
                "grouped_output": "Version Grouping Output Directory:",
                "organized_output": "Version Organization Output Directory:",
                "action_buttons": "Action Buttons",
                "single_step_buttons": "Single Step Operations",
                "one_click_buttons": "One-Click Operations",
                "extract_objects": "Extract Objects",
                "analyze_files": "AI Analysis",
                "group_parallel": "Version Grouping",
                "compare_and_organize": "Version Compare & Organize",
                "stable_group_to_organize": "Iterative Version Analysis",
                "fast_one_click": "Fast One-Click",
                "standard_one_click": "Standard One-Click",
                "clear_log": "Clear Log",
                "language": "Language",
                "log_section": "Execution Log",
                "browse": "Browse",
                "select_git_dir": "Select Git Directory (.git) or Repository Root",
                "select_extract_dir": "Select Extract Output Directory",
                "select_analyze_dir": "Select AI Analysis Output Directory",
                "select_grouped_dir": "Select Version Grouping Output Directory",
                "select_organized_dir": "Select Version Organization Output Directory",
                "error": "Error",
                "info": "Info",
                "git_dir_not_exist": "Specified Git directory does not exist",
                "invalid_git_dir": "Specified path is not a valid Git directory",
                "git_dir_hint": "Please select .git directory, or repository root directory containing .git subdirectory",
                "api_key_required": "Please enter API key",
                "time_format_error": "Time format error",
                "extract_success": "Extraction complete! Processed {processed} objects, saved {saved} files",
                "extract_failed": "Extraction failed",
                "analyze_success": "AI analysis complete! Analyzed {total} files, saved {saved} valuable files",
                "analyze_failed": "AI analysis failed",
                "group_success": "Grouping complete! Processed {groups} version groups",
                "group_failed": "Grouping failed",
                "compare_organize_success": "Compare & organize complete! Processed {groups} version groups",
                "compare_organize_failed": "Compare & organize failed",
                "stable_success": "Stable group to organize complete! Processed {groups} version groups",
                "stable_failed": "Stable group to organize failed",
                "fast_one_click_success": "Fast one-click complete!",
                "fast_one_click_failed": "Fast one-click failed",
                "standard_one_click_success": "Standard one-click complete!",
                "standard_one_click_failed": "Standard one-click failed",
                "complete": "Complete",
                "git_dir_required_for_extract": "Git directory is required for extracting objects",
                "no_git_dir_warning": "No Git directory specified, will use intermediate files as input source",
                "command_executing": "Executing command (output will show in system terminal)...",
                "command_completed": "Command completed",
                "command_failed": "Command failed"
            }
        
    def create_widgets(self):
        """创建GUI组件"""
        # 使用两列布局：左侧配置，右侧操作
        self.create_config_section()  # 左侧配置区域
        self.create_action_section()  # 右侧操作区域
        self.create_log_section()     # 底部日志区域
        
    def create_config_section(self):
        """创建左侧配置区域"""
        config_frame = ttk.Frame(self.main_frame)
        config_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        config_frame.columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(config_frame, text=self.texts["title"], font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # 路径配置
        self.create_path_section(config_frame, 1)
        
        # 时间配置
        self.create_time_section(config_frame, 2)
        
        # AI配置
        self.create_ai_section(config_frame, 3)
        
        # 输出配置
        self.create_output_section(config_frame, 4)
        
    def create_path_section(self, parent, row):
        """创建路径配置区域"""
        path_frame = ttk.LabelFrame(parent, text=self.texts["path_config"], padding="5")
        path_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        path_frame.columnconfigure(1, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["path_config"] = path_frame
        
        # Git目录选择
        git_dir_label = ttk.Label(path_frame, text=self.texts["git_dir_optional"])
        git_dir_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["git_dir_optional"] = git_dir_label
        
        git_frame = ttk.Frame(path_frame)
        git_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        git_frame.columnconfigure(0, weight=1)
        
        self.git_repo_var = tk.StringVar()
        git_entry = ttk.Entry(git_frame, textvariable=self.git_repo_var)
        git_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        browse_btn = ttk.Button(git_frame, text=self.texts["browse"], command=self.browse_git_repo)
        browse_btn.grid(row=0, column=1)
        self.ui_elements["browse"] = browse_btn
        
        # 路径提示
        hint_label = ttk.Label(path_frame, text=self.texts["path_hint"], foreground="gray", font=("Arial", 8))
        hint_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self.ui_elements["path_hint"] = hint_label
        
    def create_time_section(self, parent, row):
        """创建时间配置区域"""
        time_frame = ttk.LabelFrame(parent, text=self.texts["time_config"], padding="5")
        time_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        time_frame.columnconfigure(1, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["time_config"] = time_frame
        
        # 时间模式选择
        self.time_mode_var = tk.StringVar(value="2am")
        from_2am_radio = ttk.Radiobutton(time_frame, text=self.texts["from_2am"], variable=self.time_mode_var, 
                       value="2am", command=self.on_time_mode_change)
        from_2am_radio.grid(row=0, column=0, sticky="w")
        self.ui_elements["from_2am"] = from_2am_radio
        
        custom_time_radio = ttk.Radiobutton(time_frame, text=self.texts["custom_time"], variable=self.time_mode_var, 
                       value="custom", command=self.on_time_mode_change)
        custom_time_radio.grid(row=1, column=0, sticky="w")
        self.ui_elements["custom_time"] = custom_time_radio
        
        # 自定义时间输入
        custom_frame = ttk.Frame(time_frame)
        custom_frame.grid(row=0, column=1, rowspan=2, sticky="ew", padx=(20, 0))
        custom_frame.columnconfigure(1, weight=1)
        custom_frame.columnconfigure(3, weight=1)
        
        start_time_label = ttk.Label(custom_frame, text=self.texts["start_time"])
        start_time_label.grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.ui_elements["start_time"] = start_time_label
        
        self.start_time_var = tk.StringVar()
        self.start_entry = ttk.Entry(custom_frame, textvariable=self.start_time_var, state="disabled")
        self.start_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        end_time_label = ttk.Label(custom_frame, text=self.texts["end_time"])
        end_time_label.grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.ui_elements["end_time"] = end_time_label
        
        self.end_time_var = tk.StringVar()
        self.end_entry = ttk.Entry(custom_frame, textvariable=self.end_time_var, state="disabled")
        self.end_entry.grid(row=0, column=3, sticky="ew")
        
        # 时间格式提示
        time_format_text = "格式: YYYY-MM-DD HH:MM" if self.current_language == "zh" else "Format: YYYY-MM-DD HH:MM"
        time_hint = ttk.Label(time_frame, text=time_format_text, foreground="gray", font=("Arial", 8))
        time_hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self.ui_elements["time_format"] = time_hint
        
        # 预填充当前时间范围
        self.prefill_time_range()
        
    def create_ai_section(self, parent, row):
        """创建AI配置区域"""
        ai_frame = ttk.LabelFrame(parent, text=self.texts["ai_config"], padding="5")
        ai_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        ai_frame.columnconfigure(1, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["ai_config"] = ai_frame
        
        # AI模型选择
        ai_model_label = ttk.Label(ai_frame, text=self.texts["ai_model"])
        ai_model_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["ai_model"] = ai_model_label
        
        self.ai_model_var = tk.StringVar()
        ai_model_combo = ttk.Combobox(ai_frame, textvariable=self.ai_model_var, state="readonly")
        ai_model_combo['values'] = self.config_manager.get_available_models()
        ai_model_combo.set(self.config_manager.get_default_model())
        ai_model_combo.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        ai_model_combo.bind('<<ComboboxSelected>>', self.on_ai_model_change)
        
        # API密钥
        api_key_label = ttk.Label(ai_frame, text=self.texts["api_key"])
        api_key_label.grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["api_key"] = api_key_label
        
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(ai_frame, textvariable=self.api_key_var, show="*")
        api_key_entry.grid(row=1, column=1, sticky="ew", pady=(0, 5))
        
        # 并发数
        max_workers_label = ttk.Label(ai_frame, text=self.texts["max_workers"])
        max_workers_label.grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["max_workers"] = max_workers_label
        
        self.max_workers_var = tk.StringVar(value="50")
        max_workers_entry = ttk.Entry(ai_frame, textvariable=self.max_workers_var)
        max_workers_entry.grid(row=2, column=1, sticky="ew")
        
    def create_output_section(self, parent, row):
        """创建输出配置区域"""
        output_frame = ttk.LabelFrame(parent, text=self.texts["output_config"], padding="5")
        output_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        output_frame.columnconfigure(1, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["output_config"] = output_frame
        
        # 提取输出目录
        extract_output_label = ttk.Label(output_frame, text=self.texts["extract_output"])
        extract_output_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["extract_output"] = extract_output_label
        
        extract_frame = ttk.Frame(output_frame)
        extract_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 3))
        extract_frame.columnconfigure(0, weight=1)
        
        self.extract_output_var = tk.StringVar(value="extracted_objects")
        extract_entry = ttk.Entry(extract_frame, textvariable=self.extract_output_var)
        extract_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        extract_browse_btn = ttk.Button(extract_frame, text=self.texts["browse"], command=self.browse_extract_output)
        extract_browse_btn.grid(row=0, column=1)
        self.ui_elements["extract_browse"] = extract_browse_btn
        
        # AI分析输出目录
        analyze_output_label = ttk.Label(output_frame, text=self.texts["analyze_output"])
        analyze_output_label.grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["analyze_output"] = analyze_output_label
        
        analyze_frame = ttk.Frame(output_frame)
        analyze_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 3))
        analyze_frame.columnconfigure(0, weight=1)
        
        self.analyze_output_var = tk.StringVar(value="analyzed_files")
        analyze_entry = ttk.Entry(analyze_frame, textvariable=self.analyze_output_var)
        analyze_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        analyze_browse_btn = ttk.Button(analyze_frame, text=self.texts["browse"], command=self.browse_analyze_output)
        analyze_browse_btn.grid(row=0, column=1)
        self.ui_elements["analyze_browse"] = analyze_browse_btn
        
        # 版本分析输出目录
        grouped_output_label = ttk.Label(output_frame, text=self.texts["grouped_output"])
        grouped_output_label.grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["grouped_output"] = grouped_output_label
        
        grouped_frame = ttk.Frame(output_frame)
        grouped_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 3))
        grouped_frame.columnconfigure(0, weight=1)
        
        self.grouped_output_var = tk.StringVar(value="grouped_files")
        grouped_entry = ttk.Entry(grouped_frame, textvariable=self.grouped_output_var)
        grouped_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        grouped_browse_btn = ttk.Button(grouped_frame, text=self.texts["browse"], command=self.browse_grouped_output)
        grouped_browse_btn.grid(row=0, column=1)
        self.ui_elements["grouped_browse"] = grouped_browse_btn
        
        # 版本组织输出目录
        organized_output_label = ttk.Label(output_frame, text=self.texts["organized_output"])
        organized_output_label.grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.ui_elements["organized_output"] = organized_output_label
        
        organized_frame = ttk.Frame(output_frame)
        organized_frame.grid(row=7, column=0, columnspan=2, sticky="ew")
        organized_frame.columnconfigure(0, weight=1)
        
        self.organized_output_var = tk.StringVar(value="organized_files")
        organized_entry = ttk.Entry(organized_frame, textvariable=self.organized_output_var)
        organized_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        organized_browse_btn = ttk.Button(organized_frame, text=self.texts["browse"], command=self.browse_organized_output)
        organized_browse_btn.grid(row=0, column=1)
        self.ui_elements["organized_browse"] = organized_browse_btn
        
    def create_action_section(self):
        """创建右侧操作按钮区域"""
        action_frame = ttk.Frame(self.main_frame)
        action_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        action_frame.columnconfigure(0, weight=1)
        
        # 语言切换按钮
        lang_frame = ttk.Frame(action_frame)
        lang_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        lang_frame.columnconfigure(0, weight=1)
        
        self.lang_btn = ttk.Button(lang_frame, text="🌐", command=self.toggle_language, width=3)
        self.lang_btn.grid(row=0, column=1, padx=(0, 0))
        
        # 单步骤操作
        single_frame = ttk.LabelFrame(action_frame, text=self.texts["single_step_buttons"], padding="5")
        single_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        single_frame.columnconfigure(0, weight=1)
        single_frame.columnconfigure(1, weight=1)
        single_frame.columnconfigure(2, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["single_step_buttons"] = single_frame
        
        # 将按钮分为两行，每行3个按钮
        extract_btn = ttk.Button(single_frame, text=self.texts["extract_objects"], command=self.extract_objects)
        extract_btn.grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        self.ui_elements["extract_objects"] = extract_btn
        
        analyze_btn = ttk.Button(single_frame, text=self.texts["analyze_files"], command=self.analyze_files)
        analyze_btn.grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        self.ui_elements["analyze_files"] = analyze_btn
        
        group_btn = ttk.Button(single_frame, text=self.texts["group_parallel"], command=self.group_parallel)
        group_btn.grid(row=0, column=2, padx=3, pady=3, sticky="ew")
        self.ui_elements["group_parallel"] = group_btn
        
        compare_btn = ttk.Button(single_frame, text=self.texts["compare_and_organize"], command=self.compare_and_organize)
        compare_btn.grid(row=1, column=0, padx=3, pady=3, sticky="ew")
        self.ui_elements["compare_and_organize"] = compare_btn
        
        stable_btn = ttk.Button(single_frame, text=self.texts["stable_group_to_organize"], command=self.stable_group_to_organize)
        stable_btn.grid(row=1, column=1, padx=3, pady=3, sticky="ew")
        self.ui_elements["stable_group_to_organize"] = stable_btn
        
        # 一键操作
        oneclick_frame = ttk.LabelFrame(action_frame, text=self.texts["one_click_buttons"], padding="5")
        oneclick_frame.grid(row=2, column=0, sticky="ew")
        oneclick_frame.columnconfigure(0, weight=1)
        oneclick_frame.columnconfigure(1, weight=1)
        oneclick_frame.columnconfigure(2, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["one_click_buttons"] = oneclick_frame
        
        fast_btn = ttk.Button(oneclick_frame, text=self.texts["fast_one_click"], command=self.fast_one_click)
        fast_btn.grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        self.ui_elements["fast_one_click"] = fast_btn
        
        standard_btn = ttk.Button(oneclick_frame, text=self.texts["standard_one_click"], command=self.standard_one_click)
        standard_btn.grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        self.ui_elements["standard_one_click"] = standard_btn
        
        clear_btn = ttk.Button(oneclick_frame, text=self.texts["clear_log"], command=self.clear_log)
        clear_btn.grid(row=0, column=2, padx=3, pady=3, sticky="ew")
        self.ui_elements["clear_log"] = clear_btn
        
    def create_log_section(self):
        """创建底部日志区域"""
        log_frame = ttk.LabelFrame(self.main_frame, text=self.texts["log_section"], padding="5")
        log_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # 保存UI元素引用
        self.ui_elements["log_section"] = log_frame
        
        # 日志提示
        hint_text = "注意：命令执行过程的详细输出将显示在系统终端中" if self.current_language == "zh" else "Note: Detailed command output will be shown in the system terminal"
        log_hint = ttk.Label(log_frame, text=hint_text, 
                            foreground="blue", font=("Arial", 9))
        log_hint.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.ui_elements["log_hint"] = log_hint
        
        # 日志文本框
        self.log_text = tk.Text(log_frame, height=18, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=1, column=0, sticky="nsew")
        log_scrollbar.grid(row=1, column=1, sticky="ns")
        
    def toggle_language(self):
        """切换语言"""
        self.current_language = "en" if self.current_language == "zh" else "zh"
        self.texts = self.get_texts()
        self.update_ui_texts()
        
    def update_ui_texts(self):
        """更新界面文本"""
        self.root.title(self.texts["title"])
        
        # 直接更新所有保存的UI元素
        for key, element in self.ui_elements.items():
            if key in self.texts:
                if isinstance(element, ttk.LabelFrame):
                    element.configure(text=self.texts[key])
                elif isinstance(element, ttk.Label):
                    element.configure(text=self.texts[key])
                elif isinstance(element, ttk.Button):
                    element.configure(text=self.texts[key])
                elif isinstance(element, ttk.Radiobutton):
                    element.configure(text=self.texts[key])
        
        # 更新日志提示文本
        hint_text = "注意：命令执行过程的详细输出将显示在系统终端中" if self.current_language == "zh" else "Note: Detailed command output will be shown in the system terminal"
        if "log_hint" in self.ui_elements:
            self.ui_elements["log_hint"].configure(text=hint_text)
        
        # 更新时间格式提示文本
        time_format_text = "格式: YYYY-MM-DD HH:MM" if self.current_language == "zh" else "Format: YYYY-MM-DD HH:MM"
        if "time_format" in self.ui_elements:
            self.ui_elements["time_format"].configure(text=time_format_text)
        
    def browse_git_repo(self):
        """浏览Git仓库"""
        directory = filedialog.askdirectory(title=self.texts["select_git_dir"])
        if directory:
            self.git_repo_var.set(directory)
            
    def browse_extract_output(self):
        """浏览提取输出目录"""
        directory = filedialog.askdirectory(title=self.texts["select_extract_dir"])
        if directory:
            self.extract_output_var.set(directory)
            
    def browse_analyze_output(self):
        """浏览AI分析输出目录"""
        directory = filedialog.askdirectory(title=self.texts["select_analyze_dir"])
        if directory:
            self.analyze_output_var.set(directory)
            
    def browse_grouped_output(self):
        """浏览版本分组输出目录"""
        directory = filedialog.askdirectory(title=self.texts["select_grouped_dir"])
        if directory:
            self.grouped_output_var.set(directory)
            
    def browse_organized_output(self):
        """浏览版本组织输出目录"""
        directory = filedialog.askdirectory(title=self.texts["select_organized_dir"])
        if directory:
            self.organized_output_var.set(directory)
            
    def prefill_time_range(self):
        """预填充时间范围"""
        # 获取当前时间
        now = datetime.datetime.now()
        today_2am = now.replace(hour=2, minute=0, second=0, microsecond=0)
        
        # 如果当前时间小于今天2点，则使用昨天2点
        if now < today_2am:
            start_time = today_2am - datetime.timedelta(days=1)
        else:
            start_time = today_2am
        
        # 设置预填充值
        self.start_time_var.set(start_time.strftime("%Y-%m-%d %H:%M"))
        self.end_time_var.set(now.strftime("%Y-%m-%d %H:%M"))
    
    def on_time_mode_change(self):
        """时间模式改变事件"""
        if self.time_mode_var.get() == "2am":
            self.start_time_var.set("")
            self.end_time_var.set("")
            # 禁用时间输入框
            self.start_entry.configure(state="disabled")
            self.end_entry.configure(state="disabled")
        else:
            # 启用时间输入框并预填充
            self.start_entry.configure(state="normal")
            self.end_entry.configure(state="normal")
            self.prefill_time_range()
                    
    def on_ai_model_change(self, event=None):
        """AI模型改变事件"""
        # 这里可以添加模型切换时的逻辑
        pass
        
    def log_message(self, message):
        """记录日志消息"""
        self.log_text.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def validate_inputs(self, require_git_dir=False) -> bool:
        """验证输入"""
        # 验证Git目录（仅在需要时）
        if require_git_dir:
            git_dir = self.git_repo_var.get().strip()
            if not git_dir:
                self.show_error(self.texts["git_dir_required_for_extract"])
                return False
                
            git_path = Path(git_dir)
            if not git_path.exists():
                self.show_error(self.texts["git_dir_not_exist"])
                return False
                
            if not git_path.name == ".git" and not (git_path / "objects").exists():
                self.show_error(self.texts["invalid_git_dir"])
                return False
        else:
            # 如果不要求Git目录，检查是否提供了Git目录
            git_dir = self.git_repo_var.get().strip()
            if not git_dir:
                self.log_message(self.texts["no_git_dir_warning"])
            
        # 验证API密钥（检查环境变量和配置文件）
        api_key = self.get_api_key()
        if not api_key:
            self.show_error(self.texts["api_key_required"])
            return False
            
        return True
        
    def show_error(self, message):
        """显示错误消息"""
        messagebox.showerror(self.texts["error"], message)
        
    def show_info(self, message):
        """显示信息消息"""
        messagebox.showinfo(self.texts["info"], message)
        
    def get_api_key(self) -> str:
        """获取API密钥（优先使用GUI输入，否则使用环境变量）"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            try:
                ai_config = self.config_manager.get_ai_config(self.ai_model_var.get())
                api_key = ai_config.get("api_key", "")
            except Exception as e:
                self.log_message(f"获取API密钥失败: {e}")
                return ""
        return api_key
    
    def get_time_range(self) -> tuple:
        """获取时间范围"""
        if self.time_mode_var.get() == "2am":
            return create_time_range_from_2am()
        else:
            try:
                start_time = datetime.datetime.strptime(self.start_time_var.get(), "%Y-%m-%d %H:%M")
                end_time = datetime.datetime.strptime(self.end_time_var.get(), "%Y-%m-%d %H:%M")
                return start_time, end_time
            except ValueError:
                self.show_error(self.texts["time_format_error"])
                return None, None
    
    def build_command_args(self, operation: str) -> list:
        """构建精简的命令行参数"""
        args = [sys.executable, "main.py"]
        
        # 根据操作类型选择对应的子命令
        if operation == "extract":
            args.append("extract")
            # 添加Git目录（必需）
            git_dir = self.git_repo_var.get().strip()
            if git_dir:
                args.extend(["--git-dir", git_dir])
            else:
                raise ValueError("提取Git对象需要指定Git目录")
                
        elif operation == "analyze":
            args.append("analyze")
            
        elif operation == "group":
            args.append("group")
            
        elif operation == "compare":
            args.append("compare")
            
        elif operation == "iterate":
            args.append("iterate")
            
        elif operation == "full":
            args.append("full")
            # 添加Git目录（可选）
            git_dir = self.git_repo_var.get().strip()
            if git_dir:
                args.extend(["--git-dir", git_dir])
                
        elif operation == "full_fast":
            args.append("full")
            args.append("--fast")
            # 添加Git目录（可选）
            git_dir = self.git_repo_var.get().strip()
            if git_dir:
                args.extend(["--git-dir", git_dir])
        
        # 添加时间参数（仅在自定义时间模式下）
        if self.time_mode_var.get() == "custom":
            start_time = self.start_time_var.get().strip()
            end_time = self.end_time_var.get().strip()
            if start_time:
                args.extend(["--start-time", start_time])
            if end_time:
                args.extend(["--end-time", end_time])
        
        # 添加AI配置（仅在非默认值时）
        ai_model = self.ai_model_var.get()
        if ai_model != "moonshot":  # 默认模型
            args.extend(["--ai-model", ai_model])
            
        api_key = self.get_api_key()
        if api_key:  # 仅在提供了API密钥时
            args.extend(["--api-key", api_key])
            
        max_workers = self.max_workers_var.get()
        if max_workers != "50":  # 默认并发数
            args.extend(["--max-workers", max_workers])
        
        # 添加输出目录（仅在非默认值时）
        extract_output = self.extract_output_var.get()
        if extract_output != "extracted_objects":
            args.extend(["--extract-output", extract_output])
            
        analyze_output = self.analyze_output_var.get()
        if analyze_output != "analyzed_files":
            args.extend(["--analyze-output", analyze_output])
            
        grouped_output = self.grouped_output_var.get()
        if grouped_output != "grouped_files":
            args.extend(["--grouped-output", grouped_output])
            
        organized_output = self.organized_output_var.get()
        if organized_output != "organized_files":
            args.extend(["--organized-output", organized_output])
        
        return args
    
    def execute_command(self, operation: str, operation_name: str):
        """执行命令"""
        if not self.validate_inputs(require_git_dir=(operation == "extract")):
            return
            
        def command_thread():
            try:
                self.log_message(f"开始{operation_name}...")
                self.log_message(self.texts["command_executing"])
                
                # 构建命令
                args = self.build_command_args(operation)
                self.log_message(f"执行命令: {' '.join(args)}")
                
                # 在系统终端中执行命令，不捕获输出
                if sys.platform == "win32":
                    # Windows系统
                    result = subprocess.run(
                        args,
                        shell=True,  # 使用shell确保在系统终端中显示
                        cwd=os.getcwd()
                    )
                else:
                    # Unix/Linux系统
                    result = subprocess.run(
                        args,
                        cwd=os.getcwd()
                    )
                
                # 检查返回码
                if result.returncode == 0:
                    self.log_message(self.texts["command_completed"])
                    self.log_message(f"{operation_name}完成！")
                else:
                    self.log_message(self.texts["command_failed"])
                    self.log_message(f"返回码: {result.returncode}")
                    
            except Exception as e:
                self.log_message(f"{operation_name}失败: {e}")
                messagebox.showerror(self.texts["error"], f"{operation_name}失败: {e}")
                
        threading.Thread(target=command_thread, daemon=True).start()
    
    def extract_objects(self):
        """提取Git对象"""
        self.execute_command("extract", "提取Git对象")
        
    def analyze_files(self):
        """AI分析文件"""
        self.execute_command("analyze", "AI分析")
        
    def group_parallel(self):
        """分组（并行）"""
        self.execute_command("group", "版本分组")
        
    def compare_and_organize(self):
        """组内比较并组织（并行）"""
        self.execute_command("compare", "版本比较并组织")
        
    def stable_group_to_organize(self):
        """稳定型分组到组织"""
        self.execute_command("iterate", "迭代式版本分析")
        
    def fast_one_click(self):
        """快速型一键"""
        self.execute_command("full_fast", "快速型一键操作")
        
    def standard_one_click(self):
        """标准型一键"""
        self.execute_command("full", "标准型一键操作")

def main():
    root = tk.Tk()
    app = RefactoredGitRescuerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 