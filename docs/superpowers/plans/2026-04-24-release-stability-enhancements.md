# Release Stability Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate backend-port confusion, return structured summary failures, and broaden knowledge search coverage without destabilizing the public release.

**Architecture:** Keep the existing Electron + React + FastAPI layout, but add one small backend instance-identity contract, one startup guard service, one explicit summary-error contract, and one broader text-search constant set. The implementation should stay incremental: lock down backend behavior with targeted tests first, then wire the startup script and UI surfaces to the new contracts.

**Tech Stack:** PowerShell, Python, FastAPI, httpx, React, TypeScript, Vitest, pytest

---

## File Map

- `jarvis-server\app\config.py`
  - Defines runtime host/port and the expected instance identity for this repo.
- `jarvis-server\app\routers\health.py`
  - Exposes the current backend health payload, now including instance metadata for startup validation.
- `jarvis-server\app\services\server_instance_service.py`
  - New focused service that probes the configured backend slot and raises a clear conflict error before startup.
- `scripts\dev-server.ps1`
  - Calls the server-slot guard before launching `uvicorn`.
- `jarvis-server\tests\test_health.py`
  - Locks the health contract, including instance metadata.
- `jarvis-server\tests\test_server_instance_service.py`
  - New unit tests for free-port, matching-instance, and conflicting-instance startup behavior.
- `jarvis-server\app\services\summary_service.py`
  - Preserves useful summary generation while raising typed provider failures.
- `jarvis-server\app\routers\assistant.py`
  - Maps typed summary failures into structured `502` / `503` API responses.
- `jarvis-server\tests\test_summary_service.py`
  - Verifies provider/auth/timeout mapping at the service level.
- `jarvis-server\tests\test_assistant_api.py`
  - Verifies `/api/summary` returns structured error details and that search routes still work.
- `jarvis-ui\src\app\api\assistant-client.ts`
  - Parses structured error payloads into a reusable frontend error type.
- `jarvis-ui\src\app\api\assistant-client.test.ts`
  - Verifies structured error parsing does not regress the existing JSON header merge behavior.
- `jarvis-ui\src\features\console\MainConsole.tsx`
  - Stores summary failure state and routes summary failures into the summary workspace.
- `jarvis-ui\src\features\workspace\WorkspaceRouter.tsx`
  - Renders either summary results or the new summary error message + hint.
- `jarvis-ui\src\features\console\MainConsole.test.tsx`
  - Verifies the summary workspace shows actionable failure guidance.
- `jarvis-server\app\services\search_service.py`
  - Centralizes supported text extensions and result limits.
- `jarvis-server\tests\test_search_service.py`
  - New unit tests for multi-extension search coverage and result caps.
- `README.md`
  - Documents startup conflict behavior, summary-failure semantics, and supported knowledge-search file types.

### Task 1: Expose instance identity in the health contract

**Files:**
- Modify: `jarvis-server\app\config.py`
- Modify: `jarvis-server\app\routers\health.py`
- Modify: `jarvis-server\tests\test_health.py`

- [ ] **Step 1: Write the failing health-contract tests**

```python
def test_health_reports_service_name() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "jarvis-server",
        "mode": "m6",
        "degraded": False,
        "dependencies": {
            "database": "ready",
            "llm": "missing",
            "speech": "missing",
            "config": "missing",
        },
        "instance": {
            "signature": "jarvis-public-release",
            "root": str(config_module.ROOT_DIR),
            "host": "127.0.0.1",
            "port": 8001,
        },
    }


def test_server_runtime_config_reads_instance_identity() -> None:
    runtime_config = get_server_runtime_config()

    assert runtime_config["instance_signature"] == "jarvis-public-release"
    assert runtime_config["root"] == str(config_module.ROOT_DIR)
```

- [ ] **Step 2: Run the health tests to verify the new contract fails**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_health.py -q
```

Expected: FAIL because `/api/health` does not yet include `instance` and `get_server_runtime_config()` does not yet expose identity fields.

- [ ] **Step 3: Add repo identity to runtime config and health**

```python
ROOT_DIR = Path(__file__).resolve().parents[2]


def get_instance_signature() -> str:
    return ROOT_DIR.name


def get_server_runtime_config() -> dict[str, str | int]:
    settings = get_settings()
    return {
        "host": settings.server_host,
        "port": settings.server_port,
        "instance_signature": get_instance_signature(),
        "root": str(ROOT_DIR),
    }
