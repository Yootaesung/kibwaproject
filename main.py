# main.py
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional, Tuple
import os
import aiofiles
import json
import traceback
from urllib.parse import unquote, quote
import hashlib
import tempfile
import PyPDF2
from job_data import JOB_CATEGORIES, JOB_DETAILS, get_job_document_schema
from prompts import get_document_analysis_prompt, get_company_analysis_prompt
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from fpdf import FPDF
from pydantic import BaseModel
import numpy as np
import io
from fpdf import FPDF

load_dotenv()

# OpenAI API 설정
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
COMPANIES_DATA_DIR = os.path.join(DATA_DIR, "companies")
os.makedirs(COMPANIES_DATA_DIR, exist_ok=True)
# 기업 분석 파일 저장을 위한 고정 파일명 추가
COMPANY_ANALYSIS_FILE = os.path.join(COMPANIES_DATA_DIR, "current_company_analysis.json")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
templates = Jinja2Templates(directory="templates")

class AnalyzeDocumentRequest(BaseModel):
    job_title: str
    document_content: Dict[str, Any]
    version: int
    feedback_reflection: Optional[str] = None
    company_name: Optional[str] = None

class SaveDocumentRequest(BaseModel):
    job_slug: str
    doc_type: str
    version: int
    content: Dict[str, Any]
    feedback: str
    individual_feedbacks: Dict[str, str] = {}

class AnalyzeCompanyRequest(BaseModel):
    company_name: str

