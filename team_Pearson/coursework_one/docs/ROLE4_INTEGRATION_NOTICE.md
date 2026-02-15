# CW1 Integration Notice / 对接通知 (Role 4 Integrator)

Audience / 适用对象: Roles 3, 5, 6, 7, 8  
Goal / 目标: Parallel development with low conflict and fast merge to team branch / 并行开发、低冲突、快速合流

## 0) First-time setup / 首次同步（先做这个）
If you do not have the repo locally yet / 如果你本地还没有仓库:

```bash
git clone https://github.com/celiahkkd-byte/ift_coursework_2025.git
cd ift_coursework_2025
git checkout feature/coursework_one_Team_04_Pearson
git pull origin feature/coursework_one_Team_04_Pearson
```

If you already cloned before / 如果你之前已经克隆过:

```bash
cd ift_coursework_2025
git checkout feature/coursework_one_Team_04_Pearson
git pull origin feature/coursework_one_Team_04_Pearson
```

Important / 重点说明:
- "Go to project directory" means your own local `ift_coursework_2025`, not someone else's computer.
- “进入项目目录”指的是你自己电脑上的 `ift_coursework_2025`，不是别人电脑里的目录。
- Everyone syncs from the same team branch above, then creates their own role branch.
- 每个人都先同步同一个团队分支，再创建自己的角色分支开发。

## 1) Branch workflow / 分支流程（必须）
Run from repo root `ift_coursework_2025/`:

```bash
git checkout feature/coursework_one_Team_04_Pearson
git pull origin feature/coursework_one_Team_04_Pearson
git checkout -b feature/cw1-role6-source-a
```

Branch naming / 分支命名:
- `feature/cw1-role<id>-<module>`
- examples: `feature/cw1-role5-universe-db`, `feature/cw1-role8-normalize-quality`

After coding / 开发完成后:

```bash
git add <your files>
git commit -m "roleX: <change summary>"
git push -u origin <your branch>
```

Open PR to / 发 PR 到:
- `feature/coursework_one_Team_04_Pearson`
- Do NOT open PR to `main`.
- 不要把 PR 的目标分支选成 `main`。

## 2) File ownership / 文件归属（只改自己的）
- Role 5: `modules/db/*`
- Role 6: `modules/input/extract_source_a.py`
- Role 7: `modules/input/extract_source_b.py`
- Role 8: `modules/output/normalize.py` and `modules/output/quality.py`
- Role 3: `modules/output/load.py`
- Role 4 (Integrator): `Main.py` and integration flow

### 2.1 Output/DB infra ownership / Output与数据库基础设施分工补充
- Role 3 (primary): Output persistence implementation
  - `team_Pearson/coursework_one/modules/output/load.py`
  - `sql/init.sql` (upsert rules, indexes, constraints; if this file is used in your repo structure)
- Role 5 (support): Validate SQL compatibility with existing DB schema and company universe tables
- Role 4 (primary for integration safety): Global runtime/config wiring

Do not modify others' modules or `Main.py` without agreement.  
未经沟通，不要改别人模块和 `Main.py`。

## 3) Fixed interface contracts / 固定接口契约（函数名不可改）
1. `modules.db.get_company_universe(company_limit: int) -> list[str]`
2. `modules.input.extract_source_a(company_ids, run_date, backfill_years, frequency) -> list[dict]`
3. `modules.input.extract_source_b(company_ids, run_date, backfill_years, frequency) -> list[dict]`
4. `modules.output.normalize_records(records) -> list[dict]`
5. `modules.output.run_quality_checks(records) -> dict`
6. `modules.output.load_curated(records, dry_run: bool) -> int`

## 4) Minimum upstream schema / 上游最小字段要求（Role 6/7）
Each record returned by `extract_source_a/b` must include / 每条记录至少包含:
- `company_id`
- `observation_date`
- `factor_name`
- `factor_value`
- `source`
- `metric_frequency` (`daily|monthly|quarterly|annual`)

Recommended for staleness control / 为了时效性控制，强烈建议增加:
- `source_report_date`

