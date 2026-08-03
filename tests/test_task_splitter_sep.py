"""TaskSplitter：明确「；」/换行分隔的多选组合应确定性拆成多任务。"""

from __future__ import annotations

import asyncio

from backend.llm.task_splitter import split_tasks


def test_semicolon_split_is_deterministic_without_llm() -> None:
    result = asyncio.run(split_tasks("兴修水利；操练士卒", client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert [s.original_fragment for s in result.subtasks] == ["兴修水利", "操练士卒"]
    assert "；" in result.split_reason


def test_newline_split_is_deterministic_without_llm() -> None:
    result = asyncio.run(split_tasks("兴修水利\n操练士卒", client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert [s.original_fragment for s in result.subtasks] == ["兴修水利", "操练士卒"]
    assert "换行" in result.split_reason


def test_newline_split_with_manual_suffix() -> None:
    text = "兴修水利\n操练士卒\n并派使者与邻国结盟"
    result = asyncio.run(split_tasks(text, client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert len(result.subtasks) == 3
    assert result.subtasks[2].description == "并派使者与邻国结盟"


def test_mixed_semicolon_and_newline_split() -> None:
    text = "兴修水利；操练士卒\n并派使者与邻国结盟"
    result = asyncio.run(split_tasks(text, client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert [s.original_fragment for s in result.subtasks] == [
        "兴修水利",
        "操练士卒",
        "并派使者与邻国结盟",
    ]


def test_semicolon_split_with_manual_suffix() -> None:
    text = "兴修水利；操练士卒；并派使者与邻国结盟"
    result = asyncio.run(split_tasks(text, client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert len(result.subtasks) == 3
    assert result.subtasks[2].description == "并派使者与邻国结盟"


def test_semicolon_split_caps_at_four() -> None:
    text = "甲政令；乙政令；丙政令；丁政令；戊政令"
    result = asyncio.run(split_tasks(text, client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert len(result.subtasks) == 4
    assert "前 4 段" in result.split_reason


def test_newline_split_caps_at_four() -> None:
    text = "甲政令\n乙政令\n丙政令\n丁政令\n戊政令"
    result = asyncio.run(split_tasks(text, client=object()))  # type: ignore[arg-type]
    assert result.is_multi_task is True
    assert len(result.subtasks) == 4
    assert "前 4 段" in result.split_reason
