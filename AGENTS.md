# AGENTS.md

## Purpose

This repository contains small, focused Python concurrency examples for
practice, learning, and interview preparation.

Each example should remain:

- self-contained
- easy to read
- classical enough to be useful as study/reference material
- correct under concurrent access
- backed by automated tests

## Tech Stack

- Python 3.14+
- Standard library first
- `unittest` for tests
- `pyproject.toml` for package metadata

## Project Structure

- `src/concurrencyexamples/<example>/`
  - reusable example package code
- `tests/concurrencyexamples/<example>/`
  - unit tests that mirror the example package
- `README.md`
  - high-level project overview and example list

## Implementation Guidelines

- Keep each example package focused on one problem or concurrency pattern.
- Prefer simple, classical examples over feature-rich demos. The goal is to
  teach one concurrency idea clearly, not to build a mini application.
- Prefer clear standard-library concurrency primitives from `threading`,
  `queue`, `concurrent.futures`, `multiprocessing`, `asyncio`, and
  `contextvars`.
- Favor correctness and readability over cleverness.
- Keep APIs minimal and idiomatic for Python.
- Use syntax and standard-library APIs supported by the project's declared
  Python version when they improve clarity. Do not downgrade source syntax to
  work around an IDE configured for an older interpreter.
- Do not add separate `demo.py` modules by default. Tests should be the primary
  executable examples. Add a runnable module only when the example cannot be
  understood or verified well through unit tests.
- Use descriptive package names without underscores or hyphens, such as
  `boundedqueue`, `workerpool`, or `ratelimiter`.
- Raise specific exceptions for invalid inputs or unrecoverable misuse.
- Avoid unnecessary dependencies for small examples.
- Make shared state ownership explicit. A reader should be able to see which
  lock, queue, event, or task owns each piece of mutable state.
- Avoid sleep-based synchronization in implementation code unless time is the
  actual subject of the example.

## Documentation Guidelines

- Add module docstrings for every example module.
- Add docstrings for every public class, function, and method.
- Keep docstrings concise and useful; explain the caller-facing purpose before
  implementation mechanics.
- In package `__init__.py` docstrings, use a short two-sentence summary:
  describe the business scenario first, then name the main concurrency primitive
  and the caller-facing guarantee. Keep detailed explanation out of
  `__init__.py`.
- In implementation module docstrings, include the business scenario first so
  readers understand the example's problem. Then describe the concurrency
  technique used and why it fits the scenario.
- Prefer business or caller language first, such as jobs, batches, resources,
  success, failure, timeout, cancellation, and cleanup. Mention locks, queues,
  threads, or tasks when those details affect how callers use the API.
- For concurrency examples, document concurrency safety, blocking behavior,
  cancellation behavior, ownership, default behavior, invalid inputs, and
  returned exceptions when relevant.
- Keep comments sparse. Use them to explain non-obvious coordination logic, not
  straightforward assignments.

## Testing Guidelines

- Every new example should include dedicated `unittest` coverage.
- Treat tests as executable documentation for the example.
- Put tests under `tests/concurrencyexamples/<example>/`.
- Keep `tests/__init__.py` and `tests/concurrencyexamples/__init__.py` so
  unittest discovery can run with `-t .` without shadowing the source package.
- Test files should be named `test_<module>.py`.
- Test classes should use descriptive names such as `BoundedQueueTest` or
  `WorkerPoolTest`.
- Add a short comment above each test method explaining the caller-facing
  behavior or guarantee being verified.
- Tests should validate normal behavior, edge cases, and concurrency
  coordination behavior.
- Use `unittest.IsolatedAsyncioTestCase` for async examples.
- Prefer deterministic tests over timing-sensitive tests.
- Prefer synchronization primitives such as `threading.Barrier`, `Event`,
  `Condition`, or `Queue` over polling or sleep-based coordination in tests.
- Use short timeout-based guards only to prevent a hung test.
- Process-based examples may require an environment that allows child
  processes, process queues, and semaphores.
- Import implementation code through the package name:
  `concurrencyexamples.<example>`.
- After changes, run:

```bash
python3.14 -m compileall -q src tests
PYTHONPATH=src python3.14 -m unittest discover -s tests -t .
```

## README Maintenance

- Update `README.md` when adding a new example.
- Keep the implemented example table in sync with the repository.
- In the implemented example table, use one `What it demonstrates` column that
  combines the business use case with precise Python concurrency terms.
- Keep the implemented example table grouped by concurrency style: shared state
  and basic thread coordination first, then queue-based handoff, executor and
  process workflows, async primitives, and composed workflows. When adding an
  example, insert it where it best fits by complexity and technique, rather
  than appending it automatically.

## New Example Checklist

1. Create `src/concurrencyexamples/<example>/`.
2. Add `__init__.py` with a short package summary and the public exports for
   the example.
3. Add focused implementation modules with public docstrings.
4. Add `tests/concurrencyexamples/<example>/test_<module>.py`.
5. Cover normal, edge, and concurrent behavior.
6. Update `README.md`.
7. Run the quality commands from Testing Guidelines.
