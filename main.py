from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional
import os
import aiofiles
import json # JSON 처리를 위해 추가

from job_data import JOB_CATEGORIES, JOB_DETAILS, get_job_document_schema
from prompts import get_document_analysis_prompt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI API 설정
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 실제 OpenAI 모델을 호출하여 문서 분석 피드백을 생성합니다.
async def get_ai_feedback(job_title: str, doc_type: str, document_content: Dict[str, Any]):
    """
    OpenAI GPT 모델을 호출하여 문서 분석 피드백을 생성합니다.
    """
    try:
        prompt = get_document_analysis_prompt(job_title, doc_type, document_content)
        print(f"Generated Prompt for {doc_type} (Job: {job_title}):\n{prompt[:200]}...")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional career consultant AI."}, 
                {"role": "user", "content": prompt}
            ]
        )

        feedback = response.choices[0].message.content
        return feedback

    except Exception as e:
        print(f"Error during OpenAI feedback generation: {e}")
        return f"AI 피드백을 생성하는 중 오류가 발생했습니다: {e}"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    초기 진입 페이지. 각 직무 카테고리 및 직무 목록을 보여줍니다.
    """
    return templates.TemplateResponse("index.html", {"request": request, "job_categories": JOB_CATEGORIES})

@app.get("/editor/{job_slug}", response_class=HTMLResponse)
async def get_document_editor_page(request: Request, job_slug: str):
    """
    특정 직무에 대한 문서 편집기 페이지를 렌더링합니다.
    """
    # URL 슬러그를 직무명으로 변환
    job_title_map = {v.replace(" ", "-").lower(): k for k, v_list in JOB_CATEGORIES.items() for v in v_list}
    job_title_map.update({v.replace("/", "-").replace(" ", "-").lower(): k for k, v_list in JOB_CATEGORIES.items() for v in v_list})

    job_title = None
    for category_jobs in JOB_CATEGORIES.values():
        for j_title in category_jobs:
            if j_title.replace(" ", "-").lower() == job_slug:
                job_title = j_title
                break
        if job_title:
            break

    if not job_title:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # job_data에서 해당 직무의 상세 정보 가져오기 (필요시)
    job_details = JOB_DETAILS.get(job_title, {})

    return templates.TemplateResponse(
        "document_editor.html",
        {"request": request, "job_title": job_title, "job_slug": job_slug, "job_details": job_details}
    )

@app.get("/api/job_schema/{doc_type}", response_class=JSONResponse)
async def get_document_schema(doc_type: str, job_slug: str):
    """
    프론트엔드에서 특정 문서 타입에 대한 입력 양식 스키마를 요청할 때 사용.
    """
    schema = get_job_document_schema(job_slug, doc_type)
    if not schema:
        raise HTTPException(status_code=404, detail="Document schema not found for this type or job.")
    return JSONResponse(content=schema)

@app.post("/api/analyze_document/{doc_type}", response_class=JSONResponse)
async def analyze_document(
    request: Request,
    doc_type: str,
    job_title: str = Form(...), # 폼 데이터에서 직무명 직접 받기
    document_content: str = Form(...), # JSON 문자열 형태로 받기
    current_version: int = Form(...) # 현재 버전 정보
):
    """
    사용자가 제출한 특정 문서의 내용을 AI로 분석하고 피드백을 반환.
    이 엔드포인트는 프론트엔드의 JavaScript Fetch API 요청을 받습니다.
    """
    try:
        parsed_document_content = json.loads(document_content) # JSON 문자열을 파싱
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON for document_content")

    # AI 모델을 호출하여 피드백 생성 (더미 함수 사용)
    feedback = await get_ai_feedback(job_title, doc_type, parsed_document_content)

    return JSONResponse(content={
        "feedback": feedback,
        "new_version_content": parsed_document_content, # AI 분석 후 저장된 내용
        "ai_analysis_status": "success"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)