# get_ai_feedback 함수 정의 (수정)
async def get_ai_feedback(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    previous_document_data: Optional[Dict[str, Any]] = None,
    older_document_data: Optional[Dict[str, Any]] = None,
    additional_user_context: Optional[str] = None,
    company_name: Optional[str] = None,
    company_analysis: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    try:
        job_detail = JOB_DETAILS.get(job_title)
        job_competencies_list = job_detail.get("competencies") if job_detail else None

        system_instruction, user_prompt = get_document_analysis_prompt(
            job_title=job_title,
            doc_type=doc_type,
            document_content=document_content,
            job_competencies=job_competencies_list,
            previous_document_data=previous_document_data,
            older_document_data=older_document_data,
            additional_user_context=additional_user_context,
            company_name=company_name,
            company_analysis=company_analysis,
        )
        
        print(f"Generated System Instruction for {doc_type} (Job: {job_title}, Company: {company_name}):\n{system_instruction[:500]}...")
        print(f"Generated User Prompt for {doc_type} (Job: {job_title}, Company: {company_name}):\n{user_prompt[:500]}...")

        if user_prompt.startswith("오류:"):
            return JSONResponse(content={"error": user_prompt}, status_code=400)

        messages_for_ai = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ]

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai,
            response_format={"type": "json_object"}
        )

        ai_raw_response = response.choices[0].message.content.strip()
        print(f"Raw AI Response: {ai_raw_response}")

        try:
            parsed_feedback = json.loads(ai_raw_response)
        except json.JSONDecodeError:
            print(f"AI response was not valid JSON: {ai_raw_response}")
            return JSONResponse(
                content={
                    "summary": "AI 응답 파싱 오류로 요약 불가",
                    "overall_feedback": f"AI 응답 파싱 오류: 유효한 JSON 형식이 아닙니다. 원본: {ai_raw_response[:200]}...",
                    "individual_feedbacks": {}
                }, 
                status_code=500
            )

        summary_text = parsed_feedback.get("summary", "요약 내용을 생성할 수 없습니다.")
        overall_feedback = parsed_feedback.get("overall_feedback", "AI 피드백을 생성하는 데 문제가 발생했습니다.")
        individual_feedbacks = parsed_feedback.get("individual_feedbacks", {})

        if "찾을 수 없다" in overall_feedback or "유효한 포트폴리오 내용을 찾을 수 없" in overall_feedback or "unable to access external URLs" in overall_feedback:
            return JSONResponse(content={"error": overall_feedback}, status_code=400)

        return JSONResponse(content={
            "summary": summary_text,
            "overall_feedback": overall_feedback,
            "individual_feedbacks": individual_feedbacks
        }, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

# get_embedding 함수 정의 (기존과 동일)
async def get_embedding(text: str) -> List[float]:
    try:
        text = text.replace("\n", " ")
        response = client.embeddings.create(input=text, model=OPENAI_EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")

# _cosine_similarity 함수 정의 (기존과 동일)
def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    dot_product = np.dot(vec1_np, vec2_np)
    magnitude1 = np.linalg.norm(vec1_np)
    magnitude2 = np.linalg.norm(vec2_np)
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

# calculate_content_hash 함수 정의 (기존과 동일)
def calculate_content_hash(content: Dict[str, Any]) -> str:
    sorted_items_str = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(sorted_items_str.encode('utf-8')).hexdigest()

# 기업 분석 파일 로드 함수 (수정)
async def load_company_analysis(company_name: str) -> Optional[Dict[str, Any]]:
    # 고정된 파일명 사용
    file_path = COMPANY_ANALYSIS_FILE
    if os.path.exists(file_path):
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        loaded_analysis = json.loads(content)
        # 파일에 저장된 기업명과 요청된 기업명이 일치하는지 확인
        if loaded_analysis.get("company_name") == company_name:
            return loaded_analysis
    return None

# --- NEW: Last company analysis loading endpoint ---
async def load_last_company_analysis_from_file() -> Optional[Dict[str, Any]]:
    """Loads the last saved company analysis from the fixed file."""
    if os.path.exists(COMPANY_ANALYSIS_FILE):
        try:
            async with aiofiles.open(COMPANY_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading last company analysis: {e}")
    return None

@app.get("/api/load_last_company_analysis", response_class=JSONResponse)
async def get_last_company_analysis():
    """Returns the last saved company analysis data, if available."""
    last_analysis = await load_last_company_analysis_from_file()
    if last_analysis:
        return JSONResponse(content=last_analysis)
    return JSONResponse(content={})

# --- FastAPI 엔드포인트 ---
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
async def get_document_schema_endpoint(doc_type: str, job_slug: str):
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

    schema = get_job_document_schema(job_title, doc_type)
    if not schema:
        raise HTTPException(status_code=404, detail="Document schema not found for this type or job.")
    return JSONResponse(content=schema)

@app.get("/api/load_documents/{job_slug}", response_class=JSONResponse)
async def api_load_documents(job_slug: str):
    decoded_job_slug = unquote(job_slug)
    print(f"API Load Documents: Received job_slug: {job_slug}, Decoded: {decoded_job_slug}")

    job_title_found = False
    for category_jobs in JOB_CATEGORIES.values():
        for j_title in category_jobs:
            normalized_j_title_slug = j_title.replace(" ", "-").replace("/", "-").lower()
            if normalized_j_title_slug == decoded_job_slug:
                job_title_found = True
                break
        if job_title_found:
            break
            
    if not job_title_found:
        print(f"API Load Documents: Job not found for slug: {decoded_job_slug}")
        raise HTTPException(status_code=404, detail=f"Job not found for slug: {decoded_job_slug}")

    try:
        loaded_data = await load_documents_from_file_system(decoded_job_slug)
        return JSONResponse(content=loaded_data)
    except Exception as e:
        print(f"Error loading documents for {decoded_job_slug}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load documents: {e}")

# --- 파일 시스템 기반 데이터 로드 및 저장 함수 ---
async def load_documents_from_file_system(job_slug: str) -> Dict[str, List[Dict[str, Any]]]:
    job_data_dir = os.path.join(DATA_DIR, job_slug)
    loaded_data = {
        "resume": [],
        "cover_letter": [],
        "portfolio": [] 
    }

    if os.path.exists(job_data_dir):
        for doc_type in loaded_data.keys():
            doc_type_dir = os.path.join(job_data_dir, doc_type)
            if os.path.exists(doc_type_dir):
                versions = []
                for filename in os.listdir(doc_type_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(doc_type_dir, filename)
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                        try:
                            doc_data = json.loads(content)
                            if "individual_feedbacks" not in doc_data:
                                doc_data["individual_feedbacks"] = {}
                            if "embedding" not in doc_data:
                                print(f"Warning: Embedding missing for {job_slug}/{doc_type}/v{doc_data.get('version', 'N/A')}. Generating now...")
                                text_to_embed = ""
                                if doc_type == "cover_letter":
                                    text_to_embed = " ".join([
                                        doc_data["content"].get("reason_for_application", ""),
                                        doc_data["content"].get("expertise_experience", ""),
                                        doc_data["content"].get("collaboration_experience", ""),
                                        doc_data["content"].get("challenging_goal_experience", ""),
                                        doc_data["content"].get("growth_process", "")
                                    ])
                                elif doc_type == "resume":
                                    text_to_embed = " ".join([
                                        json.dumps(doc_data["content"].get("education_history", ""), ensure_ascii=False),
                                        json.dumps(doc_data["content"].get("career_history", ""), ensure_ascii=False),
                                        doc_data["content"].get("certifications", ""),
                                        doc_data["content"].get("awards_activities", ""),
                                        doc_data["content"].get("skills_tech", "")
                                    ])
                                elif doc_type == "portfolio":
                                    # 수정: 포트폴리오의 경우 'content' 딕셔너리 내 'summary' 필드를 사용
                                    text_to_embed = doc_data["content"].get("summary", "")
                                
                                if text_to_embed.strip():
                                    doc_data["embedding"] = await get_embedding(text_to_embed)
                                else:
                                    doc_data["embedding"] = []
                                    print(f"No content to embed for {job_slug}/{doc_type}/v{doc_data.get('version', 'N/A')}.")

                            versions.append(doc_data)
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON from {filename}")
                versions.sort(key=lambda x: x.get("version", 0))
                loaded_data[doc_type] = versions
    
    return loaded_data

async def save_document_to_file_system(document_data: Dict[str, Any]):
    job_slug = document_data["job_title"].replace(" ", "-").replace("/", "-").lower()
    doc_type = document_data["doc_type"]
    version = document_data["version"]

    job_data_dir = os.path.join(DATA_DIR, job_slug)
    doc_type_dir = os.path.join(job_data_dir, doc_type)
    
    os.makedirs(doc_type_dir, exist_ok=True)

    file_path = os.path.join(doc_type_dir, f"v{version}.json")

    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(document_data, ensure_ascii=False, indent=4))
    
    print(f"Document {doc_type} v{version} for {job_slug} saved to file system.")
    return True

async def retrieve_relevant_feedback_history(
    job_slug: str,
    doc_type: str,
    current_content: Dict[str, Any],
    current_version: int,
    top_k: int = 2
) -> List[Dict[str, Any]]:
    print(f"Starting retrieve_relevant_feedback_history for job_slug: {job_slug}, doc_type: {doc_type}, current_version: {current_version}")
    all_docs_of_type = []
    loaded_all_docs = await load_documents_from_file_system(job_slug)
    if doc_type in loaded_all_docs:
        all_docs_of_type = loaded_all_docs[doc_type]
        all_docs_of_type = [doc for doc in all_docs_of_type if doc.get("version", 0) < current_version]
        all_docs_of_type.sort(key=lambda x: x.get("version", 0), reverse=True) 

    text_for_current_embedding = ""
    if doc_type == "resume":
        text_for_current_embedding = " ".join([
            json.dumps(current_content.get("education_history", ""), ensure_ascii=False),
            json.dumps(current_content.get("career_history", ""), ensure_ascii=False),
            current_content.get("certifications", ""),
            current_content.get("awards_activities", ""),
            current_content.get("skills_tech", "")
        ])
    elif doc_type == "cover_letter":
        text_for_current_embedding = (
            f"지원 이유: {current_content.get('reason_for_application', '')} "
            f"전문성 경험: {current_content.get('expertise_experience', '')} "
            f"협업 경험: {current_content.get('collaboration_experience', '')} "
            f"도전적 목표 경험: {current_content.get('challenging_goal_experience', '')} "
            f"성장 과정: {current_content.get('growth_process', '')}"
        )
    elif doc_type == "portfolio":
        text_for_current_embedding = current_content.get("summary", "")
    elif doc_type in ["portfolio_summary_url", "portfolio_summary_text"]:
        text_for_current_embedding = current_content.get("portfolio_url", "") or current_content.get("extracted_text", "")

    if not text_for_current_embedding.strip():
        print(f"Warning: No valid content for embedding for {job_slug}/{doc_type} current version {current_version}. Returning empty history.")
        return []

    current_embedding = await get_embedding(text_for_current_embedding)
    if not current_embedding:
        print("Error: Could not generate embedding for current content. Returning empty history.")
        return []
    print(f"Generated current embedding. Length: {len(current_embedding)}")
    
    sim_results = []
    for entry in all_docs_of_type:
        if "embedding" not in entry or not entry["embedding"]:
            print(f"Skipping entry version {entry.get('version')} due to missing embedding.")
            continue
            
        similarity = _cosine_similarity(current_embedding, entry["embedding"])
        sim_results.append((similarity, entry))
            
    sim_results.sort(key=lambda x: x[0], reverse=True)
    
    retrieved_history = []
    for sim, entry in sim_results:
        if len(retrieved_history) < top_k:
            retrieved_history.append(entry)
            print(f"Retrieved history: version {entry.get('version')}, similarity: {sim:.4f}")
        else:
            break
            
    retrieved_history.sort(key=lambda x: x.get("version", 0), reverse=True)
    
    print(f"Finished retrieve_relevant_feedback_history. Found {len(retrieved_history)} relevant entries.")
    return retrieved_history

# 새로운 기업 분석 엔드포인트
@app.post("/api/analyze_company", response_class=JSONResponse)
async def analyze_company_endpoint(request_data: AnalyzeCompanyRequest):
    company_name = request_data.company_name
    if not company_name:
        raise HTTPException(status_code=400, detail="기업명을 입력해주세요.")

    try:
        # 이전에 분석한 기업 정보가 있는지 확인
        existing_analysis = await load_company_analysis(company_name)
        if existing_analysis:
            print(f"Using cached analysis for company: {company_name}")
            return JSONResponse(content={
                "message": f"'{company_name}' 기업 분석을 성공적으로 불러왔습니다.",
                "company_analysis": existing_analysis
            })

        # 새로운 기업 분석 프롬프트 생성 및 AI 요청
        system_instruction, user_prompt = get_company_analysis_prompt(company_name)
        messages_for_ai = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ]
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai,
            response_format={"type": "json_object"}
        )
        
        ai_raw_response = response.choices[0].message.content.strip()
        parsed_analysis = json.loads(ai_raw_response)

        # 분석 결과에 기업명을 추가
        parsed_analysis["company_name"] = company_name
        
        # 분석 결과를 고정된 단일 파일에 저장 (기존 파일 덮어쓰기)
        file_path = COMPANY_ANALYSIS_FILE
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(parsed_analysis, ensure_ascii=False, indent=4))
        
        return JSONResponse(content={
            "message": f"'{company_name}' 기업 분석을 성공적으로 완료했습니다.",
            "company_analysis": parsed_analysis
        })

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"기업 분석 중 오류가 발생했습니다: {e}")