## 4.1) Mixed-frequency policy / 混合频率处理规则（必须遵守）
- `--frequency` is pipeline run frequency, not the natural frequency of each metric.
- `--frequency` 是流水线运行频率，不等于每个因子的天然发布频率。
- Each row must carry its own `metric_frequency`.
- 每条记录必须标注自己的 `metric_frequency`。
- Low-frequency factors (quarterly/annual) must use step-forward fill with staleness limits; do not fake daily "new" fundamentals.
- 低频因子（季/年）在高频运行中必须使用前值延续并遵守过期阈值，不能伪造“每日新财报”。
- High-frequency factors (daily) may be aggregated to monthly for portfolio rebalance use.
- 高频因子（日报）可在组合调仓前聚合到月频使用。

Current data requirements reference / 当前需求对应频率示例:
- `News Sentiment`: daily
- `Dividend Yield`, `P/B`: monthly
- `Debt/Equity`: quarterly
- `EBITDA Margin`: quarterly/annual

## 5) Integrator flow / 总装流程（已接入）
- `get_company_universe`
- `extract_source_a` + `extract_source_b`
- `normalize_records`
- `run_quality_checks`
- `load_curated`
- run log

## 5.1) Docker requirements & what we need to build / Docker 要求与是否需要自己构建

### English
- **Do we need to write our own Dockerfile / rebuild everything?**
  - **No.** For CW1, we primarily **use the provided `docker-compose.yml` in the repo root** to start the infrastructure (PostgreSQL / MongoDB / MinIO, etc.).
  - Most services in the compose file use `image:` and will be pulled automatically.
  - If the compose file contains a special seeding service with `build:` (e.g., a database seeder), **Docker will build it automatically when you run `docker compose up --build`**. We do **not** need to redesign containers.

- **Hard rule**: run Docker only from the **repo root** (`ift_coursework_2025/`) where `docker-compose.yml` lives.

- **When do we change `docker-compose.yml`?**
  - Only if we **explicitly add new infrastructure components** (e.g., Airflow/Kafka). If we add anything, it must be **containerized and integrated via `docker-compose.yml`**.

- **Connection details** (host/port/user/password) must follow what is defined in `docker-compose.yml`.
  - We will consolidate these into our project config later (Role 4 will publish the final `.env`/config convention).

### 中文
- **我们需要自己写 Dockerfile / 重建整个环境吗？**
  - **不需要。** CW1 主要是**使用老师提供的仓库根目录 `docker-compose.yml`** 启动基础设施（PostgreSQL / MongoDB / MinIO 等）。
  - compose 里大多数服务是 `image:`，会自动拉取镜像。
  - 如果 compose 里有带 `build:` 的特殊服务（例如初始化/灌库 seeder），执行 `docker compose up --build` 时 **Docker 会自动构建**。我们不需要重新设计容器。

- **硬规则**：只能在**仓库根目录**（`ift_coursework_2025/`，有 `docker-compose.yml` 那层）运行 Docker。

- **什么时候需要改 `docker-compose.yml`？**
  - 仅当我们**明确新增基础设施组件**（例如 Airflow/Kafka）。新增任何组件都必须**Docker 容器化**并通过 `docker-compose.yml` 集成。

- **连接信息**（host/port/user/password）必须以 `docker-compose.yml` 为准。

  - 我们之后会把这些整理进项目配置（4号会统一发布 `.env`/配置规范）。

## 5.2) Runtime config (.env) & connection conventions / 运行配置（.env）与连接规范

### English
**Where is the config template?**
- Template file: `team_Pearson/coursework_one/.env.example`
- Create your local `.env` from the template (do NOT commit `.env`):
  ```bash
  cd team_Pearson/coursework_one
  cp .env.example .env
  ```

**Source of truth**
- All host/port/user/password values must match the repo-root `docker-compose.yml`.
- `.env.example` mirrors the current compose defaults for consistent local development.

