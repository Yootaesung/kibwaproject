from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional, Tuple
import os
import aiofiles
import json
import traceback
from urllib.parse import unquote
import hashlib # 해시값 생성을 위한 라이브러리 추가

# job_data.py에서 필요한 데이터들을 임포트합니다.
from job_data import JOB_CATEGORIES, JOB_DETAILS, get_job_document_schema

# prompts.py에서 get_document_analysis_prompt만 임포트합니다.
from prompts import get_document_analysis_prompt

from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from fpdf import FPDF
import tempfile
from pydantic import BaseModel
import numpy as np # 코사인 유사도 계산을 위해 numpy 추가 (pip install numpy)

load_dotenv()

# OpenAI API 설정
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small" # 더 작은 임베딩 모델 사용 (비용 효율적)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

# 데이터를 저장할 로컬 폴더 설정
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# 데이터 폴더가 없으면 생성
os.makedirs(DATA_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
# 생성된 요약 PDF 파일 등을 제공하기 위한 마운트
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data") # /data/* 경로로 DATA_DIR 접근 허용
templates = Jinja2Templates(directory="templates")

# 이력서 분석 요청을 위한 Pydantic 모델 정의
class AnalyzeDocumentRequest(BaseModel):
    job_title: str
    document_content: Dict[str, Any]
    version: int # 클라이언트에서 넘어오는 현재 버전 (newVersionNumber)
    feedback_reflection: Optional[str] = None # 사용자가 이전 피드백을 어떻게 반영했는지 설명

class SaveDocumentRequest(BaseModel):
    job_slug: str
    doc_type: str # 이 필드는 클라이언트가 저장 요청 시 명시적으로 보내야 함
    version: int
    content: Dict[str, Any]
    feedback: str
    individual_feedbacks: Dict[str, str] = {} # 개별 피드백 필드 추가

# get_ai_feedback 함수 정의
async def get_ai_feedback(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    previous_document_data: Optional[Dict[str, Any]] = None, # 전체 이전 문서 데이터
    older_document_data: Optional[Dict[str, Any]] = None, # 전체 이전 이전 문서 데이터
    additional_user_context: Optional[str] = None # 사용자가 제공한 피드백 반영 내용
) -> JSONResponse:
    """
    OpenAI GPT 모델을 호출하여 문서 분석 피드백을 생성합니다.
    이 함수는 이제 JSON 응답을 기대하며, overall_feedback과 individual_feedbacks를 반환합니다.
    """
    try:
        job_detail = JOB_DETAILS.get(job_title)
        job_competencies_list = job_detail.get("competencies") if job_detail else None

        # prompts.py의 get_document_analysis_prompt는 이제 시스템 지시와 사용자 프롬프트를 분리하여 반환
        system_instruction, user_prompt = get_document_analysis_prompt(
            job_title=job_title,
            doc_type=doc_type,
            document_content=document_content,
            job_competencies=job_competencies_list,
            previous_document_data=previous_document_data,
            older_document_data=older_document_data,
            additional_user_context=additional_user_context
        )
        
        print(f"Generated System Instruction for {doc_type} (Job: {job_title}):\n{system_instruction[:500]}...")
        print(f"Generated User Prompt for {doc_type} (Job: {job_title}):\n{user_prompt[:500]}...")

        if user_prompt.startswith("오류:"):
            return JSONResponse(content={"error": user_prompt}, status_code=400)

        messages_for_ai = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ]

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai,
            response_format={"type": "json_object"} # JSON 응답을 명시적으로 요청 (GPT-4o, GPT-4-turbo 이상 지원)
        )

        ai_raw_response = response.choices[0].message.content.strip()
        print(f"Raw AI Response: {ai_raw_response}")

        try:
            parsed_feedback = json.loads(ai_raw_response)
        except json.JSONDecodeError:
            print(f"AI response was not valid JSON: {ai_raw_response}")
            return JSONResponse(
                content={
                    "overall_feedback": f"AI 응답 파싱 오류: 유효한 JSON 형식이 아닙니다. 원본: {ai_raw_response[:200]}...",
                    "individual_feedbacks": {}
                }, 
                status_code=500
            )

        overall_feedback = parsed_feedback.get("overall_feedback", "AI 피드백을 생성하는 데 문제가 발생했습니다.")
        individual_feedbacks = parsed_feedback.get("individual_feedbacks", {})

        if "찾을 수 없다" in overall_feedback or "유효한 포트폴리오 내용을 찾을 수 없" in overall_feedback or "unable to access external URLs" in overall_feedback:
            return JSONResponse(content={"error": overall_feedback}, status_code=400)

        return JSONResponse(content={
            "overall_feedback": overall_feedback,
            "individual_feedbacks": individual_feedbacks
        }, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

# get_embedding 함수 정의
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

# _cosine_similarity 함수 정의
def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """코사인 유사도 계산 (벡터 유사성 검색 시 사용)"""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    # NumPy를 사용하여 계산 효율성 높이기
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    dot_product = np.dot(vec1_np, vec2_np)
    magnitude1 = np.linalg.norm(vec1_np)
    magnitude2 = np.linalg.norm(vec2_np)
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

# 콘텐츠 해시 생성 함수
def calculate_content_hash(content: Dict[str, Any]) -> str:
    """딕셔너리 내용을 정렬하여 일관된 해시를 생성합니다."""
    # 딕셔너리의 키를 기준으로 정렬하여 일관된 문자열 표현 생성
    # ensure_ascii=False는 한글 등의 유니코드 문자가 \uXXXX 대신 원본으로 유지되도록 함
    # sort_keys=True는 딕셔너리 키 순서를 정렬하여 일관된 해시를 보장
    sorted_items_str = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(sorted_items_str.encode('utf-8')).hexdigest()

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
async def get_document_schema_endpoint(doc_type: str, job_slug: str): # 엔드포인트 이름 변경 (함수명 중복 방지)
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

# 새로 추가된 엔드포인트
@app.get("/api/load_documents/{job_slug}", response_class=JSONResponse)
async def api_load_documents(job_slug: str):
    """
    특정 직무(job_slug)에 해당하는 모든 문서(이력서, 자기소개서, 포트폴리오)를 로드합니다.
    """
    decoded_job_slug = unquote(job_slug)
    print(f"API Load Documents: Received job_slug: {job_slug}, Decoded: {decoded_job_slug}")

    # 실제 job_title 유효성 검사 (필요하다면)
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
    """
    파일 시스템에서 특정 job_slug에 해당하는 모든 문서 버전(이력서, 자기소개서, 포트폴리오)을 불러옵니다.
    """
    job_data_dir = os.path.join(DATA_DIR, job_slug)
    loaded_data = {
        "resume": [],
        "cover_letter": [],
        "portfolio": [] 
    }

    if os.path.exists(job_data_dir):
        for doc_type in loaded_data.keys(): # resume, cover_letter, portfolio 순회
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
                                # 임베딩 필드 존재 여부 확인 (기존 데이터 호환성)
                                if "embedding" not in doc_data:
                                    print(f"Warning: Embedding missing for {job_slug}/{doc_type}/v{doc_data.get('version', 'N/A')}. Generating now...")
                                    # 임베딩 재생성 로직 (기존 데이터에 임베딩이 없을 경우)
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
                                        text_to_embed = doc_data["content"].get("summary", "") # 포트폴리오는 summary 필드를 임베딩
                                    
                                    if text_to_embed.strip():
                                        doc_data["embedding"] = await get_embedding(text_to_embed)
                                    else:
                                        doc_data["embedding"] = [] # 임베딩할 내용이 없으면 빈 리스트
                                        print(f"No content to embed for {job_slug}/{doc_type}/v{doc_data.get('version', 'N/A')}.")

                                versions.append(doc_data)
                            except json.JSONDecodeError:
                                print(f"Error decoding JSON from {filename}")
                versions.sort(key=lambda x: x.get("version", 0)) # 오름차순 정렬
                loaded_data[doc_type] = versions
    
    return loaded_data

async def save_document_to_file_system(document_data: Dict[str, Any]):
    """
    문서 내용을 파일 시스템에 저장합니다. 동일 버전이 존재하면 업데이트합니다.
    """
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
    current_version: int, # 현재 버전 추가: 동일 버전 또는 미래 버전 제외 위함
    top_k: int = 2 # 가장 유사한 2개의 이전 기록을 가져옴
) -> List[Dict[str, Any]]:
    """
    현재 문서의 특정 필드 내용과 가장 관련성 높은 이전 피드백 기록을 파일 시스템에서 검색합니다.
    """
    print(f"Starting retrieve_relevant_feedback_history for job_slug: {job_slug}, doc_type: {doc_type}, current_version: {current_version}")
    all_docs_of_type = []
    loaded_all_docs = await load_documents_from_file_system(job_slug)
    if doc_type in loaded_all_docs:
        all_docs_of_type = loaded_all_docs[doc_type]
        # 현재 분석 중인 버전과 같거나 높은 버전은 비교 대상에서 제외
        all_docs_of_type = [doc for doc in all_docs_of_type if doc.get("version", 0) < current_version]
        # 최신 버전이 먼저 오도록 정렬 (유사도 계산 전 우선 순위)
        all_docs_of_type.sort(key=lambda x: x.get("version", 0), reverse=True) 

    # 현재 콘텐츠를 기반으로 임베딩 생성 (전체 문서 혹은 핵심 필드를 결합하여 생성)
    text_for_current_embedding = ""
    if doc_type == "resume":
        # 이력서의 경우 주요 필드들을 결합
        text_for_current_embedding = " ".join([
            json.dumps(current_content.get("education_history", ""), ensure_ascii=False),
            json.dumps(current_content.get("career_history", ""), ensure_ascii=False),
            current_content.get("certifications", ""),
            current_content.get("awards_activities", ""),
            current_content.get("skills_tech", "")
        ])
    elif doc_type == "cover_letter":
        # 자기소개서의 경우 주요 질문 답변들을 결합
        text_for_current_embedding = (
            f"지원 이유: {current_content.get('reason_for_application', '')} "
            f"전문성 경험: {current_content.get('expertise_experience', '')} "
            f"협업 경험: {current_content.get('collaboration_experience', '')} "
            f"도전적 목표 경험: {current_content.get('challenging_goal_experience', '')} "
            f"성장 과정: {current_content.get('growth_process', '')}"
        )
    elif doc_type == "portfolio": 
        # 포트폴리오의 경우 저장된 'summary' 필드를 사용
        text_for_current_embedding = current_content.get("summary", "") 
    elif doc_type in ["portfolio_summary_url", "portfolio_summary_text"]: # 이 경우는 임베딩이 불필요할 수 있으나, 만약을 대비
        text_for_current_embedding = current_content.get("portfolio_url", "") or current_content.get("extracted_text", "")


    if not text_for_current_embedding.strip():
        print(f"Warning: No valid content for embedding for {job_slug}/{doc_type} current version {current_version}. Returning empty history.")
        return []

    current_embedding = await get_embedding(text_for_current_embedding)
    if not current_embedding:
        print("Error: Could not generate embedding for current content. Returning empty history.")
        return []
    print(f"Generated current embedding. Length: {len(current_embedding)}")
    
    sim_results = [] # similarities 대신 sim_results 변수명 사용
    for entry in all_docs_of_type:
        # 임베딩이 없는 데이터는 건너뜁니다.
        if "embedding" not in entry or not entry["embedding"]:
            print(f"Skipping entry version {entry.get('version')} due to missing embedding.")
            continue
            
        similarity = _cosine_similarity(current_embedding, entry["embedding"])
        sim_results.append((similarity, entry))
            
    sim_results.sort(key=lambda x: x[0], reverse=True) # 유사도 높은 순으로 정렬
    
    retrieved_history = []
    # 유사도 높은 순으로 최대 top_k개 가져오기
    for sim, entry in sim_results:
        if len(retrieved_history) < top_k:
            retrieved_history.append(entry)
            print(f"Retrieved history: version {entry.get('version')}, similarity: {sim:.4f}")
        else:
            break
            
    # 가져온 기록을 최신순으로 다시 정렬 (프롬프트에 유용하도록)
    retrieved_history.sort(key=lambda x: x.get("version", 0), reverse=True)
    
    print(f"Finished retrieve_relevant_feedback_history. Found {len(retrieved_history)} relevant entries.")
    return retrieved_history

