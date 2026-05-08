"""Task contracts and evidence requirements for completion checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .task_intent import TaskIntent


TOOL_GROUPS: dict[str, frozenset[str]] = {
    "image_text": frozenset({"ocr_image", "analyze_image"}),
    "image_understanding": frozenset({"analyze_image"}),
    "audio_text": frozenset({"transcribe_audio"}),
    "video_understanding": frozenset({"analyze_video"}),
    "web_research": frozenset({"web_search", "web_fetch"}),
    "history_retrieval": frozenset({"search_history", "search_knowledge"}),
    "workspace_read": frozenset({"read_file", "glob_files", "grep_files", "code_navigation"}),
    "workspace_write": frozenset({"apply_patch", "write_file", "edit_file"}),
    "verification": frozenset({"verify", "exec"}),
}

_MEDIA_HISTORY_RE = re.compile(r"^(Images|Audios|Videos):\s*(?P<paths>.+)$", re.IGNORECASE | re.MULTILINE)
_URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.IGNORECASE)
_IMAGE_TASK_HINT_RE = re.compile(
    r"\b(?:image|images|photo|photos|picture|pictures|screenshot|screenshots|prompt|prompts|ocr|text)\b"
    r"|(?:圖片|照片|截圖|圖|文字|提示詞|提詞|讀取|辨識|抓出|取出|提取|擷取)",
    re.IGNORECASE,
)
_AUDIO_TASK_HINT_RE = re.compile(r"\b(?:audio|voice|speech|transcribe)\b|(?:音訊|語音|錄音|轉錄)", re.IGNORECASE)
_VIDEO_TASK_HINT_RE = re.compile(r"\b(?:video|clip)\b|(?:影片|視頻|短片)", re.IGNORECASE)
_WEB_TASK_HINT_RE = re.compile(
    r"\b(?:web|internet|online|reddit|url|link|search|news)\b"
    r"|(?:上網|網路|搜尋|查找|新聞|來源|連結)",
    re.IGNORECASE,
)
_CURRENT_IMAGE_RE = re.compile(r"User attached (?P<count>\d+) image", re.IGNORECASE)
_CURRENT_AUDIO_RE = re.compile(r"User attached (?P<count>\d+) audio", re.IGNORECASE)
_CURRENT_VIDEO_RE = re.compile(r"User attached (?P<count>\d+) video", re.IGNORECASE)


@dataclass(frozen=True)
class ResourceRef:
    """A resource that the task may need to cover."""

    id: str
    kind: str
    path: str = ""
    source: str = "history"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "path": self.path,
            "source": self.source,
        }


@dataclass(frozen=True)
class EvidenceRequirement:
    """Evidence needed before the task can be treated as complete."""

    kind: str
    tool_group: str = ""
    resource_ids: tuple[str, ...] = ()
    coverage: str = "any"
    min_count: int = 1
    description: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "tool_group": self.tool_group,
            "resource_ids": list(self.resource_ids),
            "coverage": self.coverage,
            "min_count": self.min_count,
            "description": self.description,
        }


@dataclass(frozen=True)
class TaskContract:
    """Language-independent completion contract for one turn."""

    objective: str
    task_type: str
    requirements: tuple[EvidenceRequirement, ...] = ()
    selected_resources: tuple[ResourceRef, ...] = ()
    final_answer_required: bool = True
    allow_no_tool_final: bool = True

    def to_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "objective": self.objective,
            "task_type": self.task_type,
            "requirements": [item.to_metadata() for item in self.requirements],
            "selected_resources": [item.to_metadata() for item in self.selected_resources],
            "final_answer_required": self.final_answer_required,
            "allow_no_tool_final": self.allow_no_tool_final,
        }


@dataclass(frozen=True)
class ToolEvidence:
    """One completed tool call summarized for contract evaluation."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    resource_ids: tuple[str, ...] = ()
    result_preview: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": dict(self.args),
            "ok": self.ok,
            "resource_ids": list(self.resource_ids),
            "result_preview": self.result_preview,
        }


def build_tool_evidence(tool_name: str, args: dict[str, Any], result: str, *, ok: bool) -> ToolEvidence:
    """Create normalized evidence from a tool execution."""
    resource_ids: list[str] = []
    if tool_name in {"ocr_image", "analyze_image"}:
        image_path = str(args.get("image_path") or "").strip().replace("\\", "/")
        if image_path:
            resource_ids.append(f"image:{image_path}")
        else:
            resource_ids.append(f"image_index:{int(args.get('image_index') or 0)}")
    elif tool_name == "transcribe_audio":
        resource_ids.append(f"audio_index:{int(args.get('audio_index') or 0)}")
    elif tool_name == "analyze_video":
        resource_ids.append(f"video_index:{int(args.get('video_index') or 0)}")

    return ToolEvidence(
        name=tool_name,
        args=dict(args or {}),
        ok=ok,
        resource_ids=tuple(dict.fromkeys(resource_ids)),
        result_preview=str(result or "")[:240],
    )


