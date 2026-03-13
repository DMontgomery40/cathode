"""Cathode MCP server."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ResourceError
from mcp.types import ToolAnnotations
from pydantic import Field

from core.branding import PRODUCT_DESCRIPTION, PRODUCT_NAME
from core.intake import (
    BriefElicitationInput,
    build_brief_from_intent,
    merge_elicitation_into_brief,
    missing_brief_fields,
)
from core.job_runner import cancel_job, create_make_video_job, create_rerun_stage_job, get_job_status, list_project_jobs
from core.project_store import collect_project_artifacts, list_projects, load_plan
from core.runtime import (
    PROJECTS_DIR,
    choose_llm_provider,
    resolve_image_profile,
    resolve_tts_profile,
    resolve_video_profile,
)

SERVER_INSTRUCTIONS = (
    "Cathode turns a user's intent into a local video project. "
    "Use make_video for new work, use get_job_status for long-running operations, "
    "and read project resources when you need the full plan or artifact inventory."
)


def _transport_from_env() -> str:
    return str(os.getenv("CATHODE_MCP_TRANSPORT") or "stdio").strip().lower()


def _host_from_env() -> str:
    return str(os.getenv("CATHODE_MCP_HOST") or "127.0.0.1").strip()


def _port_from_env() -> int:
    return int(os.getenv("CATHODE_MCP_PORT") or "8765")


def _path_from_env() -> str:
    value = str(os.getenv("CATHODE_MCP_HTTP_PATH") or "/mcp").strip()
    return value if value.startswith("/") else f"/{value}"


def _error_response(
    *,
    suggestion: str,
    message: str,
    retryable: bool,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "status": "error",
        "retryable": retryable,
        "suggestion": suggestion,
        "error": {"message": message},
    }
    payload.update(extra)
    return payload


def _project_status(project_name: str, include_jobs: bool = False) -> dict[str, Any]:
    project_dir = PROJECTS_DIR / project_name
    plan = load_plan(project_dir)
    if not plan:
        return {
            "project_name": project_name,
            "project_dir": str(project_dir),
            "has_plan": False,
            "scene_count": 0,
            "last_video_path": None,
            "jobs": [],
        }
    jobs = list_project_jobs(project_dir) if include_jobs else []
    meta = plan.get("meta", {})
    return {
        "project_name": project_name,
        "project_dir": str(project_dir),
        "has_plan": True,
        "scene_count": len(plan.get("scenes", [])),
        "last_video_path": meta.get("video_path"),
        "llm_provider": meta.get("llm_provider"),
        "jobs": jobs,
    }


def build_server() -> FastMCP:
    """Create the FastMCP server instance."""
    mcp = FastMCP(
        name=PRODUCT_NAME,
        instructions=SERVER_INSTRUCTIONS,
        host=_host_from_env(),
        port=_port_from_env(),
        streamable_http_path=_path_from_env(),
        stateless_http=False,
        json_response=False,
    )

    @mcp.prompt(
        name="prepare_video_request",
        title="Prepare A Cathode Video Request",
        description="Use this when the user has a rough goal and you need to gather enough detail before calling make_video.",
    )
    def prepare_video_request(intent: str) -> str:
        return (
            "Collect only the details needed to make a strong first Cathode render.\n"
            f"User intent: {intent}\n\n"
            "Ask for:\n"
            "- who the video is for\n"
            "- the source material, notes, or facts the video should rely on\n"
            "- target runtime if it matters\n"
            "- optional visual style guidance\n\n"
            "Once you have that, call make_video."
        )

    @mcp.resource(
        "project://{project_name}/plan",
        name="project-plan",
        title="Project Plan",
        description="Read the normalized plan.json for a Cathode project. Use this when you need the full storyboard or persisted metadata.",
        mime_type="application/json",
    )
    def project_plan(project_name: str) -> str:
        project_dir = PROJECTS_DIR / project_name
        plan = load_plan(project_dir)
        if not plan:
            raise ResourceError(f"Project not found or missing plan.json: {project_name}")
        return json.dumps(plan, indent=2)

    @mcp.resource(
        "project://{project_name}/artifacts",
        name="project-artifacts",
        title="Project Artifacts",
        description="Read a compact inventory of local files generated for a Cathode project.",
        mime_type="application/json",
    )
    def project_artifacts(project_name: str) -> str:
        project_dir = PROJECTS_DIR / project_name
        if not project_dir.exists():
            raise ResourceError(f"Project not found: {project_name}")
        return json.dumps(collect_project_artifacts(project_dir), indent=2)

    @mcp.tool(
        name="make_video",
        description=(
            "Create a new Cathode video project from natural-language intent. "
            "Use this for end-to-end video generation. It may inspect a bounded local workspace when workspace_path or source_paths are provided, "
            "may ask a few follow-up questions through MCP elicitation if the brief is too thin, and starts a background job instead of blocking until render completes."
        ),
        annotations=ToolAnnotations(
            title="Make Video",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def make_video(
        intent: Annotated[str, Field(description="What the video should do. Example: make a demo video for YC.")],
        ctx: Context,
        project_name: Annotated[str | None, Field(description="Optional project folder name.", default=None)] = None,
        source_text: Annotated[str | None, Field(description="Optional notes, facts, or script text to ground the video.", default=None)] = None,
        source_paths: Annotated[list[str] | None, Field(description="Optional explicit file paths to inspect as source material.", default=None)] = None,
        workspace_path: Annotated[str | None, Field(description="Optional workspace root to inspect using a bounded allowlist of common text files.", default=None)] = None,
        footage_paths: Annotated[list[str] | None, Field(description="Optional local video clip paths to import and use as supplied footage.", default=None)] = None,
        footage_manifest: Annotated[list[dict[str, Any]] | None, Field(description="Optional structured footage manifest with local clip paths, labels, and review notes.", default=None)] = None,
        style_reference_paths: Annotated[list[str] | None, Field(description="Optional image paths used as style references for the whole project.", default=None)] = None,
        source_mode: Annotated[Literal["ideas_notes", "source_text", "final_script"] | None, Field(description="Optional source handling mode override.", default=None)] = None,
        video_goal: Annotated[str | None, Field(description="Optional explicit video goal override.", default=None)] = None,
        audience: Annotated[str | None, Field(description="Optional audience override.", default=None)] = None,
        target_length_minutes: Annotated[float | None, Field(description="Optional runtime target in minutes.", default=None, ge=0.5, le=20.0)] = None,
        tone: Annotated[str | None, Field(description="Optional narration tone override.", default=None)] = None,
        visual_style: Annotated[str | None, Field(description="Optional visual style override.", default=None)] = None,
        must_include: Annotated[str | None, Field(description="Optional required content or scenes.", default=None)] = None,
        must_avoid: Annotated[str | None, Field(description="Optional constraints or content to avoid.", default=None)] = None,
        ending_cta: Annotated[str | None, Field(description="Optional closing CTA.", default=None)] = None,
        composition_mode: Annotated[Literal["classic", "motion_only", "hybrid"] | None, Field(description="Optional composition/render mode override.", default=None)] = None,
        visual_source_strategy: Annotated[Literal["images_only", "mixed_media", "video_preferred"] | None, Field(description="Optional visuals strategy override.", default=None)] = None,
        available_footage: Annotated[str | None, Field(description="Optional footage notes or clip availability.", default=None)] = None,
        app_url: Annotated[str | None, Field(description="Optional running app URL for demo-backed capture flows.", default=None)] = None,
        launch_command: Annotated[str | None, Field(description="Optional app launch command for demo-backed capture flows.", default=None)] = None,
        expected_url: Annotated[str | None, Field(description="Optional app URL the demo-backed agent should wait for after launch.", default=None)] = None,
        preferred_agent: Annotated[Literal["codex", "claude"] | None, Field(description="Optional preferred local agent CLI for demo-backed capture flows.", default=None)] = None,
        repo_url: Annotated[str | None, Field(description="Optional repo URL to visit during demo-backed capture flows.", default=None)] = None,
        flow_hints: Annotated[list[str] | None, Field(description="Optional short guidance bullets for what the demo-backed agent should show.", default=None)] = None,
        llm_provider: Annotated[str | None, Field(description="Optional storyboard provider override.", default=None)] = None,
        image_provider: Annotated[Literal["replicate", "local", "manual"] | None, Field(description="Optional image provider override.", default=None)] = None,
        image_generation_model: Annotated[str | None, Field(description="Optional image generation model override or local Hugging Face repo id/path.", default=None)] = None,
        video_provider: Annotated[Literal["manual", "local", "agent"] | None, Field(description="Optional video provider override.", default=None)] = None,
        video_generation_model: Annotated[str | None, Field(description="Optional local video model label or path override.", default=None)] = None,
        tts_provider: Annotated[str | None, Field(description="Optional TTS provider override.", default=None)] = None,
        tts_voice: Annotated[str | None, Field(description="Optional TTS voice override.", default=None)] = None,
        tts_speed: Annotated[float | None, Field(description="Optional TTS speed override.", default=None, ge=0.25, le=4.0)] = None,
        run_until: Annotated[Literal["storyboard", "assets", "render"], Field(description="How far Cathode should run before stopping.", default="render")] = "render",
        overwrite: Annotated[bool, Field(description="If true, replace an existing project folder with the same name.", default=False)] = False,
    ) -> dict[str, Any]:
        try:
            provider = choose_llm_provider(llm_provider)
        except ValueError as exc:
            return _error_response(
                message=str(exc),
                suggestion="Set ANTHROPIC_API_KEY or OPENAI_API_KEY, then retry.",
                retryable=False,
                current_stage="queued",
                job_id="",
                project_name=project_name or "",
                project_dir="",
            )

        brief, metadata = build_brief_from_intent(
            intent=intent,
            project_name=project_name,
            source_text=source_text,
            workspace_path=workspace_path,
            source_paths=source_paths,
            footage_paths=footage_paths,
            footage_manifest=footage_manifest,
            brief_overrides={
                "source_mode": source_mode,
                "video_goal": video_goal,
                "audience": audience,
                "target_length_minutes": target_length_minutes,
                "tone": tone,
                "visual_style": visual_style,
                "must_include": must_include,
                "must_avoid": must_avoid,
                "ending_cta": ending_cta,
                "composition_mode": composition_mode,
                "visual_source_strategy": visual_source_strategy,
                "available_footage": available_footage,
                "style_reference_paths": style_reference_paths or [],
            },
        )

        if missing_brief_fields(brief):
            elicit_result = await ctx.elicit(
                message=(
                    "I can start the video, but I still need a bit more grounding. "
                    "Please provide the audience and enough source material to avoid guessing."
                ),
                schema=BriefElicitationInput,
            )
            if getattr(elicit_result, "action", "cancel") != "accept" or not getattr(elicit_result, "data", None):
                return _error_response(
                    message="Video creation was cancelled before the brief was complete.",
                    suggestion="Retry make_video and provide audience plus source material.",
                    retryable=True,
                    current_stage="queued",
                    job_id="",
                    project_name=brief["project_name"],
                    project_dir=str(PROJECTS_DIR / brief["project_name"]),
                )
            brief = merge_elicitation_into_brief(brief, elicit_result.data)

        resolved_workspace_path = str(metadata.get("workspace_context", {}).get("workspace_path") or workspace_path or "").strip() or None

        image_profile = resolve_image_profile(
            {
                "provider": image_provider,
                "generation_model": image_generation_model,
            }
        )
        video_profile = resolve_video_profile(
            {
                "provider": video_provider,
                "generation_model": video_generation_model,
            }
        )
        tts_profile = resolve_tts_profile(
            {
                "provider": tts_provider,
                "voice": tts_voice,
                "speed": tts_speed,
            }
        )

        job = create_make_video_job(
            project_name=brief["project_name"],
            brief=brief,
            run_until=run_until,
            provider=provider,
            image_profile=image_profile,
            video_profile=video_profile,
            agent_demo_profile={
                key: value
                for key, value in {
                    "workspace_path": resolved_workspace_path,
                    "app_url": app_url,
                    "launch_command": launch_command,
                    "expected_url": expected_url,
                    "preferred_agent": preferred_agent,
                    "repo_url": repo_url,
                    "flow_hints": flow_hints,
                }.items()
                if value not in (None, "", [])
            } or None,
            tts_profile=tts_profile,
            overwrite=overwrite,
        )
        job["status"] = "queued"
        job["current_stage"] = "queued"
        job["brief"] = brief
        job["workspace_context"] = metadata["workspace_context"]
        return job

    @mcp.tool(
        name="get_job_status",
        description=(
            "Check the current status of a Cathode background job. "
            "Use this after make_video or rerun_stage to track long-running storyboard, asset, or render work."
        ),
        annotations=ToolAnnotations(
            title="Get Job Status",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def get_job_status_tool(
        job_id: Annotated[str, Field(description="The Cathode background job id.")],
        project_name: Annotated[str | None, Field(description="Optional project name when you want to scope the lookup.", default=None)] = None,
    ) -> dict[str, Any]:
        return get_job_status(job_id, project_name=project_name)

    @mcp.tool(
        name="cancel_job",
        description=(
            "Cancel a running Cathode background job. "
            "Use this when a render or asset generation run is no longer wanted. This stops the worker process and marks the job cancelled."
        ),
        annotations=ToolAnnotations(
            title="Cancel Job",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    def cancel_job_tool(
        job_id: Annotated[str, Field(description="The Cathode background job id to cancel.")],
        project_name: Annotated[str | None, Field(description="Optional project name when you want to scope the lookup.", default=None)] = None,
    ) -> dict[str, Any]:
        return cancel_job(job_id, project_name=project_name)

    @mcp.tool(
        name="rerun_stage",
        description=(
            "Start a new background job that reruns one stage of an existing Cathode project. "
            "Use storyboard to rebuild scenes from saved metadata, assets to regenerate local media, or render to produce a new MP4 from existing assets."
        ),
        annotations=ToolAnnotations(
            title="Rerun Stage",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    def rerun_stage(
        project_name: Annotated[str, Field(description="Existing Cathode project name.")],
        stage: Annotated[Literal["storyboard", "assets", "render"], Field(description="Which stage to rerun.")],
        force: Annotated[bool, Field(description="If true, regenerate existing scene assets instead of only filling missing ones.", default=False)] = False,
    ) -> dict[str, Any]:
        return create_rerun_stage_job(project_name=project_name, stage=stage, force=force)

    @mcp.tool(
        name="list_projects",
        description=(
            "List Cathode projects available under the local projects directory. "
            "Use this when you need to discover existing projects before reading resources or rerunning a stage."
        ),
        annotations=ToolAnnotations(
            title="List Projects",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def list_projects_tool(
        include_jobs: Annotated[bool, Field(description="If true, include persisted job metadata for each project.", default=False)] = False,
    ) -> dict[str, Any]:
        projects = [_project_status(name, include_jobs=include_jobs) for name in list_projects()]
        return {
            "status": "ok",
            "retryable": False,
            "suggestion": "",
            "projects": projects,
        }

    return mcp


def main() -> None:
    """CLI entrypoint for the Cathode MCP server."""
    parser = argparse.ArgumentParser(description="Run the Cathode MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=_transport_from_env(),
        help="Transport to use for the Cathode MCP server.",
    )
    args = parser.parse_args()
    server = build_server()
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