# --- API 엔드포인트 ---

@app.post("/api/analyze_document/{doc_type}")
async def analyze_document_endpoint(
    doc_type: str, request_data: AnalyzeDocumentRequest
):
    try:
        job_title = request_data.job_title
        doc_content_dict = request_data.document_content
        new_version_number = request_data.version
        feedback_reflection = request_data.feedback_reflection # 사용자의 반영 내용

        job_slug = job_title.replace(" ", "-").replace("/", "-").lower()

        # 1. 이전 문서 기록 검색
        relevant_history_entries = await retrieve_relevant_feedback_history(
            job_slug=job_slug,
            doc_type=doc_type,
            current_content=doc_content_dict,
            current_version=new_version_number,
            top_k=2 # 가장 관련성 높은 이전 2개 버전까지 가져옴
        )
        
        previous_document_data = None
        older_document_data = None

        if len(relevant_history_entries) > 0:
            previous_document_data = relevant_history_entries[0] # 가장 최신/유사한 이전 버전
            
            if len(relevant_history_entries) > 1:
                older_document_data = relevant_history_entries[1] # 그 다음 이전 버전

        # 3. AI 피드백 생성
        # get_ai_feedback 함수에 previous_document_data, older_document_data, additional_user_context를 직접 전달
        feedback_response_json = await get_ai_feedback(
            job_title,
            doc_type,
            doc_content_dict,
            previous_document_data=previous_document_data,
            older_document_data=older_document_data,
            additional_user_context=feedback_reflection # 사용자가 제공한 반영 내용 전달
        )
        
        if feedback_response_json.status_code != 200:
            return feedback_response_json
        
        feedback_content = json.loads(feedback_response_json.body.decode('utf-8'))
        
        overall_ai_feedback = feedback_content.get("overall_feedback")
        individual_ai_feedbacks = feedback_content.get("individual_feedbacks", {})

        # 4. 현재 문서의 임베딩 생성 (저장을 위해)
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
        else: # portfolio
            text_for_current_embedding = json.dumps(doc_content_dict, ensure_ascii=False)

        current_doc_embedding = await get_embedding(text_for_current_embedding)
        
        # 내용 해시 계산은 계속 진행 (저장되는 데이터에 포함시키기 위함)
        current_content_hash = calculate_content_hash(doc_content_dict)

        # 5. 문서 데이터에 임베딩, 피드백, 해시 추가 후 저장
        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type, 
            "version": new_version_number,
            "content": doc_content_dict,
            "feedback": overall_ai_feedback, # 전체 피드백 저장
            "individual_feedbacks": individual_ai_feedbacks, # 개별 피드백 저장
            "embedding": current_doc_embedding, # 현재 문서의 임베딩 저장
            "content_hash": current_content_hash # 내용 해시 저장
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
    # 포트폴리오 요약도 버전을 가질 수 있도록 추가
    version: int = Form(1), 
    feedback_reflection: Optional[str] = Form(None) # 사용자 반영 내용 추가
):
    doc_type_for_prompt = ""
    prompt_content_for_ai = {}
    extracted_summary_text = "" # 추출된 요약 텍스트를 저장할 변수

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
                tmp_path = tmp.name
            
            async with aiofiles.open(tmp_path, 'wb') as f:
                await f.write(contents)
                
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
                    print(f"Error unlinking temporary file: {e}") 
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
        job_slug = job_title.replace(" ", "-").replace("/", "-").lower()

        # 이전 포트폴리오 기록 조회 (임베딩 기반 유사성 검색)
        relevant_history_entries = await retrieve_relevant_feedback_history(
            job_slug=job_slug,
            doc_type="portfolio", # 포트폴리오 요약도 'portfolio' 타입으로 기록 관리
            current_content=prompt_content_for_ai, # URL 또는 추출된 텍스트를 content로 사용
            current_version=version,
            top_k=2
        )

        previous_document_data = relevant_history_entries[0] if relevant_history_entries else None
        older_document_data = relevant_history_entries[1] if len(relevant_history_entries) > 1 else None

        # AI 피드백 생성
        ai_response_json = await get_ai_feedback(
            job_title, 
            doc_type_for_prompt, 
            prompt_content_for_ai,
            previous_document_data=previous_document_data, # 이전 문서 정보 전달
            older_document_data=older_document_data, # 이전 이전 문서 정보 전달
            additional_user_context=feedback_reflection # 사용자 반영 내용 전달
        )
        
        if ai_response_json.status_code != 200:
            return ai_response_json
        
        summary_content = json.loads(ai_response_json.body.decode('utf-8'))
        summary = summary_content.get("overall_feedback", "")
        individual_feedbacks = summary_content.get("individual_feedbacks", {}) 
        extracted_summary_text = summary # PDF 생성을 위해 요약 텍스트 저장

        if not summary:
            return JSONResponse(content={"error": "AI 요약 내용이 없습니다."}, status_code=500)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

    # PDF 생성 및 저장
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = os.path.join("static", "fonts", "NotoSansKR-Regular.ttf")
        if not os.path.exists(font_path):
            font_path_alt = os.path.join(os.getcwd(), "static", "fonts", "NotoSansKR-Regular.ttf")
            if not os.path.exists(font_path_alt):
                raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path} 또는 {font_path_alt}. static/fonts/NotoSansKR-Regular.ttf 경로를 확인해주세요.")
            font_path = font_path_alt
            
        pdf.add_font("NotoSans", "", font_path, uni=True)
        pdf.set_font("NotoSans", size=12)
        pdf.multi_cell(0, 10, extracted_summary_text) # 추출된 요약 텍스트 사용

        pdf_output_dir = os.path.join(DATA_DIR, "generated_summaries")
        os.makedirs(pdf_output_dir, exist_ok=True)

        job_slug_for_filename = job_title.replace(" ", "-").replace("/", "-").lower()
        
        # 클라이언트에서 넘겨준 version 사용
        output_filename = f"portfolio_summary_{job_slug_for_filename}_v{version}.pdf"
        pdf_filepath_on_server = os.path.join(pdf_output_dir, output_filename)

        pdf.output(pdf_filepath_on_server)
        print(f"Portfolio summary PDF saved to: {pdf_filepath_on_server}")
        
        download_url = f"/data/generated_summaries/{output_filename}"

        # 파일 시스템에 포트폴리오 정보 저장
        doc_type_for_save = "portfolio" # 포트폴리오 요약도 'portfolio' 타입으로 저장
        
        # 현재 요약 텍스트의 임베딩 생성
        summary_embedding = await get_embedding(extracted_summary_text)
        summary_content_hash = calculate_content_hash({"summary": extracted_summary_text}) # 요약 텍스트의 해시

        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type_for_save, 
            "version": version, # 클라이언트에서 넘어온 버전 사용
            "content": {
                "portfolio_pdf_filename": portfolio_pdf.filename if portfolio_pdf else None,
                "portfolio_link": portfolio_link,
                "summary_type": doc_type_for_prompt, # url인지 text인지 구분
                "summary": extracted_summary_text,
                "download_pdf_url": download_url
            },
            "feedback": extracted_summary_text, # 전체 요약을 feedback 필드에 저장
            "individual_feedbacks": individual_feedbacks, # 보통 비어있겠지만 혹시 모를 경우를 대비
            "embedding": summary_embedding, # 요약 텍스트로 임베딩 생성
            "content_hash": summary_content_hash # 요약 텍스트의 해시 저장
        }
        await save_document_to_file_system(doc_to_save)

        return JSONResponse(content={
            "message": "포트폴리오가 성공적으로 업로드 및 요약되었습니다.",
            "ai_summary": extracted_summary_text,
            "individual_feedbacks": individual_feedbacks,
            "new_version_data": doc_to_save,
            "download_url": download_url
        }, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"PDF 생성 및 저장 오류: {e}"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)