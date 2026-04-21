class SummaryService:
    def summarize(self, source_type: str, content: str) -> dict[str, object]:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        lead = lines[:3] if lines else [content.strip() or "No content provided."]
        source_label = {
            "file": "文件",
            "web": "网页",
            "session": "会话",
            "code": "代码",
            "search-results": "搜索结果",
            "workspace": "工作台",
            "voice": "语音",
        }.get(source_type, source_type)
        bullets = [
            f"source={source_type}",
            f"label={source_label}",
            f"lines={len(lines) or 1}",
            f"preview={lead[0][:80]}",
        ]
        return {
            "summary": f"{source_label}总结：{' / '.join(lead[:2])}",
            "bullets": bullets,
        }
