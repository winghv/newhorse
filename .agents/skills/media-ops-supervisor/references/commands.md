# Media Ops Supervisor — 命令参考

> 整条链路只有 3 个真门禁：**creative-gate**（生产前）、**assembly-qa-gate**（审校前）、**publish-gate**（发布前）。下方命令按门禁分组。

## creative-gate（生产前 · 反同质化硬门禁）

```bash
# 1) 生成轮换契约：自动排除近 N 期已用装置/视觉语法/证据/开场，算出 forbidden_repeats
python3 extensions/skills/creative-divergence/scripts/build_divergence_contract.py \
  --content-id <content-id> --commit

# 2) 硬去重：抽指纹与近 N 期比，算真实 similarity_score（退出码 0=pass 1=revise 2=block）
python3 extensions/skills/competitive-review/scripts/build_template_fatigue_report.py \
  --content-id <content-id> --register
```

## 生产 · 视觉（电影质感）

```bash
# 生成带电影语言（镜头/光影/构图/景深/色彩）的 shot plan，并产出多样性统计
python3 extensions/skills/video-asset-planning/scripts/build_minimax_shot_plan.py \
  --content-id <content-id>

# 转场/特效轮换计划（按场景类别在转场库内轮换 + 视觉语法偏好）
python3 extensions/skills/video-postproduction-assembly/scripts/build_transition_plan.py \
  --content-id <content-id>
```

## assembly-qa-gate（审校前）

```bash
# 视觉生产门禁：含生成图真实性、素材利用率、电影 prompt 多样性等子检查
python3 extensions/skills/video-asset-planning/scripts/build_visual_production_gate.py \
  --content-id <content-id>
```

## 诊断 · 产物治理

```bash
python3 extensions/skills/media-ops-orchestration/scripts/audit_artifacts.py --media-ops-root data/media-ops
python3 extensions/skills/media-ops-orchestration/scripts/build_publish_queue.py --media-ops-root data/media-ops
python3 extensions/skills/media-ops-orchestration/scripts/run_artifact_maintenance.py --media-ops-root data/media-ops --apply
```

## publish-gate · 发布

```bash
# workflow quality gate（publish-gate 聚合器）
python3 extensions/skills/media-ops-orchestration/scripts/build_workflow_quality_gate.py --project-root data/media-ops/<content-id>

# 生成发布包
python3 extensions/skills/multi-platform-publishing/scripts/build_publish_manifest.py --project-root data/media-ops/<content-id>

# 执行发布（默认 dry-run；真实发布需 --live）
python3 extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py \
  --project-root data/media-ops/<content-id> --account-name <account>
```

## Specialist 映射

| Specialist | Skill |
|------------|-------|
| trend-researcher | content-research |
| benchmark-analyst | benchmark-analysis |
| topic-strategist | topic-selection |
| angle-designer | angle-design |
| content-producer | content-production |
| video-production-director | video-postproduction-assembly |
| competitive-reviewer | competitive-review |
| compliance-reviewer | content-review-gate |
| distribution-operator | media-publish |
| performance-analyst | performance-retrospective |

## 快速定位

| 查找 | 文件 |
|------|------|
| 项目卡在哪 | `planning/stage-status.json` |
| 能否发布 | `publish/release-record.json` |
| 竞争审校结果 | `review/competitive-scorecard.json` |
| 视频装配状态 | `content/postproduction/render-manifest.json` |
| B-roll 素材 | `sources/source-manifest.json` |
| 发布队列 | `_registry/publish-queue.json` |
