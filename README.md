# Python Concurrency Examples

A Python 3.14+ project that implements and tests a set of practical concurrency
patterns and coordination primitives.

The codebase is organized as small, focused introductory examples such as
inventory reservations, payment webhooks, leaderboards, feature flags, service startup, circuit
breakers, deployment rollbacks, connection pools, rate limiter.
Each example demonstrates a concurrency technique using Python's standard
library and is covered by automated tests.

The repository also includes an [AGENTS.md](AGENTS.md) guide to keep
AI-assisted and human contributions consistent across examples, tests, and
documentation.

## Requirements

- Python 3.14+

## Test

```bash
PYTHONPATH=src python3.14 -m unittest discover -s tests -t .
```

## Implemented Examples

Examples are grouped by concurrency style: shared state and basic thread
coordination first, then queue-based handoff, executor and process workflows,
async primitives, and composed workflows.

| Example | What it demonstrates |
| --- | --- |
| [`inventoryreservation`](src/concurrencyexamples/inventoryreservation/) | Reserving limited stock during concurrent checkout, using `threading.Lock` to protect check-and-update inventory rules |
| [`paymentwebhook`](src/concurrencyexamples/paymentwebhook/) | Applying duplicate payment webhooks only once, using `threading.Lock` to protect idempotency checks and payment totals |
| [`leaderboard`](src/concurrencyexamples/leaderboard/) | Updating player scores and reading top rankings concurrently, using `threading.Lock` to protect score updates and snapshots |
| [`threadlocalrequest`](src/concurrencyexamples/threadlocalrequest/) | Keeping request IDs isolated per request thread, using `threading.local` for thread-specific context |
| [`asynccontextrequest`](src/concurrencyexamples/asynccontextrequest/) | Keeping request IDs isolated per async task, using `contextvars.ContextVar` for task-specific request context |
| [`featureflags`](src/concurrencyexamples/featureflags/) | Reading and refreshing an in-memory feature flag snapshot, using `threading.RLock` for nested lock-protected operations |
| [`servicestartup`](src/concurrencyexamples/servicestartup/) | Waiting for startup tasks before accepting requests, using `threading.Event` to broadcast readiness to request handler threads |
| [`scheduledcleanup`](src/concurrencyexamples/scheduledcleanup/) | Running periodic cleanup work in a background thread, using `threading.Thread` and `threading.Event` for cooperative shutdown |
| [`batchapproval`](src/concurrencyexamples/batchapproval/) | Releasing a business batch after all required reviewers approve it, using `threading.Condition` to protect shared approval state and wake waiting callers |
| [`downloadpool`](src/concurrencyexamples/downloadpool/) | Limiting partner file downloads during a reporting job, using `threading.Semaphore` to cap active worker threads |
| [`ratelimiter`](src/concurrencyexamples/ratelimiter/) | Limiting simultaneous third-party API calls, using `threading.BoundedSemaphore` to lease and release request permits safely |
| [`barrierdeployment`](src/concurrencyexamples/barrierdeployment/) | Coordinating deployment workers before switching traffic, using `threading.Barrier` to release all prepared workers together |
| [`requesttracker`](src/concurrencyexamples/requesttracker/) | Draining in-flight requests during graceful shutdown, using `threading.Condition` to reject new work and wait for active handlers to finish |
| [`boundedqueue`](src/concurrencyexamples/boundedqueue/) | Passing work from producer threads to consumer threads, using `queue.Queue` for thread-safe handoff, backpressure, and shutdown |
| [`supportqueue`](src/concurrencyexamples/supportqueue/) | Routing customer support tickets by priority, using `queue.PriorityQueue` for thread-safe prioritized handoff to agent workers |
| [`deploymentrollback`](src/concurrencyexamples/deploymentrollback/) | Registering deployment rollback actions from worker threads, using `queue.LifoQueue` for thread-safe last-in-first-out cleanup |
| [`connectionpool`](src/concurrencyexamples/connectionpool/) | Reusing limited database or API connections across request threads, using `queue.Queue` to lease and return resources safely |
| [`retryexecutor`](src/concurrencyexamples/retryexecutor/) | Retrying unreliable partner API calls across worker threads, using `concurrent.futures.ThreadPoolExecutor` to run independent tasks concurrently |
| [`fraudscorebatch`](src/concurrencyexamples/fraudscorebatch/) | Scoring CPU-heavy transactions for fraud review, using `ProcessPoolExecutor` to bypass the GIL and run independent work across CPU cores |
| [`importjobevents`](src/concurrencyexamples/importjobevents/) | Collecting import job events from worker processes, using `multiprocessing.Queue` for process-safe message passing and sentinel-based shutdown |
| [`circuitbreaker`](src/concurrencyexamples/circuitbreaker/) | Failing fast after repeated partner API failures, using `threading.Lock` to protect circuit state transitions |
| [`taskgroup`](src/concurrencyexamples/taskgroup/) | Running checkout checks concurrently before returning a decision, using `asyncio.TaskGroup` for structured async concurrency |
| [`asyncpaymentstatus`](src/concurrencyexamples/asyncpaymentstatus/) | Waiting for async payment completion from many request tasks, using `asyncio.Event` to publish one result to all waiters |
| [`asyncseatbooking`](src/concurrencyexamples/asyncseatbooking/) | Booking event seats from concurrent async requests, using `asyncio.Lock` to protect seat availability and prevent duplicate bookings |
| [`asyncreviewbatch`](src/concurrencyexamples/asyncreviewbatch/) | Releasing an async review batch after required approvals arrive, using `asyncio.Condition` to wait for shared approval state without polling |
| [`asyncjobqueue`](src/concurrencyexamples/asyncjobqueue/) | Processing submitted jobs with async background workers, using `asyncio.Queue` to hand off work and drain before shutdown |
| [`asyncshippingqueue`](src/concurrencyexamples/asyncshippingqueue/) | Dispatching express shipments before economy shipments, using `asyncio.PriorityQueue` for async prioritized handoff to carrier worker tasks |
| [`asyncbatchuploader`](src/concurrencyexamples/asyncbatchuploader/) | Uploading many files with limited async concurrency, using `asyncio.Semaphore` to cap active upload tasks |
| [`documentpipeline`](src/concurrencyexamples/documentpipeline/) | Moving documents through staged processing workers, using `queue.Queue` and `threading.Thread` to build a simple pipeline |

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

The `src/concurrencyexamples/` directory is the importable Python package for
the project. It uses a short, valid Python import name, while the distribution
name in `pyproject.toml` remains `python-concurrency-examples`.

- `src/concurrencyexamples/` contains the importable package code
- `src/concurrencyexamples/<example>/` contains one importable concurrency example
- `tests/concurrencyexamples/<example>/` contains unit tests that mirror that example
- `pyproject.toml` contains package metadata
- `README.md` provides the project overview and implemented example list
- `AGENTS.md` defines contribution rules for humans and AI agents
