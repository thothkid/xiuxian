#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步状态管理：读写 sync_state.json，按知识库（dataset_id）分仓记录索引

状态格式演进：
1. v1（旧）：{相对路径: SHA256}
2. v2（旧）：{"version": 2, "path_index": {...}, "content_index": {...}}
   —— 所有知识库共用一套索引，多库模式下会跨库串档（复用到别的库的 doc_id）
3. v3（当前）：{
     "version": 3,
     "datasets": {
       "<dataset_id>": {
         "path_index": {相对路径: SHA256},     # 路径 → 哈希（检测变更）
         "content_index": {SHA256: doc_id}     # 哈希 → RAGFlow文档ID（去重/复用）
       }
     }
   }
   —— 每个知识库独立索引，复用/删除保护只在同一知识库内生效

v1/v2 加载后不直接使用：由调用方提供「路径 → dataset_id」的归属函数，
调用 migrate_legacy() 迁移到 v3（详见 main.py）。
"""

import json
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple


# 当前状态版本
STATE_VERSION = 3


class DatasetState:
    """单个知识库的状态视图（引用底层字典，修改直接落到 SyncState 上）"""

    def __init__(self, path_index: Dict[str, str], content_index: Dict[str, str]):
        self.path_index = path_index
        self.content_index = content_index

    def is_empty(self) -> bool:
        """该知识库是否从未同步过（无任何索引）"""
        return not self.path_index and not self.content_index

    def get_hash(self, relative_path: str) -> str:
        """获取缓存的哈希值（路径索引）"""
        return self.path_index.get(relative_path, '')

    def set_hash(self, relative_path: str, hash_value: str) -> None:
        """设置缓存的哈希值（同步路径索引和内容索引）"""
        self.path_index[relative_path] = hash_value
        # 如果内容索引中已有该哈希，保留旧映射（不覆盖）
        if hash_value not in self.content_index:
            self.content_index[hash_value] = None

    def set_doc_id(self, hash_value: str, doc_id: str) -> None:
        """设置哈希对应的 RAGFlow 文档 ID（内容索引）"""
        self.content_index[hash_value] = doc_id

    def get_doc_id_by_hash(self, hash_value: str) -> Optional[str]:
        """根据哈希值获取 RAGFlow 文档 ID"""
        return self.content_index.get(hash_value)

    def remove_by_path(self, relative_path: str) -> None:
        """根据路径移除路径索引（内容索引由 remove_by_hash 按引用计数清理）"""
        self.path_index.pop(relative_path, None)

    def remove_by_hash(self, hash_value: str) -> None:
        """根据哈希值清理内容索引（当该哈希无任何路径引用时）"""
        still_used = any(h == hash_value for h in self.path_index.values())
        if not still_used and hash_value in self.content_index:
            del self.content_index[hash_value]

    def has_file(self, relative_path: str) -> bool:
        """检查文件是否在状态中"""
        return relative_path in self.path_index

    def is_content_exists(self, hash_value: str) -> bool:
        """检查内容索引中是否已存在该哈希（用于去重）"""
        return hash_value in self.content_index and self.content_index[hash_value] is not None


class SyncState:
    """同步状态管理器（v3：按 dataset_id 分仓）"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        # {dataset_id: {'path_index': {...}, 'content_index': {...}}}
        self.datasets: Dict[str, Dict[str, Dict[str, str]]] = {}
        # v1/v2 数据暂存区，等待 migrate_legacy() 迁移
        self._legacy_data: Optional[Dict[str, Dict[str, str]]] = None

    def load(self) -> None:
        """从文件加载状态（v1/v2 进入暂存区，需调用 migrate_legacy 迁移）"""
        if not self.state_file.exists():
            self.datasets = {}
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict) and data.get('version') == STATE_VERSION:
                # v3
                self.datasets = data.get('datasets', {})
                total_paths = sum(len(d.get('path_index', {})) for d in self.datasets.values())
                print(f'[OK] 加载状态 v3（知识库: {len(self.datasets)}, 路径索引: {total_paths}）')
            elif isinstance(data, dict) and data.get('version') == 2:
                # v2：单套全局索引，待迁移
                self._legacy_data = {
                    'path_index': data.get('path_index', {}),
                    'content_index': data.get('content_index', {}),
                }
                print(f'[OK] 检测到旧格式状态 v2（{len(self._legacy_data["path_index"])} 个文件），待迁移')
            elif isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
                # v1：纯 路径→哈希 映射，待迁移
                self._legacy_data = {'path_index': data, 'content_index': {}}
                print(f'[OK] 检测到旧格式状态 v1（{len(data)} 个文件），待迁移')
            else:
                raise json.JSONDecodeError('未知格式', '', 0)
        except (json.JSONDecodeError, IOError) as e:
            print(f'[WARN] 读取状态文件失败: {e}，将从空状态开始')
            self.datasets = {}
            self._legacy_data = None

    def needs_migration(self) -> bool:
        """是否有 v1/v2 旧数据等待迁移"""
        return self._legacy_data is not None

    def migrate_legacy(self, assign_dataset: Callable[[str], Optional[str]]) -> Tuple[int, int]:
        """
        将 v1/v2 旧状态迁移到 v3 分仓格式

        参数：
            assign_dataset: 归属函数，输入相对路径，返回该文件所属的 dataset_id；
                            返回 None 表示无法归属（该条目丢弃，下次同步按新文件处理）
        返回：(迁移条目数, 丢弃条目数)
        """
        if not self._legacy_data:
            return (0, 0)

        migrated = 0
        dropped = 0

        for path, hash_value in self._legacy_data['path_index'].items():
            dataset_id = assign_dataset(path)
            if not dataset_id:
                dropped += 1
                continue
            ds = self.for_dataset(dataset_id)
            ds.path_index[path] = hash_value
            migrated += 1

        # content_index：哈希归属到「持有该内容的路径」所在的知识库；
        # 无路径引用的孤儿哈希（含 None 占位）直接丢弃——它们在旧格式下也无法安全复用
        for hash_value, doc_id in self._legacy_data['content_index'].items():
            if not doc_id:
                continue
            for dataset_id, data in self.datasets.items():
                if hash_value in data['path_index'].values():
                    data['content_index'][hash_value] = doc_id
                    break

        self._legacy_data = None
        return (migrated, dropped)

    def for_dataset(self, dataset_id: str) -> DatasetState:
        """获取指定知识库的状态视图（不存在则创建空仓）"""
        if dataset_id not in self.datasets:
            self.datasets[dataset_id] = {'path_index': {}, 'content_index': {}}
        data = self.datasets[dataset_id]
        return DatasetState(data['path_index'], data['content_index'])

    def save(self) -> None:
        """保存状态到文件（v3 格式）"""
        if self._legacy_data is not None:
            # 防御：旧数据未迁移就保存会静默丢失全部旧索引
            print('[WARN] 存在未迁移的旧格式状态，跳过保存以免丢失数据')
            return
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'version': STATE_VERSION,
                'datasets': self.datasets,
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            total_paths = sum(len(d.get('path_index', {})) for d in self.datasets.values())
            total_hashes = sum(len(d.get('content_index', {})) for d in self.datasets.values())
            print(f'[OK] 保存状态（知识库: {len(self.datasets)}, 路径索引: {total_paths}, 内容索引: {total_hashes}）')
        except IOError as e:
            print(f'[ERROR] 保存状态文件失败: {e}')
