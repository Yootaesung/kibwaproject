# utils.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import os
import aiofiles
import json
import traceback
from urllib.parse import unquote
import hashlib
import PyPDF2
import numpy as np
import io
from fpdf import FPDF

from job_data import JOB_CATEGORIES, JOB_DETAILS
from prompts import get_document_analysis_prompt, get_company_analysis_prompt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# =========================
# OpenAI 설정
# =========================
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# 경로
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(USERS_DIR, exist_ok=True)

# ---- 사용자별 경로 헬퍼 ----
def _user_base_dir(user_id: str) -> Path:
    return USERS_DIR / user_id

def _user_job_dir(user_id: str, job_slug: str) -> Path:
    return _user_base_dir(user_id) / unquote(job_slug)

def _user_doc_dir(user_id: str, job_slug: str, doc_type: str) -> Path:
    return _user_job_dir(user_id, job_slug) / doc_type

def _user_company_file(user_id: str) -> Path:
    return _user_base_dir(user_id) / "companies" / "current_company_analysis.json"

# =========================
# 공통 유틸
# =========================
def get_job_title_from_slug(job_slug: str) -> Optional[str]:
    decoded_job_slug = unquote(job_slug)
    for category_jobs in JOB_CATEGORIES.values():
        for j_title in category_jobs:
            normalized_j_title_slug = j_title.replace(" ", "-").replace("/", "-").lower()
            if normalized_j_title_slug == decoded_job_slug:
                return j_title
    return None

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

def calculate_content_hash(content: Dict[str, Any]) -> str:
    sorted_items_str = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(sorted_items_str.encode("utf-8")).hexdigest()

# =========================
# OpenAI 호출
# =========================
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
        if user_prompt.startswith("오류:"):
            return JSONResponse(content={"error": user_prompt}, status_code=400)

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        ai_raw_response = response.choices[0].message.content.strip()
        parsed_feedback = json.loads(ai_raw_response)

        summary_text = parsed_feedback.get("summary", "요약 내용을 생성할 수 없습니다.")
        overall_feedback = parsed_feedback.get("overall_feedback", "AI 피드백을 생성하는 데 문제가 발생했습니다.")
        individual_feedbacks = parsed_feedback.get("individual_feedbacks", {})

        if "unable to access external URLs" in overall_feedback:
            return JSONResponse(content={"error": overall_feedback}, status_code=400)

        return JSONResponse(
            content={
                "summary": summary_text,
                "overall_feedback": overall_feedback,
                "individual_feedbacks": individual_feedbacks,
            },
            status_code=200,
        )

    except json.JSONDecodeError:
        return JSONResponse(
            content={
                "summary": "AI 응답 파싱 오류로 요약 불가",
                "overall_feedback": "AI 응답 파싱 오류: 유효한 JSON 형식이 아닙니다.",
                "individual_feedbacks": {},
            },
            status_code=500,
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={"error": f"AI 요약 오류: {e}"}, status_code=500)

async def get_embedding(text: str) -> List[float]:
    try:
        text = text.replace("\n", " ")
        response = client.embeddings.create(input=text, model=OPENAI_EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")

# =========================
# 기업 분석 로드/저장 (사용자별)
# =========================
async def load_company_analysis(user_id: str) -> Optional[Dict[str, Any]]:
    path = _user_company_file(user_id)
    if not path.exists():
        return None
    async with aiofiles.open(str(path), "r", encoding="utf-8") as f:
        content = await f.read()
    try:
        return json.loads(content)
    except Exception:
        return None

async def perform_company_analysis(company_name: str, file_path: str | Path) -> JSONResponse:
    try:
        existing: Optional[Dict[str, Any]] = None
        if Path(file_path).exists():
            async with aiofiles.open(str(file_path), "r", encoding="utf-8") as f:
                try:
                    loaded = json.loads(await f.read())
                    if loaded.get("company_name") == company_name:
                        existing = loaded
                except Exception:
                    existing = None
        if existing:
            return JSONResponse(
                content={"message": f"'{company_name}' 기업 분석을 성공적으로 불러왔습니다.", "company_analysis": existing}
            )

        system_instruction, user_prompt = get_company_analysis_prompt(company_name)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )

        ai_raw_response = response.choices[0].message.content.strip()
        parsed_analysis = json.loads(ai_raw_response)
        parsed_analysis["company_name"] = company_name

        path = Path(file_path)
        os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(str(path), "w", encoding="utf-8") as f:
            await f.write(json.dumps(parsed_analysis, ensure_ascii=False, indent=4))

        return JSONResponse(content={"message": f"'{company_name}' 기업 분석을 성공적으로 완료했습니다.", "company_analysis": parsed_analysis})
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"기업 분석 중 오류가 발생했습니다: {e}")

