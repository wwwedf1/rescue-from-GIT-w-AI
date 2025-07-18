#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
读取INI配置文件和环境变量
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_file: str = "config.ini"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        
        self.config.read(self.config_file, encoding='utf-8')
        
    def get_ai_config(self, model_name: str) -> Dict[str, Any]:
        """
        获取AI模型配置
        
        Args:
            model_name: 模型名称
            
        Returns:
            AI模型配置字典
        """
        if model_name not in self.config.sections():
            raise ValueError(f"未找到AI模型配置: {model_name}")
        
        model_config = dict(self.config[model_name])
        
        # 处理API密钥：优先使用环境变量，然后使用配置文件
        api_key = ""
        env_var = model_config.get("env_var", "")
        
        if env_var and os.getenv(env_var):
            api_key = os.getenv(env_var) or ""
        elif model_config.get("api_key"):
            api_key = model_config["api_key"]
        
        model_config["api_key"] = api_key
        
        return model_config
    
    def get_available_models(self) -> list:
        """获取可用的AI模型列表"""
        ai_models_section = "ai_models"
        if ai_models_section in self.config.sections():
            # 从配置中读取所有AI模型
            return [section for section in self.config.sections() 
                   if section.startswith(('moonshot', 'openai', 'azure'))]
        else:
            # 默认模型列表
            return ['moonshot', 'openai', 'azure']
    
    def get_default_model(self) -> str:
        """获取默认AI模型"""
        return self.config.get("ai_models", "default_model", fallback="moonshot")
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """获取分析配置"""
        analysis_config = {}
        
        if "analysis" in self.config.sections():
            analysis_config.update(dict(self.config["analysis"]))
        
        # 转换数据类型
        analysis_config["max_workers"] = int(analysis_config.get("max_workers", 50))
        analysis_config["max_content_length"] = int(analysis_config.get("max_content_length", 15000))
        analysis_config["temperature"] = float(analysis_config.get("temperature", 0.2))
        analysis_config["rpm_limit"] = int(analysis_config.get("rpm_limit", 200))
        
        # 添加预览长度配置
        analysis_config["file_analysis_preview_length"] = int(analysis_config.get("file_analysis_preview_length", 8000))
        analysis_config["batch_grouping_preview_length"] = int(analysis_config.get("batch_grouping_preview_length", 2000))
        analysis_config["iterative_similarity_preview_length"] = int(analysis_config.get("iterative_similarity_preview_length", 2000))
        analysis_config["version_analysis_preview_length"] = int(analysis_config.get("version_analysis_preview_length", -1))
        
        return analysis_config
    
    def get_version_analysis_config(self) -> Dict[str, Any]:
        """获取版本分析配置"""
        version_config = {}
        
        if "version_analysis" in self.config.sections():
            version_config.update(dict(self.config["version_analysis"]))
        
        # 转换数据类型
        stability_configs = {
            "stable": {
                "max_files_per_batch": int(version_config.get("stable_max_files_per_batch", 10)),
                "max_versions_per_group": int(version_config.get("stable_max_versions_per_group", 5)),
                "retry_count": int(version_config.get("stable_retry_count", 3)),
                "delay_between_requests": float(version_config.get("stable_delay_between_requests", 1.0))
            },
            "fast": {
                "max_files_per_batch": int(version_config.get("fast_max_files_per_batch", 20)),
                "max_versions_per_group": int(version_config.get("fast_max_versions_per_group", 8)),
                "retry_count": int(version_config.get("fast_retry_count", 1)),
                "delay_between_requests": float(version_config.get("fast_delay_between_requests", 0.5))
            }
        }
        
        return {
            "default_stability_mode": version_config.get("default_stability_mode", "stable"),
            "stability_configs": stability_configs
        }
    
    def get_file_extensions(self) -> Dict[str, str]:
        """获取文件扩展名映射"""
        if "file_extensions" in self.config.sections():
            return dict(self.config["file_extensions"])
        else:
            # 默认扩展名映射
            return {
                "python": ".py",
                "javascript": ".js",
                "typescript": ".ts",
                "java": ".java",
                "cpp": ".cpp",
                "c": ".c",
                "html": ".html",
                "css": ".css",
                "markdown": ".md",
                "text": ".txt",
                "json": ".json",
                "yaml": ".yaml",
                "toml": ".toml",
                "ini": ".ini",
                "xml": ".xml",
                "sql": ".sql",
                "shell": ".sh",
                "batch": ".bat",
                "powershell": ".ps1"
            }
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        output_config = {}
        
        if "output" in self.config.sections():
            output_config.update(dict(self.config["output"]))
        
        # 转换布尔值
        output_config["create_version_structure"] = output_config.get("create_version_structure", "true").lower() == "true"
        output_config["create_group_directories"] = output_config.get("create_group_directories", "true").lower() == "true"
        
        # 设置默认值
        output_config.setdefault("extract_output", "extracted_objects")
        output_config.setdefault("analyze_output", "analyzed_files")
        output_config.setdefault("grouped_output", "grouped_files")
        output_config.setdefault("organized_output", "organized_files")
        output_config.setdefault("newest_version_dir", "newest_version")
        output_config.setdefault("old_versions_dir", "old/oldversions")
        
        return output_config
    
    def save_config_to_file(self, output_file: str, config_data: Dict[str, Any]):
        """
        保存配置到INI文件
        
        Args:
            output_file: 输出文件路径
            config_data: 配置数据
        """
        config = configparser.ConfigParser()
        
        # 转换配置数据到ConfigParser格式
        for section_name, section_data in config_data.items():
            config[section_name] = {}
            for key, value in section_data.items():
                config[section_name][key] = str(value)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def update_config(self, section: str, key: str, value: Any):
        """
        更新配置值
        
        Args:
            section: 配置段名
            key: 配置键
            value: 配置值
        """
        if section not in self.config.sections():
            self.config.add_section(section)
        
        self.config.set(section, key, str(value))
        
        # 保存到文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_file_extension(self, file_type: str) -> str:
        """根据文件类型获取扩展名"""
        if "file_extensions" in self.config.sections():
            return self.config.get("file_extensions", file_type, fallback="txt")
        return "txt"
    
    def get_available_ai_models(self) -> list:
        """获取可用的AI模型列表"""
        models = []
        for section in self.config.sections():
            if section.startswith("ai_model_"):
                model_name = section.replace("ai_model_", "")
                models.append(model_name)
        return models if models else ["moonshot", "openai", "azure"]

# 全局配置管理器实例
config_manager = ConfigManager()

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager 