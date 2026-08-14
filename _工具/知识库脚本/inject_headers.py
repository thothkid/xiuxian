#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
知识库 Markdown 节头注入脚本（上传源＝二区 E:\修仙项目）。

项目语义不写在代码中。注入模式先校验一、二区两份《项目索引》逐字一致，
再读取索引「知识库范围与文档标记」树中每个文件后的“文档定位”和“使用边界”。
文件集合以该树为唯一权威——上传源同时存放大量不进知识库的文档，故不做全盘扫描。
任何停止只记录机器事实，不生成处理建议；执行本脚本的 AI 负责读取日志并向 thoth 报告。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


ALLOWED_ROOT = Path(r"E:\修仙项目")
INDEX_PATHS = (
    Path(r"E:\thoth\横向\WAR3修仙项目\项目索引.md"),
    ALLOWED_ROOT / "项目索引.md",
)
KB_SECTION = "### 知识库范围与文档标记"
DOC_TREE_ROOT = str(ALLOWED_ROOT) + "\\"
LOG_DIR = Path(__file__).resolve().parent / "logs"

MARK_RE = re.compile(r"^〔出处：.*〕[ \t]*$")
HEAD_RE = re.compile(r"^ {0,3}(#{2,3})[ \t]+(.+?)[ \t]*$")
OPEN_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
TREE_LINE_RE = re.compile(r"^((?:(?:│   |    ))*)(?:├──|└──) (.+?)\s*$")
META_RE = re.compile(r"\s+\[定位：(代码依据|非代码依据)｜边界：(.+)\]\s*$")
ROUTE_SUFFIX_RE = re.compile(r"\s+\[[^\[\]]+\]\s*$")


@dataclass(frozen=True)
class HeaderRule:
    location: str
    boundary: str


@dataclass(frozen=True)
class RuleSet:
    exact: Dict[str, HeaderRule]
    directories: Sequence[Tuple[str, HeaderRule]]

    def match(self, relative_path: Path) -> Optional[HeaderRule]:
        return self.exact.get(relative_path.as_posix())


@dataclass
class FilePlan:
    source: Path
    target: Path
    original: bytes
    output: bytes
    changed: bool
    marks: int


class StopIssue(Exception):
    def __init__(self, code: str, stage: str, summary: str, details=None):
        super().__init__(summary)
        self.code = code
        self.stage = stage
        self.summary = summary
        self.details = list(details or [])


class CliParser(argparse.ArgumentParser):
    def error(self, message):
        raise StopIssue("ARGUMENT_ERROR", "argument_parse", message)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


class RunLogger:
    def __init__(self):
        self.started_at = datetime.now().astimezone()
        self.mode = "unknown"
        self.dry_run = False
        self.root = ""

    def set_context(self, mode: str, dry_run: bool, root: str) -> None:
        self.mode = mode
        self.dry_run = dry_run
        self.root = root

    def emit(
        self,
        status: str,
        exit_code: int,
        reason_code: str,
        stage: str,
        summary: str,
        details=None,
        metrics=None,
    ) -> None:
        now = datetime.now().astimezone()
        detail_list = list(details or [])
        payload = {
            "timestamp": now.isoformat(),
            "started_at": self.started_at.isoformat(),
            "status": status,
            "exit_code": exit_code,
            "reason_code": reason_code,
            "stage": stage,
            "mode": self.mode,
            "dry_run": self.dry_run,
            "root": self.root,
            "summary": summary,
            "details": detail_list,
            "metrics": dict(metrics or {}),
            "ai_report_required": True,
            "ai_report_fields": [
                "status",
                "exit_code",
                "reason_code",
                "stage",
                "summary",
                "details",
                "metrics",
                "log_path",
            ],
        }

        stamp = now.strftime("%Y%m%d_%H%M%S_%f")
        log_path = LOG_DIR / f"inject_headers_{stamp}.json"
        payload["log_path"] = str(log_path)
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

        log_error = None
        try:
            atomic_write(log_path, encoded)
            atomic_write(LOG_DIR / "latest.json", encoded)
        except OSError as exc:
            log_error = str(exc)

        banner = "STOP" if status == "stopped" else "OK"
        print(f"{banner} [{reason_code}] stage={stage} exit={exit_code}")
        print(summary)
        for item in detail_list:
            print(json.dumps(item, ensure_ascii=False, sort_keys=True))
        if metrics:
            print("metrics=" + json.dumps(metrics, ensure_ascii=False, sort_keys=True))
        if log_error:
            print(f"LOG_WRITE_FAILED: {log_error}")
        else:
            print(f"LOG: {log_path}")
        print("AI_REPORT_REQUIRED: 执行AI必须将上述事实字段报告给thoth。")


