# Kith Phase 6: Good Morning Tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual task list (title, optional deadline, priority, done) with CRUD endpoints, and make the frontend two tabs: "Good Morning" (tasks, the landing tab) and "Map" (the existing graph).

**Architecture:** A `tasks` table in Postgres with a thin service and JWT-protected CRUD router. The single-page frontend gains a tab switcher; the existing graph UI moves under a Map tab and a new Good Morning tab holds the task list. No AI.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, pytest, vanilla JS frontend. Builds on Phases 0 to 5.

---

## Context for the implementer

Phases 0 to 5 are complete (56 passing tests). Relevant:
- Models in `app/models/` registered in `app/models/__init__.py` (User, Company, Message, Person, Connection).
- `app/deps.py` has `get_current_user`; `app/database.py` has `get_db`, `Base`.
- `app/main.py` includes routers (auth, health, paste, graph, people, intro, companies) and mounts `frontend/` at `/` via StaticFiles (the mount is the last line).
- `tests/conftest.py` has `client` and `db_session` fixtures; existing routers return either ORM objects via `response_model` or hand-built schemas.
- Run from the `backend` directory: `.\.venv\Scripts\python.exe -m pytest -q`.
- `frontend/index.html` is a single file: a `#auth` login section and a `#app` section containing a `.toolbar`, a `#paste` block, and a `#cy` graph; JS funcs include `showApp()`, `loadGraph()`, `api()`, `addPerson()`, `deleteSelected()`, `findPaths()`, `syncGraph()`.

No em dashes or en dashes anywhere (code, comments, commit messages).

## File Structure (Phase 6)

```
backend/app/models/task.py            NEW Task ORM
backend/app/models/__init__.py        MODIFY register Task
backend/app/schemas/tasks.py          NEW TaskCreate, TaskUpdate, TaskOut
backend/app/services/tasks.py         NEW create/list/set_done/delete
backend/app/routers/tasks.py          NEW CRUD router
backend/app/main.py                   MODIFY include tasks router
frontend/index.html                   MODIFY tabs + Good Morning task UI
backend/tests/test_tasks.py           NEW hermetic tests
```

---

## Task 1: Task model

**Files:**
- Create: `backend/app/models/task.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/task.py`**

```python
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Register it in `backend/app/models/__init__.py`**

Replace the file with:
```python
from app.models.user import User
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person
from app.models.connection import Connection
from app.models.task import Task

__all__ = ["User", "Company", "Message", "Person", "Connection", "Task"]
```

- [ ] **Step 3: Verify tables register and suite passes**

Run: `.\.venv\Scripts\python.exe -c "import app.models; from app.database import Base; print('tasks' in Base.metadata.tables)"`
Expected: `True`.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 56 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/task.py backend/app/models/__init__.py
git commit -m "feat: add Task model for the morning task list"
```

---

## Task 2: Schemas and service (TDD)

**Files:**
- Create: `backend/app/schemas/tasks.py`
- Create: `backend/app/services/tasks.py`
- Test: `backend/tests/test_tasks.py` (service part)

- [ ] **Step 1: Create `backend/app/schemas/tasks.py`**

```python
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    deadline: Optional[date] = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    done: bool


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    deadline: Optional[date] = None
    priority: str
    done: bool
    created_at: datetime
```

- [ ] **Step 2: Write the failing test `backend/tests/test_tasks.py`**

```python
from datetime import date

from app.models.user import User
from app.security import hash_password
from app.services.tasks import (
    create_task,
    delete_task,
    list_tasks,
    set_task_done,
)


def _make_user(db_session, email="t@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_task_defaults_to_medium_and_not_done(db_session):
    user = _make_user(db_session)
    task = create_task(db_session, user.id, "Call Dipunj", None, "medium")
    assert task.priority == "medium"
    assert task.done is False
    assert task.deadline is None


def test_list_orders_open_first_then_priority_then_deadline(db_session):
    user = _make_user(db_session)
    low = create_task(db_session, user.id, "low", None, "low")
    high = create_task(db_session, user.id, "high", None, "high")
    medium = create_task(db_session, user.id, "medium", None, "medium")
    done = create_task(db_session, user.id, "done", None, "high")
    set_task_done(db_session, user.id, done.id, True)

    ordered = [t.title for t in list_tasks(db_session, user.id)]
    assert ordered == ["high", "medium", "low", "done"]


def test_deadline_sorts_before_no_deadline_within_priority(db_session):
    user = _make_user(db_session)
    no_deadline = create_task(db_session, user.id, "someday", None, "medium")
    soon = create_task(db_session, user.id, "soon", date(2026, 6, 20), "medium")

    ordered = [t.title for t in list_tasks(db_session, user.id)]
    assert ordered == ["soon", "someday"]


def test_set_task_done_and_delete(db_session):
    user = _make_user(db_session)
    task = create_task(db_session, user.id, "x", None, "medium")
    updated = set_task_done(db_session, user.id, task.id, True)
    assert updated.done is True
    assert delete_task(db_session, user.id, task.id) is True
    assert delete_task(db_session, user.id, task.id) is False


def test_set_task_done_scoped_to_user(db_session):
    owner = _make_user(db_session, "owner@example.com")
    other = _make_user(db_session, "other@example.com")
    task = create_task(db_session, owner.id, "x", None, "medium")
    assert set_task_done(db_session, other.id, task.id, True) is None
```

