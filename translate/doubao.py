from openai import OpenAI

from config import (
    DEFAULT_TRANSLATE_SYSTEM_PROMPT,
    DEFAULT_TRANSLATE_USER_PROMPT,
    DOUBAO_API_KEY,
    DOUBAO_BASE_URL,
    DOUBAO_TRANSLATE_MODEL,
    MOBINOVA_CHAT_API_KEY,
    MOBINOVA_CHAT_BASE_URL,
    TRANSLATE_LANGS,
)


def _client(model: str) -> OpenAI:
    """Route by model name: gpt-* → Mobinova, otherwise Doubao."""
    if model.startswith("gpt-"):
        return OpenAI(api_key=MOBINOVA_CHAT_API_KEY, base_url=MOBINOVA_CHAT_BASE_URL)
    return OpenAI(api_key=DOUBAO_API_KEY, base_url=DOUBAO_BASE_URL)


def _lang_display(lang_code: str) -> str:
    """Map ISO code (en/zh/pt/pt-BR/id) → display name. Fallback to raw input."""
    return TRANSLATE_LANGS.get(lang_code, lang_code)


def translate_text(text: str, target_lang: str, context: str = "") -> str:
    """Translate a single string to target_lang via chat completions.

    Args:
        text: Source text (Chinese).
        target_lang: ISO code (en/zh/pt/pt-BR/id) — display name is sent to LLM.
        context: Optional context (e.g. drama synopsis) for disambiguation.
    Returns:
        Translated text.
    """
    if not text or not text.strip():
        return text
    lang_name = _lang_display(target_lang)
    system = "你是一个专业的本地化翻译。只输出译文，不要任何解释或额外说明。"
    user = (
        f"请把下面的文本翻译成{lang_name}。\n"
        f"上下文：{context or '无'}\n"
        f"待翻译文本：\n{text}"
    )
    resp = _client(DOUBAO_TRANSLATE_MODEL).chat.completions.create(
        model=DOUBAO_TRANSLATE_MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def translate_metadata(
    title: str,
    desc: str,
    target_lang: str,
    system_prompt_template: str | None = None,
    user_prompt_template: str | None = None,
    translate_model: str | None = None,
) -> tuple[str, str, str, str]:
    """Translate title + description in one call (cost-effective).

    Args:
        title: Source Chinese title.
        desc: Source Chinese description.
        target_lang: ISO code (en/zh/pt/pt-BR/id).
        system_prompt_template: optional template with {target_lang} placeholder.
        user_prompt_template: optional template with {title} and {description} placeholders.
        translate_model: model name (gpt-* → Mobinova, doubao-* → Doubao). Defaults to DOUBAO_TRANSLATE_MODEL.
    Returns:
        (translated_title, translated_desc, final_system_prompt, final_user_prompt)
    """
    model = translate_model or DOUBAO_TRANSLATE_MODEL
    lang_name = _lang_display(target_lang)
    sys_template = system_prompt_template or DEFAULT_TRANSLATE_SYSTEM_PROMPT
    usr_template = user_prompt_template or DEFAULT_TRANSLATE_USER_PROMPT

    final_system = sys_template.format(target_lang=lang_name)
    final_user = usr_template.format(title=title or "", description=desc or "")

    resp = _client(model).chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": final_system},
            {"role": "user", "content": final_user},
        ],
    )
    content = (resp.choices[0].message.content or "").strip()
    title_out = ""
    desc_out = ""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("TITLE="):
            title_out = line[len("TITLE="):].strip()
        elif line.startswith("DESC="):
            desc_out = line[len("DESC="):].strip()
    if not title_out:
        title_out = translate_text(title, target_lang)
    if not desc_out:
        desc_out = translate_text(desc, target_lang)
    return title_out, desc_out, final_system, final_user


def describe_image(
    image_bytes: bytes,
    prompt: str,
    model: str,
    target_lang: str,
    max_attempts: int = 3,
) -> str:
    """调用视觉模型对图片生成描述。返回描述文本。

    复用 _client(model) 路由：gpt-* -> Mobinova, doubao-* -> Doubao。
    图片以 base64 data URL 形式放入 OpenAI vision messages.content。
    失败重试 max_attempts 次（指数退避 2/4s）。
    """
    import base64
    import time as _time

    if not image_bytes:
        return ""

    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = _client(model).chat.completions.create(
                model=model,
                temperature=0.4,
                messages=messages,
                max_tokens=300,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_err = e
            print(f"  [describe_image retry {attempt}/{max_attempts}] {type(e).__name__}: {e}")
            if attempt < max_attempts:
                _time.sleep(2 ** attempt)
    raise last_err