```

```python
@router.get("/api/health")
async def health(request: Request) -> dict[str, object]:
    runtime_config = get_server_runtime_config()
    database_ready = bool(getattr(request.app.state, "database_ready", True))
    database_status = (
        check_database_connection(get_database_url_for_runtime()) if database_ready else "offline"
    )
    llm_status = check_llm_connection(get_active_provider())
    speech_status = check_speech_configuration(get_speech_config())
    config_status = "ready" if llm_status != "missing" or speech_status != "missing" else "missing"

    if database_ready and database_status == "ready":
        try:
            with SessionLocal() as db:
                db.execute(text("select 1"))
                db.rollback()
        except Exception:
            database_status = "offline"
            database_ready = False
    else:
        database_ready = False
    return {
        "ok": database_ready,
        "service": "jarvis-server",
        "mode": getattr(request.app.state, "mode", "m1"),
        "degraded": not database_ready,
        "dependencies": {
            "database": database_status,
            "llm": llm_status,
            "speech": speech_status,
            "config": config_status,
        },
        "instance": {
            "signature": runtime_config["instance_signature"],
            "root": runtime_config["root"],
            "host": runtime_config["host"],
            "port": runtime_config["port"],
        },
    }
```

- [ ] **Step 4: Re-run the focused health tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_health.py -q
```

Expected: PASS with the new `instance` block included in both healthy and degraded health responses.

- [ ] **Step 5: Commit the health-contract change**

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
git add -- jarvis-server/app/config.py jarvis-server/app/routers/health.py jarvis-server/tests/test_health.py
git commit -m "feat: expose server instance identity" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Block startup when the configured backend slot is occupied by the wrong instance

**Files:**
- Create: `jarvis-server\app\services\server_instance_service.py`
- Create: `jarvis-server\tests\test_server_instance_service.py`
- Modify: `scripts\dev-server.ps1`

- [ ] **Step 1: Write the failing startup-guard tests**

```python
import pytest

from app.services.server_instance_service import PortConflictError, assert_configured_server_slot


def test_assert_configured_server_slot_allows_closed_port(monkeypatch) -> None:
    monkeypatch.setattr("app.services.server_instance_service._port_is_open", lambda *_: False)

    assert_configured_server_slot()


def test_assert_configured_server_slot_allows_matching_instance(monkeypatch) -> None:
    monkeypatch.setattr("app.services.server_instance_service._port_is_open", lambda *_: True)
    monkeypatch.setattr(
        "app.services.server_instance_service._fetch_health",
        lambda *_: {
            "service": "jarvis-server",
            "instance": {
                "signature": "jarvis-public-release",
                "root": r"C:\repo\jarvis-public-release",
                "host": "127.0.0.1",
                "port": 8001,
            },
        },
    )
    monkeypatch.setattr(
        "app.services.server_instance_service.get_server_runtime_config",
        lambda: {
            "host": "127.0.0.1",
            "port": 8001,
            "instance_signature": "jarvis-public-release",
            "root": r"C:\repo\jarvis-public-release",
        },
    )

    assert_configured_server_slot()


def test_assert_configured_server_slot_blocks_unidentifiable_instance(monkeypatch) -> None:
    monkeypatch.setattr("app.services.server_instance_service._port_is_open", lambda *_: True)
    monkeypatch.setattr(
        "app.services.server_instance_service._fetch_health",
        lambda *_: {"service": "jarvis-server"},
    )

    with pytest.raises(PortConflictError, match="8001"):
        assert_configured_server_slot()
```

- [ ] **Step 2: Run the new startup-guard tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_server_instance_service.py -q
```

Expected: FAIL because the service file does not exist yet.

- [ ] **Step 3: Implement the startup-guard service**

```python
from dataclasses import dataclass
import socket

import httpx

from app.config import get_server_runtime_config


@dataclass(frozen=True)
class PortConflictError(RuntimeError):
    message: str

    def __str__(self) -> str:
        return self.message


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) == 0


def _fetch_health(host: str, port: int) -> dict[str, object]:
    response = httpx.get(f"http://{host}:{port}/api/health", timeout=1.5)
    response.raise_for_status()
    return response.json()


