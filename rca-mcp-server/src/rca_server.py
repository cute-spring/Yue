import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# --- 核心模型定义 ---

class RcaRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    issue_description: str
    root_cause: str
    solution: str
    code_changes: List[str] = []
    verification_steps: List[str] = []
    prevention_measures: List[str] = []
    impact_scope: str = "unknown"
    complexity: str = "medium"
    tags: List[str] = []
    commit_id: Optional[str] = None
    affected_files: List[str] = []

# --- FastMCP Server 初始化 ---

mcp = FastMCP(
    "RCA-Expert",
    dependencies=["pydantic", "aiofiles"]
)

# --- 存储配置 (通过环境变量实现解耦) ---

STORAGE_PATH = os.getenv("RCA_STORAGE_PATH", "./data/knowledge_base.json")
_lock = asyncio.Lock()

def _ensure_storage():
    os.makedirs(os.path.dirname(STORAGE_PATH), exist_ok=True)
    if not os.path.exists(STORAGE_PATH):
        with open(STORAGE_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f)

async def _load_records() -> List[Dict[str, Any]]:
    async with _lock:
        try:
            with open(STORAGE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

async def _save_records(records: List[Dict[str, Any]]):
    async with _lock:
        with open(STORAGE_PATH, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

# --- MCP 工具定义 ---

@mcp.tool()
async def record_rca(
    issue_description: str,
    root_cause: str,
    solution: str,
    code_changes: List[str] = [],
    verification_steps: List[str] = [],
    prevention_measures: List[str] = [],
    impact_scope: str = "unknown",
    complexity: str = "medium",
    tags: List[str] = [],
    commit_id: Optional[str] = None
) -> str:
    """
    记录一个新的根因分析 (RCA) 案例。
    当解决了一个非预期的问题或 Bug 时，应使用此工具进行归档。
    """
    _ensure_storage()
    records = await _load_records()
    
    record = RcaRecord(
        issue_description=issue_description,
        root_cause=root_cause,
        solution=solution,
        code_changes=code_changes,
        verification_steps=verification_steps,
        prevention_measures=prevention_measures,
        impact_scope=impact_scope,
        complexity=complexity,
        tags=tags,
        commit_id=commit_id
    )
    
    records.append(record.model_dump())
    await _save_records(records)
    return f"Successfully recorded RCA with ID: {record.id}"

@mcp.tool()
async def search_rca(query: str) -> str:
    """
    根据关键词或描述搜索历史 RCA 案例。
    用于在遇到类似问题时获取修复建议。
    """
    _ensure_storage()
    records_raw = await _load_records()
    records = [RcaRecord(**r) for r in records_raw]
    
    if not query:
        return "Please provide a search query."
    
    query = query.lower()
    scored_results = []
    for r in records:
        score = 0
        if query in r.issue_description.lower(): score += 5
        if query in r.root_cause.lower(): score += 3
        if any(query in tag.lower() for tag in r.tags): score += 10
        
        if score > 0:
            scored_results.append((score, r))
    
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_results:
        return "No similar historical RCA cases found."
    
    output = ["### Historical RCA Recommendations\n"]
    for score, r in scored_results[:5]:
        output.append(f"#### Case: {r.issue_description[:100]}")
        output.append(f"- **Root Cause**: {r.root_cause}")
        output.append(f"- **Solution**: {r.solution}")
        output.append(f"- **Prevention**: {', '.join(r.prevention_measures) if r.prevention_measures else 'N/A'}")
        output.append("")
    
    return "\n".join(output)

@mcp.tool()
async def generate_rca_report(record_id: Optional[str] = None) -> str:
    """
    生成 RCA 报告。
    如果提供 record_id，生成详细报告；否则生成最近案例的摘要。
    """
    _ensure_storage()
    records_raw = await _load_records()
    records = [RcaRecord(**r) for r in records_raw]
    
    if record_id:
        record = next((r for r in records if r.id == record_id), None)
        if not record:
            return f"Error: Record ID {record_id} not found."
        
        report = [
            f"# RCA Detailed Report",
            f"**ID**: `{record.id}` | **Date**: {record.timestamp[:10]}",
            f"**Complexity**: {record.complexity} | **Impact**: {record.impact_scope}",
            "\n## 1. Issue\n" + record.issue_description,
            "\n## 2. Root Cause\n" + record.root_cause,
            "\n## 3. Solution\n" + record.solution,
            "\n## 4. Code Changes\n- " + "\n- ".join(record.code_changes or ["N/A"]),
            "\n## 5. Prevention\n- " + "\n- ".join(record.prevention_measures or ["N/A"])
        ]
        return "\n".join(report)
    else:
        if not records:
            return "Knowledge base is empty."
        
        summary = ["# RCA Knowledge Base Summary", "| Date | Issue | Complexity |", "|---|---|---|"]
        for r in records[-10:]:
            summary.append(f"| {r.timestamp[:10]} | {r.issue_description[:50]}... | {r.complexity} |")
        return "\n".join(summary)

if __name__ == "__main__":
    mcp.run()