def normalized(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path.resolve())))


def validate_root(root: Path) -> Path:
    resolved = root.resolve()
    if normalized(resolved) != normalized(ALLOWED_ROOT):
        raise StopIssue(
            "ROOT_REJECTED",
            "root_validation",
            "处理根目录不是脚本允许的固定上传源根目录",
            [{"allowed": str(ALLOWED_ROOT), "received": str(resolved)}],
        )
    if not resolved.is_dir():
        raise StopIssue(
            "ROOT_NOT_FOUND",
            "root_validation",
            "固定上传源根目录不存在",
            [{"path": str(resolved)}],
        )
    return resolved


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_consistent_index() -> Tuple[str, str]:
    records = []
    for path in INDEX_PATHS:
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise StopIssue(
                "INDEX_READ_FAILED",
                "index_consistency",
                "项目索引读取失败",
                [{"path": str(path), "error": str(exc)}],
            ) from exc
        records.append({"path": str(path), "hash": sha256(data), "data": data})

    hashes = {record["hash"] for record in records}
    if len(hashes) != 1:
        raise StopIssue(
            "INDEX_MISMATCH",
            "index_consistency",
            "一、二区两份项目索引不是逐字一致",
            [{"path": record["path"], "sha256": record["hash"]} for record in records],
        )

    try:
        text = records[0]["data"].decode("utf-8-sig")
    except UnicodeError as exc:
        raise StopIssue(
            "INDEX_ENCODING_ERROR",
            "index_consistency",
            "项目索引不是有效UTF-8",
            [{"path": records[0]["path"], "error": str(exc)}],
        ) from exc
    return text, records[0]["hash"]