def assert_configured_server_slot() -> None:
    runtime_config = get_server_runtime_config()
    host = str(runtime_config["host"])
    port = int(runtime_config["port"])
    expected_signature = str(runtime_config["instance_signature"])
    expected_root = str(runtime_config["root"])

    if not _port_is_open(host, port):
        return

    try:
        payload = _fetch_health(host, port)
    except Exception as exc:
        raise PortConflictError(
            f"端口 {port} 已被占用，且现有服务无法识别。请先关闭旧的 Jarvis 实例，或修改 JARVIS_SERVER_PORT 后重试。"
        ) from exc

    instance = payload.get("instance") if isinstance(payload, dict) else None
    if not isinstance(instance, dict):
        raise PortConflictError(
            f"端口 {port} 已被占用，且现有服务缺少实例标识。请先关闭旧的 Jarvis 实例，或修改 JARVIS_SERVER_PORT 后重试。"
        )

    if instance.get("signature") != expected_signature or instance.get("root") != expected_root:
        raise PortConflictError(
            f"端口 {port} 已被另一个 Jarvis 实例占用（{instance.get('root', 'unknown root')}）。请先关闭旧实例，或修改 JARVIS_SERVER_PORT 后重试。"
        )
```

- [ ] **Step 4: Call the guard from the server startup script**

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location "$PSScriptRoot\..\jarvis-server"

python -c "from app.services.server_instance_service import assert_configured_server_slot; assert_configured_server_slot()"
$runtimeConfig = python -c "from app.config import get_server_runtime_config_json; print(get_server_runtime_config_json())" | ConvertFrom-Json
$serverHost = [string]$runtimeConfig.host
$serverPort = [int]$runtimeConfig.port

if ($env:JARVIS_SERVER_DRY_RUN -eq '1') {
    Write-Output "HOST=$serverHost"
    Write-Output "PORT=$serverPort"
    exit 0
}

python -m uvicorn app.main:create_app --factory --reload --host $serverHost --port $serverPort
```

- [ ] **Step 5: Re-run the startup-guard tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_server_instance_service.py -q
```

Expected: PASS for closed-port, matching-instance, and blocked-instance scenarios.

- [ ] **Step 6: Commit the startup-guard change**

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
git add -- jarvis-server/app/services/server_instance_service.py jarvis-server/tests/test_server_instance_service.py scripts/dev-server.ps1
git commit -m "fix: block conflicting backend startups" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: Return structured summary failures from the backend

**Files:**
- Modify: `jarvis-server\app\services\summary_service.py`
- Modify: `jarvis-server\app\routers\assistant.py`
- Modify: `jarvis-server\tests\test_summary_service.py`
- Modify: `jarvis-server\tests\test_assistant_api.py`

- [ ] **Step 1: Write the failing summary-error tests**

```python
import httpx
import pytest

from app.services.summary_service import SummaryProviderError, SummaryService


class TimeoutClient:
    def complete(self, query: str, history: list, **kwargs) -> str:  # noqa: ARG002
        raise httpx.TimeoutException("summary timeout")


class MissingKeyClient:
    def complete(self, query: str, history: list, **kwargs) -> str:  # noqa: ARG002
        raise RuntimeError("Kimi API key is not configured. Set KIMI_API_KEY before starting Jarvis.")


def test_summarize_maps_timeout_to_retryable_provider_error() -> None:
    service = SummaryService(chat_client=TimeoutClient())

    with pytest.raises(SummaryProviderError) as exc:
        service.summarize("file", "example content")

    assert exc.value.status_code == 503
    assert exc.value.code == "summary_provider_timeout"
    assert exc.value.retryable is True


def test_summarize_maps_missing_key_to_non_retryable_provider_error() -> None:
    service = SummaryService(chat_client=MissingKeyClient())

    with pytest.raises(SummaryProviderError) as exc:
        service.summarize("file", "example content")

    assert exc.value.status_code == 502
    assert exc.value.code == "summary_provider_auth_failed"
    assert exc.value.retryable is False
```

```python
def test_summary_returns_structured_502_for_provider_auth_failure(monkeypatch) -> None:
    client = TestClient(create_app())
    monkeypatch.setattr(
        assistant_router.summary_service,
        "summarize",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SummaryProviderError(
                status_code=502,
                code="summary_provider_auth_failed",
                message="总结模型认证失败。",
                hint="请检查当前模型 API Key 或提供商配置。",
                retryable=False,
            )
        ),
    )

    response = client.post(
        "/api/summary",
        json={"source_type": "session", "content": "Jarvis can summarize this session."},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "summary_provider_auth_failed",
        "message": "总结模型认证失败。",
        "hint": "请检查当前模型 API Key 或提供商配置。",
        "retryable": False,
    }
