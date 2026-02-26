"""Diff 解析和精简模块"""

import re
from dataclasses import dataclass, field

from .models.config import DiffProcessConfig


@dataclass
class DiffHunk:
    """单个变更块"""

    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[str] = field(default_factory=list)


@dataclass
class FileDiff:
    """单个文件的 diff"""

    file_path: str
    hunks: list[DiffHunk] = field(default_factory=list)
    is_new_file: bool = False
    is_deleted_file: bool = False
    header_lines: list[str] = field(default_factory=list)


def parse_diff(diff_text: str) -> list[FileDiff]:
    """解析 diff 文本为结构化数据

    Args:
        diff_text: git diff 输出

    Returns:
        文件 diff 列表
    """
    if not diff_text:
        return []

    files: list[FileDiff] = []
    current_file: FileDiff | None = None
    current_hunk: DiffHunk | None = None

    # 匹配文件头
    file_header_re = re.compile(r"^diff --git a/(.+?) b/(.+)$")
    # 匹配 hunk 头
    hunk_header_re = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$"
    )

    for line in diff_text.split("\n"):
        # 检查文件头
        file_match = file_header_re.match(line)
        if file_match:
            # 保存前一个文件的最后一个 hunk
            if current_hunk and current_file:
                current_file.hunks.append(current_hunk)
                current_hunk = None

            # 保存前一个文件
            if current_file:
                files.append(current_file)

            # 开始新文件
            current_file = FileDiff(file_path=file_match.group(2))
            continue

        if current_file is None:
            continue

        # 检查文件状态
        if line.startswith("new file mode"):
            current_file.is_new_file = True
            continue
        if line.startswith("deleted file mode"):
            current_file.is_deleted_file = True
            continue

        # 收集文件头信息（---, +++）
        if line.startswith("--- ") or line.startswith("+++ "):
            current_file.header_lines.append(line)
            continue

        # 检查 hunk 头
        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            # 保存前一个 hunk
            if current_hunk:
                current_file.hunks.append(current_hunk)

            # 开始新 hunk
            current_hunk = DiffHunk(
                file_path=current_file.file_path,
                old_start=int(hunk_match.group(1)),
                old_count=int(hunk_match.group(2) or "1"),
                new_start=int(hunk_match.group(3)),
                new_count=int(hunk_match.group(4) or "1"),
                header=hunk_match.group(5).strip(),
            )
            continue

        # 收集 hunk 内容
        if current_hunk is not None:
            current_hunk.lines.append(line)

    # 保存最后的数据
    if current_hunk and current_file:
        current_file.hunks.append(current_hunk)
    if current_file:
        files.append(current_file)

    return files


def extract_changed_context(
    hunk: DiffHunk, context_lines: int = 3
) -> tuple[list[str], int]:
    """提取变更上下文，精简 hunk 内容

    Args:
        hunk: 变更块
        context_lines: 上下文行数

    Returns:
        (精简后的行列表, 省略的行数)
    """
    if not hunk.lines:
        return [], 0

    # 找出所有变更行的索引
    change_indices = []
    for i, line in enumerate(hunk.lines):
        if line.startswith(("+", "-")) and not line.startswith("---"):
            change_indices.append(i)

    if not change_indices:
        # 没有实际变更（可能是二进制文件等）
        return hunk.lines, 0

    # 计算需要保留的区域
    keep_ranges: list[tuple[int, int]] = []
    for idx in change_indices:
        start = max(0, idx - context_lines)
        end = min(len(hunk.lines), idx + context_lines + 1)

        # 尝试合并相邻的区域
        merged = False
        for i, (r_start, r_end) in enumerate(keep_ranges):
            if start <= r_end + 1 and end >= r_start - 1:
                # 有重叠或相邻，合并
                keep_ranges[i] = (min(start, r_start), max(end, r_end))
                merged = True
                break

        if not merged:
            keep_ranges.append((start, end))

    # 按起始位置排序
    keep_ranges.sort(key=lambda x: x[0])

    # 构建精简后的行
    result: list[str] = []
    omitted_count = 0
    last_end = 0

    for start, end in keep_ranges:
        if start > last_end:
            # 有省略的部分
            omitted_lines = start - last_end
            omitted_count += omitted_lines
            if result:
                result.append(f"... (省略 {omitted_lines} 行)")

        result.extend(hunk.lines[start:end])
        last_end = end

    # 处理末尾省略
    if last_end < len(hunk.lines):
        omitted_lines = len(hunk.lines) - last_end
        omitted_count += omitted_lines
        result.append(f"... (省略 {omitted_lines} 行)")

    return result, omitted_count


def process_file_diff(
    file_diff: FileDiff, config: DiffProcessConfig
) -> tuple[str, int]:
    """处理单个文件的 diff，返回精简后的 diff 文本和行数

    Args:
        file_diff: 文件 diff 对象
        config: 精简配置

    Returns:
        (精简后的 diff 文本, 行数)
    """
    lines: list[str] = []

    # 添加文件头
    lines.append(f"diff --git a/{file_diff.file_path} b/{file_diff.file_path}")
    lines.extend(file_diff.header_lines)

    if file_diff.is_new_file:
        lines.append("new file mode 100644")
    if file_diff.is_deleted_file:
        lines.append("deleted file mode 100644")

    # 限制每个文件的 hunk 数量
    hunks_to_process = file_diff.hunks[: config.max_hunks_per_file]
    if len(file_diff.hunks) > config.max_hunks_per_file:
        lines.append(
            f"... (共 {len(file_diff.hunks)} 个变更块，仅显示前 {config.max_hunks_per_file} 个)"
        )

    total_lines = 0
    for hunk in hunks_to_process:
        # 添加 hunk 头
        hunk_header = f"@@ -{hunk.old_start}"
        if hunk.old_count != 1:
            hunk_header += f",{hunk.old_count}"
        hunk_header += f" +{hunk.new_start}"
        if hunk.new_count != 1:
            hunk_header += f",{hunk.new_count}"
        hunk_header += f" @@{hunk.header}"
        lines.append(hunk_header)

        # 添加精简后的内容
        simplified_lines, _ = extract_changed_context(hunk, config.context_lines)
        lines.extend(simplified_lines)
        total_lines += len(simplified_lines)

    return "\n".join(lines), total_lines


def process_diff(diff_text: str, config: DiffProcessConfig) -> str:
    """精简 diff 内容的主入口

    Args:
        diff_text: 原始 diff 文本
        config: 精简配置

    Returns:
        精简后的 diff 文本
    """
    if not config.enabled:
        return diff_text

    files = parse_diff(diff_text)
    if not files:
        return diff_text

    # 限制文件数量
    files_to_process = files[: config.max_files]

    result_parts: list[str] = []
    total_lines = 0

    for file_diff in files_to_process:
        file_diff_text, line_count = process_file_diff(file_diff, config)
        result_parts.append(file_diff_text)
        total_lines += line_count

        # 检查总行数限制
        if total_lines >= config.max_total_lines:
            break

    # 如果有文件被跳过，添加说明
    if len(files) > len(files_to_process):
        result_parts.append(
            f"\n... (共 {len(files)} 个文件，仅显示前 {len(files_to_process)} 个)"
        )

    return "\n\n".join(result_parts)