def parse_rules(index_text: str) -> RuleSet:
    if index_text.count(KB_SECTION) != 1:
        raise StopIssue(
            "KB_SECTION_COUNT_ERROR",
            "rule_parse",
            "项目索引中的知识库范围树标题数量不正确",
            [{"title": KB_SECTION, "count": index_text.count(KB_SECTION)}],
        )

    section_start = index_text.index(KB_SECTION) + len(KB_SECTION)
    section_tail = index_text[section_start:]
    next_section = re.search(r"\n(?:### |---)", section_tail)
    section = section_tail[:next_section.start()] if next_section else section_tail

    fence_marker = "~~~text"
    if section.count(fence_marker) != 1:
        raise StopIssue(
            "KB_TREE_FENCE_ERROR",
            "rule_parse",
            "知识库范围树的text代码块起点数量不正确",
            [{"marker": fence_marker, "count": section.count(fence_marker)}],
        )
    fence_start = section.index(fence_marker) + len(fence_marker)
    fence_end = section.find("\n~~~", fence_start)
    if fence_end < 0:
        raise StopIssue(
            "KB_TREE_FENCE_ERROR",
            "rule_parse",
            "知识库范围树缺少代码块终点",
        )

    tree_lines = section[fence_start:fence_end].strip("\r\n").splitlines()
    if not tree_lines or tree_lines[0].strip() != DOC_TREE_ROOT:
        raise StopIssue(
            "KB_TREE_ROOT_ERROR",
            "rule_parse",
            "知识库范围树根路径与脚本固定根目录不一致",
            [{"expected": DOC_TREE_ROOT, "actual": tree_lines[0].strip() if tree_lines else ""}],
        )

    exact: Dict[str, HeaderRule] = {}
    stack: List[str] = []
    errors = []

    for line_number, raw_line in enumerate(tree_lines[1:], start=2):
        if not raw_line.strip():
            continue
        match = TREE_LINE_RE.fullmatch(raw_line)
        if match is None:
            errors.append({"tree_line": line_number, "error": "目录树行格式无效", "raw": raw_line})
            continue

        prefix, content = match.groups()
        depth = len(prefix) // 4
        meta = META_RE.search(content)
        entry_text = content[:meta.start()].rstrip() if meta else content.rstrip()
        entry_text = ROUTE_SUFFIX_RE.sub("", entry_text).rstrip()

        if entry_text.endswith("\\"):
            directory = entry_text[:-1]
            if not directory:
                errors.append({"tree_line": line_number, "error": "目录名为空"})
                continue
            if depth > len(stack):
                errors.append({"tree_line": line_number, "error": "目录层级跳跃", "raw": raw_line})
                continue
            stack = stack[:depth]
            stack.append(directory)
            if meta is not None:
                errors.append({"tree_line": line_number, "error": "定位与边界必须写在文件后，不能写在目录后"})
            continue

        if depth > len(stack):
            errors.append({"tree_line": line_number, "error": "文件层级没有对应父目录", "raw": raw_line})
            continue
        relative = "/".join(stack[:depth] + [entry_text])
        if meta is None:
            errors.append({"tree_line": line_number, "path": relative, "error": "文件缺少定位或使用边界"})
            continue

        location, boundary = meta.groups()
        boundary = boundary.strip()
        if not boundary:
            errors.append({"tree_line": line_number, "path": relative, "error": "使用边界为空"})
            continue
        if relative in exact:
            errors.append({"tree_line": line_number, "path": relative, "error": "文件路径重复"})
            continue
        exact[relative] = HeaderRule(location, boundary)

    if errors:
        raise StopIssue(
            "KB_TREE_RULE_ERROR",
            "rule_parse",
            "知识库范围树中的逐文件定位或边界标记有误",
            errors,
        )
    if not exact:
        raise StopIssue(
            "KB_TREE_RULE_EMPTY",
            "rule_parse",
            "知识库范围树没有带定位与边界的文件",
        )
    return RuleSet(exact, ())


def line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith(("\n", "\r")):
        return line[-1]
    return ""


def without_eol(line: str) -> str:
    eol = line_ending(line)
    return line[:-len(eol)] if eol else line


