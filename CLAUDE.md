# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---


## 部署

本机服务器在新加坡（45.78.235.1），用户从中国大陆访问。架构是 **nginx:5173 → uvicorn:5174**（4 worker）。

```bash
# 启动 uvicorn（内部端口，只监听 127.0.0.1）
python3 main.py serve --host 127.0.0.1 --port 5174 --workers 4

# nginx 配置在 /etc/nginx/conf.d/short-drama.conf，监听 5173 反代 5174
#   - 静态资源 /static/ 由 nginx 直发 + 30 天缓存
#   - gzip 压缩 JS/CSS/JSON
#   - keep-alive 复用 TCP 连接
nginx -t && nginx -s reload

# 访问 URL：http://45.78.235.1:5173（不要带其他端口）
```

80 端口留给其他业务，不占用。改 nginx 配置后必须 `nginx -t` 校验再 reload。

---

### 5. 不要读取这个工程外文件

### 6. 严禁清除或者删除数据库数据，数据库发生变动要对数据进行迁移

### 7. 前端或者后端代码发生变动，要重新在本服务器上部署生效

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
