from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
from pathlib import Path
import os, json, traceback, re
from urllib.parse import unquote, quote
from pydantic import BaseModel

load_dotenv()

# --- utils ---
from utils import (
    get_job_title_from_slug,
    get_ai_feedback,
    load_company_analysis,
    get_embedding,
    calculate_content_hash,
    summarize_portfolio_and_generate_pdf,
)

# --- JWT(dep) ---
from auth_local import get_current_user  # Authorization: Bearer ... → user_id(str)
from job_data import JOB_CATEGORIES, JOB_DETAILS, get_job_document_schema

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---- CORS (dev) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- helpers --------
def _list_version_files(doc_dir: Path) -> List[str]:
    if not doc_dir.is_dir():
        return []
    files = [f.name for f in doc_dir.iterdir() if f.is_file() and re.fullmatch(r"v\d+\.json", f.name)]
    files.sort(key=lambda name: int(re.findall(r"\d+", name)[0]))
    return files

def _load_json(path: Path) -> Any:
    with open(str(path), "r", encoding="utf-8") as f:
        return json.load(f)

def _dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _slugify_job_title(job_title: str) -> str:
    return job_title.replace(" ", "-").replace("/", "-").lower()

# ---- user paths ----
def _user_base_dir(user_id: str) -> Path:
    return DATA_DIR / "users" / user_id

def _user_job_dir(user_id: str, job_slug: str) -> Path:
    return _user_base_dir(user_id) / unquote(job_slug)

def _user_doc_dir(user_id: str, job_slug: str, doc_type: str) -> Path:
    return _user_job_dir(user_id, job_slug) / doc_type

def _user_company_file(user_id: str) -> Path:
    return _user_base_dir(user_id) / "companies" / "current_company_analysis.json"

def _user_profile_file(user_id: str) -> Path:
    return _user_base_dir(user_id) / "profile.json"

# -------- models --------
class AnalyzeDocumentRequest(BaseModel):
    job_title: str
    document_content: Dict[str, Any]
    version: int
    feedback_reflection: Optional[str] = None
    company_name: Optional[str] = None

class AnalyzeCompanyRequest(BaseModel):
    company_name: str

class UserProfile(BaseModel):
    education: list[dict] = []
    activities: list[dict] = []
    awards: list[dict] = []
    certificates: list[str] = []

# -------- pages/schema --------
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "job_categories": JOB_CATEGORIES})

@app.get("/editor/{job_slug}", response_class=HTMLResponse)
async def get_document_editor_page(request: Request, job_slug: str):
    job_title = get_job_title_from_slug(job_slug)
    if not job_title:
        raise HTTPException(status_code=404, detail=f"Job not found: {unquote(job_slug)}")
    job_details = JOB_DETAILS.get(job_title, {})
    return templates.TemplateResponse(
        "document_editor.html",
        {"request": request, "job_title": job_title, "job_slug": job_slug, "job_details": job_details}
    )

@app.get("/apiText/document_schema/{doc_type}", response_class=JSONResponse)
async def get_document_schema_endpoint(doc_type: str, job_slug: str):
    job_title = get_job_title_from_slug(job_slug)
    if not job_title:
        raise HTTPException(status_code=404, detail="Job not found")
    schema = get_job_document_schema(job_title, doc_type)
    if not schema:
        raise HTTPException(status_code=404, detail="Document schema not found for this type or job.")
    return JSONResponse(content=schema)

# -------- profile (mypage) --------
@app.get("/apiText/user_profile", response_class=JSONResponse)
async def get_user_profile(user_id: str = Depends(get_current_user)):
    p = _user_profile_file(user_id)
    if not p.exists():
        return JSONResponse(content={
            "education": [{"level": "", "status": "", "school": "", "major": ""}],
            "activities": [{"title": "", "content": ""}],
            "awards": [{"title": "", "content": ""}],
            "certificates": [""],
        })
    try:
        return JSONResponse(content=_load_json(p))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read profile: {e}")