**Environment variables (convention)**
- PostgreSQL:
  - `POSTGRES_HOST=localhost`
  - `POSTGRES_PORT=5439`
  - `POSTGRES_DB=postgres`
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=postgres`
- MongoDB:
  - `MONGO_HOST=localhost`
  - `MONGO_PORT=27019`
  - `MONGO_DB=admin`
- MinIO:
  - `MINIO_ENDPOINT=http://localhost:9000`
  - `MINIO_ACCESS_KEY=ift_bigdata`
  - `MINIO_SECRET_KEY=minio_password`
  - `MINIO_BUCKET=csreport`

**Bucket / storage naming**
- Current MinIO bucket: `csreport`.
- Do not invent new bucket names or folder conventions without Role 3 + Role 4 alignment.
- Raw/curated pathing will be finalized after Role 3 confirms the storage design.

### 中文
**配置模板在哪里？**
- 模板文件：`team_Pearson/coursework_one/.env.example`
- 从模板生成你的本地 `.env`（不要提交 `.env`）：
  ```bash
  cd team_Pearson/coursework_one
  cp .env.example .env
  ```

**以谁为准？**
- 所有 host/port/user/password 必须以仓库根目录的 `docker-compose.yml` 为准。
- `.env.example` 只是把当前 compose 的默认值镜像出来，便于大家统一本地开发环境。

**环境变量命名（统一约定）**
- PostgreSQL：
  - `POSTGRES_HOST=localhost`
  - `POSTGRES_PORT=5439`
  - `POSTGRES_DB=postgres`
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=postgres`
- MongoDB：
  - `MONGO_HOST=localhost`
  - `MONGO_PORT=27019`
  - `MONGO_DB=admin`
- MinIO：
  - `MINIO_ENDPOINT=http://localhost:9000`
  - `MINIO_ACCESS_KEY=ift_bigdata`
  - `MINIO_SECRET_KEY=minio_password`
  - `MINIO_BUCKET=csreport`

**Bucket / 存储命名约定**
- 当前 MinIO 统一 bucket：`csreport`。
- 没有 3号 + 4号一致前，不要私自新增 bucket 名称或自定义路径规范。
- raw/curated 的路径规则会在 3号确认存储设计后最终定稿。

## 6) Local validation before PR / PR 前本地验收
Hard rule from coursework instructions / 老师要求的硬规则:
- Run `docker compose ...` only in repo root `ift_coursework_2025/`.
- Never run `docker compose` inside `team_Pearson/coursework_one/`.

Start infra from repo root first:

```bash
cd ift_coursework_2025
docker compose up -d postgres_db mongo_db miniocw
```

Then run app/tests in `team_Pearson/coursework_one/`:

```bash
poetry install
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
poetry run python Main.py --run-date 2026-02-01 --frequency monthly --dry-run
poetry run python Main.py --run-date 2026-12-31 --frequency annual --dry-run
poetry run pytest tests -q
```

One-command-sequence summary / 一条流程总结:
```bash
cd ift_coursework_2025
docker compose up -d postgres_db mongo_db miniocw
cd team_Pearson/coursework_one
poetry install
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
poetry run pytest tests -q
```

Pass criteria / 通过标准:
- Exit code is `0`
- Output contains `run_log_written_to`
- Smoke test passes

## 6.1) Role 8 Testing Scope / 8号测试职责范围
Role 8 is the primary owner of data validation tests and should ensure all testing layers are covered.
8号是数据验收测试主责，需要确保测试分层完整（单元/集成/端到端）。

Required scope / 必做范围:
- Unit tests for output validation logic:
  - `tests/test_normalize_unit.py`
  - `tests/test_quality_unit.py`
- Integration coverage for component interactions:
  - `tests/test_pipeline_integration.py`
- E2E/smoke verification of end-to-end pipeline:
  - `tests/test_e2e.py`
  - `tests/test_smoke.py`

Target checks / 验收要求:
- Use pytest through poetry:
  - `poetry run pytest tests -q`
- Keep coverage above red line:
  - `poetry run pytest tests -q --cov=modules --cov=Main --cov-fail-under=80`

## 7) Commit scope / 提交边界
- Keep all changes inside `team_Pearson/coursework_one/` plus required team-level files.
- Do not commit unrelated folders/artifacts (DB folders, caches, temp files, etc.).
