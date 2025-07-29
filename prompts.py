# prompts.py
from typing import Dict, Any, Optional
from job_data import JOB_DETAILS

def get_document_analysis_prompt(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    job_competencies: Optional[list[str]] = None,
    previous_document_content: Optional[Dict[str, Any]] = None, # 이전 버전 문서 내용
    previous_feedback: Optional[str] = None, # 이전 버전 피드백
    older_document_content: Optional[Dict[str, Any]] = None, # 그 이전 버전 문서 내용 (vN-2)
    older_feedback: Optional[str] = None # 그 이전 버전 피드백 (vN-2)
) -> str:
    """
    OpenAI AI 모델에 전달할 문서 분석 프롬프트를 생성합니다.
    이전 버전의 문서 내용과 피드백을 포함하여 AI가 더 정밀한 피드백을 제공하도록 합니다.
    """
    base_feedback_prompt = f"당신은 {job_title} 직무 채용 전문가 AI입니다. 다음 내용을 분석하여 지원자의 서류 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요. 불필요한 서론 없이 바로 피드백 본론부터 시작하세요.\\n\\n"
    base_summary_prompt = f"당신은 {job_title} 직무 채용 전문가입니다. 다음 내용을 바탕으로 한 장짜리 요약본(핵심 경력, 프로젝트, 성과 중심)을 작성해 주세요. 요약은 간결하고 핵심적이어야 합니다.\\n\\n"

    history_context = ""
    if older_document_content is not None and older_feedback is not None:
        older_content_formatted = "\n".join([f"{k}: {v}" for k, v in older_document_content.items()]) if doc_type != "cover_letter" else \
                                  f"지원동기 및 전문성: {older_document_content.get('motivation_expertise', '')}\n협업 경험: {older_document_content.get('collaboration_experience', '')}"
        history_context += f"""
--- 이전 버전 문서 (vN-2) ---
내용:
{older_content_formatted}
이 버전에 대한 피드백:
{older_feedback}
"""

    if previous_document_content is not None and previous_feedback is not None:
        previous_content_formatted = "\n".join([f"{k}: {v}" for k, v in previous_document_content.items()]) if doc_type != "cover_letter" else \
                                     f"지원동기 및 전문성: {previous_document_content.get('motivation_expertise', '')}\n협업 경험: {previous_document_content.get('collaboration_experience', '')}"
        history_context += f"""
--- 직전 버전 문서 (vN-1) ---
내용:
{previous_content_formatted}
이 버전에 대한 피드백:
{previous_feedback}
"""
    
    common_instructions = ""
    if history_context:
        common_instructions += f"""
--- 피드백 지침 ---
- 현재 문서 내용을 직전 버전 (vN-1) 및 그 이전 버전 (vN-2)과 비교하여 피드백을 제공합니다.
- 직전 버전 (vN-1)의 내용과 피드백을 더 중요하게 고려합니다.
- 이전 버전에 비해 어떤 점이 개선되었는지, 혹은 어떤 점이 여전히 미흡한지 구체적으로 언급합니다.
- 만약 이전 버전과 현재 문서 내용 간에 실질적인 변화가 거의 없다면, 그 점을 명확히 지적하고 여전히 개선이 필요함을 강조합니다.
{history_context}
"""

    if doc_type == "resume":
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        
        tech_stack_feedback_request = ""
        if job_competencies:
            tech_stack_feedback_request = f"""
- 지원자가 제시한 기술 스택({', '.join(job_competencies)})과 이력서 내용이 얼마나 잘 부합하는지 평가하고, 부족한 부분이 있다면 보완 방안을 제시해주세요.
"""

        prompt = f"""{base_feedback_prompt}
--- 현재 이력서 분석 (최신 버전) ---
현재 이력서 내용:
{content_str}

[피드백 요청]
- 답변은 500자 이내로 간결하게 작성해주세요.
- 현재 이력서 내용과 {job_title} 직무의 필수 역량 및 자격증 정보(기술 스택 포함)를 바탕으로 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요.
{tech_stack_feedback_request}
- 불필요한 서론 없이 바로 피드백 본론부터 시작하세요.
- 이력서 내용이 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 각 섹션(학력, 경력, 자격증 등)의 내용이 얼마나 잘 구성되어 있는지 평가해주세요.
- 이전에 적은 이력서와 비교하여 어떤 점이 개선되었는지, 혹은 어떤 점이 여전히 미흡한지 구체적으로 언급해주세요.
- 변화한게 없다면 그 점을 명확히 지적하고 여전히 개선이 필요함을 강조해주세요.
{common_instructions}
"""
    elif doc_type == "cover_letter":
        motivation_expertise = document_content.get('motivation_expertise', '')
        collaboration_experience = document_content.get('collaboration_experience', '')
        
        prompt = f"""{base_feedback_prompt}
--- 현재 자기소개서 분석 (최신 버전) ---
현재 자기소개서 내용:
지원동기 및 전문성: {motivation_expertise}
공동의 목표를 위해 협업을 한 경험: {collaboration_experience}

[피드백 요청]
- 자기소개서 내용이 {job_title} 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 지원동기, 전문성, 협업 경험을 더 효과적으로 나타내기 위한 구체적인 개선 방안을 제시해주세요.
- 문맥에 맞지 않거나 모호한 부분이 있다면 구체적으로 제시해주세요.
- 답변의 내용이 질문의 의도와 얼마나 부합하는지 평가해주세요.
- 구체적인 예시와 함께 개선 방안을 제안해주세요.
- 전체적인 일관성과 논리적 흐름에 대한 피드백을 추가해주세요.
- 이전에 적은 자기소개서와 비교하여 어떤 점이 개선되었는지, 혹은 어떤 점이 여전히 미흡한지 구체적으로 언급해주세요.
- 변화한게 없다면 그 점을 명확히 지적하고 여전히 개선이 필요함을 강조해주세요.
{common_instructions}
"""
    elif doc_type == "portfolio": # 기존 포트폴리오 피드백 로직 유지
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        prompt = f"{base_feedback_prompt}--- 포트폴리오 분석 ---\n\n현재 포트폴리오 설명:\n{content_str}\n\n[피드백 요청]\n{job_title} 직무 관점에서 포트폴리오의 각 프로젝트 설명이 직무 역량과 연결되어 얼마나 잘 어필되는지 분석하고, 프로젝트의 기여도, 기술 스택, 결과물을 더 효과적으로 제시하기 위한 구체적인 개선 방안을 제시해주세요. 링크 첨부의 중요성도 언급해주세요."
    elif doc_type == "portfolio_summary_url": # 기존 포트폴리오 요약 로직 유지
        portfolio_url = document_content.get("portfolio_url", "")
        if not portfolio_url:
            return "오류: 포트폴리오 URL이 제공되지 않았습니다."
        prompt = f"{base_summary_prompt}다음 URL의 포트폴리오를 분석해주세요.\nURL: {portfolio_url}\n\n[분석 요청]\n- 핵심 경력, 프로젝트, 성과를 중심으로 요약해주세요.\n- 기술 스택과 기여한 바를 명확히 해주세요.\n- 해당 직무와의 연관성을 고려해주세요."
    elif doc_type == "portfolio_summary_text": # 기존 포트폴리오 요약 로직 유지
        extracted_text = document_content.get("extracted_text", "")
        if not extracted_text:
            return "오류: 추출된 텍스트가 제공되지 않았습니다."
        prompt = f"{base_summary_prompt}다음 텍스트 내용을 바탕으로 포트폴리오를 분석해주세요.\n텍스트:\n{extracted_text}\n\n[분석 요청]\n- 핵심 경력, 프로젝트, 성과를 중심으로 요약해주세요.\n- 기술 스택과 기여한 바를 명확히 해주세요.\n- 해당 직무와의 연관성을 고려해주세요."
    else:
        return f"오류: 알 수 없는 문서 타입 '{doc_type}'입니다."

    return prompt