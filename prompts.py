import json
from typing import Dict, Any, Optional, List, Tuple

def get_document_analysis_prompt(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    job_competencies: Optional[List[str]] = None,
    previous_document_data: Optional[Dict[str, Any]] = None,
    older_document_data: Optional[Dict[str, Any]] = None,
    additional_user_context: Optional[str] = None
) -> Tuple[str, str]:
    """
    OpenAI AI 모델에 전달할 문서 분석 프롬프트를 생성합니다.
    시스템 지시와 사용자 프롬프트를 분리하여 반환합니다.
    """
    
    # --- 시스템 지시 (role: system) ---
    system_instruction = f"""
당신은 {job_title} 직무 채용 전문가 AI입니다. 지원자의 서류 합격 가능성을 높일 수 있는 구체적이고 실행 가능한 피드백을 제공해야 합니다.
**모든 응답 내용은 반드시 한국어로만 작성해야 합니다.**
사용자의 피드백 요청에 따라, 현재 문서 내용을 이전 버전과 비교하고, 이전 피드백이 어떻게 반영되었는지 평가하여 맞춤형 피드백을 제공합니다.
**주의: 이전 버전에 비해 내용이 추가되었더라도, 그 내용이 직무 적합성, 구체성, 논리성, 완성도 측면에서 오히려 품질이 저하되거나 엉성해졌다면 이를 명확히 지적하고, 개선이 필요함을 강조해야 합니다. 단순히 '변화가 있다'는 이유만으로 긍정적인 피드백을 제공해서는 안 됩니다.**
응답은 반드시 다음 JSON 형식으로 이루어져야 합니다.

{{
    "summary": "string", // 문서 전체 내용을 객관적으로 요약합니다.
    "overall_feedback": "string", // 요약된 내용을 바탕으로 개선점을 제안하는 종합 피드백입니다.
    "individual_feedbacks": {{ // 각 개별 필드/질문에 대한 피드백을 포함하는 객체입니다.
        "field_name_1": "feedback_string_1",
        "field_name_2": "feedback_string_2"
        // ... 관련 필드들에 대해 계속 이어집니다.
    }}
}}
모든 문자열 값은 유효한 JSON 문자열이어야 합니다 (예: 개행 문자 및 따옴표 처리).
"""

    # --- 사용자 프롬프트 (role: user) ---
    user_prompt_parts = []
    user_prompt_parts.append(f"Analyzing {doc_type} for the role of: {job_title}\n")

    if job_competencies:
        user_prompt_parts.append(f"Key competencies for this role: {', '.join(job_competencies)}\n")

    # 문서 내용 및 피드백 지시
    user_prompt_parts.append("\n--- 현재 문서 내용 (최신 버전) ---")
    
    def format_doc_content(content: Dict[str, Any], d_type: str) -> str:
        if d_type == "cover_letter":
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
            resume_fields_map = {
                "education_history": "학력",
                "career_history": "경력",
                "certifications": "보유 자격증",
                "awards_activities": "수상 내역 및 대외활동",
                "skills_tech": "보유 기술 스택",
            }
            formatted_parts = []
            for field_name, label in resume_fields_map.items():
                content_data = content.get(field_name)
                display_content = ""
                if isinstance(content_data, list):
                    display_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in content_data])
                elif content_data is not None and str(content_data).strip():
                    display_content = str(content_data).strip()
                else:
                    display_content = "작성되지 않음 (누락)"
                formatted_parts.append(f"{label} ({field_name}):\n{display_content}")
            return "\n".join(formatted_parts)
        elif d_type in ["portfolio_summary_url", "portfolio_summary_text"]:
            if "portfolio_url" in content:
                return f"포트폴리오 URL: {content['portfolio_url']}"
            elif "extracted_text" in content:
                # 추출된 텍스트가 너무 길 경우 일부만 보여줌
                return f"추출된 텍스트:\n{content['extracted_text'][:2000]}..."
            return str(content)
        elif d_type == "portfolio":
            summary_content = content.get("summary", "요약 내용 없음")
            link_info = f"링크: {content.get('portfolio_link', '제공되지 않음')}"
            pdf_info = f"PDF 파일명: {content.get('portfolio_pdf_filename', '제공되지 않음')}"
            return f"요약 내용:\n{summary_content}\n{link_info}\n{pdf_info}"
        return json.dumps(content, ensure_ascii=False, indent=2)

    current_content_formatted = format_doc_content(document_content, doc_type)
    user_prompt_parts.append(current_content_formatted)

    history_context_parts = []

    if previous_document_data and previous_document_data.get("content"):
        history_context_parts.append(f"""
--- 가장 관련성 높은 이전 버전 (v{previous_document_data.get('version', 'unknown')}) 문서 ---
내용:
{format_doc_content(previous_document_data['content'], doc_type)}
이 버전에 대한 전체 피드백:
{previous_document_data.get('feedback', '제공된 피드백 없음')}
""")
    if older_document_data and older_document_data.get("content"):
        history_context_parts.append(f"""
--- 그 다음 관련성 높은 이전 버전 (v{older_document_data.get('version', 'unknown')}) 문서 ---
내용:
{format_doc_content(older_document_data['content'], doc_type)}
이 버전에 대한 전체 피드백:
{older_document_data.get('feedback', '제공된 피드백 없음')}
""")

    if history_context_parts:
        user_prompt_parts.append(f"""
--- 피드백 지침 ---
- 현재 문서 내용을 바탕으로, **아래에 제시된 가장 관련성 높은 이전 문서 내용과 피드백을 반드시 참고하여 피드백을 제공합니다.**
- 특히 이전 버전(v{previous_document_data.get('version', '이전') if previous_document_data else '이전'})과 현재 버전의 주요 변경점(추가, 수정, 삭제)을 명확히 파악하고, 이에 대해 구체적으로 언급하며 개선되었는지 또는 여전히 미흡한지 평가해주세요.
- 만약 참조된 이전 내용과 현재 문서 내용 간에 실질적인 변화가 거의 없다면, 그 점을 명확히 지적하고 여전히 개선이 필요함을 강조합니다.
- **가장 중요한 점은, 현재 문서 내용이 이전 버전보다 질적으로 떨어지거나, 직무 적합성, 구체성, 논리성, 완성도 측면에서 '엉성해졌다'고 판단될 경우, 이를 명확하고 비판적으로 지적해야 합니다.** 단순히 내용이 채워졌다고 해서 긍정적으로 평가하지 마세요.
- **피드백은 '이전 버전과 비교했을 때, ...' 또는 'v{previous_document_data.get('version', '이전')}(이전 버전) 대비 ...' 와 같이 이전 버전을 명시적으로 언급하며 시작해주세요.**
{"".join(history_context_parts)}
""")

    if additional_user_context:
        user_prompt_parts.append(f"""
--- 사용자 피드백 반영 내용 ---
지원자는 이전 피드백에 대해 다음과 같이 반영했다고 설명했습니다:
"{additional_user_context}"
AI는 이 사용자 설명을 고려하여, **실제로 반영되었는지 여부를 확인하고, 반영 노력을 칭찬하거나 추가 개선점을 제안하는 피드백을 제공해야 합니다.**
""")

    user_prompt_parts.append("\n--- 피드백 요청 ---")

    if doc_type == "resume":
        user_prompt_parts.append(f"""
- **지원자가 제공한 내용만을 기반으로 구체적인 피드백을 제공해주세요.**
- 현재 이력서 내용과 {job_title} 직무의 필수 역량 및 자격증 정보(기술 스택 포함)를 바탕으로 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요.
- **만약 특정 항목의 내용이 '작성되지 않음 (누락)'으로 기재되어 있거나 비어있는 경우, 그 내용을 그대로 인지하고 '해당 정보가 누락되어 있습니다.'라고 명확히 언급한 후, 어떤 내용을 채워야 할지 구체적인 가이드라인을 제시해주세요. 존재하지 않는 내용을 상상하여 기재하지 마세요.**
- 이력서 내용이 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 각 섹션의 내용이 얼마나 잘 구성되어 있는지 평가해주세요.
- 전체적인 피드백은 'overall_feedback'에 담고, 각 섹션(예: 'education_history', 'career_history', 'certifications', 'awards_activities', 'skills_tech')에 대한 피드백은 'individual_feedbacks' 객체 안에 해당 섹션 이름을 키로 사용하여 **간결하게 1~2문장으로** 작성해주세요.
- **개인 정보 (이름, 이메일, 연락처 등)는 피드백 대상에서 제외하고 언급하지 마세요.**

다음 항목들에 대해 집중적으로 피드백해주세요:
- **education_history (학력):** 학력 정보의 명확성, 직무 관련성, 중요 학업 경험 강조 여부.
- **career_history (경력):** 경력의 구체성, 성과 중심 서술 (수치 포함), 직무 연관성, 역할 및 책임 명확성.
- **certifications (보유 자격증):** 직무 관련 자격증 유무, 중요도, 취득일 명확성, 강점 부각 여부.
- **awards_activities (수상 내역 및 대외활동):** 수상 및 활동 내용의 중요성, 직무 관련성, 기여도 명확성, 배우고 느낀 점 어필 여부.
- **skills_tech (보유 기술 스택):** 기술 스택의 적절성, 구체성 (버전, 숙련도), 직무 요구사항 부합 여부, 프로젝트 활용 경험.

""")
        if job_competencies:
            user_prompt_parts.append(f"- 지원자가 제시한 기술 스택({', '.join(job_competencies)})과 이력서 내용이 얼마나 잘 부합하는지 평가하고, 부족한 부분이 있다면 보완 방안을 제시해주세요.")

    elif doc_type == "cover_letter":
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
- **만약 내용이 존재하더라도 피상적이거나, 직무와 관련성이 떨어지거나, 논리적 흐름이 엉성하거나, 구체적인 사례가 부족하여 이전 버전보다 품질이 낮아졌다고 판단되면, 그 점을 명확히 지적하고 구체적인 개선 방안을 제시해야 합니다.**
- **모든 피드백과 요약은 반드시 한국어로 작성해주세요.**

