#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础工作流类
提取公共的工作流逻辑和配置管理
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from .config_manager import get_config_manager


class BaseWorkflow(ABC):
    """基础工作流类"""
    
    def __init__(self, config_file: str = "config.ini"):
        """
        初始化基础工作流
        
        Args:
            config_file: 配置文件路径
        """
        self.config_manager = get_config_manager()
        self.analysis_config = self.config_manager.get_analysis_config()
        self.version_config = self.config_manager.get_version_analysis_config()
        self.output_config = self.config_manager.get_output_config()
    
    def validate_git_directory(self, git_dir: str) -> bool:
        """
        验证Git目录路径
        
        Args:
            git_dir: Git目录路径
            
        Returns:
            是否有效
        """
        git_dir_path = Path(git_dir)
        if not git_dir_path.exists():
            raise ValueError(f"Git目录不存在: {git_dir}")
        
        if not git_dir_path.name == ".git" and not (git_dir_path / "objects").exists():
            raise ValueError(f"指定的路径不是有效的Git目录: {git_dir}")
        
        return True
    
    def get_api_key(self, model_name: str, custom_api_key: str = "") -> str:
        """
        获取API密钥，优先级：自定义 > 环境变量 > 配置文件
        
        Args:
            model_name: AI模型名称
            custom_api_key: 自定义API密钥
            
        Returns:
            API密钥
        """
        if custom_api_key:
            return custom_api_key
        
        try:
            ai_config = self.config_manager.get_ai_config(model_name)
            api_key = ai_config.get("api_key", "")
            if api_key:
                return api_key
        except Exception as e:
            print(f"警告: 获取AI配置失败: {e}")
        
        return ""
    
    def save_json_report(self, data: Dict, file_path: str) -> None:
        """
        保存JSON报告
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
        """
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_json_report(self, file_path: str) -> Dict:
        """
        加载JSON报告
        
        Args:
            file_path: 文件路径
            
        Returns:
            报告数据
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"报告文件不存在: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行工作流
        
        Returns:
            执行结果
        """
        pass


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, config_file: str = "config.ini"):
        """
        初始化工作流管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_manager = get_config_manager()
        self.workflows: Dict[str, BaseWorkflow] = {}
    
    def register_workflow(self, name: str, workflow: BaseWorkflow) -> None:
        """
        注册工作流
        
        Args:
            name: 工作流名称
            workflow: 工作流实例
        """
        self.workflows[name] = workflow
    
    def execute_workflow(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        执行指定工作流
        
        Args:
            name: 工作流名称
            **kwargs: 工作流参数
            
        Returns:
            执行结果
        """
        if name not in self.workflows:
            raise ValueError(f"未找到工作流: {name}")
        
        return self.workflows[name].execute(**kwargs)
    
    def list_workflows(self) -> List[str]:
        """
        列出所有工作流
        
        Returns:
            工作流名称列表
        """
        return list(self.workflows.keys()) 