# Kith Phase 6: Good Morning Tasks

**Design spec** · 2026-06-12

## Purpose

Make the first thing you see when you open Kith a clear, manual task list, so you have
direction for the day. No AI: just the notes-and-reminders tool you have wanted, built in.
The graph moves to its own tab.

## Scope

### In scope (Phase 6)
- A `Task` model and CRUD: create a task (title), an optional deadline, a priority
  (high / medium / low, default medium), mark done, delete. Manual only, no Gemini.
- Endpoints: `POST /tasks`, `GET /tasks` (sorted), `PATCH /tasks/{id}` (toggle done),
  `DELETE /tasks/{id}`, all JWT-protected and scoped per user.
- The frontend becomes two tabs: "Good Morning" (the task list, the landing tab) and
  "Map" (the existing graph). The existing add-person, paste, intro-paths, and delete
  controls all move under the Map tab unchanged.

### Explicitly deferred
- Linking a task to a person ("email Dipunj") or AI-suggested tasks.
- Recurring tasks, reminders/notifications, subtasks.
- People contact cards (next phase).

## Success criteria
- Open the app and the Good Morning tab is shown first, listing the user's open tasks.
- Add a task with just a title; deadline and priority are optional (a task with no
  deadline still creates).
- Tasks are listed open-first, then by priority (high before low), then by soonest
  deadline. Checking a task marks it done; it moves to the bottom and is struck through.
- The Map tab still shows and operates the graph exactly as before.
- Tasks are scoped per user and covered by hermetic tests.

## Architecture

### Data model (Postgres)
- New table `tasks`: `id`, `user_id` (FK users), `title`, `deadline` (nullable Date),
  `priority` (string, one of `high`/`medium`/`low`, default `medium`), `done` (bool,
  default False), `created_at`.

### Service (`app/services/tasks.py`)
- `create_task(db, user_id, title, deadline, priority) -> Task`.
- `list_tasks(db, user_id) -> list[Task]`: sorted by `done` (open first), then priority
  rank (`high`=0, `medium`=1, `low`=2), then deadline (nulls last), then `created_at`.
- `set_task_done(db, user_id, task_id, done) -> Task | None`.
- `delete_task(db, user_id, task_id) -> bool`.

### Schemas (`app/schemas/tasks.py`)
- `TaskCreate(title: str, deadline: Optional[date] = None, priority: str = "medium")`.
- `TaskUpdate(done: bool)`.
- `TaskOut(id, title, deadline, priority, done, created_at)`.

### Router (`app/routers/tasks.py`)
- `POST /tasks` -> 201 `TaskOut`.
- `GET /tasks` -> list of `TaskOut` (sorted as above).
- `PATCH /tasks/{task_id}` body `TaskUpdate` -> `TaskOut`, 404 if not found.
- `DELETE /tasks/{task_id}` -> 204, 404 if not found.

### Frontend (`frontend/index.html`)
- A top nav with two buttons, "Good Morning" and "Map", that show/hide two sections.
  Good Morning is shown by default after login.
- Good Morning section: a greeting and open-task count, an add-task row (title input,
  optional date input, priority select, Add button), and the task list. Each task shows a
  checkbox (toggles done via PATCH), the title, a colored priority badge, the deadline if
  set, and a delete button. Done tasks render struck through at the bottom.
- Map section: the existing toolbar and `#cy` graph container, moved here unchanged.

## Testing
- `tasks` service and endpoints, hermetic (SQLite, the `client`/`db_session` fixtures):
  create with and without deadline; default priority is medium; list ordering (open before
  done, high before low, soonest deadline first); PATCH toggles done; DELETE returns 204
  and 404 for unknown; auth required; scoped per user.
- The frontend tabs and task UI are verified manually.

## Files (planned)
```
backend/app/models/task.py            Task ORM
backend/app/models/__init__.py        register Task
backend/app/services/tasks.py         create/list/set_done/delete
backend/app/schemas/tasks.py          TaskCreate, TaskUpdate, TaskOut
backend/app/routers/tasks.py          POST/GET/PATCH/DELETE /tasks
backend/app/main.py                   include tasks router
frontend/index.html                   tabs + Good Morning task UI
backend/tests/test_tasks.py           hermetic tests
```
