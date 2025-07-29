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

load_dotenv()

# OpenAI API 설정
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

# 데이터를 저장할 로컬 폴더 설정
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# 데이터 폴더가 없으면 생성
os.makedirs(DATA_DIR, exist_ok=True)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 이력서 분석 요청을 위한 Pydantic 모델 정의
class AnalyzeDocumentRequest(BaseModel):
    job_title: str
    document_content: Dict[str, Any]
    version: int # 클라이언트에서 넘어오는 현재 버전 (newVersionNumber)

class SaveDocumentRequest(BaseModel):
    job_slug: str
    doc_type: str # 이 필드는 클라이언트가 저장 요청 시 명시적으로 보내야 함
    version: int
    content: Dict[str, Any]
    feedback: str

async def get_ai_feedback(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    job_competencies: Optional[list[str]] = None,
    previous_document_content: Optional[Dict[str, Any]] = None, # 이전 버전 문서 내용
    previous_feedback: Optional[str] = None, # 이전 버전 피드백
    older_document_content: Optional[Dict[str, Any]] = None, # 그 이전 버전 문서 내용 (vN-2)
    older_feedback: Optional[str] = None # 그 이전 버전 피드백 (vN-2)
):
    """
    OpenAI GPT 모델을 호출하여 문서 분석 피드백을 생성합니다.
    이전 버전의 문서 내용과 피드백을 참고하여 더 정밀한 피드백을 제공합니다.
    """
    try:
        job_detail = JOB_DETAILS.get(job_title)
        job_competencies_list = job_detail.get("competencies") if job_detail else None

        # prompt 생성 시 이전 버전 데이터 전달
        prompt = get_document_analysis_prompt(
            job_title,
            doc_type,
            document_content,
            job_competencies_list, # job_competencies를 여기서 전달
            previous_document_content,
            previous_feedback,
            older_document_content,
            older_feedback
        )
        print(f"Generated Prompt for {doc_type} (Job: {job_title}):\n{prompt[:500]}...") # 프롬프트 앞 500자만 출력

        if prompt.startswith("오류:"):
            return JSONResponse(content={"error": prompt}, status_code=400)

        messages_for_ai = [
            {"role": "system", "content": "You are a helpful AI assistant who provides detailed feedback on job application documents."},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai
        )

        summary = response.choices[0].message.content.strip()

        if "찾을 수 없다" in summary or "유효한 포트폴리오 내용을 찾을 수 없" in summary or "unable to access external URLs" in summary:
             return JSONResponse(content={"error": summary}, status_code=400)

        return JSONResponse(content={"feedback": summary}, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

async def get_embedding(text: str) -> List[float]:
    """
    주어진 텍스트에 대한 임베딩 벡터를 생성합니다.
    """
    try:
        text = text.replace("\n", " ")
        response = client.embeddings.create(input=text, model=OPENAI_EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")


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
    # job_slug에서 job_title 추출
    job_title = None
    for category_jobs in JOB_CATEGORIES.values():
        for j_title in category_jobs:
            normalized_j_title_slug = j_title.replace(" ", "-").replace("/", "-").lower()
            if normalized_j_title_slug == job_slug:
                job_title = j_title
                break
        if job_title:
            break
    
    if not job_title:
        raise HTTPException(status_code=404, detail="Job not found")

    schema = get_job_document_schema(job_title, doc_type) # job_title 사용
    if not schema:
        raise HTTPException(status_code=404, detail="Document schema not found for this type or job.")
    return JSONResponse(content=schema)

# --- 파일 시스템 기반 데이터 로드 및 저장 함수 ---
async def load_documents_from_file_system(job_slug: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    파일 시스템에서 특정 job_slug에 해당하는 모든 문서 버전(이력서, 자기소개서)을 불러옵니다.
    """
    job_data_dir = os.path.join(DATA_DIR, job_slug)
    loaded_data = {
        "resume": [],
        "cover_letter": [],
        "portfolio": [] # 포트폴리오도 로컬에 저장될 수 있으므로 포함
    }

    if os.path.exists(job_data_dir):
        for doc_type in ["resume", "cover_letter", "portfolio"]: # 포트폴리오도 고려
            doc_type_dir = os.path.join(job_data_dir, doc_type)
            if os.path.exists(doc_type_dir):
                versions = []
                # os.listdir는 동기 함수이므로 await를 사용하지 않음
                for filename in os.listdir(doc_type_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(doc_type_dir, filename)
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                            try:
                                doc_data = json.loads(content)
                                versions.append(doc_data)
                            except json.JSONDecodeError:
                                print(f"Error decoding JSON from {filename}")
                # 버전을 기준으로 정렬
                versions.sort(key=lambda x: x.get("version", 0))
                loaded_data[doc_type] = versions
    
    return loaded_data

async def save_document_to_file_system(document_data: Dict[str, Any]):
    """
    문서 내용을 파일 시스템에 저장합니다. 동일 버전이 존재하면 업데이트합니다.
    """
    job_slug = document_data["job_title"].replace(" ", "-").replace("/", "-").lower() # job_title에서 slug 생성
    doc_type = document_data["doc_type"]
    version = document_data["version"]

    job_data_dir = os.path.join(DATA_DIR, job_slug)
    doc_type_dir = os.path.join(job_data_dir, doc_type)
    
    # 폴더가 없으면 생성 (os.makedirs는 동기 함수이므로 await를 사용하지 않음)
    os.makedirs(doc_type_dir, exist_ok=True)

    file_path = os.path.join(doc_type_dir, f"v{version}.json")

    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(document_data, ensure_ascii=False, indent=4))
    
    print(f"Document {doc_type} v{version} for {job_slug} saved to file system.")
    return True

# --- API 엔드포인트 수정 (MongoDB 대신 파일 시스템 사용) ---

@app.get("/api/load_documents/{job_slug}", response_class=JSONResponse)
async def load_documents_endpoint(job_slug: str):
    """
    파일 시스템에서 특정 job_slug에 해당하는 모든 문서 버전(이력서, 자기소개서, 포트폴리오)을 불러옵니다.
    """
    decoded_job_slug = unquote(job_slug)
    # job_slug에서 job_title을 다시 찾아야 함 (현재 이 엔드포인트는 job_slug만 받음)
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

    loaded_data = await load_documents_from_file_system(decoded_job_slug)
    return JSONResponse(content=loaded_data)


# MongoDB에서 문서 삭제 (롤백) 엔드포인트는 제거됨
# @app.delete("/api/rollback_document/{doc_type}/{job_slug}/{version}", response_class=JSONResponse)
# async def rollback_document_endpoint(...) # 이 함수는 삭제됩니다.


@app.post("/api/analyze_document/{doc_type}")
async def analyze_document_endpoint(
    doc_type: str, request_data: AnalyzeDocumentRequest
):
    try:
        job_title = request_data.job_title
        doc_content_dict = request_data.document_content
        new_version_number = request_data.version
        
        # job_title을 job_slug로 변환 (파일 경로에 사용)
        job_slug = job_title.replace(" ", "-").replace("/", "-").lower()

        # 이전 버전 문서 및 피드백 조회 (파일 시스템에서)
        previous_document_content = None
        previous_feedback = None
        older_document_content = None
        older_feedback = None

        all_docs_of_type = []
        loaded_all_docs = await load_documents_from_file_system(job_slug)
        if doc_type in loaded_all_docs:
            all_docs_of_type = loaded_all_docs[doc_type]
            # 버전을 기준으로 정렬 (이미 load_documents_from_file_system에서 정렬되지만, 다시 확인)
            all_docs_of_type.sort(key=lambda x: x.get("version", 0))

        # 현재 버전에 해당하는 이전/이전 이전 문서 찾기
        for doc in all_docs_of_type:
            if doc.get("version") == new_version_number - 1:
                previous_document_content = doc.get("content")
                previous_feedback = doc.get("feedback")
            elif doc.get("version") == new_version_number - 2:
                older_document_content = doc.get("content")
                older_feedback = doc.get("feedback")
        
        # 임베딩 생성
        text_for_embedding = ""
        if doc_type == "resume":
            text_for_embedding = " ".join([f"{key}: {value}" for key, value in doc_content_dict.items()])
        elif doc_type == "cover_letter":
            # 5가지 새로운 질문 필드를 모두 포함하도록 수정
            reason_for_application = doc_content_dict.get('reason_for_application', '')
            expertise_experience = doc_content_dict.get('expertise_experience', '')
            collaboration_experience = doc_content_dict.get('collaboration_experience', '')
            challenging_goal_experience = doc_content_dict.get('challenging_goal_experience', '')
            growth_process = doc_content_dict.get('growth_process', '')

            text_for_embedding = (
                f"지원 이유: {reason_for_application} "
                f"전문성 경험: {expertise_experience} "
                f"협업 경험: {collaboration_experience} "
                f"도전적 목표 경험: {challenging_goal_experience} "
                f"성장 과정: {growth_process}"
            )
        else: # 포트폴리오 등 기타 문서
            text_for_embedding = json.dumps(doc_content_dict, ensure_ascii=False)

        embedding_vector = await get_embedding(text_for_embedding)

        # AI 피드백 생성 시 이전 버전 데이터 전달
        feedback_response = await get_ai_feedback(
            job_title,
            doc_type,
            doc_content_dict,
            previous_document_content=previous_document_content,
            previous_feedback=previous_feedback,
            older_document_content=older_document_content,
            older_feedback=older_feedback
        )
        
        if feedback_response.status_code != 200:
            return feedback_response
        
        feedback_content = json.loads(feedback_response.body.decode('utf-8'))
        ai_feedback = feedback_content.get("feedback")

        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type, 
            "version": new_version_number,
            "content": doc_content_dict,
            "feedback": ai_feedback,
            "embedding": embedding_vector
        }

        # 파일 시스템에 문서 저장
        await save_document_to_file_system(doc_to_save)

        return JSONResponse(content={"message": "Document analyzed and saved successfully!", "feedback": ai_feedback}, status_code=200)

    except Exception as e:
        print(f"Error in analyze_document_endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error during analysis and saving: {e}")


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
                await aiofiles.write(tmp.name, contents) # aiofiles.write 사용
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
                except Exception as e:
                    print(f"Error unlinking temporary file: {e}") # 에러 메시지 추가
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

    try:
        # 포트폴리오 요약은 이전 버전 문서/피드백을 고려하지 않으므로, 이 인자들은 전달하지 않음
        ai_response = await get_ai_feedback(job_title, doc_type_for_prompt, prompt_content_for_ai)
        
        if ai_response.status_code != 200:
            return ai_response
        
        summary_content = json.loads(ai_response.body.decode('utf-8'))
        summary = summary_content.get("feedback", "")

        if not summary:
            return JSONResponse(content={"error": "AI 요약 내용이 없습니다."}, status_code=500)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = os.path.join("static", "fonts", "NotoSansKR-Regular.ttf")
        if not os.path.exists(font_path):
            # Attempt to find it in a common alternative path if running from root
            font_path_alt = os.path.join(os.getcwd(), "static", "fonts", "NotoSansKR-Regular.ttf")
            if not os.path.exists(font_path_alt):
                raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path} 또는 {font_path_alt}. static/fonts/NotoSansKR-Regular.ttf 경로를 확인해주세요.")
            font_path = font_path_alt
            
        pdf.add_font("NotoSans", "", font_path, uni=True)
        pdf.set_font("NotoSans", size=12)
        pdf.multi_cell(0, 10, summary)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as out_pdf:
            pdf.output(out_pdf.name)
            pdf_path = out_pdf.name
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"PDF 생성 오류: {e}"}, status_code=500)

    return FileResponse(pdf_path, filename=f"portfolio_summary_{job_title}.pdf", media_type="application/pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)