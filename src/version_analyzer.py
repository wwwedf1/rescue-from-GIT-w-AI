#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件版本分析器
使用3种分析器：全体分组器、种子分组器、组内版本比较器
"""

import json
import os
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .ai_base import AIAnalysisBase

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('version_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class FileVersion:
    """文件版本信息"""
    original_filename: str
    original_hash: str
    ai_name: str
    ai_analysis: str
    file_type: str
    confidence: float
    suggested_filename: str
    saved_path: Optional[str]
    content: str = ""
    misjudged: bool = False


@dataclass
class VersionGroup:
    """版本组信息"""
    base_name: str
    versions: List[FileVersion]
    sorted_versions: Optional[List[FileVersion]] = None
    analysis_result: Optional[Dict] = None
    reasoning: str = ""


class BatchGroupingAnalyzer(AIAnalysisBase):
    """全体分组器 - 一次性对所有文件进行分组"""
    
    def build_prompt(self, files_info: List[Dict], **kwargs) -> str:
        """构建批量分组提示词"""
        start_time = time.time()
        logger.info(f"开始构建批量分组提示词，文件数量: {len(files_info)}")
        
        files_text = ""
        for file_info in files_info:
            files_text += f"""
文件 {file_info['index']}:
- 文件名: {file_info['filename']}
- 类型: {file_info['file_type']}
- AI分析: {file_info['analysis']}"""
            
            if file_info['content_preview']:
                files_text += f"""
- 内容预览: {file_info['content_preview']}"""
        
        prompt = f"""你是一个专业的文件版本分析专家。请分析以下文件，将可能是同一文件不同版本的文件分组。

{files_text}

请按照以下JSON格式返回分析结果：

{{
    "groups": [
        {{
            "group_name": "组名",
            "file_indices": [文件索引列表],
            "reasoning": "分组理由说明"
        }}
    ]
}}

分析要求：
1. 文件名是ai推断出来的，它能看到更长的文件片段，可以着重参考
2. 只有真正可能是同一文件不同版本的才分组
3. 在reasoning中简洁说明分组理由
4. **一组完全可以只包含一个文件**，如果某个文件无法与任何其他文件匹配，请给它单独成组

