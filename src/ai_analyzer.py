#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI文件分析器
使用AI分析提取的git对象文件，判断是否有价值并生成报告
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from .config_manager import ConfigManager
import time
from collections import deque

class AIAnalyzer:
    def __init__(self, ai_config_key: str = "moonshot", custom_api_key: str = ""):
        self.config_manager = ConfigManager()
        self.ai_config_key = ai_config_key
        
        # 获取AI配置
        self.config = self.config_manager.get_ai_config(ai_config_key)
        
        # 如果提供了自定义API密钥，使用它
        if custom_api_key:
            self.config["api_key"] = custom_api_key
            
        # 确保API密钥不为空
        if not self.config["api_key"]:
            raise ValueError(f"AI配置 '{ai_config_key}' 的API密钥为空，请检查配置文件或环境变量")
            
        self.client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )
        
        # 获取分析配置
        analysis_config = self.config_manager.get_analysis_config()
        self.max_workers = analysis_config["max_workers"]
        self.max_content_length = analysis_config["max_content_length"]
        self.temperature = analysis_config["temperature"]
        
        # ========================  请求速率限制  ========================
        # 从配置读取 RPM 限制
        self._rpm_limit = analysis_config.get("rpm_limit", 200)
        self._request_timestamps: deque = deque()  # 存储最近一次的请求时间戳
        # ============================================================
        
        # 获取预览长度配置
        self.file_analysis_preview_length = analysis_config["file_analysis_preview_length"]
        self.batch_grouping_preview_length = analysis_config["batch_grouping_preview_length"]
        self.iterative_similarity_preview_length = analysis_config["iterative_similarity_preview_length"]
        self.version_analysis_preview_length = analysis_config["version_analysis_preview_length"]
        
    def _enforce_rate_limit(self):
        """确保请求速率不超过 rpm 限制"""
        now = time.time()
        window = 60  # 秒
        # 清理过期时间戳
        while self._request_timestamps and now - self._request_timestamps[0] > window:
            self._request_timestamps.popleft()
        if len(self._request_timestamps) >= self._rpm_limit:
            # 需要等待
            sleep_time = window - (now - self._request_timestamps[0]) + 0.05  # 留一点余量
            print(f"达到速率上限({self._rpm_limit} RPM)，暂停 {sleep_time:.2f}s …")
            time.sleep(sleep_time)
        # 记录本次请求
        self._request_timestamps.append(time.time())

    def chat_complete(self, messages, model: Optional[str] = None,
                      temperature: Optional[float] = None, response_format=None, timeout: Optional[int] = None, stream: bool = False):
        """封装 openai chat.completions.create，统一速率限制"""
        self._enforce_rate_limit()
        return self.client.chat.completions.create(
            model=model or self.config["model"],
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            response_format=response_format or {"type": "json_object"},
            timeout=timeout,
            stream=stream
        )
    
    def chat_complete_stream(self, messages, model: Optional[str] = None,
                           temperature: Optional[float] = None, response_format=None, timeout: Optional[int] = None, silent: bool = False):
        """流式调用AI，实时显示输出"""
        self._enforce_rate_limit()
        
        if not silent:
            print("🤖 AI开始响应...")
        start_time = time.time()
        
        try:
            stream = self.client.chat.completions.create(
                model=model or self.config["model"],
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                response_format=response_format or {"type": "json_object"},
                timeout=timeout,
                stream=True
            )
            
            full_response = ""
            chunk_count = 0
            
            for chunk in stream:
                chunk_count += 1
                if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    if not silent:
                        print(content, end="", flush=True)
                    
                    # 每100个chunk显示一次进度
                    if not silent and chunk_count % 100 == 0:
                        elapsed = time.time() - start_time
                        print(f"\n⏱️  已处理 {chunk_count} 个chunk，耗时: {elapsed:.2f}s")
            
            elapsed = time.time() - start_time
            if not silent:
                print(f"\n✅ AI响应完成！总耗时: {elapsed:.2f}s，处理了 {chunk_count} 个chunk")
                print(f"📝 响应长度: {len(full_response)} 字符")
            
            return full_response
            
        except Exception as e:
            elapsed = time.time() - start_time
            if not silent:
                print(f"\n❌ AI流式调用失败！耗时: {elapsed:.2f}s")
                print(f"错误信息: {e}")
            raise e
        
    def analyze_file_with_ai(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        使用AI分析文件内容，获取简短分析、建议命名和文件类型判断。
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 限制文件内容大小，使用文件分析预览长度
            preview_length = self.file_analysis_preview_length
            if preview_length > 0 and len(content) > preview_length:
                content = content[:preview_length] + "\n... [内容过长，已截断]"
            elif preview_length == -1:
                # 无限制，但仍有最大长度保护
                if len(content) > self.max_content_length:
                    content = content[:self.max_content_length] + "\n... [内容过长，已截断]"

            system_prompt = """
            你是一个文件分析助手，你需要分析我提供的文件内容，判断是否是有价值的文件。
            
            有价值的文件包括：
            - 代码文件（.py, .js, .java, .cpp等）
            - 文档文件（.md, .txt, .rst等）
            - 配置文件（.json, .yaml, .toml, .ini等）
            - 其他人类可读的文件
            
            没有价值的文件包括：
            - Git ls-tree输出（格式如：100644 blob hash filename）
            - Git diff输出
            - Git log输出
            - 纯二进制文件内容
            - 系统生成的临时文件
            
            特殊情况：
            - 如果文件整体是有价值的代码或文档，但包含git冲突标记（<<<<<<< HEAD, =======, >>>>>>>），仍然认为是有价值的
            
            示例：
            
            示例1（无价值 - Git ls-tree输出）：
            ```
            100644 blob dfe0770424b2a19faf507a501ebfc23be8f54e7b	.gitattributes
            100644 blob 08e8ba8d6afcd9cebf04888ec1aad55350f8b71d	.gitignore
            100644 blob c31561c8644dc81fb40ee784bf1e55ae0279e669	API_REFERENCE.md
            ```
            分析：这是git ls-tree命令的输出，显示文件列表和hash，不是实际文件内容
            建议：无价值
            
            示例2（有价值 - 包含冲突标记的文档）：
            ```
            # AI创意工作流系统
            一个基于"掩码分解"理论的轻量级AI创作工作流框架...
            <<<<<<< HEAD
            ├── models.ini            # 模型配置文件
            =======
            >>>>>>> 7e7ea78 (Refactor project structure...)
            ```
            分析：这是有价值的README文档，虽然包含git冲突标记，但主要内容是文档
            建议：有价值
            
            示例3（有价值 - 代码文件）：
            ```
            import os
            import json
            from openai import OpenAI
            
            def analyze_file_with_ai(file_path, client):
                # 函数实现...
            ```
            分析：这是Python代码文件，包含实际的代码逻辑
            建议：有价值
            
            你的输出必须是JSON格式，包含以下字段：
            - 'name': 建议文件名，包含后缀
            - 'analysis': 简短分析（100字以内）
            - 'valuable': 布尔值，当文件为有价值的文件时为真
            - 'file_type': 文件类型（如：python, javascript, markdown, text等）
            - 'confidence': 置信度（0-1之间的浮点数）
            """
            
            user_prompt = f"请分析以下文件内容：\n\n```\n{content}\n```"

            completion = self.chat_complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False
            )

            # 类型断言，确保completion是ChatCompletion对象而不是Stream对象
            response_content = completion.choices[0].message.content  # type: ignore
            if(response_content == None):
                return None
            return json.loads(response_content)

        except Exception as e:
            print(f"分析文件 {file_path} 时发生错误: {e}")
            return None
    
    def get_file_extension(self, file_type: str, suggested_name: str) -> str:
        """根据文件类型和建议名称获取文件扩展名"""
        # 如果建议名称已经包含扩展名，直接使用
        if '.' in suggested_name:
            return suggested_name.split('.')[-1]
        
        # 根据文件类型获取扩展名
        return self.config_manager.get_file_extension(file_type.lower())
    
    def generate_new_filename(self, original_filename: str, ai_response: Dict[str, Any]) -> str:
        """生成新的文件名"""
        suggested_name = ai_response.get('name', 'untitled')
        file_type = ai_response.get('file_type', 'text')
        
        # 获取原始哈希前缀（前8位）
        hash_prefix = original_filename.split('.')[0][:8]
        
        # 获取文件扩展名
        extension = self.get_file_extension(file_type, suggested_name)
        
        # 生成新文件名
        if '.' in suggested_name:
            # 如果建议名称包含扩展名，使用它
            base_name = suggested_name.split('.')[0]
            return f"{base_name}_{hash_prefix}.{extension}"
        else:
            return f"{suggested_name}_{hash_prefix}.{extension}"
    
    def analyze_directory(self, input_dir: str, output_dir: str) -> Dict[str, Any]:
        """分析目录中的所有文件"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_path}")
        
        # 确保输出目录存在
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"开始AI分析...")
        print(f"输入目录: {input_path}")
        print(f"输出目录: {output_path}")
        print(f"AI模型: {self.config['name']} ({self.config['model']})")
        print()
        
        # 获取所有文件
        arc_files = [f for f in input_path.iterdir() if f.is_file() and f.suffix == '.txt']
        
        if not arc_files:
            print("警告: 输入目录中没有找到.txt文件")
            return {"analyzed_count": 0, "saved_count": 0, "results": []}
        
        print(f"找到 {len(arc_files)} 个文件需要分析")
        
        results = []
        saved_count = 0
        
        # 使用ThreadPoolExecutor进行并发请求
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.analyze_file_with_ai, file_path): file_path for file_path in arc_files}
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                original_filename = file_path.name
                
                try:
                    ai_response = future.result()
                    
                    if ai_response:
                        # 生成新文件名
                        new_filename = self.generate_new_filename(original_filename, ai_response)
                        
                        # 记录分析结果
                        result_entry = {
                            "original_filename": original_filename,
                            "original_hash": original_filename.split('.')[0],
                            "ai_analysis": ai_response,
                            "suggested_filename": new_filename,
                            "saved": False,
                            "saved_path": None
                        }
                        
                        # 如果文件有价值，保存到输出目录
                        if ai_response.get('valuable', False):
                            new_file_path = output_path / new_filename
                            
                            try:
                                shutil.copy2(file_path, new_file_path)
                                saved_count += 1
                                result_entry["saved"] = True
                                result_entry["saved_path"] = str(new_file_path)
                                print(f"✓ 保存: {original_filename} -> {new_filename}")
                            except Exception as e:
                                print(f"✗ 保存失败: {original_filename} -> {new_filename}: {e}")
                        else:
                            print(f"- 跳过: {original_filename} (无价值)")
                        
                        results.append(result_entry)
                    else:
                        print(f"✗ 分析失败: {original_filename}")
                        results.append({
                            "original_filename": original_filename,
                            "original_hash": original_filename.split('.')[0],
                            "ai_analysis": None,
                            "suggested_filename": None,
                            "saved": False,
                            "saved_path": None,
                            "error": "AI分析失败"
                        })
                        
                except Exception as exc:
                    print(f"✗ 处理异常: {original_filename}: {exc}")
                    results.append({
                        "original_filename": original_filename,
                        "original_hash": original_filename.split('.')[0],
                        "ai_analysis": None,
                        "suggested_filename": None,
                        "saved": False,
                        "saved_path": None,
                        "error": str(exc)
                    })
        
        # 生成分析报告
        analysis_summary = {
            "analysis_info": {
                "ai_model": self.config["name"],
                "model_name": self.config["model"],
                "input_directory": str(input_path),
                "output_directory": str(output_path),
                "total_files": len(arc_files),
                "analyzed_count": len(results),
                "saved_count": saved_count,
                "skipped_count": len(arc_files) - saved_count
            },
            "results": results
        }
        
        # 保存分析报告
        report_file = output_path / "analysis_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析完成!")
        print(f"总文件数: {len(arc_files)}")
        print(f"分析成功: {len(results)}")
        print(f"保存文件: {saved_count}")
        print(f"跳过文件: {len(arc_files) - saved_count}")
        print(f"分析报告已保存到: {report_file}")
        
        return analysis_summary

if __name__ == "__main__":
    # 示例用法
    input_dir = "extracted_objects"
    output_dir = "analyzed_files"
    
    # 创建AI分析器
    analyzer = AIAnalyzer(ai_config_key="moonshot")
    
    # 执行分析
    try:
        results = analyzer.analyze_directory(input_dir, output_dir)
        print(f"分析完成，结果: {results}")
    except Exception as e:
        print(f"分析失败: {e}") 