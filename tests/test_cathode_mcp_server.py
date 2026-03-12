from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import AnyUrl


def _write_wrapper_script(path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    script = textwrap.dedent(
        """
            import os
            import sys
            from pathlib import Path

            sys.path.insert(0, __REPO_ROOT__)

            import cathode_mcp_server as cathode

            def fake_choose_llm_provider(preferred=None):
                return preferred or "openai"

            def fake_create_make_video_job(**kwargs):
                project_name = kwargs["project_name"]
                project_dir = cathode.PROJECTS_DIR / project_name
                return {
                    "status": "queued",
                    "job_id": "job-123",
                    "project_name": project_name,
                    "project_dir": str(project_dir),
                    "current_stage": "queued",
                    "retryable": False,
                    "suggestion": "",
                    "requested_stage": kwargs.get("run_until", "render"),
                    "pid": 4242,
                    "result": {"retryable": False, "suggestion": ""},
                }

            def fake_get_job_status(job_id, project_name=None):
                if job_id == "missing":
                    return {
                        "status": "error",
                        "job_id": job_id,
                        "project_name": project_name or "",
                        "project_dir": "",
                        "current_stage": "unknown",
                        "retryable": False,
                        "suggestion": "Check the job id and try again.",
                        "requested_stage": "",
                        "pid": None,
                        "result": {},
                        "error": {"message": "Job not found: missing"},
                    }
                return {
                    "status": "succeeded",
                    "job_id": job_id,
                    "project_name": project_name or "demo_project",
                    "project_dir": str(cathode.PROJECTS_DIR / "demo_project"),
                    "current_stage": "done",
                    "retryable": False,
                    "suggestion": "",
                    "requested_stage": "render",
                    "pid": None,
                    "result": {"video_path": str(cathode.PROJECTS_DIR / "demo_project" / "demo_project.mp4")},
                    "error": None,
                }

            def fake_cancel_job(job_id, project_name=None):
                return {
                    "status": "cancelled",
                    "job_id": job_id,
                    "project_name": project_name or "demo_project",
                    "project_dir": str(cathode.PROJECTS_DIR / "demo_project"),
                    "current_stage": "cancelled",
                    "retryable": True,
                    "suggestion": "Retry the job when ready.",
                    "requested_stage": "render",
                    "pid": None,
                    "result": {"retryable": True, "suggestion": "Retry the job when ready."},
                    "error": None,
                }

            def fake_create_rerun_stage_job(**kwargs):
                return {
                    "status": "queued",
                    "job_id": "job-rerun",
                    "project_name": kwargs["project_name"],
                    "project_dir": str(cathode.PROJECTS_DIR / kwargs["project_name"]),
                    "current_stage": "queued",
                    "retryable": False,
                    "suggestion": "",
                    "requested_stage": kwargs["stage"],
                    "pid": 5252,
                    "result": {"retryable": False, "suggestion": ""},
                    "error": None,
                }

            def fake_load_plan(project_dir):
                return {
                    "meta": {
                        "project_name": Path(project_dir).name,
                        "llm_provider": "openai",
                        "video_path": str(Path(project_dir) / "demo_project.mp4"),
                    },
                    "scenes": [
                        {
                            "id": 0,
                            "title": "Intro",
                            "narration": "Hello",
                            "visual_prompt": "Prompt",
                            "scene_type": "image",
                        }
                    ],
                }

            def fake_collect_project_artifacts(project_dir):
                return {
                    "project_dir": str(project_dir),
                    "plan_path": str(Path(project_dir) / "plan.json"),
                    "images": [],
                    "clips": [],
                    "audio": [],
                    "previews": [],
                    "style_refs": [],
                    "videos": [str(Path(project_dir) / "demo_project.mp4")],
                    "jobs": [],
                }

            def fake_list_projects():
                return ["demo_project"]

            def fake_list_project_jobs(project_dir):
                return [{"job_id": "job-123", "status": "queued"}]

            cathode.choose_llm_provider = fake_choose_llm_provider
            cathode.create_make_video_job = fake_create_make_video_job
            cathode.get_job_status = fake_get_job_status
            cathode.cancel_job = fake_cancel_job
            cathode.create_rerun_stage_job = fake_create_rerun_stage_job
            cathode.load_plan = fake_load_plan
            cathode.collect_project_artifacts = fake_collect_project_artifacts
            cathode.list_projects = fake_list_projects
            cathode.list_project_jobs = fake_list_project_jobs

            cathode.PROJECTS_DIR.mkdir(exist_ok=True)
            server = cathode.build_server()
            server.run(transport=os.environ.get("CATHODE_TEST_TRANSPORT", "stdio"))
            """
    )
    path.write_text(script.replace("__REPO_ROOT__", repr(str(repo_root))))


async def _accept_elicitation(_context, _params):
    return types.ElicitResult(
        action="accept",
        content={
            "audience": "YC partners",
            "source_material": "Founder notes about the product and why it matters.",
            "target_length_minutes": 1.5,
            "visual_style": "clean editorial demo",
        },
    )


def test_stdio_server_supports_tools_and_resources(tmp_path):
    wrapper = tmp_path / "stub_server.py"
    _write_wrapper_script(wrapper)

    async def _run() -> None:
        server_params = StdioServerParameters(command=sys.executable, args=[str(wrapper)])
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {"make_video", "get_job_status", "cancel_job", "rerun_stage", "list_projects"} <= names

                make_result = await session.call_tool(
                    "make_video",
                    {
                        "intent": "Make a demo video for YC",
                        "audience": "YC partners",
                        "source_text": "Founder notes and product details.",
                        "footage_manifest": [
                            {
                                "id": "run_review",
                                "path": "/tmp/run_review.mp4",
                                "label": "Run review overlay",
                                "review_status": "warn",
                            }
                        ],
                    },
                )
                assert make_result.structuredContent["status"] == "queued"
                assert make_result.structuredContent["project_name"] == "Make_a_demo_video_for_YC"
                assert make_result.structuredContent["brief"]["footage_manifest"][0]["id"] == "run_review"

                status_result = await session.call_tool("get_job_status", {"job_id": "missing"})
                assert status_result.structuredContent["status"] == "error"
                assert "Check the job id" in status_result.structuredContent["suggestion"]

                resources = await session.list_resource_templates()
                uris = {str(resource.uriTemplate) for resource in resources.resourceTemplates}
                assert "project://{project_name}/plan" in uris
                assert "project://{project_name}/artifacts" in uris

                resource = await session.read_resource(AnyUrl("project://demo_project/plan"))
                assert "project_name" in resource.contents[0].text

        return None

    asyncio.run(_run())


def test_streamable_http_server_supports_elicitation(tmp_path):
    wrapper = tmp_path / "stub_server.py"
    _write_wrapper_script(wrapper)

    port = 8876
    env = dict(
        os.environ,
        CATHODE_TEST_TRANSPORT="streamable-http",
        CATHODE_MCP_TRANSPORT="streamable-http",
        CATHODE_MCP_PORT=str(port),
        CATHODE_MCP_HOST="127.0.0.1",
        CATHODE_MCP_HTTP_PATH="/mcp",
    )
    process = subprocess.Popen(
        [sys.executable, str(wrapper)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.2)
        else:
            raise AssertionError("Timed out waiting for HTTP MCP server to start")

        async def _run() -> None:
            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
                async with ClientSession(read, write, elicitation_callback=_accept_elicitation) as session:
                    await session.initialize()

                    make_result = await session.call_tool(
                        "make_video",
                        {
                            "intent": "Make a demo video for YC",
                        },
                    )
                    assert make_result.structuredContent["status"] == "queued"
                    assert make_result.structuredContent["brief"]["audience"] == "YC partners"

                    rerun_result = await session.call_tool(
                        "rerun_stage",
                        {"project_name": "demo_project", "stage": "render"},
                    )
                    assert rerun_result.structuredContent["job_id"] == "job-rerun"

        asyncio.run(_run())
    finally:
        process.terminate()
        process.wait(timeout=10)
