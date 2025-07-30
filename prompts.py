# prompts.py
from typing import Dict, Any, Optional
# from job_data import JOB_DETAILS # JOB_DETAILS는 get_document_analysis_prompt 내부에서 직접 사용되지 않으므로 제거

def get_document_analysis_prompt(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    job_competencies: Optional[list[str]] = None, # 이 인자는 main.py에서 JOB_DETAILS 기반으로 채워져서 넘어옴
    previous_document_content: Optional[Dict[str, Any]] = None, # 이전 버전 문서 내용
    previous_feedback: Optional[str] = None, # 이전 버전 피드백
    older_document_content: Optional[Dict[str, Any]] = None, # 그 이전 버전 문서 내용 (vN-2)
    older_feedback: Optional[str] = None # 그 이전 버전 피드백 (vN-2)
) -> str:
    """
    OpenAI AI 모델에 전달할 문서 분석 프롬프트를 생성합니다.
    이전 버전의 문서 내용과 피드백을 포함하여 AI가 더 정밀한 피드백을 제공하도록 합니다.
    AI는 JSON 형식으로 전체 피드백과 개별 질문별 피드백을 반환해야 합니다.
    """
    
    # 시스템 지시사항 및 JSON 응답 형식 가이드라인
    system_instruction = f"""
당신은 {job_title} 직무 채용 전문가 AI입니다. 지원자의 서류 합격 가능성을 높일 수 있는 구체적이고 실행 가능한 피드백을 제공해야 합니다.
응답은 반드시 다음 JSON 형식으로 이루어져야 합니다.

{{
    "overall_feedback": "string", // 문서 전체에 대한 종합적인 피드백입니다.
    "individual_feedbacks": {{ // 각 개별 필드/질문에 대한 피드백을 포함하는 객체입니다.
        "field_name_1": "feedback_string_1",
        "field_name_2": "feedback_string_2"
        // ... 관련 필드들에 대해 계속 이어집니다.
    }}
}}
모든 문자열 값은 유효한 JSON 문자열이어야 합니다 (예: 개행 문자 및 따옴표 처리).
"""

    user_prompt_parts = []
    user_prompt_parts.append(f"Analyzing {doc_type} for the role of: {job_title}\n")

    if job_competencies:
        user_prompt_parts.append(f"Key competencies for this role: {', '.join(job_competencies)}\n")

    # 문서 내용 및 피드백 지시
    user_prompt_parts.append("\n--- 현재 문서 내용 (최신 버전) ---")
    
    # Modified history_context formatting for cover_letter
    def format_doc_content_for_history(content: Dict[str, Any], d_type: str) -> str:
        if d_type == "cover_letter":
            # 자기소개서 질문 필드 정의
            questions_map = {
                "reason_for_application": "지원 동기",
                "expertise_experience": "전문성 경험",
                "collaboration_experience": "협업 경험",
                "challenging_goal_experience": "도전적 목표 경험",
                "growth_process": "성장 과정",
            }
            formatted_parts = []
            for field_name, label in questions_map.items():
                content_text = content.get(field_name, "작성되지 않음").strip()
                formatted_parts.append(f"{label}: {content_text}")
            return "\n".join(formatted_parts)
        elif d_type == "resume":
            return "\n".join([f"{k}: {v}" for k, v in content.items()])
        else: # For portfolio etc.
            return str(content) # Fallback for other dict types

    # 현재 문서 내용 포맷팅
    current_content_formatted = format_doc_content_for_history(document_content, doc_type)
    user_prompt_parts.append(current_content_formatted)


    history_context = ""
    if older_document_content is not None and older_feedback is not None:
        older_content_formatted = format_doc_content_for_history(older_document_content, doc_type)
        history_context += f"""
--- 이전 버전 문서 (vN-2) ---
내용:
{older_content_formatted}
이 버전에 대한 피드백:
{older_feedback}
"""

    if previous_document_content is not None and previous_feedback is not None:
        previous_content_formatted = format_doc_content_for_history(previous_document_content, doc_type)
        history_context += f"""
--- 직전 버전 문서 (vN-1) ---
내용:
{previous_content_formatted}
이 버전에 대한 피드백:
{previous_feedback}
"""

    if history_context:
        user_prompt_parts.append(f"""
--- 피드백 지침 ---
- 현재 문서 내용을 직전 버전 (vN-1) 및 그 이전 버전 (vN-2)과 비교하여 피드백을 제공합니다.
- 직전 버전 (vN-1)의 내용과 피드백을 더 중요하게 고려합니다.
- 이전 버전에 비해 어떤 점이 개선되었는지, 혹은 어떤 점이 여전히 미흡한지 구체적으로 언급합니다.
- 만약 이전 버전과 현재 문서 내용 간에 실질적인 변화가 거의 없다면, 그 점을 명확히 지적하고 여전히 개선이 필요함을 강조합니다.
{history_context}
""")

    user_prompt_parts.append("\n--- 피드백 요청 ---")

    if doc_type == "resume":
        user_prompt_parts.append(f"""
- **지원자가 제공한 내용만을 기반으로 구체적인 피드백을 제공해주세요.**
- 현재 이력서 내용과 {job_title} 직무의 필수 역량 및 자격증 정보(기술 스택 포함)를 바탕으로 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요.
- **만약 특정 항목의 내용이 '없음'으로 기재되어 있거나 비어있는 경우, 그 내용을 그대로 인지하고 '해당 정보가 누락되어 있다'고 명확히 언급한 후, 어떤 내용을 채워야 할지 구체적인 가이드라인을 제시해주세요. 존재하지 않는 내용을 상상하여 기재하지 마세요.**
- 이력서 내용이 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 각 섹션(학력, 경력, 자격증 등)의 내용이 얼마나 잘 구성되어 있는지 평가해주세요.
- 전체적인 피드백은 'overall_feedback'에 담고, 각 섹션(예: 'education_history', 'career_history', 'certificates_list', 'awards_activities', 'skills_tech')에 대한 피드백은 'individual_feedbacks' 객체 안에 해당 섹션 이름을 키로 사용하여 구체적으로 작성해주세요.
""")
        if job_competencies:
            user_prompt_parts.append(f"- 지원자가 제시한 기술 스택({', '.join(job_competencies)})과 이력서 내용이 얼마나 잘 부합하는지 평가하고, 부족한 부분이 있다면 보완 방안을 제시해주세요.")

    elif doc_type == "cover_letter":
        # 자기소개서 질문 필드와 레이블 정의 (prompts.py와 main.py에서 통일성을 위해)
        questions_info = [
            {"name": "reason_for_application", "label": "해당 직무에 지원한 이유"},
            {"name": "expertise_experience", "label": "해당 분야에 대한 전문성을 기르기 위해 노력한 경험"},
            {"name": "collaboration_experience", "label": "공동의 목표를 위해 협업을 한 경험"},
            {"name": "challenging_goal_experience", "label": "도전적인 목표를 세우고 성취하기 위해 노력한 경험"},
            {"name": "growth_process", "label": "자신의 성장과정"},
        ]
        
        user_prompt_parts.append(f"""
- 자기소개서 내용이 {job_title} 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 전체적인 피드백은 'overall_feedback'에 담아주세요.
- **각 질문별로 다음 항목들을 고려하여 구체적인 피드백과 개선 방안을 제시해주세요.** 이 피드백은 'individual_feedbacks' 객체 안에 해당 질문의 `name` (예: `reason_for_application`, `expertise_experience` 등)을 키로 사용하여 작성해주세요.
- **각 질문에 대한 내용이 비어있거나 '없음'으로 기재된 경우, 해당 질문에 대한 피드백에 '내용이 없습니다. 어떤 내용을 채워야 할지 구체적인 가이드라인을 제시해주세요.'와 같이 명확히 언급해주세요.**

""")
        for q_info in questions_info:
            user_prompt_parts.append(f"- **{q_info['label']} (`{q_info['name']}`):**")
            user_prompt_parts.append(f"  - 직무 이해도, 직무 적합성, 회사/산업군 관심, 기여 의지 및 성장 가능성 등을 고려하여 평가합니다.")
            user_prompt_parts.append(f"  - 자기 주도성, 학습 능력, 지속적인 성장 의지, 실제 적용 능력, 문제 해결 능력 및 성과 등을 고려하여 평가합니다.")
            user_prompt_parts.append(f"  - 팀워크, 협업 능력, 책임감, 갈등 관리 및 조율 능력, 타인에 대한 이해 및 존중 등을 고려하여 평가합니다.")
            user_prompt_parts.append(f"  - 목표 설정 능력, 실행력, 추진력, 문제 해결 능력, 회복 탄력성 및 학습 능력 등을 고려하여 평가합니다.")
            user_prompt_parts.append(f"  - 가치관, 인성, 핵심 역량 형성 과정, 자기 성찰 및 발전 의지, 인생의 전환점 및 중요한 경험 등을 고려하여 평가합니다.")
            user_prompt_parts.append(f"  - 구체적인 예시와 함께 개선 방안을 제안해주세요.")

        user_prompt_parts.append("""
- 문맥에 맞지 않거나 모호한 부분이 있다면 구체적으로 제시해주세요.
- 전체적인 일관성과 논리적 흐름에 대한 피드백을 추가해주세요.
- 답변의 내용이 질문의 의도와 얼마나 부합하는지 평가해주세요.
""")
    elif doc_type == "portfolio": # 기존 포트폴리오 피드백 로직 유지, JSON 요청 추가
        # For portfolio, individual_feedbacks can be an empty object {} or contain relevant specific points if applicable.
        content_str = "\n".join([f"{key}: {v}" for key, v in document_content.items()])
        user_prompt_parts.append(f"""
--- 포트폴리오 분석 ---
현재 포트폴리오 설명:
{content_str}

[피드백 요청]
- {job_title} 직무 관점에서 포트폴리오의 각 프로젝트 설명이 직무 역량과 연결되어 얼마나 잘 어필되는지 분석하고, 프로젝트의 기여도, 기술 스택, 결과물을 더 효과적으로 제시하기 위한 구체적인 개선 방안을 제시해주세요. 링크 첨부의 중요성도 언급해주세요.
- 전체적인 피드백은 'overall_feedback'에 담아주세요. 'individual_feedbacks'는 비어있는 객체 {{}}로 반환하거나, 프로젝트별/섹션별 핵심 피드백이 있다면 해당 키로 넣어주세요.
""")
    elif doc_type == "portfolio_summary_url": # 기존 포트폴리오 요약 로직 유지, JSON 요청 추가
        portfolio_url = document_content.get("portfolio_url", "")
        if not portfolio_url:
            return "오류: 포트폴리오 URL이 제공되지 않았습니다."
        user_prompt_parts.append(f"""
--- 포트폴리오 URL 요약 ---
다음 URL의 포트폴리오를 분석하고 요약해주세요.
URL: {portfolio_url}

[분석 요청]
- 핵심 경력, 프로젝트, 성과를 중심으로 요약해주세요.
- 기술 스택과 기여한 바를 명확히 해주세요.
- 해당 직무와의 연관성을 고려해주세요.
- 전체 요약 내용은 'overall_feedback'에 담아주세요. 'individual_feedbacks'는 비어있는 객체 {{}}로 반환해주세요. (AI는 실제 URL에 접근할 수 없으므로, 일반적인 포트폴리오 분석 기준에 따라 요약합니다.)
""")
    elif doc_type == "portfolio_summary_text": # 기존 포트폴리오 요약 로직 유지, JSON 요청 추가
        extracted_text = document_content.get("extracted_text", "")
        if not extracted_text:
            return "오류: 추출된 텍스트가 제공되지 않았습니다."
        user_prompt_parts.append(f"""
--- 포트폴리오 텍스트 요약 ---
다음 텍스트 내용을 바탕으로 포트폴리오를 분석하고 요약해주세요.
텍스트:
{extracted_text}

[분석 요청]
- 핵심 경력, 프로젝트, 성과를 중심으로 요약해주세요.
- 기술 스택과 기여한 바를 명확히 해주세요.
- 해당 직무와의 연관성을 고려해주세요.
- 전체 요약 내용은 'overall_feedback'에 담아주세요. 'individual_feedbacks'는 비어있는 객체 {{}}로 반환해주세요.
""")
    else:
        return f"오류: 알 수 없는 문서 타입 '{doc_type}'입니다."
    
    # 최종 프롬프트 구성: 시스템 지시사항 + 사용자 요청
    return system_instruction + "\n".join(user_prompt_parts)