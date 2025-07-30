# job_data.py
from typing import Optional, Dict, Any

JOB_CATEGORIES = {
    "제조/생산": [
        "생산직",
        "품질보증",
        "생산관리자",
        "설비 유지보수 엔지니어"
    ],
    "마케팅/광고": [
        "디지털 마케터",
        "콘텐츠 마케터",
        "퍼포먼스 마케터",
        "마케팅 기획자"
    ],
    "경영/비즈니스": [
        "재무/회계",
        "프로덕트 매니저",
        "사업기획자",
        "HR 담당자"
    ],
    "개발": [
        "백엔드 개발자",
        "프론트엔드 개발자",
        "AI/데이터 개발자",
        "DevOps/인프라 개발자"
    ]
}

# 각 직무별 필수 역량 및 자격증 데이터
JOB_DETAILS = {
    # 개발
    "프론트엔드 개발자": {
        "competencies": ["HTML/CSS", "JavaScript", "React", "Vue.js", "TypeScript", "Redux", "Webpack/Vite", "반응형 웹", "UI/UX 이해", "API 연동", "Git/GitHub"],
        "certifications": ["정보처리기사", "웹디자인기능사", "정보보안기사"], # 정보보안기사 추가 (웹 보안 중요성 증가)
        "description": "웹사이트의 사용자 인터페이스(UI)를 구축하고 사용자 경험(UX)을 개선하는 역할입니다."
    },
    "백엔드 개발자": {
        "competencies": [
            "Python",
            "JavaScript(TypeScript)",
            "Node.js",
            "FastAPI",
            "NestJS",
            "RDBMS (SQL)",
            "NoSQL (MongoDB, Redis 등)",
            "AWS",
            "RESTful API",
            "GraphQL",
            "Git",
            "CI/CD",
            "Docker",
            "Kubernetes",
            "Istio",
            "Helm",
            "대용량 시스템 설계 및 운영",
            "MSA",
            "시스템 설계",
            "데이터베이스 설계"
        ],
        "certifications": [
            "정보처리기사",
            "OCJP (Oracle Certified Java Programmer)",
            "SQLD/SQLP (국가공인 데이터베이스 자격증)",
            "정보보안기사"
        ],
        "description": "서버, 데이터베이스 및 애플리케이션의 핵심 로직을 담당하며, 안정적이고 확장 가능한 백엔드 시스템을 설계, 개발, 운영하고 서비스 확장에 기여합니다."
    },
    "AI/데이터 개발자": {
        "competencies": ["Python", "R", "머신러닝 알고리즘", "딥러닝 프레임워크 (TensorFlow/PyTorch)", "데이터 전처리/분석", "SQL", "빅데이터 기술 (Spark/Hadoop)"],
        "certifications": ["정보처리기사", "빅데이터분석기사", "ADsP/ADP (데이터 분석 전문가/준전문가)", "SQLD/SQLP (국가공인 데이터베이스 자격증)"], # 데이터 분석/SQL 자격증 추가
        "description": "인공지능 모델을 개발하고 데이터를 분석하여 비즈니스 통찰력을 제공합니다."
    },
    "DevOps/인프라 개발자": {
        "competencies": ["Linux/Unix", "클라우드 (AWS/Azure/GCP)", "Docker", "Kubernetes", "CI/CD (Jenkins/GitLab CI)", "스크립팅 (Bash/Python)", "네트워킹", "보안"],
        "certifications": ["리눅스마스터", "클라우드 자격증 (AWS SAA)", "정보보안기사", "네트워크관리사"], # 정보보안기사, 네트워크관리사 추가
        "description": "소프트웨어 개발 및 배포 파이프라인을 구축하고 인프라를 관리합니다."
    },

    # 마케팅/광고
    "디지털 마케터": {
        "competencies": ["SEO/SEM", "SNS 마케팅", "콘텐츠 기획", "데이터 분석 (Google Analytics)", "광고 집행 (GDN/GA)", "이메일 마케팅", "CRM"],
        "certifications": ["구글 애널리틱스 자격증", "검색광고마케터", "사회조사분석사"], # 사회조사분석사 추가 (시장 및 소비자 분석 역량)
        "description": "온라인 채널을 활용하여 제품/서비스를 홍보하고 고객을 유치합니다."
    },
    "콘텐츠 마케터": {
        "competencies": ["콘텐츠 기획/제작", "카피라이팅", "SEO", "SNS 채널 운영"],
        "certifications": ["GTQ 포토샵/일러스트", "컴퓨터그래픽스운용기능사"], # 시각 콘텐츠 제작 능력 증명 자격증 추가
        "description": "고객에게 가치있는 콘텐츠를 제작하고 배포하여 브랜드 인지도를 높입니다."
    },
    "퍼포먼스 마케터": {
        "competencies": ["데이터 분석", "A/B 테스트", "광고 최적화", "ROAS 분석"],
        "certifications": ["구글 애널리틱스 자격증", "검색광고마케터", "사회조사분석사", "SQLD/SQLP (데이터 분석 관련)"], # 데이터 관련 자격증 추가
        "description": "데이터 기반으로 광고 성과를 측정하고 최적화하여 마케팅 효율을 극대화합니다."
    },
    "마케팅 기획자": {
        "competencies": ["시장 조사", "경쟁사 분석", "마케팅 전략 수립", "예산 관리"],
        "certifications": ["사회조사분석사", "마케팅관리사"], # 사회조사분석사, 마케팅관리사 추가
        "description": "전반적인 마케팅 전략을 수립하고 실행 계획을 관리합니다."
    },
    
    # 경영/비즈니스
    "사업기획자": {
        "competencies": ["시장 분석", "사업 모델 수립", "재무 분석", "전략 기획", "PPT/보고서 작성", "커뮤니케이션", "협상력"],
        "certifications": ["경영지도사", "재경관리사", "투자자산운용사"], # 재무/투자 관련 자격증 추가
        "description": "새로운 사업 기회를 발굴하고 실행 전략을 수립합니다."
    },
    "재무/회계": {
        "competencies": ["재무제표 분석", "세무", "예산 관리", "자금 운용"],
        "certifications": ["재경관리사", "전산회계", "세무회계", "공인회계사(CPA) (최상위)", "세무사 (최상위)"], # 세무회계, CPA, 세무사 추가
        "description": "회사의 재무 상태를 관리하고 회계 기준에 따라 업무를 처리합니다."
    },
    "프로덕트 매니저": {
        "competencies": ["제품 로드맵", "사용자 스토리 작성", "데이터 분석", "UX 리서치"],
        "certifications": ["PMP (Project Management Professional)", "SQLD/SQLP (데이터 분석 관련)"], # 프로젝트 관리, 데이터 분석 자격증 추가
        "description": "제품의 전체 생명주기를 관리하며 성공적인 제품 출시를 책임집니다."
    },
    "HR 담당자": {
        "competencies": ["채용", "인사평가", "보상", "노무"],
        "certifications": ["공인노무사", "HRD 전문가", "사회조사분석사"], # HRD, 사회조사분석사 추가 (직무 분석 및 통계 능력)
        "description": "회사의 인적 자원을 관리하고 개발하는 업무를 담당합니다."
    },
    
    # 제조/생산
    "생산직": {
        "competencies": ["장비 조작", "품질 검사", "안전 수칙 준수"],
        "certifications": ["생산자동화산업기사", "위험물산업기사", "지게차운전기능사"], # 생산 자동화, 위험물, 지게차 자격증 추가 (실질적 현장 능력)
        "description": "생산 라인에서 제품을 직접 제조하고 조립하는 역할을 담당합니다."
    },
    "품질보증": {
        "competencies": ["품질 시스템(ISO)", "통계적 품질 관리(SQC)", "고객 클레임 대응"],
        "certifications": ["품질경영기사", "6시그마 자격증 (GB/BB)"], # 6시그마 자격증 추가 (공정 개선 능력)
        "description": "제품이 일정한 품질 표준을 충족하도록 보증하고 관리합니다."
    },
    "생산관리자": {
        "competencies": ["생산 계획 수립", "공정 관리", "원가 관리", "재고 관리"],
        "certifications": ["생산성경영체계(PMS) 컨설턴트", "물류관리사"], # 생산성 경영, 물류 관리 자격증 추가
        "description": "생산 활동이 효율적으로 이루어지도록 계획하고 관리합니다."
    },
    "설비 유지보수 엔지니어": {
        "competencies": ["기계/전기 설비 이해", "예방 보전", "고장 수리"],
        "certifications": ["기계정비산업기사", "전기기사/산업기사", "공조냉동기계기사/산업기사"], # 전기, 공조냉동 자격증 추가 (종합적인 설비 관리 능력)
        "description": "생산 설비가 안정적으로 가동되도록 점검, 수리, 보전 업무를 수행합니다."
    }
}