@app.post("/api/analyze_document/{doc_type}")
async def analyze_document_endpoint(
    doc_type: str, request_data: AnalyzeDocumentRequest
):
    try:
        job_title = request_data.job_title
        doc_content_dict = request_data.document_content
        new_version_number = request_data.version
        feedback_reflection = request_data.feedback_reflection
        company_name = request_data.company_name
        
        company_analysis = None
        if company_name:
            company_analysis = await load_company_analysis(company_name)
            if not company_analysis:
                # 기업 분석 정보가 없는 경우, 새로 분석하는 것을 고려하거나 경고를 반환할 수 있음
                # 현재는 None으로 두고 진행
                print(f"Warning: No analysis found for company '{company_name}'. Proceeding with job-only feedback.")

        job_slug = job_title.replace(" ", "-").replace("/", "-").lower()

        relevant_history_entries = await retrieve_relevant_feedback_history(
            job_slug=job_slug,
            doc_type=doc_type,
            current_content=doc_content_dict,
            current_version=new_version_number,
            top_k=2
        )
        
        previous_document_data = None
        older_document_data = None

        if len(relevant_history_entries) > 0:
            previous_document_data = relevant_history_entries[0]
            
            if len(relevant_history_entries) > 1:
                older_document_data = relevant_history_entries[1]

        feedback_response_json = await get_ai_feedback(
            job_title,
            doc_type,
            doc_content_dict,
            previous_document_data=previous_document_data,
            older_document_data=older_document_data,
            additional_user_context=feedback_reflection,
            company_name=company_name,
            company_analysis=company_analysis
        )
        
        if feedback_response_json.status_code != 200:
            return feedback_response_json
        
        feedback_content = json.loads(feedback_response_json.body.decode('utf-8'))
        
        overall_ai_feedback = feedback_content.get("overall_feedback")
        ai_summary = feedback_content.get("summary", "")
        individual_ai_feedbacks = feedback_content.get("individual_feedbacks", {})

        text_for_current_embedding = ""
        if doc_type == "resume":
            text_for_current_embedding = " ".join([
                json.dumps(doc_content_dict.get("education_history", ""), ensure_ascii=False),
                json.dumps(doc_content_dict.get("career_history", ""), ensure_ascii=False),
                doc_content_dict.get("certifications", ""),
                doc_content_dict.get("awards_activities", ""),
                doc_content_dict.get("skills_tech", "")
            ])
        elif doc_type == "cover_letter":
            text_for_current_embedding = (
                f"지원 이유: {doc_content_dict.get('reason_for_application', '')} "
                f"전문성 경험: {doc_content_dict.get('expertise_experience', '')} "
                f"협업 경험: {doc_content_dict.get('collaboration_experience', '')} "
                f"도전적 목표 경험: {doc_content_dict.get('challenging_goal_experience', '')} "
                f"성장 과정: {doc_content_dict.get('growth_process', '')}"
            )
        else:
            text_for_current_embedding = ai_summary

        current_doc_embedding = await get_embedding(text_for_current_embedding)
        
        current_content_hash = calculate_content_hash(doc_content_dict)

        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type, 
            "version": new_version_number,
            "content": doc_content_dict,
            "feedback": overall_ai_feedback,
            "individual_feedbacks": individual_ai_feedbacks,
            "embedding": current_doc_embedding,
            "content_hash": current_content_hash,
            "company_name": company_name,
        }

        await save_document_to_file_system(doc_to_save)

        return JSONResponse(content={
            "message": "Document analyzed and saved successfully!", 
            "ai_feedback": overall_ai_feedback,
            "individual_feedbacks": individual_ai_feedbacks,
            "new_version_data": doc_to_save
        }, status_code=200)

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in analyze_document_endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error during analysis and saving: {e}")

