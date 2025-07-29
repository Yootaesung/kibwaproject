# main.py
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Body
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
from pydantic import BaseModel
from pymongo import MongoClient # MongoDB 클라이언트 임포트

load_dotenv()

# OpenAI API 설정
OPENAI_MODEL = "gpt-4o"
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# MongoDB 설정
MONGO_URI = "mongodb://13.125.60.100:27017/"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.kibwaproject
cover_letter_collection = db.Cover_Letter
resume_collection = db.Resume
# user_documents_collection = db.user_documents # For a more generalized approach, could use one collection with doc_type field

# Helper function to get the correct collection
def _get_collection(doc_type: str):
    if doc_type == "resume":
        return resume_collection
    elif doc_type == "cover_letter":
        return cover_letter_collection
    else:
        raise HTTPException(status_code=400, detail="Unsupported document type for database operations.")

# 이력서 분석 요청을 위한 Pydantic 모델 정의
class AnalyzeDocumentRequest(BaseModel):
    job_title: str
    document_content: Dict[str, Any] # 클라이언트에서 넘어오는 JSON 객체를 받을 수 있도록 Dict[str, Any]로 명시
    version: int # 클라이언트에서 넘어오는 버전 정보 추가

async def get_ai_feedback(job_title: str, doc_type: str, document_content: Dict[str, Any]):
    """
    OpenAI GPT 모델을 호출하여 문서 분석 피드백을 생성합니다.
    """
    try:
        # job_data에서 해당 직무의 역량(competencies) 가져오기
        # job_slug는 get_document_analysis_prompt 내부에서 필요할 경우 변환되므로 job_title 그대로 전달
        job_detail = JOB_DETAILS.get(job_title)
        job_competencies = job_detail.get("competencies") if job_detail else None

        # prompt 생성 시 job_competencies 전달
        prompt = get_document_analysis_prompt(job_title, doc_type, document_content, job_competencies)
        print(f"Generated Prompt for {doc_type} (Job: {job_title}):\n{prompt[:200]}...") # 프롬프트 앞 200자만 출력

        # prompts.py에서 오류 문자열이 반환된 경우, 바로 에러 응답 반환
        if prompt.startswith("오류:"):
            return JSONResponse(content={"error": prompt}, status_code=400)


        messages_for_ai = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ]

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

@app.get("/api/document_schema/{doc_type}", response_class=JSONResponse)
async def get_document_schema(doc_type: str, job_slug: str):
    schema = get_job_document_schema(job_slug, doc_type)
    if not schema:
        raise HTTPException(status_code=404, detail="Document schema not found for this type or job.")
    return JSONResponse(content=schema)