""")
        for q_info in questions_info:
            user_prompt_parts.append(f"- **{q_info['label']} (`{q_info['name']}`):**")
            user_prompt_parts.append(f"  - 직무 이해도, 직무 적합성, 회사/산업군 관심, 기여 의지 및 성장 가능성 등을 고려하여 평가합니다. **(내용이 피상적이거나, 단순히 열정만 나열하는 경우 부족하다고 평가)**")
            user_prompt_parts.append(f"  - 자기 주도성, 학습 능력, 지속적인 성장 의지, 실제 적용 능력, 문제 해결 능력 및 성과 등을 고려하여 평가합니다. **(구체적인 경험, 과정, 결과, 수치가 부족한 경우 부족하다고 평가)**")
            user_prompt_parts.append(f"  - 팀워크, 협업 능력, 책임감, 갈등 관리 및 조율 능력, 타인에 대한 이해 및 존중 등을 고려하여 평가합니다. **(본인의 역할과 기여가 모호하거나, 갈등 해결 과정이 불분명한 경우 부족하다고 평가)**")
            user_prompt_parts.append(f"  - 목표 설정 능력, 실행력, 추진력, 문제 해결 능력, 회복 탄력성 및 학습 능력 등을 고려하여 평가합니다. **(도전의 내용이 너무 일반적이거나, 성과가 미미하거나, 배운 점이 추상적인 경우 부족하다고 평가)**")
            user_prompt_parts.append(f"  - 가치관, 인성, 핵심 역량 형성 과정, 자기 성찰 및 발전 의지, 인생의 전환점 및 중요한 경험 등을 고려하여 평가합니다. **(내용이 교훈적이거나, 직무와 무관한 개인사만 나열되는 경우 부족하다고 평가)**")
            user_prompt_parts.append(f"  - 구체적인 예시와 함께 개선 방안을 제안해주세요.")

        user_prompt_parts.append("""
