# simple_text_polisher.py
# - 단일 모델: gpt-4o-mini
# - 단일 엔드포인트: /polish-text
# - 루트/헬스에 GET, HEAD 허용
# - 에러 로깅 및 깔끔한 JSON 오류 응답

import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
# FastAPI & CORS
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # 필요 시 도메인 제한
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("uvicorn.error")

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "service": "simple_text_polisher"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}

# =========================
# 프롬프트 & 호출 유틸
# =========================
SYSTEM_PROMPT = (
    "너는 전문 CS 상담사야. 친절하고 신뢰감 있는 답변 스타일로 내용을 정리해줘. "
    "맞춤법, 띄어쓰기, 오타, 문법 오류만 수정하고, 의미를 바꾸거나 정보를 추가/삭제/요약하지 마. "
    "가능하면 원문과 유사한 길이와 형식을 유지해."
)

def build_messages(raw_text: str):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"[원문]\n{raw_text}\n\n[교정된 문장]"},
    ]

def call_gpt_4o_mini(raw_text: str) -> str:
    # 필요 시 환경변수로 출력 토큰 상한 제어 (기본 512)
    max_tokens_env = os.getenv("MAX_OUTPUT_TOKENS")
    max_tokens = int(max_tokens_env) if max_tokens_env and max_tokens_env.isdigit() else 512

    resp = client.chat.completions.create(
        model="gpt-4o-mini",              # ✅ 단일 모델 사용
        messages=build_messages(raw_text),
        temperature=0.2,
        max_tokens=max_tokens,            # 잘림 방지에 도움
    )
    return resp.choices[0].message.content.strip()

# =========================
# 엔드포인트
# =========================
@app.post("/polish-text")
async def polish_text_endpoint(request: Request):
    try:
        body = await request.json()
        raw_text = (body.get("text") or "").strip()
        if not raw_text:
            return JSONResponse({"error": "텍스트를 입력해 주세요."}, status_code=400)

        polished = call_gpt_4o_mini(raw_text)
        if not polished:
            return JSONResponse({"error": "모델 응답이 비어 있습니다."}, status_code=502)

        return JSONResponse({"polished_text": polished})

    except Exception as e:
        # 서버/모델 오류를 로깅하고 일반화된 메시지 반환
        log.exception("polish-text failed")
        return JSONResponse({"error": "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."}, status_code=500)

# =========================
# 로컬 실행
# =========================
if __name__ == "__main__":
    # Render에서는 Start Command 예시:
    # uvicorn simple_text_polisher:app --host 0.0.0.0 --port $PORT
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("simple_text_polisher:app", host="0.0.0.0", port=port)