def dominant_eol(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    if crlf >= lf and crlf >= cr and crlf > 0:
        return "\r\n"
    if cr > lf and cr > 0:
        return "\r"
    return "\n"


def opening_fence(core: str) -> Optional[Tuple[str, int]]:
    match = OPEN_FENCE_RE.match(core)
    if not match:
        return None
    run, info = match.groups()
    if run[0] == "`" and "`" in info:
        return None
    return run[0], len(run)


def closes_fence(core: str, fence: Tuple[str, int]) -> bool:
    char, minimum = fence
    return re.fullmatch(rf" {{0,3}}{re.escape(char)}{{{minimum},}}[ \t]*", core) is not None


def strip_generated_marks(lines: Sequence[str]) -> List[str]:
    out: List[str] = []
    fence: Optional[Tuple[str, int]] = None
    last_index = len(lines) - 1
    for index, line in enumerate(lines):
        core = without_eol(line)
        if fence is not None:
            out.append(line)
            if closes_fence(core, fence):
                fence = None
            continue
        opened = opening_fence(core)
        if opened is not None:
            out.append(line)
            fence = opened
            continue
        if MARK_RE.fullmatch(core):
            if index == last_index and not line_ending(line) and out:
                previous = without_eol(out[-1])
                if HEAD_RE.fullmatch(previous) and line_ending(out[-1]):
                    out[-1] = previous
            continue
        out.append(line)
    return out


def clean_section_name(raw: str) -> str:
    text = re.sub(r"[ \t]+#+[ \t]*$", "", raw)
    text = text.replace("**", "").replace("`", "").strip()
    return text or "（无题小节）"


def make_mark(file_name: str, section: str, rule: HeaderRule, eol: str) -> str:
    return (
        f"〔出处：{file_name} · §{section} ｜ "
        f"定位：{rule.location}——{rule.boundary}〕{eol}"
    )


def inject_marks(lines: Sequence[str], file_name: str, rule: HeaderRule, eol: str) -> Tuple[List[str], int]:
    out: List[str] = []
    fence: Optional[Tuple[str, int]] = None
    injected = 0
    for line in lines:
        out.append(line)
        core = without_eol(line)
        if fence is not None:
            if closes_fence(core, fence):
                fence = None
            continue
        opened = opening_fence(core)
        if opened is not None:
            fence = opened
            continue
        heading = HEAD_RE.fullmatch(core)
        if heading is None:
            continue
        original_eol = line_ending(line)
        if not original_eol:
            out[-1] = line + eol
        out.append(make_mark(file_name, clean_section_name(heading.group(2)), rule, original_eol))
        injected += 1
    return out, injected


def encode_document(text: str, bom: bool) -> bytes:
    data = text.encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


def build_plan(
    path: Path,
    root: Path,
    mode: str,
    output_root: Optional[Path],
    rules: Optional[RuleSet],
) -> FilePlan:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    stripped = strip_generated_marks(text.splitlines(keepends=True))
    marks = 0
    if mode == "inject":
        assert rules is not None
        rule = rules.match(path.relative_to(root))
        if rule is None:
            raise StopIssue(
                "RULE_COVERAGE_FAILED",
                "document_preflight",
                "Markdown没有匹配到项目索引中的定位与边界规则",
                [{"path": str(path.relative_to(root))}],
            )
        out, marks = inject_marks(stripped, path.name, rule, dominant_eol(text))
        target = path
    else:
        out = stripped
        target = path if output_root is None else output_root / path.relative_to(root)
    output = encode_document("".join(out), bom)
    return FilePlan(path, target, raw, output, output != raw, marks)


def markdown_files(root: Path) -> List[Path]:
    """剥离模式用：全盘扫描根目录下的 Markdown（跳过点开头目录）。"""
    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]


def markdown_files_from_index(root: Path, rules: "RuleSet") -> Tuple[List[Path], List[str]]:
    """
    注入模式用：只处理《项目索引》知识库范围树列出的 Markdown。

    上传源为②区，②区同时存放大量不进知识库的文档，因此不能全盘扫描；
    文件集合以索引为唯一权威。返回 (存在的文件列表, 索引列出但磁盘缺失的相对路径)。
    """
    paths, missing = [], []
    for rel in sorted(rules.exact):
        if not rel.lower().endswith(".md") or rel == "项目索引.md":
            continue
        target = root / Path(rel)
        if target.is_file():
            paths.append(target)
        else:
            missing.append(rel)
    return paths, missing


def validate_output_dir(output: Path, root: Path) -> Path:
    resolved = output.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        pass
    else:
        raise StopIssue(
            "OUTPUT_INSIDE_ROOT",
            "output_validation",
            "剥离副本目录位于上传源根目录内部",
            [{"output": str(resolved), "root": str(root)}],
        )
    if resolved.exists() and any(resolved.iterdir()):
        raise StopIssue(
            "OUTPUT_NOT_EMPTY",
            "output_validation",
            "剥离副本目录不是空目录",
            [{"output": str(resolved)}],
        )
    return resolved


def write_injection(plans: Sequence[FilePlan]) -> None:
    written: List[FilePlan] = []
    try:
        for plan in plans:
            if plan.changed:
                atomic_write(plan.target, plan.output)
                written.append(plan)
    except Exception as exc:
        rollback_errors = []
        for plan in reversed(written):
            try:
                atomic_write(plan.source, plan.original)
            except Exception as rollback_exc:
                rollback_errors.append({"path": str(plan.source), "error": str(rollback_exc)})
        raise StopIssue(
            "WRITE_FAILED",
            "document_write",
            "注入写入失败",
            [{"error": str(exc)}, {"rollback_errors": rollback_errors}],
        ) from exc


