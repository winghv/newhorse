---
name: media-ops-team
description: Extend or maintain the built-in media operations agent team in this repo. Use when modifying media-ops templates, workflow skills, publishing safety gates, runtime metadata, or UI flows that create/apply the team.
---

# Media Ops Team

## Overview

This repo contains a built-in media operations agent team implemented through:

- `extensions/agents/`
- `extensions/skills/`
- homepage template selection
- project template application

`.agents/` is not the runtime source of truth.
Treat it as developer-tool metadata that should explain or package the runtime behavior defined in `extensions/agents/` and `extensions/skills/`.

## When to Use

- adding or editing media operations templates
- changing research/benchmark/angle/production/review/publish/retros workflows
- splitting video production into short-video and mid/long-video tracks
- adding or refining autonomous-vs-supervisor execution modes for the media team
- codifying deterministic video postproduction steps into reusable skills/scripts
- adding platform-specific output skills so final deliverables are not generic cross-posts
- tightening publishing safety or approval behavior
- fixing runtime mismatches between template metadata and project `preferred_cli`
- updating tests for homepage or agent config flows

## Workflow

1. Read `docs/media-ops-team.md`.
2. Read `docs/media-ops-workflow-spec.md`.
3. If changing runtime behavior, inspect:
   - `apps/api/app/services/cli/config_loader.py`
   - `apps/api/app/api/agents.py`
   - `apps/web/app/[locale]/page.tsx`
   - `apps/web/components/AgentConfig.tsx`
4. If changing delegated specialists, inspect `apps/api/app/services/cli/delegation.py`.
5. For video workflow changes, keep `content-production` as the routing layer and move platform-specific output requirements into dedicated skills.
6. If the workflow needs to reproduce a hand-run production step reliably, prefer adding a script under the relevant skill instead of leaving it as prose only.
7. If adding a video-specialist template, wire it into both `extensions/agents/` and `delegation.py`.
8. Treat autonomous and supervisor-led modes as first-class workflow configurations, not ad hoc operator behavior.
9. For generated media, define an asset-planning or budget gate before any expensive model call. Prefer real footage, screenshots, and deterministic editing before text-to-video.
10. Keep publishing guarded by approval and dry-run rules.
11. Run backend tests and frontend build.
12. Run Playwright tests when UI flows change.

## Guardrails

- Do not hardcode secrets or cookies.
- Do not let missing approval fall through to live publishing.
- Do not add platform templates that reuse identical copy across platforms.
- Do not burn paid video-generation quota on scripts that have not passed quality review.
- Keep workflow outputs structured so downstream stages can consume them.
- Do not call a video pipeline “done” without render manifests and verification artifacts.