- 문맥에 맞지 않거나 모호한 부분이 있다면 구체적으로 제시해주세요.
- 전체적인 일관성과 논리적 흐름에 대한 피드백을 추가해주세요.
- 답변의 내용이 질문의 의도와 얼마나 부합하는지 평가해주세요.
""")
    elif doc_type == "portfolio_summary_text":
        extracted_text = document_content.get("extracted_text", "")
        if not extracted_text:
            return system_instruction, "오류: 추출된 텍스트가 제공되지 않았습니다."
        user_prompt_parts.append(f"""
--- 포트폴리오 텍스트 분석 ---
다음 텍스트 내용을 바탕으로 포트폴리오를 분석하고 **면접관이 한눈에 지원자의 핵심 역량을 파악할 수 있도록 구체적이고 효과적으로 요약**해 주세요. 그리고 요약 내용을 기반으로 합격 가능성을 높일 수 있는 **개선점 및 피드백**을 제공해주세요.

텍스트:
{extracted_text}

[분석 요청]
- **요약과 모든 피드백은 반드시 한국어로 작성해주세요.**
- **'summary' 필드에 다음 내용을 포함하여 요약해주세요:**
    - 핵심 프로젝트의 목적과 역할 (개인/팀)
    - 사용된 주요 기술 스택 및 개발 환경
    - 기술적인 문제 해결 과정 및 성과 (예: 성능 최적화, 특정 문제 해결 로직 구현 등)
    - 수치화된 성과가 있다면 반드시 강조해주세요.
    - 지원자의 차별화된 역량이 무엇인지 명확하게 요약해주세요.
