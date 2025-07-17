import os
import asyncio
import json
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
# from reportlab.lib.pagesizes import letter # PDF 생성 관련 모듈은 더 이상 필요 없음
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak # PDF 생성 관련 모듈은 더 이상 필요 없음
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle, ListStyle # PDF 생성 관련 모듈은 더 이상 필요 없음
# from reportlab.lib.enums import TA_LEFT, TA_CENTER # PDF 생성 관련 모듈은 더 이상 필요 없음
# from reportlab.lib import colors # PDF 생성 관련 모듈은 더 이상 필요 없음
from typing import Optional, List, Dict
from urllib.parse import quote # URL 인코딩을 위해 추가
import random # 임시 합격 가능성 생성을 위해 추가

import google.generativeai as genai
# from reportlab.pdfbase import pdfmetrics # PDF 생성 관련 모듈은 더 이상 필요 없음
# from reportlab.pdfbase.ttfonts import TTFont # PDF 생성 관련 모듈은 더 이상 필요 없음

# 새로 추가된 임포트
from job_data import JOB_CATEGORIES, JOB_DETAILS, ALL_JOB_SLUGS # job_data.py에서 임포트
# from prompts import generate_job_info_prompt # 이 프롬프트는 기존 PDF 생성용이므로 더 이상 필요 없음

# 환경 변수 로드
load_dotenv()

app = FastAPI()

