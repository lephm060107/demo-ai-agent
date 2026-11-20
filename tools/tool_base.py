"""
tools/tool_base.py
Định nghĩa cơ chế ghi nhận bằng chứng gọi công cụ (Tool Call Tracing) cho mọi Tool trong hệ thống.
"""

import time
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel

class ToolCallRecord(BaseModel):
    call_id: str
    timestamp: str
    tool_name: str
    action: str
    input_args: Dict[str, Any]
    output_summary: str
    records_accessed: int
    duration_ms: float
    status: str  # "OK" | "ERROR"

class ToolTracer:
    def __init__(self):
        self.records: List[ToolCallRecord] = []
        self._counter = 0

    def record(
        self,
        tool_name: str,
        action: str,
        input_args: Dict[str, Any],
        output_summary: str,
        records_accessed: int,
        start_time: float,
        status: str = "OK"
    ) -> ToolCallRecord:
        self._counter += 1
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        rec = ToolCallRecord(
            call_id=f"TC-{self._counter:03d}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            tool_name=tool_name,
            action=action,
            input_args=input_args,
            output_summary=output_summary,
            records_accessed=records_accessed,
            duration_ms=duration_ms,
            status=status
        )
        self.records.append(rec)
        return rec

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [r.model_dump() for r in self.records]

