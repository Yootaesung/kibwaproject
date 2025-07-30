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
from prompts import get_document_analysis_prompt # 수정된 get_document_analysis_prompt 임포트
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
    individual_feedbacks: Dict[str, str] = {} # 개별 피드백 필드 추가

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
    이 함수는 이제 JSON 응답을 기대하며, overall_feedback과 individual_feedbacks를 반환합니다.
    """
    try:
        job_detail = JOB_DETAILS.get(job_title)
        job_competencies_list = job_detail.get("competencies") if job_detail else None

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
        print(f"Generated Prompt for {doc_type} (Job: {job_title}):\n{prompt[:500]}...")

        if prompt.startswith("오류:"):
            # 프롬프트 생성 자체에 오류가 있다면 JSON으로 반환
            return JSONResponse(content={"error": prompt}, status_code=400)

        messages_for_ai = [
            {"role": "system", "content": "You are a helpful AI assistant who provides detailed feedback on job application documents. Always respond in the specified JSON format."},
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_for_ai,
            response_format={"type": "json_object"} # JSON 응답을 명시적으로 요청
        )

        ai_raw_response = response.choices[0].message.content.strip()
        print(f"Raw AI Response: {ai_raw_response}")

        try:
            # AI 응답이 JSON 형식이 아닐 경우를 대비한 처리
            parsed_feedback = json.loads(ai_raw_response)
        except json.JSONDecodeError:
            print(f"AI response was not valid JSON: {ai_raw_response}")
            # 유효한 JSON이 아니면 전체 응답을 overall_feedback으로 간주하고 individual_feedbacks는 비워둠
            return JSONResponse(
                content={
                    "overall_feedback": f"AI 응답 파싱 오류: 유효한 JSON 형식이 아닙니다. 원본: {ai_raw_response[:200]}...",
                    "individual_feedbacks": {}
                }, 
                status_code=500
            )

        # 필요한 키들이 있는지 확인
        overall_feedback = parsed_feedback.get("overall_feedback", "AI 피드백을 생성하는 데 문제가 발생했습니다.")
        individual_feedbacks = parsed_feedback.get("individual_feedbacks", {})

        # 특정 오류 메시지가 포함된 경우 (포트폴리오 요약 등)
        if "찾을 수 없다" in overall_feedback or "유효한 포트폴리오 내용을 찾을 수 없" in overall_feedback or "unable to access external URLs" in overall_feedback:
            return JSONResponse(content={"error": overall_feedback}, status_code=400)

        # 이제 overall_feedback과 individual_feedbacks를 함께 반환
        return JSONResponse(content={
            "overall_feedback": overall_feedback,
            "individual_feedbacks": individual_feedbacks
        }, status_code=200)

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
                                # individual_feedbacks 필드가 없으면 빈 객체로 초기화
                                if "individual_feedbacks" not in doc_data:
                                    doc_data["individual_feedbacks"] = {}
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


@app.delete("/api/rollback_document/{doc_type}/{job_slug}/{version_to_rollback}", response_class=JSONResponse)
async def rollback_document_endpoint(doc_type: str, job_slug: str, version_to_rollback: int):
    """
    파일 시스템에서 특정 문서 타입을 지정된 버전으로 롤백합니다.
    해당 버전 이후의 모든 파일을 삭제합니다.
    """
    decoded_job_slug = unquote(job_slug)
    doc_type_dir = os.path.join(DATA_DIR, decoded_job_slug, doc_type)

    if not os.path.exists(doc_type_dir):
        raise HTTPException(status_code=404, detail=f"Document type directory not found: {doc_type_dir}")

    # 현재 존재하는 모든 버전 파일 목록 가져오기
    existing_versions = []
    for filename in os.listdir(doc_type_dir):
        if filename.startswith("v") and filename.endswith(".json"):
            try:
                version_num = int(filename[1:-5]) # "vX.json" -> X 추출
                existing_versions.append(version_num)
            except ValueError:
                continue

    # 롤백할 버전보다 높은 모든 버전 삭제
    versions_to_delete = [v for v in existing_versions if v > version_to_rollback]
    for version_num in versions_to_delete:
        file_path = os.path.join(doc_type_dir, f"v{version_num}.json")
        try:
            os.remove(file_path)
            print(f"Deleted {file_path}")
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")

    # 롤백 후 해당 doc_type의 최신 버전을 클라이언트에게 알릴 필요는 없음
    # 클라이언트는 load_documents_endpoint를 다시 호출하여 업데이트된 상태를 가져감
    return JSONResponse(content={"message": f"{doc_type} for {job_slug} rolled back to version {version_to_rollback}."})


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
            # 버전을 기준으로 정렬
            all_docs_of_type.sort(key=lambda x: x.get("version", 0))

        # 현재 버전에 해당하는 이전/이전 이전 문서 찾기
        for doc in all_docs_of_type:
            if doc.get("version") == new_version_number - 1:
                previous_document_content = doc.get("content")
                # 이전 피드백은 이제 JSON 문자열일 수 있으므로, 전체 피드백만 사용
                previous_feedback = doc.get("feedback")
            elif doc.get("version") == new_version_number - 2:
                older_document_content = doc.get("content")
                older_feedback = doc.get("feedback")
        
        # 임베딩 생성
        text_for_embedding = ""
        if doc_type == "resume":
            text_for_embedding = " ".join([f"{key}: {value}" for key, value in doc_content_dict.items()])
        elif doc_type == "cover_letter":
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
        else: # 포트폴리오 등 기타 문서 (이 엔드포인트는 주로 텍스트 문서용)
            text_for_embedding = json.dumps(doc_content_dict, ensure_ascii=False)

        embedding_vector = await get_embedding(text_for_embedding)

        # AI 피드백 생성 (이제 JSON 응답을 반환)
        feedback_response_json = await get_ai_feedback(
            job_title,
            doc_type,
            doc_content_dict,
            previous_document_content=previous_document_content,
            previous_feedback=previous_feedback, # 이전 feedback은 overall_feedback string
            older_document_content=older_document_content,
            older_feedback=older_feedback # 이전 feedback은 overall_feedback string
        )
        
        if feedback_response_json.status_code != 200:
            # get_ai_feedback에서 오류가 발생한 경우 해당 응답을 그대로 반환
            return feedback_response_json
        
        # get_ai_feedback에서 반환된 JSON 내용을 직접 가져옴
        feedback_content = json.loads(feedback_response_json.body.decode('utf-8'))
        
        # overall_feedback과 individual_feedbacks를 추출
        overall_ai_feedback = feedback_content.get("overall_feedback")
        individual_ai_feedbacks = feedback_content.get("individual_feedbacks", {})


        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type, 
            "version": new_version_number,
            "content": doc_content_dict,
            "feedback": overall_ai_feedback, # 전체 피드백 저장
            "individual_feedbacks": individual_ai_feedbacks, # 개별 피드백 저장
            "embedding": embedding_vector
        }

        # 파일 시스템에 문서 저장
        await save_document_to_file_system(doc_to_save)

        return JSONResponse(content={
            "message": "Document analyzed and saved successfully!", 
            "ai_feedback": overall_ai_feedback, # 클라이언트에게 전체 피드백 반환
            "individual_feedbacks": individual_ai_feedbacks, # 클라이언트에게 개별 피드백 반환
            "new_version_data": doc_to_save # 클라이언트가 다이어그램 업데이트에 사용할 새 버전 데이터
        }, status_code=200)

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
                # aiofiles.write는 동기 함수가 아니므로 await 사용
                await aiofiles.write(tmp.name, contents) 
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
        # 포트폴리오 요약은 이전 버전 문서/피드백을 고려하지 않으므로, 이 인자들은 전달하지 않음
        # get_ai_feedback은 이제 JSON 응답을 반환
        ai_response_json = await get_ai_feedback(job_title, doc_type_for_prompt, prompt_content_for_ai)
        
        if ai_response_json.status_code != 200:
            return ai_response_json
        
        summary_content = json.loads(ai_response_json.body.decode('utf-8'))
        summary = summary_content.get("overall_feedback", "") # 전체 요약 내용을 가져옴

        # 포트폴리오의 경우 개별 피드백은 중요하지 않으므로 빈 객체로 설정하거나 필요에 따라 추가
        individual_feedbacks = summary_content.get("individual_feedbacks", {}) 

        if not summary:
            return JSONResponse(content={"error": "AI 요약 내용이 없습니다."}, status_code=500)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

    # PDF 생성 및 저장 (기존 로직 유지)
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
        pdf.multi_cell(0, 10, summary)

        # PDF 파일을 임시로 저장하고 클라이언트에 응답
        # NOTE: 이 부분은 클라이언트가 PDF를 다운로드하면서 동시에 JSON 데이터를 받을 수 없으므로,
        # JSON 응답으로 변경하고 PDF 다운로드 URL을 제공하는 방식으로 수정합니다.
        # 실제 PDF 파일을 서버의 static 디렉토리 내에 저장하고 해당 URL을 제공해야 합니다.
        
        # 새 PDF 파일 저장 경로 (실제 파일 저장 로직)
        pdf_output_dir = os.path.join(DATA_DIR, "generated_summaries")
        os.makedirs(pdf_output_dir, exist_ok=True) # 디렉토리 생성

        # 새 버전 번호 결정 (파일 시스템에서 기존 버전 로드)
        job_slug_for_filename = job_title.replace(" ", "-").replace("/", "-").lower()
        doc_type_for_save = "portfolio_summary" # 포트폴리오 요약 파일용 문서 타입
        
        # 파일명 중복을 피하기 위해 버전 번호를 직접 관리하거나, UUID 등을 사용하는 것이 좋음
        # 여기서는 단순히 다음 버전 번호를 사용하지만, 실제로는 job_slug_doc_type_vX.pdf 형태가 더 적합.
        # 일단은 `job_slug`와 현재 타임스탬프 또는 단순히 "latest" 등으로 관리하는 것이 간단
        
        # 기존 요약 파일이 있다면 버전 관리
        current_summary_versions = [f for f in os.listdir(pdf_output_dir) if f.startswith(f"portfolio_summary_{job_slug_for_filename}_v") and f.endswith(".pdf")]
        next_summary_version_number = 0
        if current_summary_versions:
            max_version = max([int(f.split('_v')[-1].replace('.pdf', '')) for f in current_summary_versions])
            next_summary_version_number = max_version + 1

        output_filename = f"portfolio_summary_{job_slug_for_filename}_v{next_summary_version_number}.pdf"
        pdf_filepath_on_server = os.path.join(pdf_output_dir, output_filename)

        pdf.output(pdf_filepath_on_server) # PDF 파일을 서버에 저장
        print(f"Portfolio summary PDF saved to: {pdf_filepath_on_server}")
        
        # 클라이언트에게 제공할 다운로드 URL
        download_url = f"/data/generated_summaries/{output_filename}"

        # 파일 시스템에 포트폴리오 정보 저장
        doc_type = "portfolio" # 포트폴리오 문서 타입
        
        # 이전에 저장된 포트폴리오 문서의 다음 버전 번호를 가져옴 (summary와 별개)
        loaded_all_docs = await load_documents_from_file_system(job_slug_for_filename)
        current_portfolio_versions = loaded_all_docs.get(doc_type, [])
        new_version_number_for_db = len(current_portfolio_versions) # 다음 버전 번호
        
        doc_to_save = {
            "job_title": job_title,
            "doc_type": doc_type, 
            "version": new_version_number_for_db,
            "content": {
                "portfolio_pdf_filename": portfolio_pdf.filename if portfolio_pdf else None,
                "portfolio_link": portfolio_link,
                "summary": summary,
                "download_pdf_url": download_url # 저장된 PDF의 다운로드 URL
            },
            "feedback": summary, # 전체 요약 내용을 feedback으로 저장
            "individual_feedbacks": individual_feedbacks, # 포트폴리오는 비어있을 가능성이 높음
            "embedding": await get_embedding(summary) # 요약 텍스트로 임베딩 생성
        }
        await save_document_to_file_system(doc_to_save)

        return JSONResponse(content={
            "message": "포트폴리오가 성공적으로 업로드 및 요약되었습니다.",
            "ai_summary": summary, # AI 요약 텍스트
            "individual_feedbacks": individual_feedbacks, # 포트폴리오의 경우 비어있을 수 있음
            "new_version_data": doc_to_save, # 새 버전 데이터 (클라이언트에서 다이어그램 업데이트용)
            "download_url": download_url # 클라이언트가 다운로드할 수 있는 URL
        }, status_code=200)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": f"PDF 생성 및 저장 오류: {e}"}, status_code=500)

# 서버에서 생성된 파일을 제공하기 위한 새로운 StaticFiles 마운트
# /data/generated_summaries 경로의 파일을 웹에서 접근 가능하게 함
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)