- [ ] **Step 3: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tasks.py -v`
Expected: import error (`app.services.tasks` does not exist).

- [ ] **Step 4: Create `backend/app/services/tasks.py`**

```python
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def create_task(
    db: Session,
    user_id: str,
    title: str,
    deadline: Optional[date],
    priority: str = "medium",
) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        deadline=deadline,
        priority=priority or "medium",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, user_id: str) -> list[Task]:
    tasks = db.scalars(select(Task).where(Task.user_id == user_id)).all()
    return sorted(
        tasks,
        key=lambda t: (
            t.done,
            _PRIORITY_RANK.get(t.priority, 1),
            t.deadline is None,
            t.deadline or date.max,
            t.created_at,
        ),
    )


def set_task_done(
    db: Session, user_id: str, task_id: str, done: bool
) -> Optional[Task]:
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    if task is None:
        return None
    task.done = done
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, user_id: str, task_id: str) -> bool:
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    if task is None:
        return False
    db.delete(task)
    db.commit()
    return True
```

- [ ] **Step 5: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tasks.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/tasks.py backend/app/services/tasks.py backend/tests/test_tasks.py
git commit -m "feat: add task schemas and service with ordering"
```

---

## Task 3: Tasks router (TDD)

**Files:**
- Create: `backend/app/routers/tasks.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_tasks.py` (endpoint part)

- [ ] **Step 1: Add the failing endpoint tests to `backend/tests/test_tasks.py`**

Append:
```python
def _register(client, email="te@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_task_endpoints_crud(client):
    headers = _register(client)

    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Email recruiter", "priority": "high"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["done"] is False

    listed = client.get("/tasks", headers=headers).json()
    assert any(t["id"] == task_id for t in listed)

    patched = client.patch(
        f"/tasks/{task_id}", headers=headers, json={"done": True}
    )
    assert patched.status_code == 200
    assert patched.json()["done"] is True

    removed = client.delete(f"/tasks/{task_id}", headers=headers)
    assert removed.status_code == 204
    assert client.delete(f"/tasks/{task_id}", headers=headers).status_code == 404


def test_task_create_without_deadline(client):
    headers = _register(client)
    response = client.post("/tasks", headers=headers, json={"title": "Just do it"})
    assert response.status_code == 201
    body = response.json()
    assert body["deadline"] is None
    assert body["priority"] == "medium"


def test_tasks_require_auth(client):
    assert client.get("/tasks").status_code in (401, 403)
    assert client.post("/tasks", json={"title": "x"}).status_code in (401, 403)
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tasks.py -v`
Expected: the new endpoint tests fail with 404 (routes not wired).

- [ ] **Step 3: Create `backend/app/routers/tasks.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.services.tasks import (
    create_task,
    delete_task,
    list_tasks,
    set_task_done,
)

router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def add_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_task(
        db, current_user.id, payload.title, payload.deadline, payload.priority
    )


@router.get("/tasks", response_model=list[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_tasks(db, current_user.id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = set_task_done(db, current_user.id, task_id, payload.done)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_task(db, current_user.id, task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return None
```

- [ ] **Step 4: Wire it into `backend/app/main.py`**

Add `tasks` to the routers import line, and add `app.include_router(tasks.router)` with the other `include_router` calls (before the `FRONTEND_DIR` / static mount line). For example the import becomes:
```python
from app.routers import auth, companies, graph, health, intro, paste, people, tasks
```
and add:
```python
app.include_router(tasks.router)
```