请确保返回的是有效的JSON格式。"""
        
        build_time = time.time() - start_time
        logger.info(f"批量分组提示词构建完成，耗时: {build_time:.2f}秒，提示词长度: {len(prompt)}字符")
        
        return prompt
        
    def parse_response(self, response: str, versions: List[FileVersion], **kwargs) -> List[VersionGroup]:
        """解析批量分组响应"""
        start_time = time.time()
        logger.info(f"开始解析批量分组响应，响应长度: {len(response)}字符")
        
        try:
            result = self.parse_json_response(response)
            
            groups: List[VersionGroup] = []
            used_indices: Set[int] = set()
            
            for group_data in result.get("groups", []):
                group_name = group_data.get("group_name", "unknown")
                file_indices = group_data.get("file_indices", [])
                reasoning = group_data.get("reasoning", "")
                
                group_versions: List[FileVersion] = []
                for idx in file_indices:
                    if 1 <= idx <= len(versions):
                        group_versions.append(versions[idx - 1])
                        used_indices.add(idx)
                
                if group_versions:
                    group = VersionGroup(base_name=group_name, versions=group_versions)
                    group.reasoning = reasoning
                    groups.append(group)
                    logger.debug(f"创建版本组: {group_name}，包含 {len(group_versions)} 个文件")
            
            # 兜底：任何未被使用到的索引也单独成组
            fallback_count = 0
            for i in range(1, len(versions) + 1):
                if i not in used_indices:
                    v = versions[i - 1]
                    single_group = VersionGroup(base_name=self._normalize_filename(v.ai_name), versions=[v])
                    single_group.reasoning = "无法与其他文件匹配，单独成组"
                    groups.append(single_group)
                    fallback_count += 1
            
            parse_time = time.time() - start_time
            logger.info(f"批量分组响应解析完成，耗时: {parse_time:.2f}秒")
            logger.info(f"解析结果: 总组数 {len(groups)}，兜底文件 {fallback_count}")
            
            return groups
            
        except Exception as e:
            logger.error(f"解析批量分组响应失败: {e}")
            logger.error(f"原始响应: {response}")
            # 回退到基于文件名的分组
            return self._fallback_grouping(versions)
    
    def analyze(self, files_info: List[Dict], versions: List[FileVersion], **kwargs) -> List[VersionGroup]:
        """执行批量分组分析"""
        # 构建提示词
        prompt = self.build_prompt(files_info=files_info, **kwargs)
        
        # 调用AI
        messages = [
            {"role": "system", "content": "你是一个专业的文件版本分析专家。"},
            {"role": "user", "content": prompt},
        ]
        
        # 检查是否启用流式输出
        use_stream = kwargs.get("use_stream", False)
        
        if use_stream:
            logger.debug("使用静默流式输出模式")
            response = self.call_ai_with_stream(messages, silent=True)
        else:
            response = self.call_ai_with_retry(messages)
        
        # 解析响应
        return self.parse_response(response, versions=versions, **kwargs)
    
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
    
    def _fallback_grouping(self, versions: List[FileVersion]) -> List[VersionGroup]:
        """回退分组策略"""
        logger.warning("使用回退分组策略")
        name_groups = {}
        for version in versions:
            normalized_name = self._normalize_filename(version.ai_name)
            if normalized_name not in name_groups:
                name_groups[normalized_name] = []
            name_groups[normalized_name].append(version)
        
        groups = []
        for base_name, group_versions in name_groups.items():
            if len(group_versions) > 1:
                group = VersionGroup(base_name=base_name, versions=group_versions)
                groups.append(group)
        
        logger.info(f"回退分组完成，创建了 {len(groups)} 个版本组")
        return groups


class IterativeGroupingAnalyzer(AIAnalysisBase):
    """种子分组器 - 为单个文件查找相似文件"""
    
    def build_prompt(self, target_version: FileVersion, candidate_files: List[Dict], **kwargs) -> str:
        """构建种子分组提示词"""
        start_time = time.time()
        logger.info(f"开始构建种子分组提示词，候选文件数量: {len(candidate_files)}")
        
        # 构建候选文件列表
        candidate_text = ""
        for file_info in candidate_files:
            candidate_text += f"""
文件 {file_info['index']}:
- 文件名: {file_info['filename']}
- 类型: {file_info['file_type']}
- 分析: {file_info['analysis']}
- 内容预览: {file_info['content_preview']}"""

        prompt = f"""请分析以下文件，找出与目标文件 '{target_version.ai_name}' 可能是同一文件不同版本的文件。

目标文件信息:
- 文件名: {target_version.ai_name}
- 类型: {target_version.file_type}
- 分析: {target_version.ai_analysis}
- 内容预览: {self.get_content_preview(target_version.content, self.ai_analyzer.iterative_similarity_preview_length)}

候选文件列表:
{candidate_text}

请返回JSON格式的结果：
{{
    "similar_files": [相似文件的索引列表],
    "reasoning": "选择理由说明",
    "confidence": 0.8
}}

