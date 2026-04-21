from sqlalchemy import desc, func, select

from app.models import (
    ActionAudit,
    ChatMessage,
    ChatSession,
    MemoryEntry,
    PreferenceState,
    ReminderEvent,
    RealtimeEvent,
    TaskItem,
    UploadedContext,
    WorkspaceState,
)


class MemoryService:
    def remember(self, db, kind: str, content: str, source: str) -> None:
        db.add(MemoryEntry(kind=kind, content=content, source=source))

    def create_task(self, db, title: str, detail: str = "") -> TaskItem:
        task = TaskItem(title=title, detail=detail)
        db.add(task)
        db.flush()
        db.add(ReminderEvent(message=f"待处理任务：{title}", task_id=task.id))
        return task

    def update_preferences(self, db, teacher_style: str, voice_name: str) -> PreferenceState:
        preference = db.scalar(select(PreferenceState).limit(1))
        if preference is None:
            preference = PreferenceState(
                teacher_style=teacher_style,
                voice_name=voice_name,
            )
            db.add(preference)
            db.flush()
            return preference

        preference.teacher_style = teacher_style
        preference.voice_name = voice_name
        db.flush()
        return preference

    def get_preferences(self, db) -> PreferenceState:
        preference = db.scalar(select(PreferenceState).limit(1))
        if preference is None:
            preference = PreferenceState()
            db.add(preference)
            db.flush()
        return preference

    def update_workspace_state(self, db, active_workspace: str, session_id: str | None = None) -> WorkspaceState:
        state = db.scalar(select(WorkspaceState).limit(1))
        if state is None:
            state = WorkspaceState(active_workspace=active_workspace, last_session_id=session_id)
            db.add(state)
            db.flush()
            return state

        state.active_workspace = active_workspace
        if session_id is not None:
            state.last_session_id = session_id
        db.flush()
        return state

    def remember_upload(self, db, title: str, source_type: str, content: str) -> UploadedContext:
        upload = UploadedContext(title=title, source_type=source_type, content=content)
        db.add(upload)
        db.flush()
        self.remember(
            db,
            kind="upload",
            content=f"{title}: {content[:120]}",
            source=source_type,
        )
        return upload

    def snapshot(self, db) -> dict[str, object]:
        tasks = list(db.scalars(select(TaskItem).order_by(desc(TaskItem.created_at)).limit(5)))
        memories = list(db.scalars(select(MemoryEntry).order_by(desc(MemoryEntry.created_at)).limit(5)))
        reminders = list(db.scalars(select(ReminderEvent).order_by(desc(ReminderEvent.created_at)).limit(5)))
        actions = list(db.scalars(select(ActionAudit).order_by(desc(ActionAudit.created_at)).limit(5)))
        uploads = list(db.scalars(select(UploadedContext).order_by(desc(UploadedContext.created_at)).limit(5)))
        preference = self.get_preferences(db)
        workspace_state = db.scalar(select(WorkspaceState).limit(1))
        latest_session_id = db.scalar(select(ChatSession.id).order_by(desc(ChatSession.created_at)).limit(1))
        total_tasks = db.scalar(select(func.count(TaskItem.id))) or 0
        completed_tasks = db.scalar(
            select(func.count(TaskItem.id)).where(TaskItem.status == "completed")
        ) or 0
        timeline = [
            {
                "type": "chat",
                "content": message.content,
            }
            for message in db.scalars(select(ChatMessage).order_by(desc(ChatMessage.id)).limit(5))
        ]
        timeline.extend(
            {
                "type": event.event_type,
                "content": event.payload,
            }
            for event in db.scalars(select(RealtimeEvent).order_by(desc(RealtimeEvent.id)).limit(5))
        )
        computed_reminders = []
        if tasks:
            computed_reminders.append(
                {
                    "id": -1,
                    "message": f"上次未完成任务：{tasks[0].title}",
                    "task_id": tasks[0].id,
                }
            )
        if workspace_state and workspace_state.active_workspace != "console":
            computed_reminders.append(
                {
                    "id": -2,
                    "message": f"你上次停在 {workspace_state.active_workspace} 工作台。",
                    "task_id": None,
                }
            )
        return {
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "detail": task.detail,
                    "status": task.status,
                    "stage": task.stage,
                }
                for task in tasks
            ],
            "memories": [
                {"id": memory.id, "kind": memory.kind, "content": memory.content, "source": memory.source}
                for memory in memories
            ],
            "reminders": computed_reminders + [
                {"id": reminder.id, "message": reminder.message, "task_id": reminder.task_id}
                for reminder in reminders
            ][:5],
            "recent_actions": [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "target": action.target,
                    "risk_level": action.risk_level,
                    "status": action.status,
                    "detail": action.detail,
                }
                for action in actions
            ],
            "timeline": timeline[:10],
            "preferences": {
                "teacher_style": preference.teacher_style,
                "voice_name": preference.voice_name,
            },
            "resume": {
                "workspace": workspace_state.active_workspace if workspace_state else "console",
                "session_id": workspace_state.last_session_id or latest_session_id,
            },
            "stage_progress": {
                "current_stage": "M6",
                "completed_tasks": completed_tasks,
                "total_tasks": total_tasks,
                "uploaded_contexts": len(uploads),
            },
            "uploaded_contexts": [
                {
                    "id": upload.id,
                    "title": upload.title,
                    "source_type": upload.source_type,
                    "preview": upload.content[:120],
                }
                for upload in uploads
            ],
        }