@app.post("/api/analyze_document/{doc_type}")
async def analyze_document_endpoint(
    doc_type: str, request_data: AnalyzeDocumentRequest
):
    try:
        job_title = request_data.job_title
        doc_content_dict = request_data.document_content
        version = request_data.version # Get version from request

        feedback_response = await get_ai_feedback(job_title, doc_type, doc_content_dict)
        
        # get_ai_feedback에서 에러가 발생하면 해당 에러 응답을 그대로 반환
        if feedback_response.status_code != 200:
            return feedback_response
        
        # 성공 시, feedback 내용을 추출하여 MongoDB에 저장
        feedback_content = json.loads(feedback_response.body.decode('utf-8')).get("feedback", "")

        # Save to MongoDB
        collection = _get_collection(doc_type)
        db_document = {
            "job_title": job_title,
            "doc_type": doc_type,
            "version": version,
            "content": doc_content_dict,
            "feedback": feedback_content,
            "created_at": mongo_client.server_info()["ok"] # Using server time as a placeholder for creation time if not available
        }
        collection.insert_one(db_document)
        print(f"Document v{version} for {job_title} ({doc_type}) saved to MongoDB.")

        return feedback_response # Return the original AI feedback response

    except Exception as e:
        print(f"Error in analyze_document_endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.get("/api/load_documents/{job_slug}", response_class=JSONResponse)
async def load_documents_endpoint(job_slug: str):
    decoded_job_slug = unquote(job_slug)
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
        raise HTTPException(status_code=404, detail=f"Job not found: {decoded_job_slug}")

    loaded_data = {
        "resume": [],
        "cover_letter": [],
        "portfolio": [] # Portfolio is not managed in DB for now, keep empty
    }

    try:
        # Load Resume documents
        for doc in resume_collection.find({"job_title": job_title}).sort("version", 1):
            doc.pop("_id") # Remove ObjectId for JSON serialization
            loaded_data["resume"].append(doc)
        
        # Load Cover Letter documents
        for doc in cover_letter_collection.find({"job_title": job_title}).sort("version", 1):
            doc.pop("_id") # Remove ObjectId for JSON serialization
            loaded_data["cover_letter"].append(doc)
        
        return JSONResponse(content=loaded_data)
    except Exception as e:
        print(f"Error loading documents from MongoDB: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to load documents: {e}")

@app.delete("/api/rollback_document/{doc_type}/{job_slug}/{version_to_rollback}")
async def rollback_document_endpoint(doc_type: str, job_slug: str, version_to_rollback: int):
    decoded_job_slug = unquote(job_slug)
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
        raise HTTPException(status_code=404, detail=f"Job not found: {decoded_job_slug}")

    try:
        collection = _get_collection(doc_type)
        # Delete documents with a version greater than the version_to_rollback
        result = collection.delete_many({
            "job_title": job_title,
            "doc_type": doc_type,
            "version": {"$gt": version_to_rollback}
        })
        print(f"Deleted {result.deleted_count} documents for {job_title} ({doc_type}) beyond version {version_to_rollback}.")
        return JSONResponse(content={"message": f"Successfully rolled back {doc_type} to version {version_to_rollback}. {result.deleted_count} documents deleted."})
    except Exception as e:
        print(f"Error during rollback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Rollback failed: {e}")


@app.post("/api/portfolio_summary")
async def portfolio_summary(
    portfolio_pdf: UploadFile = File(None),
    portfolio_link: str = Form(None),
    job_title: str = Form(...)
):
    doc_type_for_prompt = ""
    prompt_content_for_ai = {}
    
    if portfolio_pdf and portfolio_pdf.filename:
        doc_type_for_prompt = "portfolio_summary_text"
        try:
            contents = await portfolio_pdf.read()
            if len(contents) > 10 * 1024 * 1024: 
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
        if not (portfolio_link.startswith('http://') or portfolio_link.startswith('https://')):
            portfolio_link = 'http://' + portfolio_link
            
        doc_type_for_prompt = "portfolio_summary_url"
        prompt_content_for_ai = {"portfolio_url": portfolio_link}

    else:
        return JSONResponse(
            content={"error": "분석을 위해 PDF 파일 또는 유효한 링크를 입력해주세요."}, 
            status_code=400
        )

    # 2. OpenAI로 요약 생성 (get_ai_feedback 함수를 통해)
    try:
        # get_ai_feedback은 JSONResponse를 반환하므로, 이를 처리
        ai_response = await get_ai_feedback(job_title, doc_type_for_prompt, prompt_content_for_ai)
        
        # get_ai_feedback에서 에러가 발생하면 해당 에러 응답을 그대로 반환
        if ai_response.status_code != 200:
            return ai_response
        
        # 성공 시, feedback 내용을 추출하여 summary 변수에 할당
        summary_content = json.loads(ai_response.body.decode('utf-8'))
        summary = summary_content.get("feedback", "")

        if not summary: # 피드백 내용이 비어있으면 에러
            return JSONResponse(content={"error": "AI 요약 내용이 없습니다."}, status_code=500)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

    # 3. 요약 결과를 한 장짜리 PDF로 생성
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = os.path.join("static", "fonts", "NotoSansKR-Regular.ttf")
        # 폰트 파일 존재 여부 확인
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}. static/fonts/NotoSansKR-Regular.ttf 경로를 확인해주세요.")

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
    return FileResponse(pdf_path, filename=f"portfolio_summary_{job_title}.pdf", media_type="application/pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)