- [ ] **Step 5: Run the task tests and the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tasks.py -v`
Expected: 8 passed.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 64 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/tasks.py backend/app/main.py backend/tests/test_tasks.py
git commit -m "feat: add JWT-protected task CRUD endpoints"
```

---

## Task 4: Frontend tabs and the Good Morning task list

**Files:**
- Modify: `frontend/index.html`

This restructures the page into two tabs. Work carefully and preserve all existing graph behavior.

- [ ] **Step 1: Add tab nav and wrap the existing app content**

In `frontend/index.html`, the `#app` div currently contains the toolbar, the `#paste` block, and the `#cy` graph. Do two things inside `#app`:

(a) Add this nav as the FIRST child of `#app` (right after `<div id="app">`):
```html
    <div class="tabs">
      <button id="tabTasks" class="tab active" onclick="showTab('tasks')">Good Morning</button>
      <button id="tabMap" class="tab" onclick="showTab('map')">Map</button>
    </div>
    <div id="tasksView">
      <h2 id="greeting">Good morning</h2>
      <div class="taskform">
        <input id="taskTitle" placeholder="Add a task" onkeydown="if(event.key==='Enter')addTask()" />
        <input id="taskDeadline" type="date" />
        <select id="taskPriority">
          <option value="high">High</option>
          <option value="medium" selected>Medium</option>
          <option value="low">Low</option>
        </select>
        <button onclick="addTask()">Add task</button>
      </div>
      <ul id="taskList" class="tasklist"></ul>
    </div>
    <div id="mapView" style="display:none">
```

(b) Add a single closing `</div>` for `#mapView` right BEFORE the closing `</div>` of `#app` (so the existing toolbar, `#paste`, and `#cy` are now wrapped inside `#mapView`). Do not change the toolbar, paste, or cy markup themselves.

- [ ] **Step 2: Add styles**

Add these rules inside the existing `<style>` block:
```css
    .tabs { display: flex; gap: 8px; padding: 10px 20px 0; }
    .tab { background: #1e293b; color: var(--muted); border: none; border-radius: 8px 8px 0 0;
           padding: 8px 16px; cursor: pointer; font-weight: 600; }
    .tab.active { background: var(--panel); color: var(--text); }
    #tasksView { padding: 20px; max-width: 760px; }
    .taskform { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 18px; }
    .taskform input, .taskform select { width: auto; }
    .tasklist { list-style: none; padding: 0; margin: 0; }
    .taskrow { display: flex; align-items: center; gap: 10px; padding: 10px 12px;
               border: 1px solid var(--line); border-radius: 8px; margin-bottom: 8px;
               background: var(--panel); }
    .taskrow.done .tasktitle { text-decoration: line-through; color: var(--muted); }
    .tasktitle { flex: 1; }
    .badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; color: #fff; }
    .badge.high { background: #dc2626; }
    .badge.medium { background: #d97706; }
    .badge.low { background: #2563eb; }
    .deadline { color: var(--muted); font-size: 12px; }
    .taskdel { background: transparent; color: var(--muted); padding: 2px 6px; }
```

- [ ] **Step 3: Add the tab switch and task JS**

Add these functions inside the `<script>` block (near the other functions):
```javascript
    function showTab(name) {
      const tasks = name === "tasks";
      document.getElementById("tasksView").style.display = tasks ? "block" : "none";
      document.getElementById("mapView").style.display = tasks ? "none" : "block";
      document.getElementById("tabTasks").classList.toggle("active", tasks);
      document.getElementById("tabMap").classList.toggle("active", !tasks);
      if (tasks) loadTasks();
    }

    async function loadTasks() {
      const tasks = await api("/tasks");
      const open = tasks.filter(function (t) { return !t.done; }).length;
      document.getElementById("greeting").textContent =
        "Good morning. You have " + open + " open task" + (open === 1 ? "" : "s") + ".";
      const list = document.getElementById("taskList");
      list.innerHTML = "";
      for (const t of tasks) {
        const li = document.createElement("li");
        li.className = "taskrow" + (t.done ? " done" : "");
        const deadline = t.deadline ? '<span class="deadline">due ' + t.deadline + "</span>" : "";
        li.innerHTML =
          '<input type="checkbox" ' + (t.done ? "checked" : "") + ' />' +
          '<span class="tasktitle"></span>' +
          '<span class="badge ' + t.priority + '">' + t.priority + "</span>" +
          deadline +
          '<button class="taskdel">delete</button>';
        li.querySelector(".tasktitle").textContent = t.title;
        li.querySelector("input").onchange = function (e) { toggleTask(t.id, e.target.checked); };
        li.querySelector(".taskdel").onclick = function () { deleteTask(t.id); };
        list.appendChild(li);
      }
    }

    async function addTask() {
      const title = document.getElementById("taskTitle").value.trim();
      if (!title) return;
      const deadline = document.getElementById("taskDeadline").value || null;
      const priority = document.getElementById("taskPriority").value;
      await api("/tasks", { method: "POST", body: JSON.stringify({ title: title, deadline: deadline, priority: priority }) });
      document.getElementById("taskTitle").value = "";
      document.getElementById("taskDeadline").value = "";
      loadTasks();
    }

    async function toggleTask(id, done) {
      await api("/tasks/" + id, { method: "PATCH", body: JSON.stringify({ done: done }) });
      loadTasks();
    }

    async function deleteTask(id) {
      await api("/tasks/" + id, { method: "DELETE" });
      loadTasks();
    }
```

