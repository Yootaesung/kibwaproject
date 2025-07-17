import os
import asyncio
import json
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
import json
from typing import Optional

# 환경 변수 로드
load_dotenv()

app = FastAPI()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("경고: OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 직무 카테고리 및 직무 목록
JOB_CATEGORIES = {
    "개발": [
        "프론트엔드 개발자", "백엔드 개발자", "앱 개발자", "AI/데이터 개발자", "DevOps/인프라 엔지니어"
    ],
    "마케팅/광고": [
        "디지털 마케터", "콘텐츠 마케터", "퍼포먼스 마케터", "마케팅 기획자"
    ],
    "경영/비즈니스": [
        "사업기획자", "프로덕트 매니저(PM)", "재무/회계 담당자", "HR 담당자", "영업기획/BD"
    ],
    "디자인": [
        "UX/UI 디자이너", "그래픽 디자이너", "브랜드 디자이너", "모션/영상 디자이너"
    ],
    "영업": [
        "B2B 영업", "B2C 영업", "기술영업", "영업기획/관리"
    ],
    "엔지니어링/설계": [
        "기계 설계 엔지니어", "전기/전자 설계 엔지니어", "제품 개발 엔지니어", "품질관리(QA/QC)"
    ],
    "제조/생산": [
        "생산직 오퍼레이터", "생산관리자", "품질관리자", "설비 유지보수 엔지니어"
    ],
    "의료/제약/바이오": [
        "의사", "간호사", "약사", "임상시험 코디네이터(CRA)", "바이오 연구원"
    ],
    "금융": [
        "은행원", "자산운용 매니저", "금융 컨설턴트(FP)", "투자 분석가"
    ],
    "미디어": [
        "방송 PD", "콘텐츠 작가", "영상 편집자", "유튜브 콘텐츠 기획자"
    ],
    "게임 제작": [
        "게임 기획자", "게임 프로그래머", "게임 아티스트", "게임 QA/테스터"
    ],
    "물류/무역": [
        "물류 관리자", "수출입 담당자", "구매 담당자", "통관사"
    ],
    "법률/법기관": [
        "변호사", "검사", "수사관", "기업 법무 담당자"
    ],
    "건설/시설": [
        "건축가", "시공 관리자(현장소장)", "전기/소방 기술자", "인테리어 디자이너"
    ],
    "식음료": [
        "조리사(셰프)", "바리스타", "제과제빵사", "식품 품질관리자"
    ],
    "공공/복지": [
        "사회복지사", "공무원", "요양보호사", "NGO 활동가"
    ],
    "정보보호": [
        "보안 엔지니어", "보안 관제 요원(SOC)", "개인정보보호 담당자(DPO)", "사이버 위협 분석가"
    ]
}

# PDF 스타일 설정
def get_styles():
    styles = getSampleStyleSheet()
    
    # 기본 스타일을 수정하여 사용
    styles['Title'].fontSize = 24
    styles['Title'].leading = 30
    styles['Title'].spaceAfter = 20
    styles['Title'].alignment = TA_CENTER
    
    styles['Heading1'].fontSize = 18
    styles['Heading1'].leading = 22
    styles['Heading1'].spaceAfter = 10
    styles['Heading1'].spaceBefore = 10
    styles['Heading1'].bold = True
    
    styles['Normal'].fontSize = 12
    styles['Normal'].leading = 16
    styles['Normal'].spaceAfter = 8
    
    return styles

# OpenAI를 사용하여 직무 정보 생성
async def generate_job_info(job_title: str) -> dict:
    try:
        # 환경 변수에서 API 키 확인
        if not OPENAI_API_KEY:
            return {"error": "OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."}
            
        # OpenAI API 호출
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 직업 상담 전문가입니다. 사용자가 요청한 직무에 대한 상세한 정보를 제공해주세요. 응답은 항상 유효한 JSON 형식이어야 합니다."},
                {"role": "user", "content": f"{job_title} 직무에 대한 상세한 정보를 다음 형식의 JSON으로 제공해주세요:\n"
                                          "1. 직무 개요 및 요구 사항 (직무 설명, 필요 역량, 학력 및 전공)\n"
                                          "2. 역량 강화 및 준비 과정 (자격증, 어학 능력, 교육 프로그램)\n"
                                          "3. 실무 경험 쌓기 (인턴십/대외활동)\n"
                                          "4. 채용 정보 (채용 트렌드, 채용 계획/일정, 채용 공고 링크)\n"
                                          "응답은 반드시 JSON 형식이어야 하며, 각 섹션은 키-값 쌍으로 구성해주세요."}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # 응답에서 내용 추출
        content = response.choices[0].message.content
        
        # 한글 인코딩 처리
        try:
            content = content.encode('utf-8').decode('utf-8')
        except UnicodeError:
            print("Warning: Encoding error occurred while processing response")
        
        # 응답이 JSON 형식이 아닌 경우를 대비해 파싱
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # JSON 파싱에 실패하면 텍스트를 그대로 반환
            return {"error": "응답을 처리하는 중 오류가 발생했습니다.", "raw_response": content}
    except Exception as e:
        print(f"Error generating job info: {str(e)}")
        return {"error": str(e)}

# PDF 생성
def create_pdf(data: dict, filename: str):
    # 한글 폰트 설정
    try:
        # 한글 폰트 등록
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 설치된 한글 폰트를 순서대로 시도
        try:
            # Nanum 폰트 시도
            pdfmetrics.registerFont(TTFont('NanumGothic', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'))
            font_name = 'NanumGothic'
            print("NanumGothic 폰트 사용")
        except Exception as e:
            print(f"NanumGothic 폰트 등록 실패: {str(e)}")
            try:
                # Noto Sans CJK 폰트 시도
                pdfmetrics.registerFont(TTFont('NotoSans', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'))
                font_name = 'NotoSans'
                print("NotoSans 폰트 사용")
            except Exception as e:
                print(f"Noto Sans 폰트 등록 실패: {str(e)}")
                # 마지막으로 기본 폰트 사용
                font_name = 'Helvetica'
                print("기본 폰트 사용")
    except Exception as e:
        print(f"폰트 설정 중 오류 발생: {str(e)}")
        font_name = 'Helvetica'
    
    # PDF 설정
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # 스타일 정의
    styles = get_styles()
    
    # 한글 폰트를 사용하도록 스타일 수정
    for name in ['Title', 'Heading1', 'Normal']:
        style = styles[name]
        style.fontName = font_name
        style.leading = style.fontSize * 1.5  # 줄 간격 조정
    
    elements = []
    
    # 제목 추가
    elements.append(Paragraph(data.get("title", "직무 정보 보고서"), styles["Title"]))
    elements.append(Spacer(1, 20))
    
    # 각 섹션 처리
    for key, content in data.items():
        if key == "title":
            continue
            
        if isinstance(content, dict):
            # 섹션 제목 추가
            elements.append(Paragraph(key, styles["Heading1"]))
            elements.append(Spacer(1, 12))
            
            # 각 하위 항목 처리
            for subkey, subcontent in content.items():
                if isinstance(subcontent, str):
                    # 하위 항목 제목
                    elements.append(Paragraph(f"• {subkey}", styles["Normal"]))
                    # 하위 항목 내용
                    elements.append(Paragraph(str(subcontent), styles["Normal"]))
                    elements.append(Spacer(1, 6))
        else:
            # 단일 섹션 처리
            elements.append(Paragraph(key, styles["Heading1"]))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(str(content), styles["Normal"]))
            elements.append(Spacer(1, 12))
    
    doc.build(elements)

# 라우트
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "job_categories": JOB_CATEGORIES})

@app.post("/generate")
async def generate_report(job_title: str = Form(...)):
    # 직무 정보 생성
    job_info = await generate_job_info(job_title)
    
    if "error" in job_info:
        raise HTTPException(status_code=500, detail=job_info["error"])
    
    # PDF 생성
    filename = f"{job_title}_report.pdf".replace(" ", "_")
    filepath = f"static/{filename}"
    
    # PDF에 제목 추가
    job_info["title"] = f"{job_title} 직무 분석 보고서"
    create_pdf(job_info, filepath)
    
    return {"filename": filename}

@app.get("/download/{filename}")
async def download_file(filename: str):
    filepath = f"static/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=filename, media_type='application/pdf')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
