# simple_text_polisher.py

import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI
from dotenv import load_dotenv

# =========================
# 환경설정 & OpenAI 클라이언트
# =========================
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
client = OpenAI(api_key=openai_api_key)

# =========================
# FastAPI
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 필요 시 특정 도메인으로 좁히세요.
    allow_methods=["*"],
    allow_headers=["*"],
)

# (옵션) 로그 포맷
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "service": "simple_text_polisher"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}

# =========================
# 공통 규칙(프롬프트)
# =========================
SYSTEM_PROMPT = (
    "너는 전문 CS 상담사야. 친절하고 신뢰감 있는 답변 스타일로 내용을 정리해줘. "
    "맞춤법, 띄어쓰기, 오타, 문법 오류만 수정하고, 의미를 바꾸거나 정보를 추가/삭제/요약하지 마. "
    "가능하면 원문과 유사한 길이와 형식을 유지해."
)

# =========================
# 메시지 빌더 (두 API용 분리)
# =========================
def build_messages_chat(raw_text: str):
    """Chat Completions용 (content는 문자열 사용)"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"[원문]\n{raw_text}\n\n[교정된 문장]"},
    ]

def build_messages_responses(raw_text: str):
    """Responses API용 (content[].type='input_text')"""
    return [
        {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
        {"role": "user",   "content": [{"type": "input_text", "text": f"[원문]\n{raw_text}\n\n[교정된 문장]"}]},
    ]

# =========================
# Chat Completions (호환용)
# =========================
def polish_text_chat(raw_text: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=build_messages_chat(raw_text),
        temperature=0.2,
        # 필요 시 max_tokens 지정 가능
    )
    return resp.choices[0].message.content.strip()

@app.post("/polish-text")
async def polish_text_endpoint(request: Request):
    """기존 엔드포인트(호환성 유지). Chat Completions 사용."""
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)
        polished = polish_text_chat(raw_text)
        return JSONResponse({"polished_text": polished})
    except Exception as e:
        logger.exception("Chat Completions error")
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

# =========================
# Responses API 유틸 (안전 추출)
# =========================
def extract_output_text(resp) -> str:
    """
    Responses API 응답에서 텍스트를 안전하게 추출.
    - 최신 SDK: resp.output_text
    - dict 형태/구버전: resp["output"][*].content[*].text or resp["output"][*].text
    - 객체형/딕셔너리형 모두 지원
    """
    # 1) 우선 편의속성/키 시도
    text = getattr(resp, "output_text", None)
    if not text and isinstance(resp, dict):
        text = resp.get("output_text")
    if text:
        return text.strip()

    # 2) output 배열 파싱 (객체형/딕셔너리형 혼용 지원)
    def _get(o, key, default=None):
        return (o.get(key, default) if isinstance(o, dict) else getattr(o, key, default))

    output = getattr(resp, "output", None)
    if output is None and isinstance(resp, dict):
        output = resp.get("output")

    parts = []
    if isinstance(output, list):
        for item in output:
            t = _get(item, "type")
            # 형태 1: {"type":"output_text","text":"..."}
            if t == "output_text":
                txt = _get(item, "text", "")
                if txt:
                    parts.append(txt)
                    continue
            # 형태 2: {"type":"message","content":[{"type":"output_text","text":"..."}]}
            if t == "message":
                content = _get(item, "content", []) or []
                for c in content:
                    ct = _get(c, "type")
                    if ct in ("output_text", "text"):  # 일부 조합에서 "text"로 들어오는 경우도 있음
                        txt = _get(c, "text", "")
                        if txt:
                            parts.append(txt)
    return "".join(parts).strip()

# =========================
# Responses API (비스트리밍)
# =========================
def polish_text_responses(raw_text: str, *, model: str = "o4-mini", max_output_tokens: int = 512) -> str:
    """
    Responses API (비스트리밍) 버전.
    ※ o4-mini는 temperature 미지원 → 인자 제거
    """
    resp = client.responses.create(
        model=model,
        input=build_messages_responses(raw_text),
        max_output_tokens=max_output_tokens,
    )
    text = extract_output_text(resp)
    if not text:
        raise RuntimeError("Empty response from Responses API (check SDK version/model).")
    return text

@app.post("/polish-text-resp")
async def polish_text_resp_endpoint(request: Request):
    """Responses API를 사용하는 비스트리밍 엔드포인트."""
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)
        polished = polish_text_responses(raw_text)
        return JSONResponse({"polished_text": polished})
    except Exception as e:
        logger.exception("Responses API (non-stream) error")
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

# =========================
# Responses API (스트리밍)
# =========================
@app.post("/polish-text-stream")
async def polish_text_stream_endpoint(request: Request):
    """
    Responses API 스트리밍 엔드포인트
    - temperature 제거 (o4-mini 미지원)
    - 이벤트 델타를 그대로 전송
    """
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)

        def generate():
            try:
                with client.responses.stream(
                    model="o4-mini",
                    input=build_messages_responses(raw_text),
                    max_output_tokens=512,
                ) as stream:
                    for event in stream:
                        if event.type == "response.output_text.delta":
                            yield event.delta
                        elif event.type.endswith(".delta") and hasattr(event, "delta"):
                            yield event.delta
                        elif event.type == "response.error":
                            yield f"\n[ERROR] {getattr(event, 'error', 'unknown error')}"
                            break
                        elif event.type == "response.completed":
                            break
            except GeneratorExit:
                return
            except Exception as e:
                logger.exception("Responses API (stream) generator error")
                yield f"\n[SERVER ERROR] {str(e)}"

        return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        logger.exception("Responses API (stream) error")
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

# =========================
# 로컬 실행
# =========================
if __name__ == "__main__":
    # Render에서는 Start Command 예시:
    # uvicorn simple_text_polisher:app --host 0.0.0.0 --port $PORT
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("simple_text_polisher:app", host="0.0.0.0", port=port)
