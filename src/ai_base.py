#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析基类
提取公共的AI分析逻辑和提示词构建
"""

import json
import re
import time
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from .ai_analyzer import AIAnalyzer


class AIAnalysisBase(ABC):
    """AI分析基类"""
    
    def __init__(self, ai_config_key: str = "moonshot", custom_api_key: str = "", max_workers: int = 5):
        """
        初始化AI分析基类
        
        Args:
            ai_config_key: AI模型配置键
            custom_api_key: 自定义API密钥
            max_workers: 最大并发数
        """
        self.ai_analyzer = AIAnalyzer(ai_config_key=ai_config_key, custom_api_key=custom_api_key)
        self.ai_analyzer.max_workers = max_workers
        self.max_workers = max_workers
    
    def get_content_preview(self, content: str, preview_length: int) -> str:
        """
        根据预览长度获取内容预览
        
        Args:
            content: 原始内容
            preview_length: 预览长度
            
        Returns:
            预览内容
        """
        if preview_length == -1:
            return content
        elif preview_length == 0:
            return ""
        else:
            if len(content) > preview_length:
                return content[:preview_length] + "..."
            else:
                return content
    
    def build_files_info(self, files: List[Any], preview_length: int) -> List[Dict]:
        """
        构建文件信息列表
        
        Args:
            files: 文件列表
            preview_length: 预览长度
            
        Returns:
            文件信息列表
        """
        files_info = []
        for i, file_obj in enumerate(files):
            content_preview = self.get_content_preview(file_obj.content, preview_length)
            
            file_info = {
                "index": i + 1,
                "filename": file_obj.suggested_filename,  # 只展示拼接名
                # "hash": file_obj.original_hash,  # 不给AI看完整哈希
                "file_type": file_obj.file_type,
                "analysis": file_obj.ai_analysis,
                "content_preview": content_preview,
            }
            files_info.append(file_info)
        
        return files_info
    
    def call_ai_with_retry(self, messages: List[Dict], temperature: float = 0.2, 
                          timeout: int = 30, max_retries: int = 3) -> str:
        """
        带重试机制的AI调用
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            timeout: 超时时间
            max_retries: 最大重试次数
            
        Returns:
            AI响应
        """
        for attempt in range(max_retries):
            try:
                completion = self.ai_analyzer.chat_complete(
                    messages=messages,
                    temperature=temperature,
                    timeout=timeout
                )
                
                response = completion.choices[0].message.content #type: ignore
                if response is None:
                    raise ValueError("AI返回空响应")
                
                return response
                    
            except Exception as e:
                print(f"AI调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)  # 等待2秒后重试
        
        raise Exception("AI调用失败，已达到最大重试次数")
    
    def call_ai_with_stream(self, messages: List[Dict], temperature: float = 0.2, 
                           timeout: int = 30, silent: bool = False) -> str:
        """
        流式AI调用，用于调试超时问题
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            timeout: 超时时间
            silent: 静默模式，不输出调试信息
            
        Returns:
            AI响应
        """
        try:
            if not silent:
                print(f"🚀 开始流式AI调用...")
                print(f"📊 消息数量: {len(messages)}")
                print(f"🌡️  温度: {temperature}")
                print(f"⏱️  超时: {timeout}s")
                
                # 显示提示词长度
                total_length = sum(len(msg.get('content', '')) for msg in messages)
                print(f"📝 总提示词长度: {total_length} 字符")
            
            response = self.ai_analyzer.chat_complete_stream(
                messages=messages,
                temperature=temperature,
                timeout=timeout,
                silent=silent
            )
            
            return response
            
        except Exception as e:
            if not silent:
                print(f"❌ 流式AI调用失败: {e}")
            raise e
    
    def parse_json_response(self, response: str) -> Dict:
        """
        解析JSON响应
        
        Args:
            response: AI响应
            
        Returns:
            解析后的JSON数据
        """
        try:
            # 尝试提取JSON部分
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(response)
        except Exception as e:
            print(f"解析JSON响应失败: {e}")
            print(f"原始响应: {response}")
            raise e
    
    @abstractmethod
    def build_prompt(self, **kwargs) -> str:
        """
        构建提示词
        
        Returns:
            提示词字符串
        """
        pass
    
    @abstractmethod
    def parse_response(self, response: str, **kwargs) -> Any:
        """
        解析AI响应
        
        Args:
            response: AI响应
            **kwargs: 其他参数
            
        Returns:
            解析结果
        """
        pass
    
    def analyze(self, **kwargs) -> Any:
        """
        执行分析
        
        Args:
            **kwargs: 分析参数
            
        Returns:
            分析结果
        """
        # 构建提示词
        prompt = self.build_prompt(**kwargs)
        
        # 调用AI
        messages = [
            {"role": "system", "content": "你是一个专业的文件版本分析专家。"},
            {"role": "user", "content": prompt},
        ]
        
        # 检查是否启用流式输出（用于调试）
        use_stream = kwargs.get("use_stream", False)
        
        if use_stream:
            response = self.call_ai_with_stream(messages, silent=True)
        else:
            response = self.call_ai_with_retry(messages)
        
        # 解析响应
        # 过滤掉不需要传递给parse_response的参数
        parse_kwargs = {k: v for k, v in kwargs.items() if k not in ['use_stream']}
        return self.parse_response(response, **parse_kwargs) 