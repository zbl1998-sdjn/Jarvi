# Aliyun Speech + Console Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Jarvis 的语音主链路从 Azure Speech 切到阿里云 DashScope，并把主控台改成默认双侧栏收起的更强 Jarvis 控制台视觉版。

**Architecture:** 后端保持 `SpeechService -> Kimi -> realtime router` 主流程不变，只替换 `ASR/TTS` 实现、配置字段和健康检查逻辑。前端保持主控台单页架构，但改成“主区聚焦 + 覆盖式抽屉 + HUD 风格样式”，把次级信息按需展开而不是长期摊开。

**Tech Stack:** FastAPI, SQLAlchemy, httpx, dashscope SDK, React, TypeScript, Vitest, Electron

---

## File Map

- Modify: `D:\Jarvis\jarvis-server\requirements.txt`
  - 添加 DashScope SDK，移除 Azure Speech 主路径依赖。
- Modify: `D:\Jarvis\jarvis-server\app\config.py`
  - 把语音配置字段从 Azure 改为 Aliyun DashScope。
- Modify: `D:\Jarvis\jarvis-server\app\services\asr_service.py`
  - 用 `AliyunAsrService` 替换 Azure 识别实现。
- Modify: `D:\Jarvis\jarvis-server\app\services\tts_service.py`
  - 用 `AliyunTtsService` 替换 Azure 合成实现。
- Modify: `D:\Jarvis\jarvis-server\app\services\speech_service.py`
  - 接入新的阿里云 ASR/TTS 类。
- Modify: `D:\Jarvis\jarvis-server\app\services\runtime_config_service.py`
  - 把运行时语音配置结构改成阿里云字段。
- Modify: `D:\Jarvis\jarvis-server\app\routers\health.py`
  - `speech` 依赖状态按阿里云字段判断。
- Test: `D:\Jarvis\jarvis-server\tests\test_health.py`
  - 验证设置项与健康检查。
- Test: `D:\Jarvis\jarvis-server\tests\test_assistant_api.py`
  - 验证 runtime config 的语音字段改成阿里云。
- Create: `D:\Jarvis\jarvis-server\tests\test_speech_service.py`
  - 验证阿里云 ASR/TTS 调用与错误语义。
- Modify: `D:\Jarvis\jarvis-ui\src\app\api\assistant-client.ts`
  - 更新 `RuntimeSpeechConfig` 类型。
- Modify: `D:\Jarvis\jarvis-ui\src\features\config\RuntimeConfigPanel.tsx`
  - 把语音配置区改成 DashScope Key / ASR 模型 / TTS 模型 / 音色。
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`
  - 新增左右抽屉开关状态，默认收起。
- Create: `D:\Jarvis\jarvis-ui\src\features\layout\OverlayDrawer.tsx`
  - 统一覆盖式抽屉容器。
- Modify: `D:\Jarvis\jarvis-ui\src\features\panels\LeftDrawer.tsx`
  - 适配覆盖式抽屉承载。
- Modify: `D:\Jarvis\jarvis-ui\src\features\panels\RightDrawer.tsx`
  - 适配覆盖式抽屉承载。
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\TopStatusBar.tsx`
  - 精简状态展示，补侧栏入口。
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\CommandDock.tsx`
  - 适配新的主区布局。
- Modify: `D:\Jarvis\jarvis-ui\src\styles\app.css`
  - 重做主控台布局、抽屉、视觉层级、HUD 风格。
- Test: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.test.tsx`
  - 验证阿里云配置字段和侧栏默认收起 / 覆盖展开。

