#!/usr/bin/env python3
"""Print the latest workflow instance and its task states without exposing secrets."""

from __future__ import annotations

import argparse
from pathlib import Path

from deploy_workflow import load_env
from run_workflow import login


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--workflow-code", type=int, required=True)
    args = parser.parse_args()
    env = load_env(args.env_file)
    api = login(env)
    project_code = env["DOLPHINSCHEDULER_PROJECT_CODE"]
    page = api.request("GET", f"/projects/{project_code}/workflow-instances", {
        "pageNo": 1,
        "pageSize": 10,
        "workflowDefinitionCode": args.workflow_code,
    })
    records = page.get("totalList", []) if isinstance(page, dict) else []
    if not records:
        print("WORKFLOW_INSTANCE_NOT_FOUND")
        return 2
    instance = max(records, key=lambda item: item["id"])
    instance_id = instance["id"]
    tasks = api.request(
        "GET", f"/projects/{project_code}/workflow-instances/{instance_id}/tasks", {}
    )
    if isinstance(tasks, list):
        task_rows = tasks
    elif isinstance(tasks, dict):
        task_rows = next(
            (
                tasks[key]
                for key in ("taskList", "totalList", "records")
                if isinstance(tasks.get(key), list)
            ),
            [],
        )
    else:
        task_rows = []
    print(
        "WORKFLOW_INSTANCE"
        f" id={instance_id} state={instance.get('state')}"
        f" start={instance.get('startTime')} end={instance.get('endTime')}"
    )
    for task in sorted(task_rows, key=lambda item: item.get("id", 0)):
        print(
            "TASK"
            f" id={task.get('id')} name={task.get('name')} state={task.get('state')}"
            f" host={task.get('host')} retry={task.get('retryTimes')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