```

- [ ] **Step 2: Run the focused summary tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_summary_service.py tests\test_assistant_api.py -q
```

Expected: FAIL because `SummaryProviderError` does not exist and `/api/summary` does not yet translate typed failures.

- [ ] **Step 3: Add a typed summary-provider failure and map raw provider errors**

```python
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class SummaryProviderError(Exception):
    status_code: int
    code: str
    message: str
    hint: str
    retryable: bool


class SummaryService:
    def __init__(self, chat_client: KimiChatClient | None = None) -> None:
        self._chat_client = chat_client

    def summarize(self, source_type: str, content: str) -> dict[str, object]:
        client = self._chat_client or _get_chat_client()
        source_label = _SOURCE_LABELS.get(source_type, source_type)
        truncated = content[:MAX_CONTENT_CHARS]
        prompt = _SUMMARY_PROMPT_TEMPLATE.format(source_label=source_label, content=truncated)
        try:
            response = client.complete(query=prompt, history=[])
        except httpx.TimeoutException as exc:
            raise SummaryProviderError(
                status_code=503,
                code="summary_provider_timeout",
                message="总结服务暂时超时。",
                hint="请稍后重试，或检查当前模型服务连通性。",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise SummaryProviderError(
                    status_code=502,
                    code="summary_provider_auth_failed",
                    message="总结模型认证失败。",
                    hint="请检查当前模型 API Key 或提供商配置。",
                    retryable=False,
                ) from exc
            raise SummaryProviderError(
                status_code=503,
                code="summary_provider_unavailable",
                message="总结服务暂时不可用。",
                hint="请稍后重试。",
                retryable=True,
            ) from exc
        except RuntimeError as exc:
            if "API key" in str(exc):
                raise SummaryProviderError(
                    status_code=502,
                    code="summary_provider_auth_failed",
                    message="总结模型认证失败。",
                    hint="请检查当前模型 API Key 或提供商配置。",
                    retryable=False,
                ) from exc
            raise
        summary, bullets = _parse_llm_response(response)
        return {"summary": summary, "bullets": bullets}
```

```python
from fastapi import APIRouter, HTTPException
from app.services.summary_service import SummaryProviderError


@router.post("/api/summary")
def summarize(request: SummaryRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        result = summary_service.summarize(request.source_type, request.content)
        memory_service.remember(
            db,
            kind="summary",
            content=result["summary"],
            source=request.source_type,
        )
        memory_service.update_workspace_state(db, active_workspace="summary")
        db.commit()
        return result
    except SummaryProviderError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.message,
                "hint": exc.hint,
                "retryable": exc.retryable,
            },
        ) from exc
    finally:
        db.close()
```

- [ ] **Step 4: Re-run the focused summary tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_summary_service.py tests\test_assistant_api.py -q
```

Expected: PASS with `502` for auth/config failures and `503` for retryable provider failures.

- [ ] **Step 5: Commit the backend summary-error change**

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
git add -- jarvis-server/app/services/summary_service.py jarvis-server/app/routers/assistant.py jarvis-server/tests/test_summary_service.py jarvis-server/tests/test_assistant_api.py
git commit -m "fix: return structured summary failures" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: Surface structured summary failures in the summary workspace

**Files:**
- Modify: `jarvis-ui\src\app\api\assistant-client.ts`
- Modify: `jarvis-ui\src\app\api\assistant-client.test.ts`
- Modify: `jarvis-ui\src\features\console\MainConsole.tsx`
- Modify: `jarvis-ui\src\features\workspace\WorkspaceRouter.tsx`
- Modify: `jarvis-ui\src\features\console\MainConsole.test.tsx`

- [ ] **Step 1: Write the failing frontend tests**

```ts
import { AssistantApiError, summarizeContent } from './assistant-client';