# 환경 변수에서 API 키 로드
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("경고: GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    raise ValueError("Gemini API 키가 설정되지 않았습니다.")

# Gemini API 설정
genai.configure(api_key=GEMINI_API_KEY)
try:
    print("--- 사용 가능한 Gemini 모델 목록 ---")
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(m.name)
    print("----------------------------------")
except Exception as e:
    print(f"모델 목록 조회 실패: {e}")

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- 기존 PDF 관련 함수들은 모두 삭제 (또는 주석 처리) ---
# get_styles, generate_job_info, create_pdf 함수는 더 이상 사용되지 않음

# --- 새로운 라우트: 메인 페이지 (직무 선택 페이지) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    초기 진입 페이지. 각 직무 카테고리 및 직무 목록을 보여줍니다.
    ZEP에서 이 URL을 웹뷰로 열고, 사용자가 직무를 선택하면 해당 직무의 분석 페이지로 이동합니다.
    """
    return templates.TemplateResponse("index.html", {"request": request, "job_categories": JOB_CATEGORIES})

# --- 새로운 라우트: 직무별 분석 페이지 ---
@app.get("/analysis/{job_slug}", response_class=HTMLResponse)
async def get_job_analysis_page(request: Request, job_slug: str):
    """
    각 직무별 합격 가능성 분석 도구 페이지를 렌더링합니다.
    URL 슬러그를 기반으로 해당 직무의 역량 및 자격증 데이터를 전달합니다.
    """
    # job_slug를 원래 직무명으로 변환 (예: "frontend-developer" -> "프론트엔드 개발자")
    # 실제로는 JOB_DETAILS에서 역으로 찾아야 함. 여기서는 편의상 간단히 처리
    original_job_title = ""
    for category, jobs in JOB_CATEGORIES.items():
        for job_title in jobs:
            if job_title.replace(" ", "-").replace("/", "-").lower() == job_slug:
                original_job_title = job_title
                break
        if original_job_title:
            break

    if not original_job_title:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = JOB_DETAILS.get(original_job_title)
    if not job_data:
        # JOB_DETAILS에 없는 직무의 경우 기본값 또는 에러 처리
        job_data = {
            "competencies": [],
            "certifications": [],
            "description": f"'{original_job_title}' 직무에 대한 상세 정보가 준비되지 않았습니다. 일반적인 이력서 분석을 진행합니다."
        }
        # raise HTTPException(status_code=404, detail=f"Details for job '{original_job_title}' not found")

    return templates.TemplateResponse("analysis_tool.html", {
        "request": request,
        "job_title": original_job_title,
        "job_slug": job_slug,
        "job_details": job_data
    })


# --- 새로운 라우트: 이력서 분석 API 엔드포인트 ---
@app.post("/api/analyze/{job_slug}")
async def analyze_application(
    job_slug: str,
    # company_name: Optional[str] = Form(None), # 회사명은 선택사항, 필요하면 다시 추가
    resume_text: Optional[str] = Form(None), # 직접 입력된 이력서 텍스트
    resume_file: Optional[UploadFile] = File(None), # 업로드된 이력서 파일
    selected_competencies: Optional[List[str]] = Form(None), # 선택된 역량 체크박스
    selected_certifications: Optional[List[str]] = Form(None) # 선택된 자격증
):
    """
    사용자가 제출한 서류를 기반으로 합격 가능성을 분석하고 결과를 반환합니다.
    이 엔드포인트는 AI 모델을 호출하여 실제 분석을 수행합니다.
    """
    # job_slug를 원래 직무명으로 변환
    original_job_title = ""
    for category, jobs in JOB_CATEGORIES.items():
        for job_title in jobs:
            if job_title.replace(" ", "-").replace("/", "-").lower() == job_slug:
                original_job_title = job_title
                break
        if original_job_title:
            break

    if not original_job_title:
        raise HTTPException(status_code=404, detail="Job not found")

    # 이력서 내용 추출
    full_resume_content = ""
    if resume_text:
        full_resume_content += resume_text
    
    if resume_file:
        try:
            # 파일 내용을 읽어 텍스트로 변환 (간단한 텍스트 파일만 가정)
            # PDF, DOCX 파일 처리는 별도 라이브러리(PyPDF2, python-docx) 필요
            file_content = await resume_file.read()
            full_resume_content += file_content.decode('utf-8')
        except Exception as e:
            print(f"File upload processing error: {e}")
            return JSONResponse(status_code=400, content={"error": "파일 처리 중 오류가 발생했습니다. 텍스트 파일인지 확인해주세요."})

    # TODO: Gemini API를 이용한 실제 분석 로직 구현
    # prompts.py에 analyze_resume_prompt 함수를 정의하고 사용
    # 현재는 더미 데이터로 대체
    
    # AI 분석에 필요한 정보: original_job_title, full_resume_content, selected_competencies, selected_certifications, company_name(선택)
    
    # 임시 합격 가능성 (실제 AI 분석 결과로 대체 필요)
    # 예시: 이력서 길이가 길수록, 역량/자격증을 많이 선택할수록 가능성 증가 (아주 단순한 로직)
    dummy_probability = 0
    if full_resume_content:
        dummy_probability += min(len(full_resume_content) // 100, 50) # 텍스트 길이에 따라 최대 50점
    if selected_competencies:
        dummy_probability += len(selected_competencies) * 3 # 선택된 역량당 3점
    if selected_certifications:
        dummy_probability += len(selected_certifications) * 5 # 선택된 자격증당 5점

    # 직무에 따른 보너스 (예시)
    if "개발자" in original_job_title:
        dummy_probability += 10 # 개발 직무에 10점 보너스
    
    final_probability = min(100, dummy_probability + random.randint(0, 20)) # 최종 점수 0-100 사이, 약간의 랜덤성
    
    # 꼬리 유형 결정
    tail_type = "bone"
    if 0 <= final_probability <= 10:
        tail_type = "bone"
    elif 11 <= final_probability <= 40:
        tail_type = "basic_tail"
    elif 41 <= final_probability <= 70:
        tail_type = "normal_tail"
    elif 71 <= final_probability <= 90:
        tail_type = "colorful_tail"
    else: # 91 ~ 100
        tail_type = "gorgeous_tail"

    # AI 기반 피드백 (임시)
    feedback_message = "제출된 서류를 분석한 결과입니다. 현재는 초기 개발 단계이므로, 더 정확한 분석을 위해 AI 모델 학습이 필요합니다."
    if final_probability < 50:
        feedback_message += "\n강점 보완 및 부족한 부분을 채워나가시면 합격 가능성을 높일 수 있습니다."
    else:
        feedback_message += "\n훌륭한 강점을 가지고 계시네요! 꾸준히 발전시켜 나가세요."

    return JSONResponse(content={
        "success": True,
        "probability": final_probability,
        "tail_type": tail_type,
        "feedback": feedback_message
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)