class TaskContractService:
    """Build deterministic contracts from known turn facts."""

    @classmethod
    def build(
        cls,
        *,
        task_intent: TaskIntent,
        current_message: str,
        history: list[dict[str, Any]] | None = None,
        current_image_files: list[str] | None = None,
        current_audio_files: list[str] | None = None,
        current_video_files: list[str] | None = None,
    ) -> TaskContract:
        objective = str(task_intent.objective or current_message or "").strip()
        text = f"{objective}\n{current_message or ''}"
        history = history or []
        resources = cls._resources_from_turn(
            current_message=current_message,
            current_image_files=current_image_files,
            current_audio_files=current_audio_files,
            current_video_files=current_video_files,
        )
        resources.extend(cls._recent_media_resources(history))
        resources = _dedupe_resources(resources)

        requirements: list[EvidenceRequirement] = []
        selected: list[ResourceRef] = []
        task_type = _task_type_from_intent(task_intent)

        image_resources = [item for item in resources if item.kind == "image"]
        audio_resources = [item for item in resources if item.kind == "audio"]
        video_resources = [item for item in resources if item.kind == "video"]

        if image_resources and cls._looks_like_image_task(text, task_intent, current_image_files):
            selected.extend(image_resources)
            requirements.append(
                EvidenceRequirement(
                    kind="resource_coverage",
                    tool_group="image_text",
                    resource_ids=tuple(item.id for item in image_resources),
                    coverage="all",
                    min_count=len(image_resources),
                    description="Inspect each referenced image before finalizing the answer.",
                )
            )
            task_type = "media_extraction"
        elif audio_resources and cls._looks_like_audio_task(text, current_audio_files):
            selected.extend(audio_resources)
            requirements.append(
                EvidenceRequirement(
                    kind="resource_coverage",
                    tool_group="audio_text",
                    resource_ids=tuple(item.id for item in audio_resources),
                    coverage="all",
                    min_count=len(audio_resources),
                    description="Transcribe each referenced audio clip before finalizing the answer.",
                )
            )
            task_type = "media_extraction"
        elif video_resources and cls._looks_like_video_task(text, current_video_files):
            selected.extend(video_resources)
            requirements.append(
                EvidenceRequirement(
                    kind="resource_coverage",
                    tool_group="video_understanding",
                    resource_ids=tuple(item.id for item in video_resources),
                    coverage="all",
                    min_count=len(video_resources),
                    description="Analyze each referenced video before finalizing the answer.",
                )
            )
            task_type = "media_extraction"

        if cls._looks_like_web_task(text):
            requirements.append(
                EvidenceRequirement(
                    kind="tool_group",
                    tool_group="web_research",
                    coverage="any",
                    min_count=1,
                    description="Use web research tools before answering this external information request.",
                )
            )
            task_type = "web_research" if task_type == "pure_answer" else task_type

        if task_intent.expects_code_change:
            requirements.append(
                EvidenceRequirement(
                    kind="file_change",
                    min_count=1,
                    description="Record at least one workspace file change.",
                )
            )
            task_type = "code_change"

        if task_intent.expects_verification:
            requirements.append(
                EvidenceRequirement(
                    kind="verification",
                    tool_group="verification",
                    min_count=1,
                    description="Record verification evidence before finalizing.",
                )
            )

        return TaskContract(
            objective=objective,
            task_type=task_type,
            requirements=tuple(requirements),
            selected_resources=tuple(selected),
            final_answer_required=True,
            allow_no_tool_final=not requirements,
        )

    @staticmethod
    def _resources_from_turn(
        *,
        current_message: str,
        current_image_files: list[str] | None,
        current_audio_files: list[str] | None,
        current_video_files: list[str] | None,
    ) -> list[ResourceRef]:
        resources: list[ResourceRef] = []
        for index, path in enumerate(current_image_files or []):
            normalized = str(path or "").strip().replace("\\", "/")
            resources.append(ResourceRef(id=f"image:{normalized}" if normalized else f"image_index:{index}", kind="image", path=normalized, source="current_turn"))
        for index, path in enumerate(current_audio_files or []):
            normalized = str(path or "").strip().replace("\\", "/")
            resources.append(ResourceRef(id=f"audio:{normalized}" if normalized else f"audio_index:{index}", kind="audio", path=normalized, source="current_turn"))
        for index, path in enumerate(current_video_files or []):
            normalized = str(path or "").strip().replace("\\", "/")
            resources.append(ResourceRef(id=f"video:{normalized}" if normalized else f"video_index:{index}", kind="video", path=normalized, source="current_turn"))

        if not resources:
            resources.extend(_current_index_resources(current_message, _CURRENT_IMAGE_RE, "image"))
            resources.extend(_current_index_resources(current_message, _CURRENT_AUDIO_RE, "audio"))
            resources.extend(_current_index_resources(current_message, _CURRENT_VIDEO_RE, "video"))
        return resources

    @staticmethod
    def _recent_media_resources(history: list[dict[str, Any]]) -> list[ResourceRef]:
        resources: list[ResourceRef] = []
        found_recent_batch = False
        for message in reversed(history[-20:]):
            role = str(message.get("role") or "")
            if role != "user":
                continue
            content = str(message.get("content") or "")
            if "[Media-only message saved to workspace]" not in content:
                if found_recent_batch:
                    break
                continue
            found_recent_batch = True
            for match in _MEDIA_HISTORY_RE.finditer(content):
                label = match.group(1).lower()
                kind = {"images": "image", "audios": "audio", "videos": "video"}.get(label, "")
                for raw_path in match.group("paths").split(","):
                    path = raw_path.strip().replace("\\", "/")
                    if path:
                        resources.append(ResourceRef(id=f"{kind}:{path}", kind=kind, path=path, source="recent_media"))
        return resources

    @staticmethod
    def _looks_like_image_task(text: str, task_intent: TaskIntent, current_image_files: list[str] | None) -> bool:
        if current_image_files and task_intent.kind in {"analysis", "task", "writing", "question"}:
            return True
        return bool(_IMAGE_TASK_HINT_RE.search(text or ""))

    @staticmethod
    def _looks_like_audio_task(text: str, current_audio_files: list[str] | None) -> bool:
        return bool(current_audio_files or _AUDIO_TASK_HINT_RE.search(text or ""))

    @staticmethod
    def _looks_like_video_task(text: str, current_video_files: list[str] | None) -> bool:
        return bool(current_video_files or _VIDEO_TASK_HINT_RE.search(text or ""))

    @staticmethod
    def _looks_like_web_task(text: str) -> bool:
        return bool(_URL_RE.search(text or "") or _WEB_TASK_HINT_RE.search(text or ""))