def write_stripped_copy(plans: Sequence[FilePlan]) -> None:
    try:
        for plan in plans:
            atomic_write(plan.target, plan.output)
    except Exception as exc:
        raise StopIssue(
            "STRIP_OUTPUT_FAILED",
            "strip_write",
            "剥离副本写入失败",
            [{"path": str(plan.target), "error": str(exc)}],
        ) from exc


def parse_args():
    parser = CliParser(description="为知识库Markdown注入由项目索引定义的节头")
    parser.add_argument("--root", default=str(ALLOWED_ROOT), help="固定上传源根目录（二区）")
    parser.add_argument("--dry-run", action="store_true", help="完成全量预检并写日志，不改项目文档")
    parser.add_argument("--strip", action="store_true", help="生成无节头副本，不修改上传源原文件")
    parser.add_argument("--output", help="--strip 的输出目录；实写时必须不存在或为空")
    return parser.parse_args()


def main() -> int:
    logger = RunLogger()
    try:
        args = parse_args()
        mode = "strip" if args.strip else "inject"
        logger.set_context(mode, args.dry_run, args.root)
        root = validate_root(Path(args.root))
        if args.output and mode != "strip":
            raise StopIssue("OUTPUT_WITH_INJECT", "argument_validation", "注入模式收到了--output参数")
        if mode == "strip" and not args.dry_run and not args.output:
            raise StopIssue("STRIP_OUTPUT_REQUIRED", "argument_validation", "剥离实写模式没有--output参数")
        output_root = validate_output_dir(Path(args.output), root) if args.output else None

        rules = None
        index_hash = None
        if mode == "inject":
            index_text, index_hash = read_consistent_index()
            rules = parse_rules(index_text)

        if mode == "inject":
            document_paths, missing_markdown = markdown_files_from_index(root, rules)
            excluded_configuration_files = 0  # 项目索引.md 已移出知识库范围树，扫描范围内无配置输入
            file_set_details = [
                {"kind": "index_lists_but_file_missing", "path": path}
                for path in missing_markdown
            ]
            if file_set_details:
                raise StopIssue(
                    "INDEX_FILESET_MISMATCH",
                    "document_preflight",
                    "项目索引知识库范围列出的Markdown在上传源中缺失",
                    file_set_details,
                )
        else:
            document_paths = markdown_files(root)
            excluded_configuration_files = 0

        plans = []
        read_errors = []
        coverage_errors = []
        for path in document_paths:
            try:
                plans.append(build_plan(path, root, mode, output_root, rules))
            except StopIssue as exc:
                coverage_errors.extend(exc.details)
            except (OSError, UnicodeError) as exc:
                read_errors.append({"path": str(path.relative_to(root)), "error": str(exc)})
        if coverage_errors:
            raise StopIssue(
                "RULE_COVERAGE_FAILED",
                "document_preflight",
                "存在未配置文档定位与使用边界的Markdown",
                coverage_errors,
            )
        if read_errors:
            raise StopIssue(
                "DOCUMENT_READ_FAILED",
                "document_preflight",
                "Markdown读取或UTF-8解码失败",
                read_errors,
            )

        changed = [plan for plan in plans if plan.changed]
        metrics = {
            "markdown_files": len(plans),
            "excluded_configuration_files": excluded_configuration_files,
            "changed_files": len(changed),
            "result_marks": sum(plan.marks for plan in plans),
            "index_sha256": index_hash,
        }
        if not args.dry_run:
            if mode == "inject":
                write_injection(plans)
            else:
                assert output_root is not None
                output_root.mkdir(parents=True, exist_ok=True)
                write_stripped_copy(plans)

        logger.emit(
            "success",
            0,
            "OK",
            "complete",
            "脚本完成",
            metrics=metrics,
        )
        return 0
    except StopIssue as exc:
        logger.emit(
            "stopped",
            2,
            exc.code,
            exc.stage,
            exc.summary,
            details=exc.details,
        )
        return 2
    except Exception as exc:
        logger.emit(
            "stopped",
            3,
            "UNEXPECTED_ERROR",
            "unhandled_exception",
            "脚本发生未处理异常",
            details=[{"type": type(exc).__name__, "error": str(exc)}],
        )
        return 3


if __name__ == "__main__":
    sys.exit(main())






