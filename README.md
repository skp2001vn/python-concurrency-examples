# Python Concurrency Examples

A Python 3.14+ project that implements and tests a set of practical concurrency
patterns and coordination primitives.

The codebase is organized as small, focused introductory examples such as
inventory reservations, payment webhooks, service startup, graceful shutdown,
worker pools, partner API retries, bounded queues, rate limiters, task groups,
pipelines, connection pools, and pub/sub brokers. Each example demonstrates a
concurrency technique using Python's standard library and is covered by
automated tests.

The repository also includes an [AGENTS.md](AGENTS.md) guide to keep
AI-assisted and human contributions consistent across examples, tests, and
documentation.

## Requirements

- Python 3.14+

## Install

Editable install is useful while developing examples:

```bash
python3.14 -m pip install -e .
```

You can also run commands without installing by setting `PYTHONPATH=src`.

## Test

```bash
PYTHONPATH=src python3.14 -m unittest discover -s tests
```

If the project is installed in editable mode:

```bash
python3.14 -m unittest discover -s tests
```

## Implemented Examples

Examples are ordered from simpler concurrency building blocks to examples that
combine multiple coordination techniques: shared state first, then coordination
patterns, queue-based workflows, async workflows, and larger composed examples.

| Example | What it demonstrates |
| --- | --- |
| [`inventoryreservation`](src/python_concurrency_examples/examples/inventoryreservation/) | Reserving limited stock during concurrent checkout, using `threading.Lock` to protect check-and-update inventory rules |
| [`paymentwebhook`](src/python_concurrency_examples/examples/paymentwebhook/) | Applying duplicate payment webhooks only once, using `threading.Lock` to protect idempotency checks and payment totals |
| [`servicestartup`](src/python_concurrency_examples/examples/servicestartup/) | Waiting for startup tasks before accepting requests, using `threading.Event` to broadcast readiness to request handler threads |
| [`batchapproval`](src/python_concurrency_examples/examples/batchapproval/) | Releasing a business batch after all required reviewers approve it, using `threading.Condition` to protect shared approval state and wake waiting callers |
| [`downloadpool`](src/python_concurrency_examples/examples/downloadpool/) | Limiting partner file downloads during a reporting job, using `threading.Semaphore` to cap active worker threads |
| [`requesttracker`](src/python_concurrency_examples/examples/requesttracker/) | Draining in-flight requests during graceful shutdown, using `threading.Condition` to reject new work and wait for active handlers to finish |
| [`boundedqueue`](src/python_concurrency_examples/examples/boundedqueue/) | Passing work from producer threads to consumer threads, using `queue.Queue` for thread-safe handoff, backpressure, and shutdown |
| [`connectionpool`](src/python_concurrency_examples/examples/connectionpool/) | Reusing limited database or API connections across request threads, using `queue.Queue` to lease and return resources safely |
| [`retryexecutor`](src/python_concurrency_examples/examples/retryexecutor/) | Retrying unreliable partner API calls across worker threads, using `concurrent.futures.ThreadPoolExecutor` to run independent tasks concurrently |

## Agent Workflow

This repository includes [AGENTS.md](AGENTS.md) to guide AI-assisted and human
contributions when adding or updating examples.

Its purpose is to keep the repository consistent as it grows by defining:

- how new examples should be structured
- expectations for Python docstrings and public APIs
- testing requirements
- README maintenance rules
- general code quality and naming conventions

If you add a new example, check `AGENTS.md` before making changes.

## Project Structure

Implementation code lives under `src/`, and tests live under `tests/`. This is a
common Python package layout that keeps importable code separate from test code.

- `src/python_concurrency_examples/` contains importable package code
- `src/python_concurrency_examples/examples/<example>/` contains one concurrency example
- `tests/examples/<example>/` contains unit tests for that example
- `pyproject.toml` contains package metadata
- `README.md` provides the project overview and implemented example list
- `AGENTS.md` defines contribution rules for humans and AI agents
