# CW1 对接通知（Role 4 / Integrator）

适用对象：3号、5号、6号、7号、8号
目标：并行开发、低冲突、可快速合流到团队分支

## 1) 分支规范（每个人必须做）
在仓库根目录 `ift_coursework_2025/` 执行：

```bash
# 先更新团队主分支
git checkout feature/coursework_one_Team_04_Pearson
git pull origin feature/coursework_one_Team_04_Pearson

# 基于团队主分支创建个人分支（示例）
git checkout -b feature/cw1-role6-source-a
```

分支命名统一：
- `feature/cw1-role<编号>-<模块名>`
- 示例：
  - `feature/cw1-role5-universe-db`
  - `feature/cw1-role6-source-a`
  - `feature/cw1-role7-source-b`
  - `feature/cw1-role8-normalize-quality`
  - `feature/cw1-role3-loader`

开发完成后：

```bash
git add <你的文件>
git commit -m "roleX: <your change>"
git push -u origin <你的分支名>
```

然后发 PR 到：
- `feature/coursework_one_Team_04_Pearson`

## 2) 每个人只改自己的文件
- 5号（公司池/数据库）：`modules/db/*`
- 6号（数据源A）：`modules/input/extract_source_a.py`
- 7号（数据源B）：`modules/input/extract_source_b.py`
- 8号（统一格式+质检）：`modules/output/normalize.py` + `modules/output/quality.py`
- 3号（落库/存储）：`modules/output/load.py`
- 4号（Integrator）：`Main.py` 与集成流程

说明：除非先沟通，不要改他人模块和 `Main.py`。

## 3) 固定接口契约（不要改函数名）
必须保持以下函数签名可调用：

1. `modules.db.get_company_universe(company_limit: int) -> list[str]`
2. `modules.input.extract_source_a(company_ids, run_date, backfill_years, frequency) -> list[dict]`
3. `modules.input.extract_source_b(company_ids, run_date, backfill_years, frequency) -> list[dict]`
4. `modules.output.normalize_records(records) -> list[dict]`
5. `modules.output.run_quality_checks(records) -> dict`
6. `modules.output.load_curated(records, dry_run: bool) -> int`

## 4) 上游数据最小字段要求（6号/7号）
`extract_source_a/b` 返回的每条记录至少包含：
- `company_id`
- `observation_date`
- `factor_name`
- `factor_value`
- `source`

## 5) Integrator 主流程（当前已接入）
主流程顺序：
- `get_company_universe`
- `extract_source_a` + `extract_source_b`
- `normalize_records`
- `run_quality_checks`
- `load_curated`
- run log

## 6) 本地验收命令（每个人 PR 前执行）
在 `team_Pearson/coursework_one/` 下执行：

```bash
poetry install
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
poetry run pytest -q test/test_smoke.py
```

通过标准：
- 主程序返回 0
- 输出中包含 `run_log_written_to`
- smoke test 通过

## 7) 提交边界
- 所有开发仅在 `team_Pearson/coursework_one/` 及必要团队目录中完成。
- 不要提交与本任务无关的目录改动（例如数据库目录、系统缓存等）。