只选择真正可能是同一文件不同版本的文件。"""
        
        build_time = time.time() - start_time
        logger.info(f"种子分组提示词构建完成，耗时: {build_time:.2f}秒，提示词长度: {len(prompt)}字符")
        
        return prompt
    
    def parse_response(self, response: str, candidate_versions: List[FileVersion], **kwargs) -> List[FileVersion]:
        """解析种子分组响应"""
        start_time = time.time()
        logger.info(f"开始解析种子分组响应，响应长度: {len(response)}字符")
        
        try:
            result = self.parse_json_response(response)
            similar_indices = result.get("similar_files", [])
            similar_files = []

            for idx in similar_indices:
                if 1 <= idx <= len(candidate_versions):
                    similar_files.append(candidate_versions[idx - 1])

            parse_time = time.time() - start_time
            logger.info(f"种子分组响应解析完成，耗时: {parse_time:.2f}秒")
            logger.info(f"找到 {len(similar_files)} 个相似文件")
            return similar_files

        except Exception as e:
            logger.error(f"解析种子分组响应失败: {e}")
            logger.error(f"原始响应: {response}")
            return []
    
    def analyze(self, target_version: FileVersion, candidate_files: List[Dict], candidate_versions: List[FileVersion], **kwargs) -> List[FileVersion]:
        """执行种子分组分析"""
        # 构建提示词
        prompt = self.build_prompt(target_version=target_version, candidate_files=candidate_files, **kwargs)
        
        # 调用AI
        messages = [
            {"role": "system", "content": "你是一个专业的文件版本分析专家。"},
            {"role": "user", "content": prompt},
        ]
        
        # 检查是否启用流式输出
        use_stream = kwargs.get("use_stream", False)
        
        if use_stream:
            logger.debug("使用静默流式输出模式")
            response = self.call_ai_with_stream(messages, silent=True)
        else:
            response = self.call_ai_with_retry(messages)
        
        # 解析响应
        return self.parse_response(response, candidate_versions=candidate_versions, **kwargs)


class VersionComparisonAnalyzer(AIAnalysisBase):
    """组内版本比较器 - 对版本组进行详细比较"""
    
    def build_prompt(self, files_info: List[Dict], **kwargs) -> str:
        """构建版本比较提示词"""
        start_time = time.time()
        logger.info(f"开始构建版本比较提示词，文件数量: {len(files_info)}")
        
        # 检查是否有大文件（可能导致超时）
        large_files = []
        total_content_length = 0
        for file_info in files_info:
            content_length = len(file_info.get('content_preview', ''))
            total_content_length += content_length
            if content_length > 10000:  # 超过10KB的文件
                large_files.append({
                    'index': file_info['index'],
                    'filename': file_info['filename'],
                    'length': content_length
                })
        
        if large_files:
            logger.warning(f"发现大文件，可能导致超时: {large_files}")
            logger.warning(f"总内容长度: {total_content_length}字符")
        
        files_text = ""
        for file_info in files_info:
            files_text += f"""
文件 {file_info['index']}:
- 文件名: {file_info['filename']}
- 类型: {file_info['file_type']}
- AI分析: {file_info['analysis']}
- 内容预览: {file_info['content_preview']}"""

        prompt = f"""你是一个专业的文件版本分析专家。请分析以下可能是同一文件不同版本的文件。

{files_text}

请按照以下JSON格式返回分析结果：

{{
    "version_analysis": "简洁的版本分析说明，包括版本间的主要变化、关系、功能增减等",
    "confidence": 0.95,
    "notes": "其他注意事项，如可能的误判、怀疑某文件分组时被误判的原因等",
    "group_misjudged": false,
    "files": [
        {{
            "filename": "包含部分哈希尾缀的完整文件名",
            "analysis": "对该文件与组内其他文件的关系分析",
            "sort_index": 1,
            "misjudged": false
        }}
    ]
}}

分析要求：
1. 根据文件名、内容特征、修改痕迹等判断版本关系
2. 考虑Git冲突标记、注释变化、功能增减等
3. 在version_analysis中详细说明分析理由
4. 如果某些文件明显不是同一文件的不同版本，请将该文件的group_misjudged设为true
5. sort_index: 按时间顺序的排序索引（1=最旧，n=最新）