### Task 1: Replace speech config fields with Aliyun settings

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\config.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\runtime_config_service.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_health.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_assistant_api.py`

- [ ] **Step 1: Write the failing settings test**

```python
def test_settings_read_aliyun_speech_runtime_config_from_env_file(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "ALIYUN_DASHSCOPE_API_KEY=test-dashscope-key\n"
        "ALIYUN_ASR_MODEL=paraformer-realtime-v2\n"
        "ALIYUN_TTS_MODEL=cosyvoice-v1\n"
        "ALIYUN_TTS_VOICE=longxiaochun\n"
        "ALIYUN_SPEECH_LANGUAGE=zh-CN\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("ALIYUN_DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ALIYUN_ASR_MODEL", raising=False)
    monkeypatch.delenv("ALIYUN_TTS_MODEL", raising=False)
    monkeypatch.delenv("ALIYUN_TTS_VOICE", raising=False)
    monkeypatch.delenv("ALIYUN_SPEECH_LANGUAGE", raising=False)

    settings = Settings(_env_file=env_path)

    assert settings.aliyun_dashscope_api_key == "test-dashscope-key"
    assert settings.aliyun_asr_model == "paraformer-realtime-v2"
    assert settings.aliyun_tts_model == "cosyvoice-v1"
    assert settings.aliyun_tts_voice == "longxiaochun"
    assert settings.aliyun_speech_language == "zh-CN"
```

- [ ] **Step 2: Write the failing runtime-config test**

```python
def test_runtime_config_uses_aliyun_speech_fields(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    client = TestClient(create_app())
    payload = {
        "database_url": "sqlite+pysqlite:///runtime-config.db",
        "providers": [],
        "active_provider_id": "default-provider",
        "speech": {
            "api_key": "dashscope-key",
            "asr_model": "paraformer-realtime-v2",
            "tts_model": "cosyvoice-v1",
            "voice_name": "longxiaochun",
            "language": "zh-CN",
        },
    }

    save_response = client.post("/api/runtime-config", json=payload)
    assert save_response.status_code == 200
    assert save_response.json()["speech"]["api_key"] == "dashscope-key"
    assert save_response.json()["speech"]["tts_model"] == "cosyvoice-v1"
```

- [ ] **Step 3: Run tests to verify both fail**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_health.py -k aliyun -q
python -m pytest tests\test_assistant_api.py -k aliyun -q
```

Expected:

- `AttributeError` 或断言失败，提示 `Settings` / `RuntimeConfig` 还没有阿里云字段。

- [ ] **Step 4: Write the minimal settings implementation**

```python
class Settings(BaseSettings):
    aliyun_dashscope_api_key: str = Field(default="", validation_alias="ALIYUN_DASHSCOPE_API_KEY")
    aliyun_asr_model: str = Field(default="paraformer-realtime-v2", validation_alias="ALIYUN_ASR_MODEL")
    aliyun_tts_model: str = Field(default="cosyvoice-v1", validation_alias="ALIYUN_TTS_MODEL")
    aliyun_tts_voice: str = Field(default="longxiaochun", validation_alias="ALIYUN_TTS_VOICE")
    aliyun_speech_language: str = Field(default="zh-CN", validation_alias="ALIYUN_SPEECH_LANGUAGE")
```

```python
@dataclass(frozen=True)
class SpeechConfig:
    api_key: str
    asr_model: str
    tts_model: str
    voice_name: str
    language: str

def check_speech_configuration(speech: SpeechConfig) -> str:
    required = [
        speech.api_key.strip(),
        speech.asr_model.strip(),
        speech.tts_model.strip(),
        speech.voice_name.strip(),
    ]
    return "configured" if all(required) else "missing"
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_health.py -k aliyun -q
python -m pytest tests\test_assistant_api.py -k aliyun -q
```

Expected:

- 两组测试 PASS。

- [ ] **Step 6: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add jarvis-server\app\config.py jarvis-server\app\services\runtime_config_service.py jarvis-server\tests\test_health.py jarvis-server\tests\test_assistant_api.py
git commit -m "feat: switch speech config to aliyun fields"
```

### Task 2: Replace Azure speech services with DashScope implementations

**Files:**
- Modify: `D:\Jarvis\jarvis-server\requirements.txt`
- Modify: `D:\Jarvis\jarvis-server\app\services\asr_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\tts_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\speech_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_speech_service.py`

- [ ] **Step 1: Write the failing ASR/TTS tests**

```python
def test_aliyun_asr_service_uses_dashscope_sdk(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeAudioASR:
        @staticmethod
        def recognize(*, file: str, model: str):
            captured["file"] = file
            captured["model"] = model
            return {"output": {"text": "open lesson"}}

    monkeypatch.setattr("app.services.asr_service.AudioASR", FakeAudioASR)
    monkeypatch.setattr("app.services.asr_service.get_settings", lambda: SimpleNamespace(
        aliyun_dashscope_api_key="dashscope-key",
        aliyun_asr_model="paraformer-realtime-v2",
        aliyun_speech_language="zh-CN",
    ))

    result = AliyunAsrService().transcribe_audio(b"\x01\x02", 16000)

    assert result == "open lesson"
    assert captured["model"] == "paraformer-realtime-v2"
```

```python
def test_aliyun_tts_service_returns_mp3_bytes(monkeypatch) -> None:
    class FakeTextToSpeech:
        @staticmethod
        def tts(*, text: str, model: str, voice: str):
            return {"audio": b"fake-mp3"}

    monkeypatch.setattr("app.services.tts_service.TextToSpeech", FakeTextToSpeech)
    monkeypatch.setattr("app.services.tts_service.get_settings", lambda: SimpleNamespace(
        aliyun_dashscope_api_key="dashscope-key",
        aliyun_tts_model="cosyvoice-v1",
        aliyun_tts_voice="longxiaochun",
    ))

    audio, mime_type = AliyunTtsService().synthesize_text("你好")

    assert audio == b"fake-mp3"
    assert mime_type == "audio/mpeg"
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_speech_service.py -q
```

Expected:

- `ImportError`、`NameError` 或断言失败，提示阿里云服务类还不存在。

- [ ] **Step 3: Add DashScope dependency**

```text
fastapi==0.116.1
uvicorn[standard]==0.35.0
pydantic-settings==2.11.0
sqlalchemy==2.0.43
psycopg[binary]==3.2.10
pytest==8.4.2
httpx==0.28.1
dashscope==1.20.14
```

- [ ] **Step 4: Write the minimal ASR/TTS implementation**

```python
class AliyunAsrService:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.aliyun_dashscope_api_key
        self.model = settings.aliyun_asr_model

    def transcribe_audio(self, audio_bytes: bytes, sample_rate_hz: int) -> str:
        if not self.api_key:
            raise RuntimeError("Aliyun DashScope ASR is not configured.")

        dashscope.api_key = self.api_key
        with NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        try:
            result = AudioASR.recognize(file=temp_path, model=self.model)
        finally:
            Path(temp_path).unlink(missing_ok=True)

        text = result.get("output", {}).get("text", "").strip()
        if not text:
            raise RuntimeError("Aliyun DashScope ASR returned no text.")
        return text
```

```python
class AliyunTtsService:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.aliyun_dashscope_api_key
        self.model = settings.aliyun_tts_model
        self.voice_name = settings.aliyun_tts_voice

    def synthesize_text(self, text: str, voice_name: str | None = None) -> tuple[bytes, str]:
        if not self.api_key:
            raise RuntimeError("Aliyun DashScope TTS is not configured.")

        dashscope.api_key = self.api_key
        result = TextToSpeech.tts(
            text=text,
            model=self.model,
            voice=voice_name or self.voice_name,
        )
        audio = result.get("audio") or result.get("output", {}).get("audio")
        if not audio:
            raise RuntimeError("Aliyun DashScope TTS returned no audio.")
        return audio, "audio/mpeg"
```

```python
from app.services.asr_service import AliyunAsrService
from app.services.tts_service import AliyunTtsService

self.asr_service = AliyunAsrService()
self.tts_service = AliyunTtsService()
```

- [ ] **Step 5: Run the speech tests and realtime regression**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_speech_service.py tests\test_realtime_ws.py -q
```

Expected:

- 新增语音服务测试 PASS。
- realtime websocket 既有测试继续 PASS。

- [ ] **Step 6: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add jarvis-server\requirements.txt jarvis-server\app\services\asr_service.py jarvis-server\app\services\tts_service.py jarvis-server\app\services\speech_service.py jarvis-server\tests\test_speech_service.py
git commit -m "feat: replace azure speech services with aliyun dashscope"
```

### Task 3: Rewire health checks and runtime-config API to Aliyun semantics

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\routers\health.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\assistant.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_assistant_api.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_health.py`

- [ ] **Step 1: Write the failing health assertion**

```python
def test_health_reports_aliyun_speech_dependency_shape() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["dependencies"]["speech"] in {"missing", "configured"}
```

```python
payload["speech"] = {
    "api_key": "dashscope-key",
    "asr_model": "paraformer-realtime-v2",
    "tts_model": "cosyvoice-v1",
    "voice_name": "longxiaochun",
    "language": "zh-CN",
}
```

- [ ] **Step 2: Run tests to verify they fail on old field names**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_assistant_api.py -k runtime_config -q
python -m pytest tests\test_health.py -k speech -q
```

Expected:

- 断言仍指向 `key/region` 或返回旧 Azure 语义。

- [ ] **Step 3: Write the minimal router changes**

```python
@router.post("/api/runtime-config/check")
async def check_runtime_config_endpoint() -> dict[str, object]:
    runtime_config = get_runtime_config()
    return {
        "active_provider_id": runtime_config.active_provider_id,
        "dependencies": {
            "database": check_database_connection(runtime_config.database_url),
            "llm": check_llm_connection(get_active_provider()),
            "speech": check_speech_configuration(runtime_config.speech),
            "config": "ready",
        },
    }
```

```python
speech_status = check_speech_configuration(get_speech_config())
```

- [ ] **Step 4: Run the server regression set**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_health.py tests\test_assistant_api.py -q
```

Expected:

- `speech` 相关断言全部 PASS。

- [ ] **Step 5: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add jarvis-server\app\routers\health.py jarvis-server\app\routers\assistant.py jarvis-server\tests\test_assistant_api.py jarvis-server\tests\test_health.py
git commit -m "feat: align health and runtime config with aliyun speech"
```

### Task 4: Update the config center to Aliyun speech fields

**Files:**
- Modify: `D:\Jarvis\jarvis-ui\src\app\api\assistant-client.ts`
- Modify: `D:\Jarvis\jarvis-ui\src\features\config\RuntimeConfigPanel.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.test.tsx`

- [ ] **Step 1: Write the failing UI config test**

```tsx
it('renders aliyun speech config labels instead of azure fields', async () => {
  render(<MainConsole />);

  expect(await screen.findByText('DashScope API Key')).toBeInTheDocument();
  expect(await screen.findByText('ASR 模型')).toBeInTheDocument();
  expect(await screen.findByText('TTS 模型')).toBeInTheDocument();
  expect(await screen.findByText('音色')).toBeInTheDocument();
  expect(screen.queryByText('Azure Key')).not.toBeInTheDocument();
  expect(screen.queryByText('Region')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Update the mock payload so the test fails for the right reason**

```tsx
speech: {
  api_key: 'dashscope-key',
  asr_model: 'paraformer-realtime-v2',
  tts_model: 'cosyvoice-v1',
  voice_name: 'longxiaochun',
  language: 'zh-CN',
},
```

- [ ] **Step 3: Run the targeted test to verify failure**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\features\console\MainConsole.test.tsx -t "renders aliyun speech config labels instead of azure fields" --maxWorkers 1 --minWorkers 1
```

Expected:

- 失败在旧文案 `Azure Key` / `Region` 仍存在。

- [ ] **Step 4: Write the minimal type and panel changes**

```ts
export interface RuntimeSpeechConfig {
  api_key: string;
  asr_model: string;
  tts_model: string;
  voice_name: string;
  language: string;
}
```

```tsx
<label className="settings-field">
  <span>DashScope API Key</span>
  <input
    className="settings-input"
    onChange={(event) =>
      setDraft((current) => ({
        ...current,
        speech: { ...current.speech, api_key: event.target.value },
      }))
    }
    value={draft.speech.api_key}
  />
</label>
<label className="settings-field">
  <span>ASR 模型</span>
  <input
    className="settings-input"
    onChange={(event) =>
      setDraft((current) => ({
        ...current,
        speech: { ...current.speech, asr_model: event.target.value },
      }))
    }
    value={draft.speech.asr_model}
  />
</label>
```

- [ ] **Step 5: Run the UI regression**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\features\console\MainConsole.test.tsx -t "renders aliyun speech config labels instead of azure fields" --maxWorkers 1 --minWorkers 1
npx vitest run src\app\vite-base.test.ts src\app\api\chat-client.test.ts
```

Expected:

- 配置中心断言 PASS。
- 稳定 UI 基线测试继续 PASS。

- [ ] **Step 6: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add jarvis-ui\src\app\api\assistant-client.ts jarvis-ui\src\features\config\RuntimeConfigPanel.tsx jarvis-ui\src\features\console\MainConsole.test.tsx
git commit -m "feat: update config center for aliyun speech"
```

### Task 5: Add overlay drawers and collapse both sidebars by default

**Files:**
- Create: `D:\Jarvis\jarvis-ui\src\features\layout\OverlayDrawer.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\panels\LeftDrawer.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\panels\RightDrawer.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\TopStatusBar.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\CommandDock.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.test.tsx`

- [ ] **Step 1: Write the failing drawer behavior test**

```tsx
it('keeps both sidebars collapsed by default and opens overlay drawers on demand', async () => {
  render(<MainConsole />);

  expect(screen.queryByText('Pending task: Review M6 timeline')).not.toBeInTheDocument();
  expect(screen.queryByText('服务与模型配置')).not.toBeInTheDocument();

  fireEvent.click(screen.getByLabelText('打开左侧栏'));
  expect(await screen.findByText('Pending task: Review M6 timeline')).toBeInTheDocument();

  fireEvent.click(screen.getByLabelText('打开右侧栏'));
  expect(await screen.findByText('服务与模型配置')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\features\console\MainConsole.test.tsx -t "keeps both sidebars collapsed by default and opens overlay drawers on demand" --maxWorkers 1 --minWorkers 1
```

Expected:

- 失败，因为当前页面默认直接渲染两侧内容。

- [ ] **Step 3: Add the overlay drawer component**

```tsx
interface OverlayDrawerProps {
  open: boolean;
  side: 'left' | 'right';
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function OverlayDrawer({ open, side, title, onClose, children }: OverlayDrawerProps) {
  if (!open) return null;

  return (
    <div className="overlay-drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        aria-label={title}
        className={`overlay-drawer overlay-drawer--${side}`}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </aside>
    </div>
  );
}
```

- [ ] **Step 4: Wire MainConsole to use collapsed-by-default drawers**

```tsx
const [leftDrawerOpen, setLeftDrawerOpen] = useState(false);
const [rightDrawerOpen, setRightDrawerOpen] = useState(false);

<TopStatusBar
  ...
  onOpenLeftDrawer={() => setLeftDrawerOpen(true)}
  onOpenRightDrawer={() => setRightDrawerOpen(true)}
/>

<OverlayDrawer open={leftDrawerOpen} side="left" title="左侧栏" onClose={() => setLeftDrawerOpen(false)}>
  <LeftDrawer ... />
</OverlayDrawer>

<OverlayDrawer open={rightDrawerOpen} side="right" title="右侧栏" onClose={() => setRightDrawerOpen(false)}>
  <RightDrawer ... />
</OverlayDrawer>
```

- [ ] **Step 5: Update the top bar to expose drawer toggles**

```tsx
<button aria-label="打开左侧栏" className="status-icon-button" onClick={onOpenLeftDrawer} type="button">
  菜单
</button>
<button aria-label="打开右侧栏" className="status-icon-button" onClick={onOpenRightDrawer} type="button">
  面板
</button>
```

- [ ] **Step 6: Run the targeted UI tests**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\features\console\MainConsole.test.tsx -t "keeps both sidebars collapsed by default and opens overlay drawers on demand" --maxWorkers 1 --minWorkers 1
npx vitest run src\features\console\MainConsole.test.tsx -t "renders aliyun speech config labels instead of azure fields" --maxWorkers 1 --minWorkers 1
```

Expected:

- 抽屉默认收起测试 PASS。
- 语音配置文案测试继续 PASS。

- [ ] **Step 7: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add jarvis-ui\src\features\layout\OverlayDrawer.tsx jarvis-ui\src\features\console\MainConsole.tsx jarvis-ui\src\features\panels\LeftDrawer.tsx jarvis-ui\src\features\panels\RightDrawer.tsx jarvis-ui\src\features\console\TopStatusBar.tsx jarvis-ui\src\features\console\CommandDock.tsx jarvis-ui\src\features\console\MainConsole.test.tsx
git commit -m "feat: collapse sidebars into overlay drawers"
```

### Task 6: Redesign the console styling so the default screen feels focused

**Files:**
- Modify: `D:\Jarvis\jarvis-ui\src\styles\app.css`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\TopStatusBar.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\CommandDock.tsx`
- Test: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.test.tsx`

- [ ] **Step 1: Write the failing structure assertion**

```tsx
it('renders a focused console shell with compact status and command dock visible by default', async () => {
  render(<MainConsole />);

  expect(await screen.findByText('Jarvis')).toBeInTheDocument();
  expect(await screen.findByText('发送')).toBeInTheDocument();
  expect(await screen.findByText('启动语音')).toBeInTheDocument();
  expect(screen.queryByText('服务与模型配置')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\features\console\MainConsole.test.tsx -t "renders a focused console shell with compact status and command dock visible by default" --maxWorkers 1 --minWorkers 1
```

Expected:

- 失败，因为当前主界面默认可见模块过多。

- [ ] **Step 3: Write the minimal layout and style changes**

```tsx
<main className="console-shell">
  <TopStatusBar ... />
  <section className="console-hero">
    <VoiceOrb state={voiceState} />
    <div className="console-reply-card">{reply || 'Jarvis 已待命，随时开始。'}</div>
  </section>
  <CommandDock ... />
</main>
```

```css
.console-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(0, 229, 255, 0.18), transparent 35%),
    linear-gradient(180deg, #07111b 0%, #02070d 100%);
  color: #e6f7ff;
}

.overlay-drawer {
  position: fixed;
  top: 0;
  bottom: 0;
  width: min(420px, 92vw);
  background: rgba(6, 16, 28, 0.96);
  box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.12), 0 16px 48px rgba(0, 0, 0, 0.45);
}

.overlay-drawer--left { left: 0; }
.overlay-drawer--right { right: 0; }

.console-hero {
  max-width: 980px;
  margin: 0 auto;
  padding: 48px 24px 160px;
}
```

- [ ] **Step 4: Run the frontend build and stable tests**

Run:

```powershell
Set-Location 'D:\Jarvis'
npm run build:ui
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\app\vite-base.test.ts src\app\api\chat-client.test.ts
```

Expected:

- UI build 成功。
- 稳定前端测试继续 PASS。

- [ ] **Step 5: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add jarvis-ui\src\styles\app.css jarvis-ui\src\features\console\MainConsole.tsx jarvis-ui\src\features\console\TopStatusBar.tsx jarvis-ui\src\features\console\CommandDock.tsx jarvis-ui\src\features\console\MainConsole.test.tsx
git commit -m "feat: refresh console shell styling"
```

### Task 7: Run end-to-end regression for speech + desktop shell

**Files:**
- Modify: `D:\Jarvis\.env.example`
- Modify: `D:\Jarvis\README.md`
- Test: `D:\Jarvis\jarvis-server\tests\test_health.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_assistant_api.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_realtime_ws.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_speech_service.py`
- Test: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.test.tsx`

- [ ] **Step 1: Update the environment example**

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/jarvis
ALIYUN_DASHSCOPE_API_KEY=your-dashscope-api-key
ALIYUN_ASR_MODEL=paraformer-realtime-v2
ALIYUN_TTS_MODEL=cosyvoice-v1
ALIYUN_TTS_VOICE=longxiaochun
ALIYUN_SPEECH_LANGUAGE=zh-CN
```

- [ ] **Step 2: Update README smoke steps**

```md
1. 在配置中心填入 DashScope API Key。
2. 确认左右侧栏默认收起，通过顶部入口展开。
3. 点击“启动语音”，完成一次录音 -> 转写 -> 回复 -> 播报。
```

- [ ] **Step 3: Run the full backend suite**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest -q
```

Expected:

- 后端全量测试 PASS。

- [ ] **Step 4: Run frontend and Electron verification**

Run:

```powershell
Set-Location 'D:\Jarvis'
npm run test:electron
npm run build:ui
npm run build:electron
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src\features\console\MainConsole.test.tsx -t "keeps both sidebars collapsed by default and opens overlay drawers on demand" --maxWorkers 1 --minWorkers 1
npx vitest run src\features\console\MainConsole.test.tsx -t "renders aliyun speech config labels instead of azure fields" --maxWorkers 1 --minWorkers 1
```

Expected:

- Electron tests PASS。
- UI / Electron 构建 PASS。
- 两条主控台关键回归用例 PASS。

- [ ] **Step 5: Commit**

```powershell
Set-Location 'D:\Jarvis'
git add .env.example README.md
git commit -m "docs: document aliyun speech and console refresh smoke"
```
