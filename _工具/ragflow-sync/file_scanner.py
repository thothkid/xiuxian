#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件扫描器：实时读取 .gitignore 过滤规则，扫描本地文档"""

import fnmatch
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Set


def calculate_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_gitignore_rules(gitignore_path: Path) -> List[str]:
    """
    实时读取 .gitignore 文件，解析为过滤规则列表
    跳过空行、注释和反斜杠续行
    返回: 规则字符串列表
    """
    if not gitignore_path.exists():
        print(f'⚠ 未找到 .gitignore 文件: {gitignore_path}')
        return []

    rules = []
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行、注释和反斜杠续行
                if not line or line.startswith('#') or line.startswith('\\'):
                    continue
                rules.append(line)
    except Exception as e:
        print(f'⚠ 读取 .gitignore 失败: {e}')

    return rules


def is_hidden(file_path: Path) -> bool:
    """检查文件或路径中的任何目录名是否以 . 开头（隐藏文件/目录）"""
    # 检查文件名
    if file_path.name.startswith('.'):
        return True
    # 检查路径中的任何目录组件
    for part in file_path.parts:
        if part.startswith('.'):
            return True
    return False


def is_ignored(file_path: Path, base_dir: Path, rules: List[str]) -> bool:
    """
    判断文件是否应被 .gitignore 规则排除
    支持基本 .gitignore 语法：
    - *.ext: 通配符匹配文件名
    - dir/: 匹配目录
    - path/to/file: 匹配相对路径
    - !pattern: 排除规则（暂不支持）
    """
    # 获取相对于项目根目录的路径
    try:
        relative_path = file_path.relative_to(base_dir)
    except ValueError:
        return False

    # 隐藏文件/目录一律排除——只按项目内相对路径判定，
    # 项目根目录自身位于点目录（如 git worktree 的 .claude/worktrees/）下时不应整树误判为隐藏
    if is_hidden(relative_path):
        return True

    if not rules:
        return False

    relative_str = str(relative_path)
    parts = relative_path.parts

    for rule in rules:
        # 如果是目录规则（以 / 结尾），只匹配目录路径
        if rule.endswith('/'):
            dir_name = rule.rstrip('/')
            # 检查路径的任何前缀是否匹配
            for i in range(len(parts)):
                partial = '/'.join(parts[:i + 1])
                if fnmatch.fnmatch(partial, dir_name) or fnmatch.fnmatch(parts[i], dir_name):
                    return True
        # 如果规则包含 /（但不是结尾），则是路径匹配
        elif '/' in rule:
            if fnmatch.fnmatch(relative_str, rule):
                return True
            # 也检查目录前缀
            for i in range(len(parts)):
                partial = '/'.join(parts[:i + 1])
                if fnmatch.fnmatch(partial, rule):
                    return True
        # 否则是文件名匹配（匹配任何层级的文件名）
        else:
            if fnmatch.fnmatch(parts[-1], rule):
                return True
            # 也匹配完整路径
            if fnmatch.fnmatch(relative_str, rule):
                return True

    return False


def scan_directory(
    base_dir: Path,
    scan_dirs: List[str],
    exclude_patterns: List[str] = None
) -> Dict[str, Path]:
    """
    扫描指定目录，返回 {相对路径: 绝对路径} 映射
    参数:
        base_dir: 项目根目录
        scan_dirs: 要扫描的目录列表（如 ['docs', 'xlsx']）
        exclude_patterns: 排除规则列表（glob 模式，匹配相对于项目根目录的路径）
                         示例：['*.xlsx', '*.zip', 'temp/*']
    返回: {相对路径(字符串): 绝对路径(Path)}
    """
    gitignore_path = base_dir / '.gitignore'
    rules = load_gitignore_rules(gitignore_path)
    exclude = exclude_patterns or []

    result = {}

    for scan_dir in scan_dirs:
        dir_path = base_dir / scan_dir
        if not dir_path.exists() or not dir_path.is_dir():
            print(f'⚠ 扫描目录不存在，跳过: {dir_path}')
            continue

        for file_path in dir_path.rglob('*'):
            if not file_path.is_file():
                continue

            # 检查 .gitignore
            if is_ignored(file_path, base_dir, rules):
                continue

            # 使用相对路径作为键（相对于项目根目录）
            relative = str(file_path.relative_to(base_dir))

            # 应用排除规则（匹配相对路径）
            excluded = False
            for pattern in exclude:
                if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    excluded = True
                    break
            if excluded:
                continue

            result[relative] = file_path

    return result


def compute_file_hashes(file_map: Dict[str, Path]) -> Dict[str, str]:
    """
    计算文件映射中所有文件的 SHA256 哈希
    返回: {相对路径: SHA256}
    """
    hashes = {}
    for relative_path, absolute_path in file_map.items():
        try:
            hashes[relative_path] = calculate_sha256(absolute_path)
        except Exception as e:
            print(f'⚠ 计算哈希失败: {relative_path} - {e}')
    return hashes