@app.post("/api/portfolio_summary")
async def portfolio_summary(
    portfolio_pdf: UploadFile = File(None),
    portfolio_link: str = Form(None),
    job_title: str = Form(...),
    version: int = Form(1), 
    feedback_reflection: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None)
):
    doc_type_for_prompt = ""
    prompt_content_for_ai = {}
    
    if portfolio_pdf and portfolio_pdf.filename:
        doc_type_for_prompt = "portfolio_summary_text"
        try:
            contents = await portfolio_pdf.read()
            if len(contents) > 10 * 1024 * 1024: 
                raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다. 10MB 이하의 파일을 업로드해주세요.")
            
            reader = PyPDF2.PdfReader(io.BytesIO(contents))
            extracted_text = "".join([page.extract_text() or "" for page in reader.pages])
            
            if not extracted_text.strip():
                raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출하지 못했습니다. 스캔된 이미지 PDF일 수 있습니다.")
            
            prompt_content_for_ai = {"extracted_text": extracted_text}
            
        except Exception as e:
            print(traceback.format_exc())
            raise HTTPException(status_code=400, detail=f"PDF 처리 중 오류가 발생했습니다: {str(e)}")
            
    elif portfolio_link and portfolio_link.strip():
        if not (portfolio_link.startswith('http://') or portfolio_link.startswith('https://')):
            portfolio_link = 'http://' + portfolio_link
            
        doc_type_for_prompt = "portfolio_summary_url"
        prompt_content_for_ai = {"portfolio_url": portfolio_link}

    else:
        raise HTTPException(status_code=400, detail="분석을 위해 PDF 파일 또는 유효한 링크를 입력해주세요.")
    
    try:
        job_slug = job_title.replace(" ", "-").replace("/", "-").lower()

        relevant_history_entries = await retrieve_relevant_feedback_history(
            job_slug=job_slug,
            doc_type="portfolio",
            current_content=prompt_content_for_ai,
            current_version=version,
            top_k=2
        )

        previous_document_data = relevant_history_entries[0] if relevant_history_entries else None
        older_document_data = relevant_history_entries[1] if len(relevant_history_entries) > 1 else None

        company_analysis = None
        if company_name:
            company_analysis = await load_company_analysis(company_name)
            if not company_analysis:
                print(f"Warning: No analysis found for company '{company_name}'. Proceeding with job-only feedback.")


        ai_response_json = await get_ai_feedback(
            job_title, 
            doc_type_for_prompt, 
            prompt_content_for_ai,
            previous_document_data=previous_document_data,
            older_document_data=older_document_data,
            additional_user_context=feedback_reflection,
            company_name=company_name,
            company_analysis=company_analysis
        )
        
        if ai_response_json.status_code != 200:
            return ai_response_json
        
        summary_content = json.loads(ai_response_json.body.decode('utf-8'))
        
        overall_summary_text = summary_content.get("summary", "요약 내용을 생성할 수 없습니다.")
        overall_feedback_text = summary_content.get("overall_feedback", "피드백 내용을 생성할 수 없습니다.")
        individual_feedbacks = summary_content.get("individual_feedbacks", {}) 

        if not overall_summary_text or overall_summary_text == "요약 내용을 생성할 수 없습니다.":
            raise HTTPException(status_code=500, detail="AI 요약 내용이 없습니다.")

    except HTTPException as e:
        raise e
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"AI 요약 오류: {e}")

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        font_path = os.path.join("static", "fonts", "NotoSansKR-Regular.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}. static/fonts/NotoSansKR-Regular.ttf 경로를 확인해주세요.")

        pdf.add_font('NotoSansKR', '', font_path, uni=True)
        pdf.set_font('NotoSansKR', '', 12)

        pdf.multi_cell(0, 10, txt=f"{job_title} 포트폴리오 요약본\n", align='C')
        pdf.ln(10)
        
        pdf.set_font('NotoSansKR', '', 14)
        pdf.cell(0, 10, "▶ 포트폴리오 요약", ln=1, align='L')
        pdf.set_font('NotoSansKR', '', 12)
        pdf.multi_cell(0, 10, txt=overall_summary_text)
        pdf.ln(10)
        
        job_slug = job_title.replace(" ", "-").replace("/", "-").lower()
        doc_type_for_save = "portfolio"
        job_data_dir = os.path.join(DATA_DIR, job_slug, doc_type_for_save)
        os.makedirs(job_data_dir, exist_ok=True)
        
        pdf_filename = f"v{version}_summary.pdf"
        pdf_file_path = os.path.join(job_data_dir, pdf_filename)
        pdf.output(pdf_file_path)
        
        summary_embedding = await get_embedding(overall_summary_text)
        summary_content_hash = calculate_content_hash({"summary": overall_summary_text})

        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type_for_save,
            "version": version,
            "content": {
                "portfolio_pdf_filename": portfolio_pdf.filename if portfolio_pdf else None,
                "portfolio_link": portfolio_link,
                "summary_type": doc_type_for_prompt,
                "summary": overall_summary_text,
                "download_pdf_url": f"/api/download_pdf/{job_slug}/{doc_type_for_save}/{pdf_filename}"
            },
            "feedback": overall_feedback_text,
            "individual_feedbacks": individual_feedbacks,
            "embedding": summary_embedding,
            "content_hash": summary_content_hash,
            "company_name": company_name,
        }
        await save_document_to_file_system(doc_to_save)
        
        return JSONResponse(content={
            "message": "AI 요약본이 생성되었습니다.",
            "overall_summary": overall_summary_text,
            "overall_feedback": overall_feedback_text,
            "individual_feedbacks": individual_feedbacks,
            "download_url": doc_to_save["content"]["download_pdf_url"]
        }, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"PDF 생성 및 저장 오류: {e}")

@app.get("/api/download_pdf/{job_slug}/{doc_type}/{filename}")
async def download_pdf_file(job_slug: str, doc_type: str, filename: str):
    file_path = os.path.join(DATA_DIR, job_slug, doc_type, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
        
    encoded_filename = quote(filename)
    content_disposition_header = f"attachment; filename*=UTF-8''{encoded_filename}"
    
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": content_disposition_header}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)