def missing_evidence(contract: TaskContract | None, evidence: tuple[ToolEvidence, ...], *, file_change_count: int, verification_passed: bool) -> tuple[str, ...]:
    """Return human-readable missing evidence items for a contract."""
    if contract is None:
        return ()
    missing: list[str] = []
    ok_evidence = [item for item in evidence if item.ok]
    for requirement in contract.requirements:
        if requirement.kind == "tool_group":
            tools = TOOL_GROUPS.get(requirement.tool_group, frozenset())
            count = sum(1 for item in ok_evidence if item.name in tools)
            if count < max(1, requirement.min_count):
                missing.append(requirement.description or f"Use one of: {', '.join(sorted(tools))}")
        elif requirement.kind == "resource_coverage":
            tools = TOOL_GROUPS.get(requirement.tool_group, frozenset())
            covered = {
                resource_id
                for item in ok_evidence
                if item.name in tools
                for resource_id in item.resource_ids
            }
            required = set(requirement.resource_ids)
            if requirement.coverage == "all":
                uncovered = tuple(resource_id for resource_id in requirement.resource_ids if resource_id not in covered)
                if uncovered:
                    missing.append(
                        f"Missing {requirement.tool_group} coverage for: {', '.join(uncovered)}"
                    )
            elif len(covered & required) < max(1, requirement.min_count):
                missing.append(requirement.description or f"Missing {requirement.tool_group} coverage")
        elif requirement.kind == "file_change" and file_change_count < max(1, requirement.min_count):
            missing.append(requirement.description or "Record a workspace file change.")
        elif requirement.kind == "verification" and not verification_passed:
            missing.append(requirement.description or "Record passing verification evidence.")
    return tuple(missing)


def _task_type_from_intent(task_intent: TaskIntent) -> str:
    if task_intent.expects_code_change:
        return "code_change"
    if task_intent.kind in {"conversation", "question", "command"}:
        return "pure_answer"
    return task_intent.kind or "task"


def _current_index_resources(current_message: str, pattern: re.Pattern[str], kind: str) -> list[ResourceRef]:
    match = pattern.search(current_message or "")
    if not match:
        return []
    count = int(match.group("count") or 0)
    return [ResourceRef(id=f"{kind}_index:{index}", kind=kind, source="current_turn") for index in range(max(0, count))]


def _dedupe_resources(resources: list[ResourceRef]) -> list[ResourceRef]:
    by_id: dict[str, ResourceRef] = {}
    order: list[str] = []
    for item in resources:
        if not item.id or item.id in by_id:
            continue
        by_id[item.id] = item
        order.append(item.id)
    return [by_id[item_id] for item_id in order]
