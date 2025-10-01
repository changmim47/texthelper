# simple_text_polisher.py

import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI
from dotenv import load_dotenv
from contextlib import closing

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

@app.get("/")
def root():
    return {"status": "ok", "service": "simple_text_polisher"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# =========================
# 공통 프롬프트/메시지 빌드
# =========================
SYSTEM_PROMPT = (
    "아래 문장을 자연스럽고 정확한 한국어로 교정해 주세요. "
    "맞춤법, 띄어쓰기, 오타, 문법 오류를 수정해 주세요, "
    "어투는 공손하고 부드럽게 유지해 주세요. "
    "전문 CS 상담사 마인드로, 친절하고 신뢰감 있는 답변 스타일로 다듬어 주세요"
)

def build_messages(raw_text: str):
    """
    Responses API에서 사용하는 메시지 형식.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"[원문]\n{raw_text}\n\n[교정된 문장]"}
    ]

# =========================
# 기존: Chat Completions (호환용)
# =========================
def polish_text_chat(raw_text: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=build_messages(raw_text),
        temperature=0.2,
        # 필요 시 max_tokens 추가 가능
    )
    return resp.choices[0].message.content.strip()

@app.post("/polish-text")
async def polish_text_endpoint(request: Request):
    """
    기존 엔드포인트(호환성 유지). Chat Completions 사용.
    """
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)
        polished = polish_text_chat(raw_text)
        return JSONResponse({"polished_text": polished})
    except Exception as e:
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

# =========================
# 추가 1: Responses API (비스트리밍)
# =========================
def polish_text_responses(raw_text: str, *, model: str = "o4-mini", max_output_tokens: int = 512) -> str:
    """
    Responses API (비스트리밍) 버전.
    """
    resp = client.responses.create(
        model=model,
        input=build_messages(raw_text),
        temperature=0.2,
        max_output_tokens=max_output_tokens,  # 출력 토큰 상한
    )
    # Python SDK는 편의 속성으로 output_text 제공
    return (resp.output_text or "").strip()

@app.post("/polish-text-resp")
async def polish_text_resp_endpoint(request: Request):
    """
    Responses API를 사용하는 비스트리밍 엔드포인트.
    """
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)
        polished = polish_text_responses(raw_text)
        if not polished:
            return JSONResponse({"error": "모델 응답이 비어 있습니다."}, status_code=500)
        return JSONResponse({"polished_text": polished})
    except Exception as e:
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

# =========================
# 추가 2: Responses API (스트리밍)
# =========================
@app.post("/polish-text-stream")
async def polish_text_stream_endpoint(request: Request):
    """
    Responses API 스트리밍 엔드포인트 (수정판)
    - contextlib.closing 제거
    - 예외/클라이언트 끊김 처리 보강
    """
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)

        def generate():
            try:
                # ❌ with closing(...) X
                # ✅ 컨텍스트 매니저 그대로 사용
                with client.responses.stream(
                    model="o4-mini",                     # 필요 시 gpt-4o-mini로 교체 가능
                    input=build_messages(raw_text),
                    temperature=0.2,
                    max_output_tokens=512,
                ) as stream:
                    for event in stream:
                        if event.type == "response.output_text.delta":
                            # Starlette는 str/bytes 모두 허용. utf-8 텍스트 스트림으로 흘려보냄
                            yield event.delta
                        elif event.type == "response.error":
                            yield f"\n[ERROR] {getattr(event, 'error', 'unknown error')}"
                            break
                        elif event.type == "response.completed":
                            break
            except GeneratorExit:
                # 클라이언트가 중간에 연결 끊었을 때(브라우저 탭 닫힘 등)
                return
            except Exception as e:
                # 서버 내부 오류를 스트림 끝부분에 표시(로그도 남기길 권장)
                yield f"\n[SERVER ERROR] {str(e)}"

        return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

# =========================
# 로컬 실행
# =========================
if __name__ == "__main__":
    # Render에서는 대시보드 Start Command에:
    # uvicorn simple_text_polisher:app --host 0.0.0.0 --port $PORT
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("simple_text_polisher:app", host="0.0.0.0", port=port)
