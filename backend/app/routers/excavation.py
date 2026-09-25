"""开挖审批接口：维护开挖申请，覆盖初审通过、终审批准、驳回申请等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.excavation import ExcavationService

router = APIRouter(prefix="/api/excavation", tags=["开挖审批"])

service = ExcavationService()

LIST_FIELDS = ["申请编号", "申请单位", "施工地点", "施工范围", "涉及管线", "开挖深度", "审批意见", "申请状态"]
STATUSES = ["待初审", "初审通过", "待终审", "已批准", "已驳回"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按申请编号检索"),
    status: str | None = Query(default=None, description="待初审、初审通过、待终审、已批准、已驳回"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按申请编号与状态过滤开挖审批列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条开挖申请明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"开挖申请 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条开挖申请，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="开挖申请已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条开挖申请执行初审通过、终审批准、驳回申请；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出开挖审批清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "excavation", "total": total, "items": items}