# 각 직무별 문서 양식 (입력 필드 정의)
# doc_type: resume, cover_letter, portfolio, career_statement
JOB_DOCUMENT_SCHEMAS = {
    "resume": {
        "korean_name": "이력서",
        "sections": [
            {
                "title": "학력 사항",
                "fields": [
                    {"name": "education_history", "label": "학력", "type": "textarea", "placeholder": "최종 학력부터 고등학교까지 상세히 기재 (학교명, 전공, 기간, 학점 등).", "required": True},
                ]
            },
            {
                "title": "경력 사항",
                "fields": [
                    {"name": "career_history", "label": "경력", "type": "textarea", "placeholder": "회사명, 직위, 재직 기간, 주요 업무 및 성과 (신입의 경우 프로젝트 경험 위주로 작성). 각 경력/프로젝트별로 역할, 사용 기술, 기여도, 결과(수치화)를 구체적으로 작성해주세요.", "required": True},
                ]
            },
            {
                "title": "자격증",
                "fields": [
                    {"name": "certificates_list", "label": "보유 자격증", "type": "textarea", "placeholder": "취득 자격증을 모두 기재 (자격증명, 발행기관, 취득일). 직무 관련 자격증 우선 기재.", "required": False},
                ]
            },
            {
                "title": "수상 및 기타 활동",
                "fields": [
                    {"name": "awards_activities", "label": "수상 내역 및 대외활동", "type": "textarea", "placeholder": "수상 내역, 대외활동, 동아리 활동 등을 작성하세요.", "required": False},
                ]
            },
            {
                "title": "기술 스택",
                "fields": [
                    {"name": "skills_tech", "label": "보유 기술 스택", "type": "textarea", "placeholder": "활용 가능한 프로그래밍 언어, 프레임워크, 툴 등을 상세히 작성하세요.", "required": True},
                ]
            }
        ]
    },
    "cover_letter": {
        "korean_name": "자기소개서",
        "fields": [
            {"name": "reason_for_application", "label": "해당 직무에 지원한 이유", "type": "textarea", "placeholder": "내용을 입력하세요.", "required": True},
            {"name": "expertise_experience", "label": "해당 분야에 대한 전문성을 기르기 위해 노력한 경험", "type": "textarea", "placeholder": "내용을 입력하세요.", "required": True},
            {"name": "collaboration_experience", "label": "공동의 목표를 위해 협업을 한 경험", "type": "textarea", "placeholder": "내용을 입력하세요.", "required": True},
            {"name": "challenging_goal_experience", "label": "도전적인 목표를 세우고 성취하기 위해 노력한 경험", "type": "textarea", "placeholder": "내용을 입력하세요.", "required": True},
            {"name": "growth_process", "label": "자신의 성장과정", "type": "textarea", "placeholder": "내용을 입력하세요.", "required": True},
        ]
    },
    "portfolio": { # 기존 포트폴리오 스키마 유지
        "korean_name": "포트폴리오",
        "fields": [
            {"name": "portfolio_pdf", "label": "포트폴리오 PDF 업로드", "type": "file", "accept": ".pdf", "placeholder": "포트폴리오 PDF 파일을 업로드하세요."},
            {"name": "portfolio_link", "label": "포트폴리오 링크 입력", "type": "text", "placeholder": "포트폴리오가 업로드된 웹사이트, 블로그, Github 등 링크를 입력하세요."}
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