- **'overall_feedback' 필드에 다음을 고려하여 피드백을 작성해주세요:**
    - {job_title} 직무 관점에서 포트폴리오 내용의 강점과 약점을 분석해주세요.
    - 특히 기술 스택의 적절성, 프로젝트 설명의 구체성(기여도, 성과)에 대한 개선점을 제안해주세요.
- 'individual_feedbacks'는 비어있는 객체 {{}}로 반환해주세요.
""")
    elif doc_type == "portfolio_summary_url":
        portfolio_url = document_content.get("portfolio_url", "")
        if not portfolio_url:
            return system_instruction, "오류: 포트폴리오 URL이 제공되지 않았습니다."
        user_prompt_parts.append(f"""
--- 포트폴리오 URL 분석 ---
다음 URL의 포트폴리오를 분석하고 **면접관이 한눈에 지원자의 핵심 역량을 파악할 수 있도록 구체적이고 효과적으로 요약**해 주세요. 그리고 요약 내용을 기반으로 합격 가능성을 높일 수 있는 **개선점 및 피드백**을 제공해주세요.

URL: {portfolio_url}

[분석 요청]
- **AI는 실제 URL에 직접 접속할 수 없습니다.** 따라서 URL만으로 포트폴리오의 구조와 내용을 유추하고, 일반적인 백엔드 포트폴리오의 성공 요건을 기반으로 분석 및 피드백을 제공합니다.
- **'summary' 필드에 다음 내용을 포함하여 요약해주세요:**
    - 일반적인 백엔드 포트폴리오의 구성 요소(프로젝트, 기술 스택, 성과 등)를 가정하여 요약.
    - 특히, URL 기반 포트폴리오의 접근성, 디자인, 명확한 정보 제공 방식에 대해 요약.
- **'overall_feedback' 필드에 다음을 고려하여 피드백을 작성해주세요:**
    - 포트폴리오 링크의 유효성, 보안성(HTTPS), 가독성 등 기술 외적인 측면에 대한 중요성을 강조해주세요.
    - 링크 내부에 프로젝트 별로 지원자의 역할, 사용 기술, 문제 해결 과정, 그리고 성과가 명확하게 기재되어 있어야 함을 강조해주세요.
- 'individual_feedbacks'는 비어있는 객체 {{}}로 반환해주세요.
""")
    elif doc_type == "portfolio":
        user_prompt_parts.append(f"""
--- 포트폴리오 정보 분석 ---
현재 저장된 포트폴리오 데이터는 다음과 같습니다.
{json.dumps(document_content, ensure_ascii=False, indent=2)}

[피드백 요청]
- **요약과 모든 피드백은 반드시 한국어로 작성해주세요.**
- **포트폴리오의 요약 내용을 기반으로, {job_title} 직무 관점에서 직무 역량과 얼마나 잘 연결되어 어필되는지 분석하고 구체적인 개선 방안을 제시해주세요.**
- **포트폴리오가 URL 링크 또는 PDF 파일 형태로 제출되었을 때, 그 형식의 적절성 및 정보 접근성(예: 링크 유효성, PDF 내용 추출 가능성)에 대해서도 언급해주세요.** (AI는 실제 링크에 접근하지 않으므로, 일반적인 유의사항을 언급합니다.)
- **포트폴리오 내용 자체를 객관적으로 요약한 내용은 'summary' 필드에, 개선 피드백은 'overall_feedback' 필드에 작성해주세요.**
- 'individual_feedbacks'는 비어있는 객체 {{}}로 반환하거나, 특정 프로젝트별/섹션별 핵심 피드백이 있다면 해당 키로 넣어주세요.
""")

    else:
        return system_instruction, f"오류: 알 수 없는 문서 타입 '{doc_type}'입니다."
    
    return system_instruction, "\n".join(user_prompt_parts)