#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git对象提取器
从指定的git objects目录中提取指定时间范围内的对象文件
"""

import os
import subprocess
import shutil
import datetime
from pathlib import Path
import hashlib
import json
from typing import Optional, Dict, List

class GitObjectExtractor:
    def __init__(self, git_dir_path: str, output_dir: str):
        self.git_dir_path = Path(git_dir_path)
        
        # 如果提供的是.git目录，直接使用
        if self.git_dir_path.name == ".git":
            self.git_objects_path = self.git_dir_path / "objects"
        else:
            # 如果提供的是仓库根目录，查找.git子目录
            self.git_objects_path = self.git_dir_path / ".git" / "objects"
        
        self.output_dir = Path(output_dir)
        self.extraction_log = []
        
        # 获取仓库根目录（用于git命令）
        if self.git_dir_path.name == ".git":
            self.repo_root = self.git_dir_path.parent
        else:
            self.repo_root = self.git_dir_path
        
    def get_file_modification_time(self, file_path: Path) -> Optional[datetime.datetime]:
        """获取文件的修改时间"""
        try:
            stat = os.stat(file_path)
            return datetime.datetime.fromtimestamp(stat.st_mtime)
        except Exception as e:
            print(f"警告: 无法获取文件修改时间 {file_path}: {e}")
            return None
    
    def is_in_time_range(self, file_path: Path, start_time: datetime.datetime, end_time: datetime.datetime) -> bool:
        """检查文件修改时间是否在指定时间范围内"""
        mod_time = self.get_file_modification_time(file_path)
        if mod_time is None:
            return False
        
        return start_time <= mod_time <= end_time
    
    def get_git_object_content(self, object_hash: str) -> Optional[str]:
        """使用git cat-file -p获取对象内容"""
        try:
            result = subprocess.run(
                ['git', 'cat-file', '-p', object_hash],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.repo_root
            )
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"警告: 无法获取对象 {object_hash}: {result.stderr}")
                return None
        except Exception as e:
            print(f"错误: 执行git cat-file失败 {object_hash}: {e}")
            return None
    
    def save_content_to_file(self, content: str, file_path: Path) -> bool:
        """保存内容到文件"""
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"错误: 保存文件失败 {file_path}: {e}")
            return False
    
    def is_valid_git_hash(self, hash_str: str) -> bool:
        """检查是否为有效的Git对象哈希"""
        # Git对象哈希是40个十六进制字符
        if len(hash_str) != 40:
            return False
        
        # 检查是否只包含十六进制字符
        try:
            int(hash_str, 16)
            return True
        except ValueError:
            return False
    
    def extract_objects(self, start_time: datetime.datetime, end_time: datetime.datetime) -> Dict:
        """提取指定时间范围内的git对象"""
        if not self.git_objects_path.exists():
            raise FileNotFoundError(f"Git对象目录不存在: {self.git_objects_path}")
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"开始扫描Git对象目录: {self.git_objects_path}")
        print(f"输出目录: {self.output_dir}")
        print(f"Git目录路径: {self.git_dir_path}")
        print(f"仓库根目录: {self.repo_root}")
        print(f"时间范围: {start_time} 到 {end_time}")
        print()
        
        processed_count = 0
        saved_count = 0
        extraction_results = []
        
        # 遍历所有子目录（前两个字符的哈希目录）
        for subdir in self.git_objects_path.iterdir():
            if not subdir.is_dir():
                continue
                
            # 检查子目录修改时间
            if not self.is_in_time_range(subdir, start_time, end_time):
                continue
                
            # 跳过非Git对象目录（如info、pack等）
            if subdir.name in ['info', 'pack']:
                print(f"跳过非对象目录: {subdir.name}")
                continue
                
            print(f"处理目录: {subdir.name}")
            
            # 遍历子目录中的文件
            for obj_file in subdir.iterdir():
                if not obj_file.is_file():
                    continue
                    
                # 检查文件修改时间
                if not self.is_in_time_range(obj_file, start_time, end_time):
                    continue
                    
                # 构建完整的对象哈希
                object_hash = subdir.name + obj_file.name
                
                # 验证对象哈希是否有效
                if not self.is_valid_git_hash(object_hash):
                    print(f"  跳过无效对象: {object_hash}")
                    continue
                    
                processed_count += 1
                
                print(f"  处理对象: {object_hash}")
                
                # 获取对象内容
                content = self.get_git_object_content(object_hash)
                if content is None:
                    continue
                
                # 保存到输出目录
                output_file = self.output_dir / f"{object_hash}.txt"
                if self.save_content_to_file(content, output_file):
                    saved_count += 1
                    print(f"    已保存: {output_file}")
                    
                    # 记录提取信息
                    mod_time = self.get_file_modification_time(obj_file)
                    extraction_results.append({
                        "original_hash": object_hash,
                        "saved_filename": f"{object_hash}.txt",
                        "file_path": str(output_file),
                        "modification_time": mod_time.isoformat() if mod_time else None,
                        "content_length": len(content)
                    })
        
        # 保存提取日志
        log_file = self.output_dir / "extraction_log.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "extraction_info": {
                    "git_objects_path": str(self.git_objects_path),
                    "git_dir_path": str(self.git_dir_path),
                    "repo_root": str(self.repo_root),
                    "output_dir": str(self.output_dir),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "processed_count": processed_count,
                    "saved_count": saved_count
                },
                "extracted_files": extraction_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n提取完成!")
        print(f"处理的对象数量: {processed_count}")
        print(f"成功保存的文件数量: {saved_count}")
        print(f"提取日志已保存到: {log_file}")
        
        return {
            "processed_count": processed_count,
            "saved_count": saved_count,
            "extraction_results": extraction_results,
            "log_file": str(log_file)
        }

def create_time_range_from_2am() -> tuple:
    """创建从凌晨2点开始的时间范围"""
    now = datetime.datetime.now()
    today_2am = now.replace(hour=2, minute=0, second=0, microsecond=0)
    
    # 如果当前时间小于凌晨2点，则使用昨天的凌晨2点
    if now < today_2am:
        start_time = today_2am - datetime.timedelta(days=1)
    else:
        start_time = today_2am
    
    end_time = now
    
    return start_time, end_time

def create_custom_time_range(start_date: str, start_time: str, end_date: str, end_time: str) -> tuple:
    """创建自定义时间范围"""
    try:
        start_datetime = datetime.datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        end_datetime = datetime.datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        return start_datetime, end_datetime
    except ValueError as e:
        raise ValueError(f"时间格式错误: {e}")

if __name__ == "__main__":
    # 示例用法
    git_dir_path = r"D:\tools\heavychat\heavychat\.git"  # 直接指定.git目录
    output_dir = "extracted_objects"
    
    # 检查git命令是否可用
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未找到git命令，请确保git已安装并在PATH中")
        exit(1)
    
    # 检查Git目录路径是否存在
    if not os.path.exists(git_dir_path):
        print(f"错误: Git目录路径不存在: {git_dir_path}")
        exit(1)
    
    # 创建提取器
    extractor = GitObjectExtractor(git_dir_path, output_dir)
    
    # 使用从凌晨2点开始的时间范围
    start_time, end_time = create_time_range_from_2am()
    
    # 执行提取
    try:
        results = extractor.extract_objects(start_time, end_time)
        print(f"提取完成，结果: {results}")
    except Exception as e:
        print(f"提取失败: {e}") 