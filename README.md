# Threads API Integration

這是給 Hermes / Gary 使用的 Threads 官方 API 串接工具。

## 已支援

- 產生 OAuth 授權 URL
- OAuth code 交換短期 token，再換長期 token
- refresh 長期 token
- 查 Threads profile
- 查自己的 Threads 貼文
- 發純文字 Threads 貼文

## 前置條件

1. 到 Meta for Developers 建立 App
2. 開啟 Threads API use case / product
3. 加入你的 Threads 帳號為 app tester，或完成 App Review
4. 設定 OAuth redirect URI：

```text
http://localhost:8787/callback
```

5. 複製 `.env.example` 為 `.env`，填入：

```text
THREADS_CLIENT_ID=
THREADS_CLIENT_SECRET=
THREADS_REDIRECT_URI=http://localhost:8787/callback
```

## 安裝

```bash
cd ~/.hermes/work/threads-api-integration
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## OAuth 授權流程

```bash
python threads_cli.py oauth-url
```

打開輸出的 URL，登入 Threads / Meta 並同意授權。授權後會跳回：

```text
http://localhost:8787/callback?code=...
```

複製 `code=` 後面的值，執行：

```bash
python threads_cli.py exchange --code 'PASTE_CODE_HERE'
```

成功後會產生：

```text
token.json
```

## 使用

查個人檔案：

```bash
python threads_cli.py profile
```

列出最近貼文：

```bash
python threads_cli.py list --limit 5
```

發文：

```bash
python threads_cli.py post '這是一則透過 Threads API 發出的測試貼文。'
```

刷新 token：

```bash
python threads_cli.py refresh
```

## 權限

目前預設要求：

- `threads_basic`
- `threads_content_publish`
- `threads_read_replies`
- `threads_manage_replies`
- `threads_manage_insights`

如果只要發文，可先降低為：

```bash
python threads_cli.py oauth-url --scopes threads_basic threads_content_publish
```

## 注意

- `token.json` 含有 access token，不要 commit 或公開。
- App 未發布前，通常只有 app role / tester 可以授權。
- 若要讓非 tester 使用，需要 Meta App Review 核准相關 Threads 權限。