- [ ] **Step 4: Show the tasks tab on login**

Find `showApp()` and add a call to load tasks and default to the tasks tab. After the existing body of `showApp` (which sets display and calls `loadGraph()`), add:
```javascript
      showTab("tasks");
```
Keep the existing `loadGraph()` call so the map is ready when switched to.

- [ ] **Step 5: Manual check**

Start the app on SQLite and open http://localhost:8000:
```
$env:DATABASE_URL = "sqlite:///./kith_local.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Register, confirm the Good Morning tab shows first, add a task with and without a deadline, set a priority, check it off (moves to bottom, struck through), delete it, and switch to Map to confirm the graph still works.

- [ ] **Step 6: Confirm the suite still passes (no backend change here)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 64 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add Good Morning tasks tab and Map tab to the UI"
```

---

## Task 5: End-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Start the app on a fresh SQLite database in the background**

From the `backend` directory:
```
$env:DATABASE_URL = "sqlite:///./kith_p6.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

- [ ] **Step 2: Exercise the task API**

```
$reg = Invoke-RestMethod -Uri http://localhost:8000/auth/register -Method Post -ContentType application/json -Body '{"email":"p6@example.com","password":"hunter2"}'
$h = @{ Authorization = "Bearer " + $reg.access_token }
Invoke-RestMethod -Uri http://localhost:8000/tasks -Method Post -ContentType application/json -Headers $h -Body '{"title":"Email Dipunj","priority":"high","deadline":"2026-06-20"}' | Out-Null
Invoke-RestMethod -Uri http://localhost:8000/tasks -Method Post -ContentType application/json -Headers $h -Body '{"title":"Read a book"}' | Out-Null
Invoke-RestMethod -Uri http://localhost:8000/tasks -Method Get -Headers $h | ConvertTo-Json -Depth 5
```
Expected: two tasks, the high-priority one first, with the correct deadline and a medium default on the second.

- [ ] **Step 3: Confirm the page is served and stop the server**

`curl http://localhost:8000/ -UseBasicParsing | Select-String "Good Morning"` should find the tab label. Then stop the background server.

- [ ] **Step 4: Manual browser confirmation**

Tell the user to open the app, use the Good Morning tab to add and check off tasks, and confirm the Map tab still works.

---

## Self-Review

**Spec coverage:** Task model and CRUD (Tasks 1 to 3); optional deadline and default-medium priority (Task 2 service + Task 3 tests); list ordering open-first then priority then deadline (Task 2 `list_tasks` + tests); tabs with Good Morning as landing and the graph under Map (Task 4); per-user scoping and auth (Task 2/3 tests). Deferred items (task-to-person links, recurring, contact cards) correctly absent.

**Type consistency:** `create_task(db, user_id, title, deadline, priority)`, `list_tasks(db, user_id)`, `set_task_done(db, user_id, task_id, done)`, `delete_task(db, user_id, task_id)` are defined in Task 2 and called identically in Task 3's router and the tests. `TaskCreate(title, deadline, priority)`, `TaskUpdate(done)`, `TaskOut` (from_attributes) match the router usage. The frontend posts `{title, deadline, priority}` and patches `{done}`, matching the schemas.

**Placeholder scan:** No TBDs. Every code step is complete; tests have real assertions and exact counts (56, 64).

**Known pragmatic choices:** `TaskOut` uses `from_attributes` and the router returns ORM objects directly (read within the request session, like FastAPI expects). Deadline is a plain date. Ordering is computed in Python for clarity over a SQL ORDER BY. The frontend stays one static file; its tabs and task UI are verified manually.
