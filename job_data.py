# job_data.py
from typing import Optional, Dict, Any

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

# 각 직무별 필수 역량 및 자격증 데이터 (이 부분을 추가해야 합니다)
# 실제 데이터는 더 상세하게 채워야 합니다.
JOB_DETAILS = {
    "프론트엔드 개발자": {
        "competencies": ["HTML/CSS", "JavaScript", "React", "Vue.js", "TypeScript", "Redux", "Webpack/Vite", "반응형 웹", "UI/UX 이해", "API 연동", "Git/GitHub"],
        "certifications": ["정보처리기사", "웹디자인기능사"], # 예시
        "description": "웹사이트의 사용자 인터페이스(UI)를 구축하고 사용자 경험(UX)을 개선하는 역할입니다."
    },
    "백엔드 개발자": {
        "competencies": ["Python", "Java", "Node.js", "Spring Framework", "Django/Flask", "RESTful API", "RDBMS (SQL)", "NoSQL", "Docker", "AWS/GCP/Azure"],
        "certifications": ["정보처리기사", "OCJP (Oracle Certified Java Programmer)"], # 예시
        "description": "서버, 데이터베이스 및 애플리케이션의 핵심 로직을 담당합니다."
    },
    "UX/UI 디자이너": {
        "competencies": ["Figma/Sketch/Adobe XD", "Photoshop/Illustrator", "사용자 리서치", "와이어프레임/프로토타이핑", "정보 설계", "디자인 시스템"],
        "certifications": ["컴퓨터그래픽스운용기능사", "웹디자인기능사"], # 예시
        "description": "사용자 경험(UX)을 설계하고 사용자 인터페이스(UI)를 디자인합니다."
    },
    # --- 중요: 여기에 다른 모든 직무에 대한 JOB_DETAILS를 추가해야 합니다. ---
    # 각 직무에 맞는 실제 역량과 자격증 데이터를 채워주세요.
    # 예시:
    "앱 개발자": {
        "competencies": ["Kotlin/Swift", "Android/iOS SDK", "UI/UX 원칙", "RESTful API 연동", "SQLite/Realm", "Firebase"],
        "certifications": ["정보처리기사"],
        "description": "모바일 애플리케이션을 개발하고 유지보수합니다."
    },
    "AI/데이터 개발자": {
        "competencies": ["Python", "R", "머신러닝 알고리즘", "딥러닝 프레임워크 (TensorFlow/PyTorch)", "데이터 전처리/분석", "SQL", "빅데이터 기술 (Spark/Hadoop)"],
        "certifications": ["정보처리기사", "빅데이터분석기사"],
        "description": "인공지능 모델을 개발하고 데이터를 분석하여 비즈니스 통찰력을 제공합니다."
    },
    "DevOps/인프라 엔지니어": {
        "competencies": ["Linux/Unix", "클라우드 (AWS/Azure/GCP)", "Docker", "Kubernetes", "CI/CD (Jenkins/GitLab CI)", "스크립팅 (Bash/Python)", "네트워킹", "보안"],
        "certifications": ["리눅스마스터", "클라우드 자격증 (AWS SAA)"],
        "description": "소프트웨어 개발 및 배포 파이프라인을 구축하고 인프라를 관리합니다."
    },
    # 마케팅/광고 직무 예시
    "디지털 마케터": {
        "competencies": ["SEO/SEM", "SNS 마케팅", "콘텐츠 기획", "데이터 분석 (Google Analytics)", "광고 집행 (GDN/GA)", "이메일 마케팅", "CRM"],
        "certifications": ["구글 애널리틱스 자격증", "검색광고마케터"],
        "description": "온라인 채널을 활용하여 제품/서비스를 홍보하고 고객을 유치합니다."
    },
    "사업기획자": {
        "competencies": ["시장 분석", "사업 모델 수립", "재무 분석", "전략 기획", "PPT/보고서 작성", "커뮤니케이션", "협상력"],
        "certifications": ["경영지도사"],
        "description": "새로운 사업 기회를 발굴하고 실행 전략을 수립합니다."
    },
    # ... 기타 직무들도 유사한 방식으로 추가해야 합니다.
}

