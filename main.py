# main.py
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional
import os
import aiofiles
import json
import traceback
from urllib.parse import unquote

from job_data import JOB_CATEGORIES, JOB_DETAILS, get_job_document_schema
from prompts import get_document_analysis_prompt
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from fpdf import FPDF
import tempfile

load_dotenv()

# OpenAI API 설정
OPENAI_MODEL = "gpt-4o"
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

async def get_ai_feedback(job_title: str, doc_type: str, document_content: Dict[str, Any]):
    """
    OpenAI GPT 모델을 호출하여 문서 분석 피드백을 생성합니다.
    """
    try:
        # job_data에서 해당 직무의 역량(competencies) 가져오기
        job_slug = job_title.replace(" ", "-").replace("/", "-").lower() # prompts.py에서 사용할 수 있도록 slug로 변환
        job_detail = JOB_DETAILS.get(job_title) # job_title 그대로 사용
        job_competencies = job_detail.get("competencies") if job_detail else None

        # prompt 생성 시 job_competencies 전달
        prompt = get_document_analysis_prompt(job_title, doc_type, document_content, job_competencies)
        print(f"Generated Prompt for {doc_type} (Job: {job_title}):\n{prompt[:200]}...") # 프롬프트 앞 200자만 출력

        messages_for_ai = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ]

        # 이전 조건문 및 tools 변수 사용을 모두 제거하고,
        # 기본 메시지만으로 API를 호출합니다.
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai
        )

        summary = response.choices[0].message.content.strip()

        # AI가 '내용을 찾을 수 없다'고 응답했을 때의 처리
        if "찾을 수 없다" in summary or "유효한 포트폴리오 내용을 찾을 수 없" in summary or "unable to access external URLs" in summary:
             return JSONResponse(content={"error": summary}, status_code=400)

        return JSONResponse(content={"feedback": summary}, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "job_categories": JOB_CATEGORIES})

@app.get("/editor/{job_slug}", response_class=HTMLResponse)
async def get_document_editor_page(request: Request, job_slug: str):
    decoded_job_slug = unquote(job_slug)
    print(f"Received job_slug: {job_slug}, Decoded: {decoded_job_slug}")

    job_title = None
    for category_jobs in JOB_CATEGORIES.values():
        for j_title in category_jobs:
            normalized_j_title_slug = j_title.replace(" ", "-").replace("/", "-").lower()
            if normalized_j_title_slug == decoded_job_slug:
                job_title = j_title
                break
        if job_title:
            break

    if not job_title:
        print(f"Job not found for slug: {decoded_job_slug}")
        raise HTTPException(status_code=404, detail=f"Job not found: {decoded_job_slug}")
    
    job_details = JOB_DETAILS.get(job_title, {})

    return templates.TemplateResponse(
        "document_editor.html",
        {"request": request, "job_title": job_title, "job_slug": job_slug, "job_details": job_details}
    )

@app.get("/api/job_schema/{doc_type}", response_class=JSONResponse)
async def get_document_schema(doc_type: str, job_slug: str):
    schema = get_job_document_schema(job_slug, doc_type)
    if not schema:
        raise HTTPException(status_code=404, detail="Document schema not found for this type or job.")
    return JSONResponse(content=schema)

@app.post("/api/analyze_document/{doc_type}")
async def analyze_document_endpoint(
    doc_type: str, request: Request, job_title: str = Form(...), document_content: str = Form(...)
):
    try:
        doc_content_dict = json.loads(document_content)
        feedback = await get_ai_feedback(job_title, doc_type, doc_content_dict)
        return feedback
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid document_content JSON format")
    except Exception as e:
        print(f"Error in analyze_document_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.post("/api/portfolio_summary")
async def portfolio_summary(
    portfolio_pdf: UploadFile = File(None),
    portfolio_link: str = Form(None),
    job_title: str = Form(...)
):
    summary = ""
    doc_type_for_prompt = ""
    prompt_content_for_ai = {}
    
    if portfolio_pdf and portfolio_pdf.filename:
        # PDF 파일에서 텍스트 추출
        doc_type_for_prompt = "portfolio_summary_text"
        try:
            # 파일 크기 확인 (10MB 이하만 허용)
            contents = await portfolio_pdf.read()
            if len(contents) > 10 * 1024 * 1024:  # 10MB
                return JSONResponse(
                    content={"error": "파일 크기가 너무 큽니다. 10MB 이하의 파일을 업로드해주세요."}, 
                    status_code=400
                )
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
                
            try:
                reader = PdfReader(tmp_path)
                extracted_text = ""
                for page in reader.pages:
                    extracted_text += page.extract_text() or ""
                
                if not extracted_text.strip():
                    return JSONResponse(
                        content={"error": "PDF에서 텍스트를 추출하지 못했습니다. 스캔된 이미지 PDF이거나 텍스트가 포함되어 있지 않을 수 있습니다."}, 
                        status_code=400
                    )
                
                prompt_content_for_ai = {"extracted_text": extracted_text}
                
            finally:
                # 임시 파일 정리
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        except Exception as e:
            print(traceback.format_exc())
            return JSONResponse(
                content={"error": f"PDF 처리 중 오류가 발생했습니다: {str(e)}"}, 
                status_code=400
            )
            
    elif portfolio_link and portfolio_link.strip():
        # URL 유효성 검사
        if not (portfolio_link.startswith('http://') or portfolio_link.startswith('https://')):
            portfolio_link = 'http://' + portfolio_link
            
        doc_type_for_prompt = "portfolio_summary_url"
        prompt_content_for_ai = {"portfolio_url": portfolio_link}

    else:
        return JSONResponse(
            content={"error": "분석을 위해 PDF 파일 또는 유효한 링크를 입력해주세요."}, 
            status_code=400
        )

    # 2. OpenAI로 요약 생성
    try:
        summary_prompt = get_document_analysis_prompt(job_title, doc_type_for_prompt, prompt_content_for_ai)

        messages_for_ai = [
            {"role": "system", "content": "You are a professional career consultant AI."},
            {"role": "user", "content": summary_prompt}
        ]
        
        # ⭐ tools 매개변수를 전달하는 조건문 및 tools 변수 사용을 모두 제거하고,
        # 기본 메시지만으로 API를 호출합니다.
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai
        )

        summary = response.choices[0].message.content.strip()

        # AI가 '내용을 찾을 수 없다'고 응답했을 때의 처리
        if "찾을 수 없다" in summary or "유효한 포트폴리오 내용을 찾을 수 없" in summary or "unable to access external URLs" in summary:
             return JSONResponse(content={"error": summary}, status_code=400)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

    # 3. 요약 결과를 한 장짜리 PDF로 생성
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = os.path.join("static", "fonts", "NotoSansKR-Regular.ttf")
        pdf.add_font("NotoSans", "", font_path, uni=True)
        pdf.set_font("NotoSans", size=12)
        pdf.multi_cell(0, 10, summary)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as out_pdf:
            pdf.output(out_pdf.name)
            pdf_path = out_pdf.name
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"PDF 생성 오류: {e}"}, status_code=500)

    # 4. PDF 파일 반환
    return FileResponse(pdf_path, filename="portfolio_summary.pdf", media_type="application/pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)