@app.post("/apiText/user_profile", response_class=JSONResponse)
async def save_user_profile(profile: UserProfile, user_id: str = Depends(get_current_user)):
    try:
        path = _user_profile_file(user_id)
        _dump_json(path, profile.dict())
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")

# -------- load documents --------
@app.get("/apiText/load_documents/{job_slug}", response_class=JSONResponse)
async def api_load_documents(job_slug: str, user_id: str = Depends(get_current_user)):
    job_title = get_job_title_from_slug(job_slug)
    if not job_title:
        raise HTTPException(status_code=404, detail=f"Job not found for slug: {unquote(job_slug)}")
    try:
        result: Dict[str, List[Dict[str, Any]]] = {"resume": [], "cover_letter": [], "portfolio": []}
        for doc_type in result.keys():
            d = _user_doc_dir(user_id, job_slug, doc_type)
            for name in _list_version_files(d):
                try:
                    result[doc_type].append(_load_json(d / name))
                except Exception:
                    traceback.print_exc()
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load documents: {e}")

# -------- company analysis --------
@app.post("/apiText/analyze_company", response_class=JSONResponse)
async def analyze_company_endpoint(request_data: AnalyzeCompanyRequest, user_id: str = Depends(get_current_user)):
    company_name = request_data.company_name
    if not company_name:
        raise HTTPException(status_code=400, detail="기업명을 입력해주세요.")
    from utils import perform_company_analysis
    user_company_file = _user_company_file(user_id)
    user_company_file.parent.mkdir(parents=True, exist_ok=True)
    return await perform_company_analysis(company_name, str(user_company_file))

@app.get("/apiText/load_last_company_analysis", response_class=JSONResponse)
async def load_last_company_analysis(user_id: str = Depends(get_current_user)):
    company_file = _user_company_file(user_id)
    if not company_file.exists():
        return JSONResponse(content={
            "company_name": "",
            "summary": "",
            "core_values": [],
            "key_strengths": [],
            "interview_tips": [],
            "raw": {}
        })
    try:
        data = _load_json(company_file)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read analysis: {e}")

