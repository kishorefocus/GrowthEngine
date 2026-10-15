"""
Video generator interface + stub.
Prompt 3 fills this in with actual video generation logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class VideoSpec:
    title: str
    script: str
    target_keyword: Optional[str] = None
    shot_list: Optional[list] = None


@dataclass
class VideoResult:
    asset_url: str
    success: bool
    error: Optional[str] = None


class VideoGenerator(ABC):
    @abstractmethod
    async def generate(self, spec: VideoSpec) -> VideoResult:
        ...


class StubVideoGenerator(VideoGenerator):
    async def generate(self, spec: VideoSpec) -> VideoResult:
        logger.info("[VideoGenerator:STUB] Would generate video: %s", spec.title)
        return VideoResult(asset_url="", success=False, error="Not implemented — Prompt 3")


def get_video_generator() -> VideoGenerator:
    return StubVideoGenerator()
