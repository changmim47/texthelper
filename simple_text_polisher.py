# simple_text_polisher.py

import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
client = OpenAI(api_key=openai_api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "simple_text_polisher"}

@app.get("/health")
def health():
    return {"status": "healthy"}

def polish_text(raw_text: str) -> str:
    prompt = (
        "아래 문장을 자연스럽고 정확한 한국어로 교정해 주세요.\n"
        "- 맞춤법, 띄어쓰기, 오타, 문법 오류를 수정해 주세요.\n"
        "- 어투는 공손하고 부드럽게 유지해 주세요.\n"
        "- 전문 CS 상담사 마인드로, 친절하고 신뢰감 있는 답변 스타일로 다듬어 주세요.\n\n"
        "[원문]\n"
        f"{raw_text}\n\n"
        "[교정된 문장]"
    )
    resp = client.chat.completions.create(
        model="gpt-4o",  # ✅ 모델만 변경
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

@app.post("/polish-text")
async def polish_text_endpoint(request: Request):
    try:
        body = await request.json()
        raw_text = body.get("text")
        if not raw_text or not raw_text.strip():
            return JSONResponse(content={"error": "텍스트를 입력해 주세요."}, status_code=400)
        polished = polish_text(raw_text)
        return JSONResponse(content={"polished_text": polished})
    except Exception as e:
        return JSONResponse(content={"error": f"서버 오류: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    # 로컬 실행용 (Render에서는 Start Command로 uvicorn을 사용 권장)
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("simple_text_polisher:app", host="0.0.0.0", port=port)