# =========================
# 파일 시스템 연동 (사용자별)
# =========================
async def load_documents_from_file_system(user_id: str, job_slug: str) -> Dict[str, List[Dict[str, Any]]]:
    base = _user_job_dir(user_id, job_slug)
    loaded_data: Dict[str, List[Dict[str, Any]]] = {"resume": [], "cover_letter": [], "portfolio": []}
    if not base.exists():
        return loaded_data

    for doc_type in loaded_data.keys():
        d = base / doc_type
        if not d.exists():
            continue
        versions: List[Dict[str, Any]] = []
        for p in d.iterdir():
            if p.is_file() and p.suffix == ".json" and p.name.startswith("v"):
                async with aiofiles.open(str(p), "r", encoding="utf-8") as f:
                    content = await f.read()
                try:
                    doc_data = json.loads(content)
                    doc_data.setdefault("individual_feedbacks", {})

                    # 임베딩 없으면 생성 (신규 스키마 우선)
                    if "embedding" not in doc_data or not doc_data["embedding"]:
                        c = doc_data.get("content", {}) or {}
                        text_to_embed = ""
                        if doc_type == "cover_letter":
                            cl_keys = [
                                "reason_for_application",
                                "expertise_experience",
                                "collaboration_experience",
                                "challenging_goal_experience",
                                "growth_process",
                            ]
                            text_to_embed = " ".join([c.get(k, "") for k in cl_keys])
                        elif doc_type == "resume":
                            text_to_embed = " ".join([
                                json.dumps(c.get("education", []), ensure_ascii=False),
                                json.dumps(c.get("activities", []), ensure_ascii=False),
                                json.dumps(c.get("awards", []), ensure_ascii=False),
                                json.dumps(c.get("certificates", []), ensure_ascii=False),
                            ])
                        elif doc_type == "portfolio":
                            text_to_embed = c.get("summary", "") or ""

                        doc_data["embedding"] = await get_embedding(text_to_embed) if text_to_embed.strip() else []

                    versions.append(doc_data)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from {p.name}")

        versions.sort(key=lambda x: x.get("version", 0))
        loaded_data[doc_type] = versions

    return loaded_data

async def save_document_to_file_system(user_id: str, document_data: Dict[str, Any]):
    job_slug = document_data["job_title"].replace(" ", "-").replace("/", "-").lower()
    doc_type = document_data["doc_type"]
    version = document_data["version"]

    out_dir = _user_doc_dir(user_id, job_slug, doc_type)
    os.makedirs(out_dir, exist_ok=True)

    file_path = out_dir / f"v{version}.json"
    async with aiofiles.open(str(file_path), "w", encoding="utf-8") as f:
        await f.write(json.dumps(document_data, ensure_ascii=False, indent=4))
    return True

