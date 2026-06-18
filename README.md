# AI Customer Service Backend

一个基于 FastAPI 的简单 AI 智能客服后端示例，适合本地演示和接口联调。

## 运行环境

- Windows 11
- Python 3.10 及以上
- 当前环境已实测通过 Python 3.13

## 快速启动

在 PowerShell 中进入项目根目录：

```powershell
cd "c:\Users\dell\Desktop\AICustomerService"
```

创建并激活虚拟环境：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 提示脚本执行被禁止，可先执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

启动服务：

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## 启动后访问

- 首页: http://127.0.0.1:8000/
- 健康检查: http://127.0.0.1:8000/health
- Swagger 文档: http://127.0.0.1:8000/docs

## 示例接口

商品列表：

```http
GET /api/v1/product
```

订单列表：

```http
GET /api/v1/order
```

对话接口：

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "帮我查一下订单 ORDER20240615001",
  "session_id": "test-001",
  "history": []
}
```

## 环境变量

当前项目即使不配置大模型 Key 也可以启动，未配置时会使用本地兜底回复逻辑。

可选环境变量：

- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_API_BASE`
- `DATABASE_URL`
- `CORS_ORIGINS`

## 说明

- 当前订单、商品、知识库数据主要为内存示例数据。
- 默认数据库为项目根目录下的 `aicustomer.db`。
