from collections.abc import AsyncIterator
from typing import Protocol


class WebSearchProvider(Protocol):
    async def search(self, topic: str) -> list[dict]: ...


class KnowledgeProvider(Protocol):
    async def search(self, topic: str) -> list[dict]: ...


class LLMProvider(Protocol):
    async def plan(self, topic: str, dimensions: list[str]) -> list[str]: ...

    async def generate(
        self, topic: str, evidence: list[dict], output_format: str
    ) -> str: ...

    def stream(
        self, topic: str, evidence: list[dict], output_format: str
    ) -> AsyncIterator[str]: ...


class MockWebSearchProvider:
    async def search(self, topic: str) -> list[dict]:
        return [
            {
                "source_label": "Fixture · 示例 Web 来源 A",
                "excerpt": f"合成占位材料 A：主题标签为“{topic}”。该文本仅用于测试证据列表和日期筛选，不包含主题事实或真实来源内容。",
                "relevance": 0.94,
                "published_at": "2025-03-14",
            },
            {
                "source_label": "Fixture · 示例 Web 来源 B",
                "excerpt": f"合成占位材料 B：主题标签为“{topic}”。该文本只用于演示固定数据的时间和引用路径，不代表研究发现。",
                "relevance": 0.87,
                "published_at": "2025-06-02",
            },
        ]


class MockKnowledgeProvider:
    async def search(self, topic: str) -> list[dict]:
        return [
            {
                "source_label": "Fixture · 示例本地来源",
                "excerpt": f"合成占位材料 C：主题标签为“{topic}”。该文本仅用于界面演示，不是本地文档或该主题的证据。",
                "relevance": 0.82,
                "published_at": "2024-11-19",
            }
        ]


class MockLLMProvider:
    async def plan(self, topic: str, dimensions: list[str]) -> list[str]:
        dimensions_text = "、".join(dimensions) if dimensions else "主要分析因素"
        return [
            f"关于“{topic}”有哪些可用证据？",
            f"这些资料如何描述{dimensions_text}？",
            "有哪些来源限制或证据空白需要说明？",
        ]

    async def generate(
        self, topic: str, evidence: list[dict], output_format: str
    ) -> str:
        if not evidence:
            return f"当前没有为“{topic}”返回固定演示证据。本报告只记录已启用来源的证据缺口，不推断研究结论。"
        sentence = f"本次“{topic}”仅使用固定合成 Fixture 展示证据与引用流程，不包含主题匹配或事实检索，也不构成关于该主题的研究结论。"
        if output_format == "bullet_points":
            sentence = f"• 本次“{topic}”仅使用固定合成 Fixture 演示证据与引用流程，不代表主题事实或研究结论。"
        elif output_format == "executive_summary":
            sentence = f"摘要：本次“{topic}”仅使用固定合成 Fixture 演示证据与引用流程，不代表主题事实或研究结论。"
        return sentence

    async def stream(
        self, topic: str, evidence: list[dict], output_format: str
    ) -> AsyncIterator[str]:
        text = await self.generate(topic, evidence, output_format)
        for offset in range(0, len(text), 16):
            yield text[offset : offset + 16]