it('throws AssistantApiError with structured detail when summary fails', async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 502,
    json: async () => ({
      detail: {
        code: 'summary_provider_auth_failed',
        message: '总结模型认证失败。',
        hint: '请检查当前模型 API Key 或提供商配置。',
        retryable: false,
      },
    }),
  } as Response);

  await expect(summarizeContent('workspace', 'Jarvis')).rejects.toMatchObject({
    name: 'AssistantApiError',
    status: 502,
    detail: {
      code: 'summary_provider_auth_failed',
      message: '总结模型认证失败。',
    },
  });
});
```

```ts
it('summary workspace shows actionable provider guidance when summarize fails', async () => {
  mockState.summarizeContent.mockRejectedValueOnce(
    new AssistantApiError(503, {
      code: 'summary_provider_timeout',
      message: '总结服务暂时超时。',
      hint: '请稍后重试，或检查当前模型服务连通性。',
      retryable: true,
    }),
  );

  render(<MainConsole />);

  fireEvent.click(await screen.findByText('总结'));

  expect(await screen.findByText('总结服务暂时超时。')).toBeInTheDocument();
  expect(screen.getByText('请稍后重试，或检查当前模型服务连通性。')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run src\app\api\assistant-client.test.ts src\features\console\MainConsole.test.tsx
```

Expected: FAIL because the client still throws a generic `Error` and the summary workspace has no summary-error state.

- [ ] **Step 3: Add a reusable frontend API error and summary-error workspace state**

```ts
export interface AssistantErrorDetail {
  code?: string;
  message: string;
  hint?: string;
  retryable?: boolean;
}

export class AssistantApiError extends Error {
  status: number;
  detail: AssistantErrorDetail | null;

  constructor(status: number, detail: AssistantErrorDetail | null) {
    super(detail?.message ?? `Jarvis assistant request failed with status ${status}`);
    this.name = 'AssistantApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getServerBaseUrl()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new AssistantApiError(response.status, payload?.detail ?? null);
  }

  return (await response.json()) as T;
}
```

```ts
const [summaryError, setSummaryError] = useState<AssistantErrorDetail | null>(null);

async function runSummary(sourceType: string, content: string) {
  setSummaryError(null);
  setSummaryResult(null);
  try {
    setSummaryResult(await summarizeContent(sourceType, content));
  } catch (error) {
    const detail =
      error instanceof AssistantApiError
        ? error.detail
        : { message: '总结失败，请稍后重试。', hint: '请检查模型配置或稍后重试。', retryable: true };
    setSummaryError(detail);
  }
  setActiveWorkspace('summary');
}
```

```tsx
interface WorkspaceRouterProps {
  activeWorkspace: WorkspaceId;
  searchResults: SearchResult[];
  summaryResult: SummaryResult | null;
  summaryError: AssistantErrorDetail | null;
  recentActions: ActionRecord[];
  timeline: TimelineEntry[];
  uploadedContexts: UploadedContext[];
}

if (activeWorkspace === 'summary') {
  return (
    <section className="workspace-card">
      <h2>总结视图</h2>
      {summaryError ? (
        <article className="workspace-result workspace-result--error">
          <strong>{summaryError.message}</strong>
          {summaryError.hint ? <p>{summaryError.hint}</p> : null}
        </article>
      ) : summaryResult ? (
        <>
          <h3>总结结论</h3>
          <p>{summaryResult.summary}</p>
          <h3>关键要点</h3>
          <ul>
            {summaryResult.bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        </>
      ) : (
        <p>还没有总结结果。</p>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Re-run the focused frontend tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run src\app\api\assistant-client.test.ts src\features\console\MainConsole.test.tsx
```

Expected: PASS with both the API-client parsing test and the summary-workspace rendering test green.

- [ ] **Step 5: Commit the frontend summary-error change**

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
git add -- jarvis-ui/src/app/api/assistant-client.ts jarvis-ui/src/app/api/assistant-client.test.ts jarvis-ui/src/features/console/MainConsole.tsx jarvis-ui/src/features/workspace/WorkspaceRouter.tsx jarvis-ui/src/features/console/MainConsole.test.tsx
git commit -m "feat: show actionable summary errors" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 5: Expand knowledge search coverage and document the new behavior

**Files:**
- Modify: `jarvis-server\app\services\search_service.py`
- Create: `jarvis-server\tests\test_search_service.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing search-coverage tests**

```python
from pathlib import Path

from app.services.search_service import SEARCH_RESULT_LIMIT, SearchService


def test_search_scans_supported_text_extensions(tmp_path) -> None:
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    (knowledge_root / "notes.md").write_text("Jarvis markdown", encoding="utf-8")
    (knowledge_root / "notes.txt").write_text("Jarvis text", encoding="utf-8")
    (knowledge_root / "agent.py").write_text("print('Jarvis python')", encoding="utf-8")
    (knowledge_root / "config.json").write_text('{"name": "Jarvis"}', encoding="utf-8")
    (knowledge_root / "rules.yaml").write_text("name: Jarvis", encoding="utf-8")
    (knowledge_root / "extra.yml").write_text("name: Jarvis", encoding="utf-8")

    service = SearchService()
    service._get_knowledge_root = lambda: knowledge_root  # type: ignore[method-assign]

    results = service.search("Jarvis", "knowledge")
    titles = {result.title for result in results}

    assert {"notes.md", "notes.txt", "agent.py", "config.json", "rules.yaml", "extra.yml"} <= titles


def test_search_respects_the_central_result_cap(tmp_path) -> None:
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    for index in range(10):
        (knowledge_root / f"note-{index}.md").write_text(f"Jarvis result {index}", encoding="utf-8")

    service = SearchService()
    service._get_knowledge_root = lambda: knowledge_root  # type: ignore[method-assign]

    results = service.search("Jarvis", "knowledge")

    assert len(results) == SEARCH_RESULT_LIMIT
```

- [ ] **Step 2: Run the focused search tests**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_search_service.py -q
```

Expected: FAIL because `SEARCH_RESULT_LIMIT` does not exist and the search service still only scans `*.md`.

- [ ] **Step 3: Centralize supported extensions and the search-result limit**

```python
SUPPORTED_TEXT_EXTENSIONS = {".md", ".txt", ".py", ".json", ".yaml", ".yml"}
SEARCH_RESULT_LIMIT = 8
AUTO_SEARCH_RESULT_LIMIT = 8


class SearchService:
    def search(self, query: str, scope: str) -> list[SearchResult]:
        if scope == "web":
            return self.search_web(query)
        if scope == "auto":
            return self.search_auto(query)

        roots: dict[str, Path] = {
            "local": ROOT_DIR,
            "knowledge": self._get_knowledge_root(),
        }
        root = roots.get(scope, ROOT_DIR)
        if not root.exists():
            return []

        results: list[SearchResult] = []
        lowered_query = query.lower()
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if lowered_query not in text.lower() and lowered_query not in path.name.lower():
                continue
            first_match = next(
                (line.strip() for line in text.splitlines() if lowered_query in line.lower()),
                path.name,
            )
            results.append(
                SearchResult(
                    scope=scope,
                    path=str(path),
                    title=path.name,
                    snippet=first_match[:180],
                )
            )
            if len(results) >= SEARCH_RESULT_LIMIT:
                break
        return results

    def search_auto(self, query: str) -> list[SearchResult]:
        combined = [*self.search(query, "knowledge"), *self.search(query, "local")]
        if combined:
            return combined[:AUTO_SEARCH_RESULT_LIMIT]
        return self.search_web(query)
```

- [ ] **Step 4: Update the README while the behavior is fresh**

```md
## 运行时说明

- 如果 `JARVIS_SERVER_PORT` 已被旧的 Jarvis 实例占用，`npm run dev:server` 会直接报错并阻止启动，避免桌面壳误连到旧后端。
- `/api/summary` 在模型认证失败时会返回结构化 `502`，在上游超时或暂时不可用时会返回结构化 `503`。
- 知识库搜索当前支持：`.md`、`.txt`、`.py`、`.json`、`.yaml`、`.yml`。
```

- [ ] **Step 5: Run the search tests and the documentation-adjacent regressions**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_search_service.py tests\test_assistant_api.py -q

Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run src\app\api\assistant-client.test.ts src\features\console\MainConsole.test.tsx

Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
npm run test:electron
```

Expected:

- `pytest` reports the new search tests and assistant API regressions passing
- `vitest` reports the structured summary UI tests passing
- `npm run test:electron` still passes, proving the startup path is still wired correctly

- [ ] **Step 6: Run the final full verification**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest -q

Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run
npm run build

Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
npm run test:electron
npm run build:electron
```

Expected: all existing backend, frontend, and Electron suites remain green after the stability pass.

- [ ] **Step 7: Commit the search + docs + final verification change**

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release'
git add -- jarvis-server/app/services/search_service.py jarvis-server/tests/test_search_service.py README.md
git commit -m "feat: expand knowledge search coverage" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```