# 각 직무별 문서 양식 (입력 필드 정의)
# doc_type: resume, cover_letter, portfolio, career_statement
JOB_DOCUMENT_SCHEMAS = {
    "resume": {
        "fields": [
            {"name": "education", "label": "학력", "type": "textarea", "placeholder": "최종 학력, 학교명, 전공, 학위, 졸업년월일 등을 상세히 입력하세요. (예: 20XX년 X월 OO대학교 OO학과 졸업, 학사)"},
            {"name": "gpa", "label": "학점", "type": "text", "placeholder": "총 평점 및 만점 기준을 입력하세요. (예: 4.0/4.5)"},
            {"name": "awards", "label": "수상 내역", "type": "textarea", "placeholder": "수상명, 수상일, 주최 기관, 간략한 설명 등을 입력하세요. (예: 20XX년 OO공모전 대상 - 프로젝트명)"},
            {"name": "activities", "label": "대외 활동", "type": "textarea", "placeholder": "활동명, 활동 기간, 역할, 주요 성과 또는 배운 점 등을 입력하세요. (예: 20XX년 OO봉사단 활동 - 팀장, OO 프로젝트 진행)"},
            {"name": "career_experience", "label": "경력 사항", "type": "textarea", "placeholder": "근무 회사명, 근무 기간, 직무명, 담당 업무 및 주요 성과를 구체적으로 작성하세요. 신입의 경우 인턴십, 프로젝트 경험 등을 작성합니다."}
        ]
    },
    "cover_letter": {
        "fields": [
            {"name": "qa", "label": "자기소개서 질문과 답변", "type": "custom_qa", "placeholder": "자유롭게 질문과 답변 항목을 추가하세요."}
            # Custom Q&A type will be handled specially by JS in document_editor.html
        ]
    },
    "portfolio": {
        "fields": [
            {"name": "project_name", "label": "대표 프로젝트명", "type": "text", "placeholder": "포트폴리오의 대표적인 프로젝트 이름을 입력하세요. (예: 스마트 도시 데이터 분석 시스템 개발)"},
            {"name": "project_details", "label": "프로젝트 상세", "type": "textarea", "placeholder": "각 프로젝트의 목표, 역할, 사용 기술 스택, 개발 과정, 기여도 및 핵심 성과를 상세히 설명하세요. 수치화된 성과가 있다면 좋습니다."},
            {"name": "project_links", "label": "관련 링크", "type": "text", "placeholder": "Github, 개인 블로그, 데모 영상 등 프로젝트 관련 링크를 쉼표(,)로 구분하여 입력하세요."}
        ]
    },
    "career_statement": {
        "fields": [
            {"name": "company_name", "label": "회사명", "type": "text", "placeholder": "근무했던 회사 이름을 입력하세요. (예: (주)ABC 테크놀로지)"},
            {"name": "employment_period", "label": "근무 기간", "type": "text", "placeholder": "근무 시작일과 종료일을 입력하세요. (예: 2020.03 ~ 2023.08)"},
            {"name": "role", "label": "담당 직무 및 역할", "type": "text", "placeholder": "회사 내에서 담당했던 직무명과 구체적인 역할을 입력하세요. (예: 백엔드 개발팀 / API 개발 및 유지보수)"},
            {"name": "achievements", "label": "주요 성과", "type": "textarea", "placeholder": "핵심 프로젝트, 달성한 목표, 개선 사항 등 구체적인 업무 성과를 작성하세요. 가급적 수치화하여 표현하세요."}
        ]
    }
}

# 모든 직무를 플랫 리스트로 만들기 (URL 슬러그로 사용하기 위함)
ALL_JOB_SLUGS = []
for category_jobs in JOB_CATEGORIES.values():
    for job_title in category_jobs:
        # URL 친화적인 슬러그 생성 (예: "프론트엔드 개발자" -> "프론트엔드-개발자")
        slug = job_title.replace(" ", "-").replace("/", "-").lower()
        ALL_JOB_SLUGS.append(slug)

def get_job_document_schema(job_slug: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """
    주어진 문서 타입에 맞는 양식 스키마를 반환합니다.
    현재는 직무에 상관없이 문서 타입별 공통 스키마를 사용합니다.
    """
    # job_slug를 실제 job_title로 변환 (필요시)
    job_title_map = {}
    for category_jobs in JOB_CATEGORIES.values():
        for jt in category_jobs:
            job_title_map[jt.replace(" ", "-").replace("/", "-").lower()] = jt

    actual_job_title = job_title_map.get(job_slug)
    
    # 향후 job_title에 따라 스키마를 다르게 줄 수도 있습니다.
    # 예: if actual_job_title == "프론트엔드 개발자": return specific_frontend_resume_schema
    
    return JOB_DOCUMENT_SCHEMAS.get(doc_type)