# -------- analyze & save (update current, clone next) --------
@app.post("/apiText/analyze_document/{doc_type}")
async def analyze_document_endpoint(
    doc_type: str,
    request_data: AnalyzeDocumentRequest,
    user_id: str = Depends(get_current_user),
):
    try:
        job_title = request_data.job_title
        doc_content_dict = request_data.document_content
        current_version = int(request_data.version or 0)  # 편집 중인 버전
        next_version = current_version + 1

        feedback_reflection = request_data.feedback_reflection
        company_name = request_data.company_name

        company_analysis = await load_company_analysis(user_id)
        job_slug = _slugify_job_title(job_title)

        # 비교용 이전/그전 버전은 "현재 버전 기준"으로 로드
        doc_dir = _user_doc_dir(user_id, job_slug, doc_type)
        prev_path = doc_dir / f"v{current_version}.json"
        older_path = doc_dir / f"v{current_version-1}.json"
        previous_document_data = _load_json(prev_path) if prev_path.exists() else None
        older_document_data = _load_json(older_path) if older_path.exists() else None

        # AI 피드백 생성 (현재 vs 이전 비교)
        feedback_response_json = await get_ai_feedback(
            job_title, doc_type, doc_content_dict,
            previous_document_data=previous_document_data,
            older_document_data=older_document_data,
            additional_user_context=feedback_reflection,
            company_name=company_name,
            company_analysis=company_analysis,
        )
        if getattr(feedback_response_json, "status_code", 200) != 200:
            return feedback_response_json

        feedback_content = json.loads(feedback_response_json.body.decode("utf-8"))
        overall_ai_feedback = feedback_content.get("overall_feedback", "")
        individual_ai_feedbacks = feedback_content.get("individual_feedbacks", {})
        ai_summary = feedback_content.get("summary", "")

        # 임베딩 텍스트
        if doc_type == "portfolio":
            text_for_current_embedding = ai_summary
        elif doc_type == "resume":
            text_for_current_embedding = " ".join([
                json.dumps(doc_content_dict.get("education", []), ensure_ascii=False),
                json.dumps(doc_content_dict.get("activities", []), ensure_ascii=False),
                json.dumps(doc_content_dict.get("awards", []), ensure_ascii=False),
                json.dumps(doc_content_dict.get("certificates", []), ensure_ascii=False),
            ])
        else:  # cover_letter
            text_for_current_embedding = (
                f"지원 이유: {doc_content_dict.get('reason_for_application', '')} "
                f"전문성 경험: {doc_content_dict.get('expertise_experience', '')} "
                f"협업 경험: {doc_content_dict.get('collaboration_experience', '')} "
                f"도전적 목표 경험: {doc_content_dict.get('challenging_goal_experience', '')} "
                f"성장 과정: {doc_content_dict.get('growth_process', '')}"
            )

        current_doc_embedding = await get_embedding(text_for_current_embedding)
        current_content_hash = calculate_content_hash(doc_content_dict)

        # 1) 현재 버전 저장/갱신 (vN)
        current_doc = {
            "job_title": job_title,
            "doc_type": doc_type,
            "version": current_version,
            "content": doc_content_dict,
            "feedback": overall_ai_feedback,
            "individual_feedbacks": individual_ai_feedbacks,
            "embedding": current_doc_embedding,
            "content_hash": current_content_hash,
            "company_name": company_name,
        }
        _dump_json(doc_dir / f"v{current_version}.json", current_doc)

        # 2) 다음 버전 복제 생성 (vN+1)
        next_doc = json.loads(json.dumps(current_doc, ensure_ascii=False))
        next_doc["version"] = next_version
        _dump_json(doc_dir / f"v{next_version}.json", next_doc)

        return JSONResponse(content={
            "message": "Document analyzed and saved successfully!",
            "summary": ai_summary,
            # 편의 필드(기존 프론트 호환)
            "ai_feedback": overall_ai_feedback,
            "individual_feedbacks": individual_ai_feedbacks,
            # 명시적으로 두 버전 반환
            "current_version_data": current_doc,
            "next_version_data": next_doc,
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error during analysis and saving: {e}")

# -------- portfolio summary: update current, clone next --------
@app.post("/apiText/portfolio_summary", response_class=JSONResponse)
async def portfolio_summary(
    job_title: str = Form(...),
    company_name: Optional[str] = Form(None),
    portfolio_link: Optional[str] = Form(None),
    version: Optional[str] = Form(None),  # 현재 버전(vN)
    portfolio_pdf: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user),
):
    try:
        job_slug = _slugify_job_title(job_title)
        doc_dir = _user_doc_dir(user_id, job_slug, "portfolio")

        current_version = int(version or 0)
        next_version = current_version + 1

        # 현재 버전(vN)으로 요약/PDF 생성 및 JSON 저장
        pdf_path, download_url, ai_summary = await summarize_portfolio_and_generate_pdf(
            user_id=user_id,
            file=portfolio_pdf,
            url=portfolio_link,
            job_title=job_title,
            version=current_version,      # vN 저장
            feedback_reflection=None,
            company_name=company_name,
        )

        # 방금 저장한 vN.json 읽기
        vN_path = doc_dir / f"v{current_version}.json"
        current_doc = _load_json(vN_path) if vN_path.exists() else {
            "job_title": job_title,
            "doc_type": "portfolio",
            "version": current_version,
            "content": {"summary": ai_summary or "", "portfolio_link": portfolio_link or ""},
            "feedback": ai_summary or "",
            "individual_feedbacks": {},
            "embedding": [],
            "content_hash": calculate_content_hash({"summary": ai_summary or "", "portfolio_link": portfolio_link or ""}),
            "company_name": company_name,
        }

        # 다음 버전(vN+1) 복제 생성
        next_doc = json.loads(json.dumps(current_doc, ensure_ascii=False))
        next_doc["version"] = next_version
        _dump_json(doc_dir / f"v{next_version}.json", next_doc)

        return JSONResponse(content={
            "download_url": download_url,
            "ai_summary": current_doc.get("content", {}).get("summary", ai_summary),
            "individual_feedbacks": current_doc.get("individual_feedbacks", {}),
            "current_version_data": current_doc,
            "next_version_data": next_doc,
        })
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Portfolio summary failed: {e}")

# -------- rollback --------
@app.delete("/apiText/rollback_document/{doc_type}/{job_slug}/{version}")
async def rollback_document(doc_type: str, job_slug: str, version: int, user_id: str = Depends(get_current_user)):
    try:
        doc_dir = _user_doc_dir(user_id, job_slug, doc_type)
        if not doc_dir.is_dir():
            raise HTTPException(status_code=404, detail="Document path not found")

        files = _list_version_files(doc_dir)
        if not files:
            raise HTTPException(status_code=404, detail="No versions to rollback")

        max_ver = int(re.findall(r"\d+", files[-1])[0])
        if version < 0 or version > max_ver:
            raise HTTPException(status_code=400, detail="Invalid target version")
        
        deleted: List[str] = []
        for name in files:
            v = int(re.findall(r"\d+", name)[0])
            if v > version:
                try:
                    (doc_dir / name).unlink(missing_ok=False)
                    deleted.append(name)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to delete {name}: {e}")

        remaining = _list_version_files(doc_dir)
        latest_version = int(re.findall(r"\d+", remaining[-1])[0]) if remaining else 0
        latest_data: Dict[str, Any] = {}
        if remaining:
            latest_path = doc_dir / remaining[-1]
            latest_data = _load_json(latest_path)

        return JSONResponse(content={
            "status": "ok",
            "deleted": deleted,
            "latest_version": latest_version,
            "latest_data": latest_data,
        })
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Rollback failed: {e}")

# -------- pdf download --------
@app.get("/apiText/download_pdf/{job_slug}/{doc_type}/{filename}")
async def download_pdf_file(job_slug: str, doc_type: str, filename: str, user_id: str = Depends(get_current_user)):
    file_path = _user_doc_dir(user_id, job_slug, doc_type) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    encoded_filename = quote(filename)
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )

