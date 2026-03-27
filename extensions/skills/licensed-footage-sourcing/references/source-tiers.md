# Source Tiers

## Allowed First-Tier Sources

- `brand-owned`: 品牌或账号自己拍摄、购买、持有使用权的素材
- `stock-library`: 已购买或订阅并确认可商用的视频素材库
- `public-domain`: 明确进入公有领域，或明确允许当前用途的公共版权库
- `official-promo-footage`: 官方机构、品牌、产品发布方明确可引用或可嵌入的公开视频

## Conditional Sources

这些来源只有在用途、署名和许可边界都确认后，才可进入 `approved`：

- 政府或机构公开素材
- 新闻发布会公开视频
- 官方 YouTube / Bilibili / 新闻站素材

如果只是“网上能看到”，但没有看到可复用许可，不算通过。

## Disallowed Sources

- 普通创作者视频的搬运或二改
- 来源不明的聚合站、剪辑号、素材搬运号
- 许可状态不明的论坛、网盘、二次上传视频
- 任何需要“先下载再说”的灰色来源

## License Status

`source_manifest` 中统一使用这三个状态：

- `approved`: 许可清楚，可进入生产链
- `hold`: 许可不清楚，暂时不能用
- `rejected`: 明确不允许当前用途或风险过高

## Manifest Checklist

每条片段至少要补齐：

- `source_type`
- `source_name`
- `source_url`
- `license_status`
- `license_basis`
- `attribution_required`
- `usage_scope`
- `usage_notes`
- `fallback_query`

缺任一关键字段，都不算可执行素材。

## Editorial Guidance

- B-roll 优先承担情境、节奏和转场，不替代关键证据
- 如果某个片段只是“好看”，但对理解没有帮助，优先舍弃
- 对核心论点的证明，优先使用自有录屏、截图、实验结果或明确可验证证据
