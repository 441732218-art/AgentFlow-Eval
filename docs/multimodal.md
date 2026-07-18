# 多模态评估

AgentFlow-Eval 支持图像、PDF、表格与文本等文件的上传、内容提取与多模态评分。

## 支持格式（5+）

| 类型 | 扩展名 | 提取能力 |
|------|--------|----------|
| 图像 | png, jpg, jpeg, gif, webp, bmp | 尺寸/色均值/亮度直方图；可选 CLIP/ViT |
| PDF | pdf | 分页文本（pypdf / PyPDF2） |
| 表格 | csv, tsv, xlsx, xlsm | Markdown 表 + 结构化 sample_rows |
| 文本 | txt, md, json, log | UTF-8 解码 / JSON 美化 |

## 架构

```
Upload ──► Storage (local | S3/MinIO)
              │
              ▼
         Extractors (image / pdf / sheet / text)
              │
              ▼
         MediaAsset (DB: text + features JSON)
              │
              ▼
         Evaluator
           ├─ rule_multimodal (无 Key 可用)
           └─ vision_llm (GPT-4V / gpt-4o-mini 等 OpenAI 兼容)
```

## 配置

```bash
# 存储
STORAGE_BACKEND=local          # local | s3 | minio
LOCAL_STORAGE_PATH=data/uploads
MEDIA_MAX_UPLOAD_BYTES=20971520

# MinIO / S3
# STORAGE_BACKEND=minio
# S3_ENDPOINT_URL=http://localhost:9000
# S3_BUCKET=agentflow
# S3_ACCESS_KEY=minioadmin
# S3_SECRET_KEY=minioadmin
# S3_REGION=us-east-1

# 视觉模型（OpenAI 兼容）
OPENAI_API_KEY=sk-...
VISION_MODEL=gpt-4o-mini
```

依赖（`requirements.txt`）：`Pillow`, `pypdf`, `openpyxl`。  
可选：`boto3`（S3）、`torch`+`transformers`/`open_clip`（真 CLIP 向量）。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/media/formats` | 支持的扩展名与后端 |
| POST | `/api/v1/media/upload` | multipart 上传；`extract=true` 默认提取 |
| GET | `/api/v1/media/{id}` | 资产元数据 |
| POST | `/api/v1/media/{id}/extract` | 重新提取 |
| POST | `/api/v1/media/{id}/evaluate` | 多模态评分 |
| GET | `/api/v1/media?task_id=` | 列表 |

### 上传示例

```bash
curl -X POST http://localhost:8000/api/v1/media/upload \
  -F "file=@chart.png" \
  -F "task_id=<optional-task-id>" \
  -F "extract=true"
```

### 评估示例

```bash
curl -X POST http://localhost:8000/api/v1/media/<asset_id>/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "图中趋势如何？",
    "expected_text": "上升",
    "use_vision_llm": true
  }'
```

响应维度（规则/视觉通用）：

- `content_coverage` — 内容是否有效提取  
- `text_relevance` — 与 expected/query 的词重叠  
- `structure_quality` — 页数/表格/特征完整度  
- `total` — 平均分 0–100  

无 API Key 或视觉调用失败时自动 **降级为 rule_multimodal**（`degraded=true`）。

## 图像特征

默认（Pillow）：

- `width` / `height` / `mean_rgb` / `luma_hist8`

可选 CLIP：

- 安装 `open_clip` 或 `transformers` 后自动尝试  
- 存储 `clip_preview`（前 16 维）+ `clip_norm`，避免把完整向量塞进 JSON

`compare_image_features()` 可对两张图做直方图/CLIP 余弦相似度。

## 数据库

表 `media_assets`（迁移 `008_media_assets`）：

- 存储键、SHA256、kind、提取文本、features、可选 `task_id` / `test_suite_id`

```bash
cd backend && alembic upgrade head
```

SQLite 开发：`create_all` 会建表。

## 权限

| 操作 | 权限 |
|------|------|
| 上传 | `task:create` |
| 读取/列表/格式 | `task:read` |
| 重提取 | `task:update` |
| 评估 | `evaluation:submit` |

## 测试

```bash
cd backend
pip install Pillow pypdf openpyxl
pytest tests/unit/test_multimodal.py tests/unit/test_media_api.py -q
```

## 代码入口

| 路径 | 说明 |
|------|------|
| `app/core/multimodal/storage.py` | Local + S3/MinIO |
| `app/core/multimodal/extractors/*` | 图像/PDF/表/文本 |
| `app/core/multimodal/evaluator.py` | 规则 + Vision LLM |
| `app/api/v1/endpoints/media.py` | REST API |
| `app/models/media_asset.py` | ORM |
