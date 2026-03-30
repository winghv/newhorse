"""Tests for post-publish followup bootstrap."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_live_xiaohongshu_note_package(project_root: Path) -> None:
    (project_root / "research").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "note").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "retros").mkdir(parents=True, exist_ok=True)

    (project_root / "research" / "research-brief.md").write_text("# brief\n", encoding="utf-8")
    write_json(project_root / "planning" / "topic-selection.json", {"topic": "live note"})
    write_json(project_root / "angles" / "angle-brief.json", {"angle": "live"})
    (project_root / "assets" / "note" / "1.png").write_bytes(b"png")
    write_json(
        project_root / "content" / "xiaohongshu-note.json",
        {
            "platform": "xiaohongshu",
            "format": "note",
            "title": "发布前3道门禁",
            "note": "正文内容",
            "tags": ["AI工作流", "小红书运营"],
            "image_plan": [{"path": "assets/note/1.png"}],
        },
    )
    write_json(project_root / "review" / "competitive-scorecard.json", {"total_score": 31, "review_decision": "pass"})
    write_json(project_root / "review" / "review-gate.json", {"approval_status": "pass", "safe_to_publish": True})
    write_json(
        project_root / "publish" / "publish-manifest-prelive.json",
        {
            "platform": "xiaohongshu",
            "content_type": "note",
            "content_id": project_root.name,
            "account_name": "xhs-ready",
            "decision": "ready_for_live_publish",
            "publish_mode": "immediate_live_publish",
            "blocking_reasons": [],
        },
    )
    write_json(
        project_root / "publish" / "release-record.json",
        {
            "status": "live_submitted",
            "publish": {
                "latest_manifest_path": "publish/publish-manifest-prelive.json",
                "latest_result_path": "publish/publish-result-auto.json",
            },
        },
    )
    write_json(
        project_root / "publish" / "publish-result-auto.json",
        {
            "platform": "xiaohongshu",
            "content_type": "note",
            "content_id": project_root.name,
            "mode": "live",
            "status": "submitted",
            "decision": "ready_for_live_publish",
            "account": {"account_name": "xhs-ready", "status": "valid"},
            "metadata": {
                "title": "发布前3道门禁",
                "note": "正文内容",
                "tags": ["AI工作流", "小红书运营"],
            },
            "command_preview": ["sau", "xiaohongshu", "upload-note"],
            "blocking_reasons": [],
            "notes": [],
            "upload_stdout": "Xiaohongshu note upload submitted: 1 images",
            "upload_stderr": None,
        },
    )
    (project_root / "retros" / "retro-plan.md").write_text(
        "# Retro Plan\n\n- `T+2h`\n- `T+24h`\n- `T+48h`\n",
        encoding="utf-8",
    )
    (project_root / "retros" / "performance-summary.md").write_text(
        "# Performance Summary\n\n当前仍处于 `dry-run` 阶段。\n",
        encoding="utf-8",
    )
    write_json(
        project_root / "retros" / "next-experiment-brief.json",
        {
            "experiment_id": "xhs-followup",
            "measurement_windows": ["T+2h", "T+24h", "T+48h"],
            "next_action": "先观察评论区与主页访问。",
        },
    )


def test_bootstrap_post_publish_followup_creates_xhs_monitoring_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    audit_script = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "audit_artifacts.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    before_path = media_ops_root / "_registry" / "artifact-registry.before.json"
    run_command(
        [
            sys.executable,
            str(audit_script),
            "--media-ops-root",
            str(media_ops_root),
            "--output",
            str(before_path),
        ],
        repo_root,
    )
    before = json.loads(before_path.read_text(encoding="utf-8"))
    package_before = before["packages"][0]
    assert "comment_insights" in package_before["missing_recommended"]
    assert "profile_visit_signal" in package_before["missing_recommended"]
    assert "follow_conversion_readout" in package_before["missing_recommended"]

    result = run_command(
        [
            sys.executable,
            str(followup_script),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )
    payload = json.loads(result.stdout)

    comment_insights_path = Path(payload["comment_insights"])
    profile_visit_path = Path(payload["profile_visit_signal"])
    follow_conversion_path = Path(payload["follow_conversion_readout"])
    checklist_path = Path(payload["live_monitoring_checklist"])

    assert comment_insights_path.exists()
    assert profile_visit_path.exists()
    assert follow_conversion_path.exists()
    assert checklist_path.exists()

    comment_payload = json.loads(comment_insights_path.read_text(encoding="utf-8"))
    assert comment_payload["status"] == "pending_collection"
    assert [item["window"] for item in comment_payload["measurement_windows"]] == ["T+2h", "T+24h", "T+48h"]

    performance_summary = (project_root / "retros" / "performance-summary.md").read_text(encoding="utf-8")
    assert "已真实发布" in performance_summary
    assert "T+2h / T+24h / T+48h" in performance_summary

    after_path = media_ops_root / "_registry" / "artifact-registry.after.json"
    run_command(
        [
            sys.executable,
            str(audit_script),
            "--media-ops-root",
            str(media_ops_root),
            "--output",
            str(after_path),
        ],
        repo_root,
    )
    after = json.loads(after_path.read_text(encoding="utf-8"))
    package_after = after["packages"][0]
    assert "comment_insights" not in package_after["missing_recommended"]
    assert "profile_visit_signal" not in package_after["missing_recommended"]
    assert "follow_conversion_readout" not in package_after["missing_recommended"]


def test_bootstrap_manual_comment_ops_packet_creates_observation_log_and_playbook(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    comment_ops_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_comment_ops_packet.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command(
        [
            sys.executable,
            str(followup_script),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )

    result = run_command(
        [
            sys.executable,
            str(comment_ops_script),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )
    payload = json.loads(result.stdout)

    observation_log_path = Path(payload["manual_observation_log"])
    reply_playbook_path = Path(payload["comment_reply_playbook"])

    assert observation_log_path.exists()
    assert reply_playbook_path.exists()

    observation_log = json.loads(observation_log_path.read_text(encoding="utf-8"))
    assert observation_log["status"] == "pending_collection"
    assert observation_log["measurement_windows"][0]["window"] == "T+2h"
    assert observation_log["measurement_windows"][0]["metrics"]["profile_visits"] is None
    assert observation_log["measurement_windows"][0]["top_comments"] == []

    reply_playbook = reply_playbook_path.read_text(encoding="utf-8")
    assert "Template Request" in reply_playbook
    assert "Skeptical Pushback" in reply_playbook
    assert "3道门禁" in reply_playbook


def test_bootstrap_followup_note_package_creates_next_xhs_package(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command(
        [
            sys.executable,
            str(followup_script),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )

    result = run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )
    payload = json.loads(result.stdout)
    followup_root = Path(payload["project_root"])

    assert followup_root.exists()
    assert (followup_root / "research" / "research-brief.md").exists()
    assert (followup_root / "planning" / "topic-selection.json").exists()
    assert (followup_root / "angles" / "angle-brief.json").exists()
    assert (followup_root / "content" / "xiaohongshu-note.json").exists()

    topic_selection = json.loads((followup_root / "planning" / "topic-selection.json").read_text(encoding="utf-8"))
    assert topic_selection["selected_topic"]["cluster"] == "template_request"

    angle_brief = json.loads((followup_root / "angles" / "angle-brief.json").read_text(encoding="utf-8"))
    assert "检查清单" in angle_brief["objective"]

    note_packet = json.loads((followup_root / "content" / "xiaohongshu-note.json").read_text(encoding="utf-8"))
    assert note_packet["platform"] == "xiaohongshu"
    assert note_packet["format"] == "note"
    assert note_packet["publish_metadata"]["series_name"] == "发布门禁系列"
    assert len(note_packet["page_plan"]) >= 5


def test_bootstrap_followup_note_review_creates_scorecard_and_blocking_review_gate(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_review.py"
    )
    audit_script = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "audit_artifacts.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command([sys.executable, str(followup_script), "--project-root", str(project_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )

    followup_root = media_ops_root / "2026-03-28-xhs-live-followup-template-request"
    result = run_command(
        [
            sys.executable,
            str(review_script),
            "--project-root",
            str(followup_root),
        ],
        repo_root,
    )
    payload = json.loads(result.stdout)
    scorecard_path = Path(payload["competitive_scorecard"])
    review_gate_path = Path(payload["review_gate"])

    assert scorecard_path.exists()
    assert review_gate_path.exists()

    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    review_gate = json.loads(review_gate_path.read_text(encoding="utf-8"))
    assert scorecard["review_decision"] == "pass"
    assert scorecard["total_score"] >= 29
    assert review_gate["approval_status"] == "revise"
    assert review_gate["safe_to_publish"] is False
    assert any("视觉稿" in item for item in review_gate["required_fixes"])

    audit_output = media_ops_root / "_registry" / "artifact-registry.json"
    run_command(
        [
            sys.executable,
            str(audit_script),
            "--media-ops-root",
            str(media_ops_root),
            "--output",
            str(audit_output),
        ],
        repo_root,
    )
    audit_payload = json.loads(audit_output.read_text(encoding="utf-8"))
    package = next(pkg for pkg in audit_payload["packages"] if pkg["content_id"] == "2026-03-28-xhs-live-followup-template-request")
    assert package["lifecycle_status"] == "reviewed_not_ready"


def test_bootstrap_note_asset_brief_generates_prompts_and_image_plan(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    asset_brief_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_asset_brief.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command([sys.executable, str(followup_script), "--project-root", str(project_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )

    followup_root = media_ops_root / "2026-03-28-xhs-live-followup-template-request"
    result = run_command(
        [
            sys.executable,
            str(asset_brief_script),
            "--project-root",
            str(followup_root),
        ],
        repo_root,
    )
    payload = json.loads(result.stdout)
    asset_brief_path = Path(payload["asset_brief"])
    prompt_doc_path = Path(payload["prompt_doc"])

    assert asset_brief_path.exists()
    assert prompt_doc_path.exists()

    asset_brief = json.loads(asset_brief_path.read_text(encoding="utf-8"))
    assert asset_brief["platform"] == "xiaohongshu"
    assert len(asset_brief["pages"]) >= 5
    assert asset_brief["pages"][0]["output_path"].endswith("assets/note/page-01-cover.png")

    note_packet = json.loads((followup_root / "content" / "xiaohongshu-note.json").read_text(encoding="utf-8"))
    assert len(note_packet["image_plan"]) == len(note_packet["page_plan"])
    assert note_packet["image_plan"][0]["path"] == "assets/note/page-01-cover.png"

    prompt_doc = prompt_doc_path.read_text(encoding="utf-8")
    assert "Page 1" in prompt_doc
    assert "发布前3道门禁检查清单" in prompt_doc


def test_note_review_stays_blocked_when_image_plan_only_has_planned_paths(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    asset_brief_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_asset_brief.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_review.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command([sys.executable, str(followup_script), "--project-root", str(project_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )
    followup_root = media_ops_root / "2026-03-28-xhs-live-followup-template-request"
    run_command([sys.executable, str(asset_brief_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(review_script), "--project-root", str(followup_root)], repo_root)

    review_gate = json.loads((followup_root / "review" / "review-gate.json").read_text(encoding="utf-8"))
    assert review_gate["approval_status"] == "revise"
    assert review_gate["safe_to_publish"] is False


def test_render_note_cards_generates_pngs_and_unblocks_review(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    asset_brief_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_asset_brief.py"
    )
    render_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "render_note_cards.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_review.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command([sys.executable, str(followup_script), "--project-root", str(project_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )
    followup_root = media_ops_root / "2026-03-28-xhs-live-followup-template-request"
    run_command([sys.executable, str(asset_brief_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(render_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(review_script), "--project-root", str(followup_root)], repo_root)

    assert (followup_root / "assets" / "note" / "page-01-cover.png").exists()
    assert (followup_root / "assets" / "note" / "page-06-cta.png").exists()

    review_gate = json.loads((followup_root / "review" / "review-gate.json").read_text(encoding="utf-8"))
    assert review_gate["approval_status"] == "pass"
    assert review_gate["safe_to_publish"] is True


def test_followup_note_dry_run_manifest_uses_tag_suggestions(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    followup_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    asset_brief_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_asset_brief.py"
    )
    render_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "render_note_cards.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_review.py"
    )
    manifest_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command([sys.executable, str(followup_script), "--project-root", str(project_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )
    followup_root = media_ops_root / "2026-03-28-xhs-live-followup-template-request"
    run_command([sys.executable, str(asset_brief_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(render_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(review_script), "--project-root", str(followup_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(manifest_script),
            "--project-root",
            str(followup_root),
            "--account-name",
            "xhs-ready",
        ],
        repo_root,
    )

    manifest = json.loads((followup_root / "publish" / "publish-manifest-auto.json").read_text(encoding="utf-8"))
    assert manifest["metadata"]["tags"] == ["AI工作流", "自动化发布", "内容运营", "小红书运营", "发布SOP"]


def test_bootstrap_prepublish_retros_creates_followup_retros_and_clears_audit_gaps(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    post_publish_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_post_publish_followup.py"
    )
    prepublish_retros_script = (
        repo_root
        / "extensions"
        / "skills"
        / "performance-retrospective"
        / "scripts"
        / "bootstrap_prepublish_retros.py"
    )
    package_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_followup_note_package.py"
    )
    asset_brief_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_asset_brief.py"
    )
    render_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "render_note_cards.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "xiaohongshu-note-packaging"
        / "scripts"
        / "bootstrap_note_review.py"
    )
    publish_workflow_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )
    live_plan_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_live_execution_plan.py"
    )
    audit_script = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "audit_artifacts.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-28-xhs-live"
    make_live_xiaohongshu_note_package(project_root)

    run_command([sys.executable, str(post_publish_script), "--project-root", str(project_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(package_script),
            "--project-root",
            str(project_root),
            "--output-content-id",
            "2026-03-28-xhs-live-followup-template-request",
        ],
        repo_root,
    )

    followup_root = media_ops_root / "2026-03-28-xhs-live-followup-template-request"
    run_command([sys.executable, str(asset_brief_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(render_script), "--project-root", str(followup_root)], repo_root)
    run_command([sys.executable, str(review_script), "--project-root", str(followup_root)], repo_root)
    run_command(
        [
            sys.executable,
            str(publish_workflow_script),
            "--project-root",
            str(followup_root),
            "--account-name",
            "xhs-ready",
        ],
        repo_root,
    )
    run_command(
        [
            sys.executable,
            str(live_plan_script),
            "--project-root",
            str(followup_root),
            "--account-name",
            "xhs-ready",
        ],
        repo_root,
    )

    result = run_command(
        [
            sys.executable,
            str(prepublish_retros_script),
            "--project-root",
            str(followup_root),
        ],
        repo_root,
    )
    payload = json.loads(result.stdout)

    retro_plan_path = Path(payload["retro_plan"])
    performance_summary_path = Path(payload["performance_summary"])
    next_experiment_path = Path(payload["next_experiment_brief"])

    assert retro_plan_path.exists()
    assert performance_summary_path.exists()
    assert next_experiment_path.exists()

    retro_plan = retro_plan_path.read_text(encoding="utf-8")
    assert "Measurement Windows" in retro_plan
    assert "1 / 2 / 3" in retro_plan

    performance_summary = performance_summary_path.read_text(encoding="utf-8")
    assert "dry-run" in performance_summary
    assert "尚未真实发布" in performance_summary
    assert "ready_for_live_publish" in performance_summary

    next_experiment = json.loads(next_experiment_path.read_text(encoding="utf-8"))
    assert next_experiment["source_content_id"] == "2026-03-28-xhs-live-followup-template-request"
    assert next_experiment["parent_content_id"] == "2026-03-28-xhs-live"
    assert next_experiment["measurement_windows"] == ["T+2h", "T+24h", "T+48h"]

    audit_output = media_ops_root / "_registry" / "artifact-registry.json"
    run_command(
        [
            sys.executable,
            str(audit_script),
            "--media-ops-root",
            str(media_ops_root),
            "--output",
            str(audit_output),
        ],
        repo_root,
    )
    audit_payload = json.loads(audit_output.read_text(encoding="utf-8"))
    package = next(pkg for pkg in audit_payload["packages"] if pkg["content_id"] == "2026-03-28-xhs-live-followup-template-request")
    assert "retro_plan" not in package["missing_recommended"]
    assert "performance_summary" not in package["missing_recommended"]
    assert "next_experiment_brief" not in package["missing_recommended"]
    assert package["lifecycle_status"] == "ready_for_publish"