请确保返回的是有效的JSON格式。"""
        
        build_time = time.time() - start_time
        logger.info(f"版本比较提示词构建完成，耗时: {build_time:.2f}秒，提示词长度: {len(prompt)}字符")
        
        return prompt
    
    def parse_response(self, response: str, versions: List[FileVersion], **kwargs) -> Dict:
        """解析版本比较响应"""
        start_time = time.time()
        logger.info(f"开始解析版本比较响应，响应长度: {len(response)}字符")
        
        try:
            result = self.parse_json_response(response)
            
            files_data = result.get("files", [])
            group_misjudged = result.get("group_misjudged", False)
            
            file_analysis_list = []
            sorted_versions = []
            
            for file_data in files_data:
                filename = file_data.get("filename", "")
                # 根据拼接的文件名查找对应的版本
                version = None
                for v in versions:
                    if v.suggested_filename == filename:
                        version = v
                        break
                
                if version:
                    version.misjudged = file_data.get("misjudged", False) or group_misjudged
                    
                    file_analysis = {
                        "file": version,
                        "analysis": file_data.get("analysis", ""),
                        "sort_index": file_data.get("sort_index", 1),
                        "misjudged": version.misjudged
                    }
                    file_analysis_list.append(file_analysis)
                    
                    sort_index = file_data.get("sort_index", 1)
                    while len(sorted_versions) < sort_index:
                        sorted_versions.append(None)
                    sorted_versions[sort_index - 1] = version
            
            sorted_versions = [v for v in sorted_versions if v is not None]
            
            if not sorted_versions:
                sorted_versions = versions
                file_analysis_list = []
                for i, version in enumerate(versions):
                    file_analysis_list.append({
                        "file": version,
                        "analysis": f"文件 {i+1} 的默认分析",
                        "sort_index": i + 1,
                        "misjudged": False
                    })

            parse_time = time.time() - start_time
            logger.info(f"版本比较响应解析完成，耗时: {parse_time:.2f}秒")
            logger.info(f"解析结果: 排序版本数 {len(sorted_versions)}，文件分析数 {len(file_analysis_list)}")

            return {
                "success": True,
                "sorted_versions": sorted_versions,
                "file_analysis_list": file_analysis_list,
                "analysis": result.get("version_analysis", ""),
                "confidence": result.get("confidence", 0.5),
                "notes": result.get("notes", ""),
                "group_misjudged": group_misjudged,
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            logger.error(f"原始响应: {response}")
            return {
                "success": False,
                "error": f"解析失败: {e}",
                "sorted_versions": versions,
                "file_analysis_list": [],
                "analysis": "解析失败",
                "group_misjudged": True,
                "raw_response": response,
            }

    def analyze(self, files_info: List[Dict], versions: List[FileVersion], **kwargs) -> Dict:
        """
        执行版本比较分析
        
        Args:
            files_info: 文件信息列表
            versions: 版本列表
            **kwargs: 其他参数
            
        Returns:
            分析结果
        """
        # 构建提示词
        prompt = self.build_prompt(files_info=files_info, **kwargs)
        
        # 调用AI
        messages = [
            {"role": "system", "content": "你是一个专业的文件版本分析专家。"},
            {"role": "user", "content": prompt},
        ]
        
        # 检查是否启用流式输出（用于调试）
        use_stream = kwargs.get("use_stream", False)
        
        if use_stream:
            logger.debug("使用静默流式输出模式")
            response = self.call_ai_with_stream(messages, silent=True)
        else:
            response = self.call_ai_with_retry(messages)
        
        # 解析响应
        return self.parse_response(response, versions=versions, **kwargs)


# 工具函数
def load_analysis_report(report_path: str) -> Dict:
    """加载分析报告"""
    logger.info(f"加载分析报告: {report_path}")
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_file_versions(report_data: Dict, files_dir: str) -> List[FileVersion]:
    """从分析报告中提取文件版本信息"""
    logger.info(f"开始提取文件版本信息，文件目录: {files_dir}")
    start_time = time.time()
    
    versions = []

    for result in report_data.get("results", []):
        if not result.get("saved", False):
            continue

        saved_path = result.get("saved_path")
        content = ""
        if saved_path and os.path.exists(saved_path):
            try:
                with open(saved_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"无法读取文件 {saved_path}: {e}")

        version = FileVersion(
            original_filename=result["original_filename"],
            original_hash=result["original_hash"],
            ai_name=result["ai_analysis"]["name"],
            ai_analysis=result["ai_analysis"]["analysis"],
            file_type=result["ai_analysis"]["file_type"],
            confidence=result["ai_analysis"]["confidence"],
            suggested_filename=result["suggested_filename"],
            saved_path=saved_path,
            content=content,
        )
        versions.append(version)

    extract_time = time.time() - start_time
    logger.info(f"文件版本信息提取完成，耗时: {extract_time:.2f}秒，提取了 {len(versions)} 个版本")

    return versions


def save_json_report(data: Dict, file_path: str):
    """保存JSON报告"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2) 