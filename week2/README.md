# Week 2

Week 2 combines local and cloud prompting with a small SQLite-backed data pipeline. The project has three parts: a provider-agnostic prompt wrapper, a job tagging pipeline that writes `tech_stack` values, and a skill-gap analyzer that compares tagged jobs against a resume.

## Project Overview

The goal of this week is to take job description data, enrich it with technical tags, and then compare those tags to a resume to highlight missing skills. The prompting layer supports both Ollama and Gemini so the same interface can be tested locally or with a cloud model.

## Setup Instructions

### Prerequisites

- Windows PowerShell
- Python 3.14
- `uv`
- Ollama, if you want to run local models
- A Google API key from Google AI Studio, if you want to use Gemini

### Create the virtual environment

Run these commands from inside `week2`:

```powershell
cd C:\Users\adam arbain\kyouth-data-ai-adam\week2
uv venv .venv --python 3.14
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

Install the project dependencies defined in `pyproject.toml`:

```powershell
uv lock
uv sync
```

### Configure Ollama

Install Ollama on Windows:

```powershell
irm https://ollama.com/install.ps1 | iex
```

Check that Ollama is available:

```powershell
ollama -v
Invoke-RestMethod http://127.0.0.1:11434/
```

Pull the local models used in this project:

```powershell
ollama pull llama3.1
ollama pull phi3
ollama pull deepseek-r1:1.5b
```

### Configure Gemini

Create a key at https://aistudio.google.com/ and set it in your current shell session:

```powershell
$env:GOOGLE_API_KEY="your_key_here"
```

Do not commit the API key to the repository. If you want to use a specific Gemini model for tagging, set `GEMINI_MODEL` before running the tagging script.

## Usage

### Prompt wrapper

`prompt_model.py` sends a prompt to Ollama for non-Gemini model names and to Gemini for model names that start with `gemini-`.

Example local call:

```powershell
uv run python prompt_model.py llama3.1 "tell me one malasyian joke"
```

Example Gemini call:

```powershell
uv run python prompt_model.py gemini-2.5-flash "tell me one malasyian joke"
```

Expected output:

```text
--- RESPONSE ---
<model response or error string>
```

### Tag jobs

`tag_data.py` reads from a SQLite `jobs` table, finds rows where `tech_stack` is empty, infers a comma-separated stack, and writes the result back through the MCP SQLite service.

Run with the default database search order:

```powershell
uv run tag_data.py
```

Run against a specific database path:

```powershell
uv run tag_data.py C:\path\to\jobs_d1.db
```

Expected output includes one line per updated job, for example `Analyzed Job <source_id>: <tech_stack>`, followed by a summary with token usage and elapsed time.

### Find skill gaps

`find_skill_gaps.py` reads a resume and the tagged job rows, then returns the skills present in the job market but missing from the resume.

Run with the default resume and database discovery:

```powershell
uv run find_skill_gaps.py
```

Run with an explicit resume and database path:

```powershell
uv run find_skill_gaps.py C:\path\to\resume.txt C:\path\to\jobs_d1.db
```

Expected output looks like this:

```text
gaps=['python', 'sql'] time=0.123 tokens=456
```

Any non-fatal notes are printed after the summary.

## API / Function Reference

### `prompt_model.py`

- `prompt_model(model: str, prompt: str) -> str`
	- Purpose: routes a prompt to Ollama or Gemini and returns a text response.
	- Inputs: `model` is a model name such as `llama3.1` or `gemini-2.5-flash`; `prompt` is free-form text.
	- Output: a string response or a string error message; it does not raise for provider failures.
- `_main_from_argv(argv: list[str]) -> int`
	- Purpose: command-line entry point for manual testing.
	- Inputs: CLI arguments in the form `python prompt_model.py <model> <prompt>`.
	- Output: exit code `0` on normal completion, `2` for missing arguments.

### `tag_data.py`

- `tag_data(db_url: str) -> dict[str, object]`
	- Purpose: tags jobs that still have an empty `tech_stack` value.
	- Inputs: a database path or empty string. The script also checks `TAG_DATA_DB_PATH` and then the local defaults under `data/jobs_d1.db` and `data/3_gold/jobs.db`.
	- Output: a dictionary containing `tokens_used`, `elapsed_ms`, `updated_rows`, and `quality`.
- `_tag_data_async(db_path: Path) -> dict[str, Any]`
	- Purpose: coordinates MCP calls, batching, and database updates.
	- Inputs: a resolved SQLite database path.
	- Output: the same summary object returned by `tag_data`.
- `_generate_tags_for_batch(...) -> tuple[list[dict[str, str]], int]`
	- Purpose: generates `source_id` to `tech_stack` mappings for one batch.
	- Inputs: MCP session, batch rows, and Gemini model name.
	- Output: normalized tagged rows plus token usage for the batch.

### `find_skill_gaps.py`

- `find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`
	- Purpose: compares resume skills with the set of skills found in tagged jobs.
	- Inputs: a resume path and a database path. If the resume path is empty, the script falls back to `data/resume.txt` and then `data/resume_d3.txt`.
	- Output: a `SkillGapResult` object containing `gaps`, `matched_skills`, `ignored_skills`, `skill_stats`, `total_jobs`, `total_unique_job_skills`, `tokens_used`, `time_used_seconds`, and `notes`.
- `_summarize_demand(...) -> tuple[list[str], list[SkillDemandStat], list[str], int, int]`
	- Purpose: counts how often each skill appears across tagged jobs and determines which ones are missing from the resume.
	- Inputs: tagged job rows and the resume skill set.
	- Output: sorted gap names, per-skill demand stats, matched skills, total job count, and total unique job skill count.

### `src/sqlite_mcp_server.py`

- `fetch_pending_jobs(after_rowid: int = 0, batch_size: int = 5, db_path: str = "")`
	- Purpose: returns jobs where `tech_stack` is still empty.
- `fetch_tagged_jobs(after_rowid: int = 0, batch_size: int = 200, db_path: str = "")`
	- Purpose: returns jobs that already have a populated `tech_stack`.
- `update_tech_stack(source_id: str, tech_stack: str, db_path: str = "")`
	- Purpose: writes one inferred stack back to SQLite.
- `count_pending_jobs(db_path: str = "")`
	- Purpose: counts jobs that still need tagging.

## Data / Assumptions

The pipeline uses a SQLite database with a `jobs` table. The scripts assume the table contains at least `source_id`, `job_title`, `description`, and `tech_stack`. The tagging step only updates rows where `tech_stack` is empty; it does not overwrite existing tags.

Default database discovery happens in this order:

1. A database path passed on the command line
2. `TAG_DATA_DB_PATH`
3. `data/jobs_d1.db`
4. `data/3_gold/jobs.db`

The skill-gap script reads tagged rows only. It normalizes resume and job skills to a canonical lowercase vocabulary so the output is deterministic. If Gemini is unavailable in the tagging pipeline, the code falls back to a rule-based stack extractor so the database can still be populated.

## Testing

Validation was done by checking the actual script entry points and their CLI behavior in the source code, then aligning the README to those real interfaces.

Suggested manual checks:

1. Run `uv run python prompt_model.py llama3.1 "hello"` and confirm a response string is printed after `--- RESPONSE ---`.
2. Run `uv run tag_data.py` against a database with empty `tech_stack` values and confirm updated jobs are logged.
3. Run `uv run find_skill_gaps.py` and confirm the result prints in `gaps=[...] time=... tokens=...` format.

## Limitations

- The project does not provide a formal automated test suite in this folder.
- Tagging quality depends on model availability, prompt quality, and the completeness of the job descriptions.
- The rule-based fallback is intentionally simple and can miss domain-specific tools or overgeneralize common terms.
- The skill-gap logic compares against a curated canonical skill list, so any skill outside that vocabulary will be ignored.
- `find_skill_gaps.py` reports gaps from tagged jobs rather than writing them back into SQLite, so it is an analysis step rather than a database update step.

## Architecture Reflection

The design keeps the responsibilities separated on purpose. `prompt_model.py` is a thin provider router, `tag_data.py` owns the enrichment workflow, and `find_skill_gaps.py` only analyzes already-tagged data. That separation keeps each script easy to run independently and makes failure handling more predictable.

I prioritized determinism and recoverability over sophistication. The tagging pipeline can fall back to a rule-based extractor when Gemini is not available, which is less accurate than a pure model-driven approach but much more reliable for local grading and repeatable runs. The skill-gap analyzer also uses a canonical skill vocabulary so the result is stable across repeated executions.

If I had more time, I would add automated tests around the database helpers, make the skill vocabulary configurable from a file, and add a small validation layer for the expected SQLite schema before any writes happen.







