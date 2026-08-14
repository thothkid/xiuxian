#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAGFlow HTTP API 客户端封装"""

import requests
from typing import Dict, List, Optional


class RagflowClient:
    """RAGFlow API 客户端"""

    def __init__(self, base_url: str, api_key: str, dataset_id: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.dataset_id = dataset_id
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _url(self, endpoint: str) -> str:
        """构建完整 API URL"""
        return f'{self.base_url}{endpoint}'

    def list_documents(self) -> Dict[str, dict]:
        """
        获取知识库中所有文档列表
        返回: {文档名称: {'id': document_id, 'size': file_size}}
        """
        result = {}
        page = 1
        page_size = 200  # 增大页大小，减少请求次数

        while True:
            url = self._url(f'/api/v1/datasets/{self.dataset_id}/documents')
            params = {'page': page, 'page_size': page_size}

            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                if data.get('code') != 0:
                    raise RuntimeError(f'RAGFlow API 错误: {data.get("message", "未知错误")}')

                # RAGFlow 不同版本响应格式可能不同：data 可能是 dict 或 list
                raw_data = data.get('data', {})
                if isinstance(raw_data, dict):
                    # 注意：RAGFlow API 返回的 key 是 'docs' 而非 'documents'
                    documents = raw_data.get('docs', raw_data.get('documents', []))
                    total = raw_data.get('total', 0)
                elif isinstance(raw_data, list):
                    documents = raw_data
                    total = len(documents)
                else:
                    documents = []
                    total = 0

                for doc in documents:
                    name = doc.get('name', '')
                    doc_id = doc.get('id', '')
                    if name and doc_id:
                        result[name] = {
                            'id': doc_id,
                            'size': doc.get('size', 0)
                        }

                # 判断是否还有更多页
                if len(documents) < page_size or page * page_size >= total:
                    break
                page += 1

            except requests.RequestException as e:
                raise RuntimeError(f'获取文档列表失败: {e}')

        return result

    def upload_document(self, file_path: str, filename: str) -> Optional[str]:
        """
        上传文档到知识库
        返回: document_id 或 None
        """
        url = self._url(f'/api/v1/datasets/{self.dataset_id}/documents?type=local')

        try:
            with open(file_path, 'rb') as f:
                # 上传文件时不使用 Content-Type header，让 requests 自动设置 multipart/form-data
                upload_headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}
                upload_headers['Authorization'] = self.headers['Authorization']
                files = {'file': (filename, f, 'application/octet-stream')}
                resp = requests.post(url, headers=upload_headers, files=files, timeout=120)
                resp.raise_for_status()
                data = resp.json()

                if data.get('code') != 0:
                    raise RuntimeError(f'上传文档失败: {data.get("message", "未知错误")}')

                # data 是一个数组，获取第一个元素的 id
                result_data = data.get('data', [])
                if isinstance(result_data, list) and len(result_data) > 0:
                    return result_data[0].get('id')
                return None

        except requests.RequestException as e:
            raise RuntimeError(f'上传文档失败: {e}')

    def delete_documents(self, document_ids: List[str]) -> int:
        """
        批量删除文档
        返回: 成功删除的数量
        """
        if not document_ids:
            return 0

        url = self._url(f'/api/v1/datasets/{self.dataset_id}/documents')
        payload = {'ids': document_ids}

        try:
            resp = requests.delete(url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get('code') != 0:
                raise RuntimeError(f'删除文档失败: {data.get("message", "未知错误")}')

            return len(document_ids)

        except requests.RequestException as e:
            raise RuntimeError(f'删除文档失败: {e}')

    def parse_document(self, document_id: str) -> bool:
        """
        触发文档解析
        返回: 是否成功
        """
        url = self._url(f'/api/v1/datasets/{self.dataset_id}/chunks')

        try:
            payload = {'document_ids': [document_id]}
            resp = requests.post(url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get('code') != 0:
                raise RuntimeError(f'触发解析失败: {data.get("message", "未知错误")}')

            return True

        except requests.RequestException as e:
            raise RuntimeError(f'触发解析失败: {e}')

    def download_document(self, document_id: str) -> Optional[bytes]:
        """
        下载文档内容（用于计算云端文档的真实哈希）
        返回: 文件字节内容或 None
        """
        url = self._url(f'/api/v1/datasets/{self.dataset_id}/documents/{document_id}')

        try:
            resp = requests.get(url, headers=self.headers, timeout=60, stream=True)
            resp.raise_for_status()
            
            # RAGFlow 可能返回文件内容或 JSON，尝试判断
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                # 返回的是错误信息
                data = resp.json()
                if data.get('code') != 0:
                    raise RuntimeError(f'下载文档失败: {data.get("message", "未知错误")}')
                return None
            
            # 返回文件内容
            return resp.content

        except requests.RequestException as e:
            print(f'  [WARN] 下载文档失败: {e}')
            return None
