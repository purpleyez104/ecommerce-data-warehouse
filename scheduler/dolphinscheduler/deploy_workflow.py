#!/usr/bin/env python3
"""Create and release the M6 workflow with a dedicated DolphinScheduler account."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
import urllib.parse
import urllib.request


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or not value:
            raise ValueError("invalid DolphinScheduler environment file")
        values[key] = value
    required = {
        "DOLPHINSCHEDULER_URL", "DOLPHINSCHEDULER_USER",
        "DOLPHINSCHEDULER_PASSWORD", "DOLPHINSCHEDULER_PROJECT_CODE",
    }
    if required - values.keys():
        raise ValueError("DolphinScheduler environment file is incomplete")
    return values


class Api:
    """最小 API Client；Cookie 仅保存在内存中。"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def request(
        self,
        method: str,
        path: str,
        values: dict[str, object],
        allowed_codes: set[int] | None = None,
    ) -> object:
        encoded = urllib.parse.urlencode({
            key: value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
            for key, value in values.items()
        })
        url = f"{self.base_url}{path}"
        data = encoded.encode() if method in {"POST", "PUT"} else None
        if method == "GET" and encoded:
            url = f"{url}?{encoded}"
        with self.opener.open(urllib.request.Request(url, data=data, method=method), timeout=30) as response:
            payload = json.load(response)
        code = payload.get("code")
        if allowed_codes and code in allowed_codes:
            return None
        if code != 0:
            raise RuntimeError(f"DolphinScheduler API failed: code={payload.get('code')} msg={payload.get('msg')}")
        return payload.get("data")


def deploy(
    env: dict[str, str],
    payload: dict,
    defaults: dict[str, str],
    workflow_code: int | None = None,
) -> tuple[int, str]:
    api = Api(env["DOLPHINSCHEDULER_URL"])
    api.request("POST", "/login", {
        "userName": env["DOLPHINSCHEDULER_USER"],
        "userPassword": env["DOLPHINSCHEDULER_PASSWORD"],
    })
    project_code = env["DOLPHINSCHEDULER_PROJECT_CODE"]
    existing = api.request(
        "GET",
        f"/projects/{project_code}/workflow-definition/query-by-name",
        {"name": payload["name"]},
        allowed_codes={50003},
    )
    global_params = payload["globalParams"]
    for item in global_params:
        item["value"] = defaults[item["prop"]]
    values = {
        "name": payload["name"],
        "description": payload["description"],
        "globalParams": global_params,
        "locations": payload["locations"],
        "timeout": payload["timeout"],
        "taskRelationJson": payload["taskRelationJson"],
        "taskDefinitionJson": payload["taskDefinitionJson"],
        "executionType": payload["executionType"],
    }
    if existing:
        if workflow_code is None:
            raise ValueError("workflow already exists; pass --workflow-code for an explicit update")
        values["releaseState"] = "ONLINE"
        release_path = f"/projects/{project_code}/workflow-definition/{workflow_code}/release"
        api.request("POST", release_path, {
            "releaseState": "OFFLINE", "name": payload["name"],
        })
        try:
            api.request(
                "PUT",
                f"/projects/{project_code}/workflow-definition/{workflow_code}",
                values,
            )
        except Exception:
            # 更新失败时恢复旧版本 ONLINE，避免一次部署错误让正式 Workflow 持续离线。
            api.request("POST", release_path, {
                "releaseState": "ONLINE", "name": payload["name"],
            })
            raise
        return workflow_code, "updated"
    if workflow_code is not None:
        raise ValueError("--workflow-code was provided, but the workflow does not exist")
    result = api.request("POST", f"/projects/{project_code}/workflow-definition", values)
    code = result["code"] if isinstance(result, dict) else int(result)
    api.request("POST", f"/projects/{project_code}/workflow-definition/{code}/release", {
        "releaseState": "ONLINE", "name": payload["name"],
    })
    return int(code), "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--model-as-of-date")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch-contract")
    parser.add_argument("--data-start-date", required=True)
    parser.add_argument("--workflow-code", type=int)
    args = parser.parse_args()
    root = "/data/projects/ecommerce-data-warehouse-m6"
    defaults = {
        "project_home": root,
        "datax_env": f"{root}/runtime/private/datax.env",
        "doris_env": f"{root}/runtime/private/doris.env",
        "doris_connector_jar": "/data/ecommerce-m6-runtime/lib/spark-doris-connector-spark-3.5-26.0.0.jar",
        "business_date": args.business_date,
        "model_as_of_date": args.model_as_of_date,
        "batch_id": args.batch_id,
        "run_id": args.run_id,
        "batch_contract": args.batch_contract,
        "data_start_date": args.data_start_date,
    }
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    required_parameters = {item["prop"] for item in payload.get("globalParams", [])}
    if "batch_contract" in required_parameters and not args.batch_contract:
        parser.error("--batch-contract is required by this workflow payload")
    if "model_as_of_date" in required_parameters and not args.model_as_of_date:
        parser.error("--model-as-of-date is required by this workflow payload")
    code, action = deploy(load_env(args.env_file), payload, defaults, args.workflow_code)
    print(f"WORKFLOW_DEPLOY_PASS action={action} code={code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