# -------- 5173 ↔ 8000 token bridge --------
@app.get("/auth/bridge", response_class=HTMLResponse)
def auth_bridge():
    allowed = ["http://localhost:5173", "http://127.0.0.1:5173"]
    allowed_json = json.dumps(allowed)

    # f-string 금지. 플레이스홀더 치환.
    html = r"""<!doctype html><meta charset="utf-8">
<script>
(function(){
  var ALLOWED = __ALLOWED__;
  function isJWT(x){return typeof x==="string"&&/^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$/.test(x);}
  window.addEventListener("message", function(ev){
    if (ALLOWED.indexOf(ev.origin) === -1) return;
    var d = ev.data || {};
    try {
      if (d.type === "SET_TOKEN") {
        if (!isJWT(d.token)) throw new Error("invalid token");
        sessionStorage.setItem("token", d.token);
        localStorage.setItem("token", d.token);
        ev.source && ev.source.postMessage({type:"ACK"}, ev.origin);
      } else if (d.type === "CLEAR_TOKEN") {
        sessionStorage.removeItem("token");
        localStorage.removeItem("token");
        ev.source && ev.source.postMessage({type:"ACK"}, ev.origin);
      } else {
        ev.source && ev.source.postMessage({type:"ERR", message:"unknown type"}, ev.origin);
      }
    } catch(e) {
      ev.source && ev.source.postMessage({type:"ERR", message:String(e && e.message || e)}, ev.origin);
    }
  });
})();
</script>
"""
    html = html.replace("__ALLOWED__", allowed_json)
    return HTMLResponse(html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
