import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv

# ◼️ 환경 변수 로드 및 OpenAI 클라이언트 설정
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

client = OpenAI(api_key=openai_api_key)

# ◼️ FastAPI 앱 생성
app = FastAPI()

# ◼️ CORS 설정 (모든 도메인 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ◼️ GPT를 이용해 텍스트 다듬는 함수
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
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # 더 안정적이고 일관되게 다듬기
    )
    return response.choices[0].message.content.strip()

# ◼️ 텍스트 입력 받아 교정 결과 반환
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

# ◼️ 서버 실행 (로컬 + 개발 서버 용)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))  # Render가 PORT를 내려줌
    uvicorn.run("simple_text_polisher:app", host="0.0.0.0", port=port)