# =========================
# 유사 이력 검색 (사용자별)
# =========================
async def retrieve_relevant_feedback_history(
    user_id: str,
    job_slug: str,
    doc_type: str,
    current_content: Dict[str, Any],
    current_version: int,
    top_k: int = 2,
) -> List[Dict[str, Any]]:
    # 모든 과거 문서
    loaded_all_docs = await load_documents_from_file_system(user_id, job_slug)
    all_docs_of_type: List[Dict[str, Any]] = [doc for doc in loaded_all_docs.get(doc_type, []) if doc.get("version", 0) < current_version]
    all_docs_of_type.sort(key=lambda x: x.get("version", 0), reverse=True)

    # 현재 입력으로부터 임베딩 텍스트 구성
    text_for_current_embedding = ""
    if doc_type == "resume":
        text_for_current_embedding = " ".join([
            json.dumps(current_content.get("education", []), ensure_ascii=False),
            json.dumps(current_content.get("activities", []), ensure_ascii=False),
            json.dumps(current_content.get("awards", []), ensure_ascii=False),
            json.dumps(current_content.get("certificates", []), ensure_ascii=False),
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
        text_for_current_embedding = current_content.get("summary", "") or ""
    elif doc_type in ["portfolio_summary_url", "portfolio_summary_text"]:
        text_for_current_embedding = current_content.get("portfolio_url", "") or current_content.get("extracted_text", "")

    if not text_for_current_embedding.strip():
        return []

    current_embedding = await get_embedding(text_for_current_embedding)
    if not current_embedding:
        return []

    sim_results: List[Tuple[float, Dict[str, Any]]] = []
    for entry in all_docs_of_type:
        if "embedding" not in entry or not entry["embedding"]:
            continue
        similarity = _cosine_similarity(current_embedding, entry["embedding"])
        sim_results.append((similarity, entry))

    sim_results.sort(key=lambda x: x[0], reverse=True)
    retrieved_history = [entry for sim, entry in sim_results[:top_k]]
    retrieved_history.sort(key=lambda x: x.get("version", 0), reverse=True)
    return retrieved_history

# =========================
# 포트폴리오 요약 & PDF
# =========================
async def summarize_portfolio_and_generate_pdf(
    user_id: str,
    file=None,
    url: Optional[str] = None,
    job_title: Optional[str] = None,
    version: Optional[int] = None,
    feedback_reflection: Optional[str] = None,
    company_name: Optional[str] = None,
):
    # 입력 정리
    doc_type_for_prompt = ""
    prompt_content_for_ai: Dict[str, Any] = {}

    if file and getattr(file, "filename", None):
        doc_type_for_prompt = "portfolio_summary_text"
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다. 10MB 이하의 파일을 업로드해주세요.")
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(contents))
            extracted_text = "".join([(page.extract_text() or "") for page in reader.pages])
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"PDF 처리 중 오류: {e}")
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출하지 못했습니다. 스캔 PDF일 수 있습니다.")
        prompt_content_for_ai = {"extracted_text": extracted_text}
    elif url and str(url).strip():
        link = str(url).strip()
        if not (link.startswith("http://") or link.startswith("https://")):
            link = "http://" + link
        doc_type_for_prompt = "portfolio_summary_url"
        prompt_content_for_ai = {"portfolio_url": link}
    else:
        raise HTTPException(status_code=400, detail="분석을 위해 PDF 파일 또는 유효한 링크를 입력해주세요.")

    # AI 요약 & 피드백
    try:
        job_slug = (job_title or "").replace(" ", "-").replace("/", "-").lower()
        relevant_history_entries = await retrieve_relevant_feedback_history(
            user_id=user_id,
            job_slug=job_slug,
            doc_type=doc_type_for_prompt,
            current_content=prompt_content_for_ai,
            current_version=version or 1,
            top_k=2,
        )
        prev = relevant_history_entries[0] if relevant_history_entries else None
        older = relevant_history_entries[1] if len(relevant_history_entries) > 1 else None

        company_analysis = await load_company_analysis(user_id)

        ai_response_json = await get_ai_feedback(
            job_title or "",
            doc_type_for_prompt,
            prompt_content_for_ai,
            previous_document_data=prev,
            older_document_data=older,
            additional_user_context=feedback_reflection,
            company_name=company_name,
            company_analysis=company_analysis,
        )
        if ai_response_json.status_code != 200:
            data = json.loads(ai_response_json.body.decode("utf-8"))
            raise HTTPException(status_code=ai_response_json.status_code, detail=data.get("error", "AI 호출 오류"))

        parsed = json.loads(ai_response_json.body.decode("utf-8"))
        overall_summary_text = parsed.get("summary", "요약 내용을 생성할 수 없습니다.")

        if not overall_summary_text or overall_summary_text == "요약 내용을 생성할 수 없습니다.":
            raise HTTPException(status_code=500, detail="AI 요약 내용이 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI 요약 오류: {e}")

    # PDF 생성 & 저장
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        font_path = BASE_DIR / "static" / "fonts" / "NotoSansKR-Regular.ttf"
        if not font_path.exists():
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")
        pdf.add_font("NotoSansKR", "", str(font_path), uni=True)
        pdf.set_font("NotoSansKR", "", 12)

        title_text = f"{job_title or '포트폴리오'} 요약본\n"
        pdf.multi_cell(0, 10, txt=title_text, align="C")
        pdf.ln(10)
        pdf.set_font("NotoSansKR", "", 14)
        pdf.cell(0, 10, "▶ 포트폴리오 요약", ln=1, align="L")
        pdf.set_font("NotoSansKR", "", 12)
        pdf.multi_cell(0, 10, txt=overall_summary_text)
        pdf.ln(10)

        job_slug = (job_title or "portfolio").replace(" ", "-").replace("/", "-").lower()
        out_dir = _user_doc_dir(user_id, job_slug, "portfolio")
        os.makedirs(out_dir, exist_ok=True)

        pdf_filename = f"v{(version or 1)}_summary.pdf"
        pdf_file_path = out_dir / pdf_filename
        pdf.output(str(pdf_file_path))

        return str(pdf_file_path), f"/api/download_pdf/{job_slug}/portfolio/{pdf_filename}", overall_summary_text

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF 생성 및 저장 오류: {e}")
