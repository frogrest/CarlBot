# Local LLM Setup — Managed `llama.cpp` Runtime

CarlBot can run its own local OpenAI-compatible model server (a `llama-server`
process from [llama.cpp](https://github.com/ggml-org/llama.cpp)). When configured,
CarlBot starts and stops the runtime automatically — you do **not** launch Ollama
or any other model server by hand, and **no paid API key is required**.

> **Verification status (honest):** the runtime management, configuration, and
> client wiring are implemented and covered by mocked tests. A **real inference
> smoke test has not been run on this host because no GGUF model is installed
> yet.** Do not treat local inference as verified until you complete
> [Verify it works](#6-verify-it-works). Everything below describes the intended
> configuration; the deterministic (non-LLM) behaviours remain the default and
> keep working with no model.

This stays inside the emulated lab. The runtime binds to `127.0.0.1` only, has no
tools, and cannot grant itself permission to act — the deterministic policy
engine remains the sole authority for simulated actions.

---

## 1. What CarlBot manages for you

- Checks whether the runtime binary and model file are configured.
- Starts the local server on startup (or on retry) and waits for readiness.
- Reuses the same server for the chat assistant and, in the agent service, the
  optional incident reasoner.
- Stops the child process on shutdown.
- Reports truthful states to both the API and the UI: `disabled`,
  `runtime_missing`, `model_not_configured`, `loading`, `ready`, `busy`, `error`.
- Missing files produce actionable instructions instead of a crash.
- Existing non-AI features keep working when the model is unavailable.

CarlBot will **not** silently download model weights, run unverified installers,
or require a separate model server. It *can* download a model, but only when you
explicitly choose one from the built-in catalog in the UI (see §3b) — never on
its own and never from an arbitrary URL.

The `helpdesk` and `agent` services each expose the same endpoints (identical
router, mounted in both so the two runtimes stay consistent):

| Endpoint | Purpose |
|---|---|
| `GET /api/llm/status` | Truthful runtime/model state |
| `POST /api/llm/start` | Retry initialization (idempotent) |
| `GET /api/llm/models` | Catalog + install/selection state + download progress |
| `POST /api/llm/models/{id}/download` | Start downloading a catalog model |
| `POST /api/llm/models/{id}/download/cancel` | Cancel the active download |
| `POST /api/llm/models/{id}/select` | Make an installed model active + reload |
| `DELETE /api/llm/models/{id}` | Delete a downloaded model file |

All of these take a **catalog id**, never a URL or filesystem path. They cannot
run arbitrary commands and can only act on the fixed allow-list.

---

## 2. Prerequisites

- Windows 11 (or any OS) with a working Python 3.13+ environment for local runs,
  or Docker Desktop for the container stack.
- A `llama-server` binary built from llama.cpp for your platform.
- A compatible **GGUF instruct** model file (see §3).

### Getting `llama-server`

Download an official llama.cpp release for your platform (Windows builds are
published on the llama.cpp releases page), or build it from source. Then either:

- put `llama-server` on your `PATH`, **or**
- point `LOCAL_LLM_SERVER_BIN` at the executable's full path.

The binary is a plain executable; CarlBot never builds a shell command from user
input — it passes a validated argument list with `shell=False`.

---

## 3. Getting a model

Obtain the model from the provider's official site/app (for example a Qwen 7B–8B
class instruction-tuned model). Choose a **4-bit quantized GGUF** instruct build
(e.g. `Q4_K_M`) for CPU inference.

- **Do not commit model weights to Git** and do not bundle them in releases.
- You are responsible for the model's license and terms of use.
- Approximate footprint for a 7B–8B 4-bit model: **~4–6 GB on disk** and roughly
  **6–9 GB RAM** while loaded. CPU-only inference is the supported baseline; do
  not assume Intel Iris Xe acceleration.

Set the model file path with `LOCAL_LLM_MODEL_PATH`. No hardcoded personal path
is used anywhere in the source.

### 3b. Choosing and downloading a model from the UI

You do not have to fetch a model by hand. The `◈ CarlBot AI` view has a
**Local AI model** panel that lists a small, curated catalog of compatible
4-bit GGUF instruct models (id, size, RAM guidance, license) and lets you
download one with a single click. Downloads are user-initiated only, stream to
a `.part` file with a live progress bar, are verified to start with the `GGUF`
magic bytes, and are then atomically moved into the local models folder.

- Models are written under `LOCAL_LLM_MODELS_DIR` (default `/app/data/models`,
  i.e. under the mounted `data/` volume). The selected model is recorded in
  `models.json` in that folder, so the choice survives restarts and is shared by
  the helpdesk and agent services when they share the volume.
- The catalog is a fixed allow-list in `services/local_llm/catalog.py`; each
  entry's `download_url` and `size_bytes` were verified against the provider.
  The backend never accepts an arbitrary URL.
- Downloading is a deliberate, explicit action. CarlBot still never starts a
  multi-gigabyte download on its own.
- A catalog model's license and terms are the operator's responsibility; the UI
  shows the license for each entry.

Example catalog entries (sizes are the recorded quantized-file sizes):

| Model | Quant | ~Size | Min RAM | License |
|---|---|---|---|---|
| Qwen2.5 3B Instruct | Q4_K_M | ~1.8 GB | 4 GB | Apache-2.0 |
| Gemma 2 2B IT | Q4_K_M | ~1.6 GB | 4 GB | Gemma Terms of Use |
| Llama 3.2 3B Instruct | Q4_K_M | ~1.9 GB | 4 GB | Llama 3.2 Community License |
| Phi-3.5 Mini Instruct | Q4_K_M | ~2.2 GB | 5 GB | MIT |
| **Qwen2.5 7B Instruct** (recommended) | Q4_K_M | ~4.4 GB | 8 GB | Apache-2.0 |
| Llama 3.1 8B Instruct | Q4_K_M | ~4.6 GB | 8 GB | Llama 3.1 Community License |

After a download completes, press **Use this model** to select it and reload the
runtime (equivalent to `POST /api/llm/models/{id}/select`). The status badge
then reflects the backend's truthful state; it still shows *Runtime missing*
until a `llama-server` binary is installed.

---

## 4. Configuration

All settings are environment variables with safe defaults. Only set what you
need.

| Variable | Default | Purpose |
|---|---|---|
| `LOCAL_LLM_ENABLED` | `1` | Enable/disable the managed runtime (`0` turns it off) |
| `LOCAL_LLM_MODEL_PATH` | *(empty)* | Fallback path to a `.gguf` model file (a UI selection takes precedence) |
| `LOCAL_LLM_SERVER_BIN` | *(auto)* | Path/name of the `llama-server` binary; defaults to searching `PATH` for `llama-server` |
| `LOCAL_LLM_MODELS_DIR` | `/app/data/models` | Folder where downloaded models and the `models.json` registry live |
| `LOCAL_LLM_HOST` | `127.0.0.1` | Bind address (loopback; do not expose publicly) |
| `LOCAL_LLM_PORT` | `8080` | Local server port |
| `LOCAL_LLM_N_CTX` | `4096` | Prompt context size (conservative by default) |
| `LOCAL_LLM_N_THREADS` | `0` (auto) | CPU threads for generation |
| `LOCAL_LLM_MAX_OUTPUT_TOKENS` | `512` | Hard cap on generated tokens per request |
| `LOCAL_LLM_STARTUP_TIMEOUT` | `180` | Seconds to wait for the model to load |
| `LOCAL_LLM_GENERATION_TIMEOUT` | `120` | Seconds allowed per generation |

Invalid values are rejected with a clear message; the service still starts and
reports an `error` state rather than crashing.

### Precedence with an external endpoint

The existing external configuration (`LLM_BASE_URL`, `LLM_MODEL`, and the
environment-only `LLM_API_KEY`) still works and is unchanged.

- If the managed runtime is **enabled and ready**, it is used.
- Otherwise, if `LLM_BASE_URL` and `LLM_MODEL` are set, that endpoint is used.
- Otherwise, CarlBot uses its **deterministic** reasoning (no model).

The `model` field sent to a managed runtime is ignored by `llama-server`; any
non-empty name is accepted.

### Docker

`docker-compose.yml` forwards `LOCAL_LLM_*` to the `helpdesk` and `agent`
services. A container cannot see your host's `llama-server` binary or model file
unless you mount them:

```yaml
# sketch — add to the helpdesk/agent services you intend to use
volumes:
  - /path/to/llamaserver-dir:/opt/llama:ro
  - /path/to/models:/models:ro
environment:
  LOCAL_LLM_SERVER_BIN: /opt/llama/llama-server
  LOCAL_LLM_MODEL_PATH: /models/your-model.gguf
```

CPU-only inference uses the **host's** CPU and RAM; give the container enough
resources. Per the current design, the `helpdesk` and `agent` services each
manage their own runtime instance, so running both with a loaded model uses
memory twice.

---

## 5. Using it

Start CarlBot normally. The helpdesk (chat) and agent services load the model on
startup and report status.

- `GET /api/llm/status` — truthful runtime/model state, plus setup instructions
  when something is missing.
- `POST /api/llm/start` — retry initialization (idempotent, takes no body).

The HTTP status endpoint above is the source of truth, and the CarlBot UI now
mirrors it. In the `◈ CarlBot AI` view (and as a compact badge beside the
ticket-side chat) CarlBot shows the backend-reported state — *Runtime missing*,
*Model not configured*, *Loading model*, *Local model ready*, *Local model busy*,
*Runtime error*, or *Local inference off* — plus whether inference runs locally,
setup instructions when something is missing, and a **Retry initialization**
button. The UI never shows **Ready** until the backend confirms the model
loaded; it only renders what `/api/llm/status` reports.

`/clear` in the chat clears the **conversation only** — it does not delete
tickets, notes, audit records, knowledge documents, or model files.

---

## 6. Verify it works

After installing a model and binary:

1. `GET http://localhost:8000/api/llm/status` (helpdesk) or
   `GET http://localhost:8002/api/llm/status` (agent). Expect `"state": "ready"`
   once loading completes.
2. Ask the chat a question; the reply badge shows `LLM` when the local model
   answered, `DETERMINISTIC` when it fell back.
3. Run the test suite (mocked; no download required):

```bash
python -m compileall services tests
python -m pytest -q
```

An optional real-model smoke test is intentionally not part of the default
suite, so CI never downloads a multi-gigabyte file.

---

## 7. Troubleshooting

| State | Meaning | What to do |
|---|---|---|
| `runtime_missing` | `llama-server` not found | Install the binary or set `LOCAL_LLM_SERVER_BIN` |
| `model_not_configured` | No readable `.gguf` file | Set `LOCAL_LLM_MODEL_PATH` to an existing file |
| `loading` | Model is being loaded | Wait for the startup timeout; large models take a while |
| `error` | Startup failed, timed out, or the process crashed | Check the status detail and the server log output; verify the GGUF variant and available RAM |
| `busy` | A generation is in progress | Only one generation runs at a time; retry shortly |

Common causes: wrong quant/format, insufficient RAM, a port already in use, or a
binary built for a different platform.

---

## 8. Limitations

- CPU-only inference; an 8B 4-bit model will **not** match a frontier cloud
  model in quality or speed.
- No GPU offload is enabled by default (the server is started with
  `-ngl 0`).
- The agent's reasoner and the helpdesk chat each load their own model when both
  are enabled — plan for the memory.
- Local inference is only "offline" once the binary and model file are present
  locally; obtaining them requires network access.
- Do not claim local inference works until the smoke test in §6 has actually
  succeeded on your machine.
- The status/retry **HTTP endpoints and the UI indicator are implemented**; the
  badge reflects the backend state and cannot show *Ready* on its own.
- The two `POST /api/llm/start` routes are unauthenticated (like the rest of
  this local lab API). They are bounded to starting the pre-configured server
  and are not intended to be exposed beyond loopback.
