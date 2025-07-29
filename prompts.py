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
    base_feedback_prompt = f"당신은 {job_title} 직무 채용 전문가 AI입니다. 다음 내용을 분석하여 지원자의 서류 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요. 불필요한 서론 없이 바로 피드백 본론부터 시작하세요.\n\n"
    base_summary_prompt = f"당신은 {job_title} 직무 채용 전문가입니다. 다음 내용을 바탕으로 한 장짜리 요약본(핵심 경력, 프로젝트, 성과 중심)을 작성해 주세요. 요약은 간결하고 핵심적이어야 합니다.\n\n"

    history_context = ""
    # Modified history_context formatting for cover_letter
    def format_doc_content_for_history(content, d_type):
        if d_type == "cover_letter":
            return (
                f"지원동기: {content.get('reason_for_application', '')}\n"
                f"전문성 경험: {content.get('expertise_experience', '')}\n"
                f"협업 경험: {content.get('collaboration_experience', '')}\n"
                f"도전적 목표 경험: {content.get('challenging_goal_experience', '')}\n"
                f"성장 과정: {content.get('growth_process', '')}"
            )
        else:
            return "\n".join([f"{k}: {v}" for k, v in content.items()])

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
- **지원자가 제공한 내용만을 기반으로 구체적인 피드백을 제공해주세요.**
- 현재 이력서 내용과 {job_title} 직무의 필수 역량 및 자격증 정보(기술 스택 포함)를 바탕으로 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요.
- **만약 특정 항목의 내용이 '없음'으로 기재되어 있거나 비어있는 경우, 그 내용을 그대로 인지하고 '해당 정보가 누락되어 있다'고 명확히 언급한 후, 어떤 내용을 채워야 할지 구체적인 가이드라인을 제시해주세요. 존재하지 않는 내용을 상상하여 기재하지 마세요.**
- 불필요한 서론 없이 바로 피드백 본론부터 시작하세요.
- 이력서 내용이 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 각 섹션(학력, 경력, 자격증 등)의 내용이 얼마나 잘 구성되어 있는지 평가해주세요.
- 이전에 적은 이력서와 비교하여 어떤 점이 개선되었는지, 혹은 어떤 점이 여전히 미흡한지 구체적으로 언급해주세요.
- 변화한게 없다면 그 점을 명확히 지적하고 여전히 개선이 필요함을 강조해주세요.
{common_instructions}
"""
    elif doc_type == "cover_letter":
        reason_for_application = document_content.get('reason_for_application', '')
        expertise_experience = document_content.get('expertise_experience', '')
        collaboration_experience = document_content.get('collaboration_experience', '')
        challenging_goal_experience = document_content.get('challenging_goal_experience', '')
        growth_process = document_content.get('growth_process', '')

        prompt = f"""{base_feedback_prompt}
--- 현재 자기소개서 분석 (최신 버전) ---
현재 자기소개서 내용:
1. 해당 직무에 지원한 이유: {reason_for_application}
2. 해당 분야에 대한 전문성을 기르기 위해 노력한 경험: {expertise_experience}
3. 공동의 목표를 위해 협업을 한 경험: {collaboration_experience}
4. 도전적인 목표를 세우고 성취하기 위해 노력한 경험: {challenging_goal_experience}
5. 자신의 성장과정: {growth_process}

[피드백 요청]
- 자기소개서 내용이 {job_title} 직무에 얼마나 적합하고 어필되는지 분석해주세요.
- 각 질문별로 다음 항목들을 고려하여 구체적인 피드백과 개선 방안을 제시해주세요.

1. 해당 직무에 지원한 이유:
    - 직무 이해도: 지원자가 해당 직무의 특성과 필요 역량을 얼마나 정확하게 이해하고 있는지 확인합니다. 피상적인 지원 동기가 아닌, 직무에 대한 깊은 이해를 바탕으로 한 지원 동기인지 평가합니다.
    - 직무 적합성: 지원자의 강점, 경험, 가치관 등이 해당 직무와 얼마나 잘 부합하는지 평가합니다. 단순히 해보고 싶다가 아니라, 본인이 이 직무에 왜 적합한 인재인지를 보여줘야 합니다.
    - 회사 및 산업군에 대한 관심: 지원하는 회사나 해당 산업군에 대한 관심과 이해도를 파악합니다. 단순히 직무만 보고 지원한 것이 아니라, 회사의 비전이나 사업 방향에 대한 관심이 있는지도 중요합니다.
    - 기여 의지 및 성장 가능성: 지원자가 해당 직무를 통해 회사에 어떻게 기여하고 싶은지, 그리고 개인적으로 어떤 성장을 기대하는지 파악하여 장기적인 관점에서 함께할 수 있는 인재인지 확인합니다.

2. 해당 분야에 대한 전문성을 기르기 위해 노력한 경험:
    - 자기 주도성 및 학습 능력: 지원자가 특정 분야의 전문성을 높이기 위해 스스로 어떤 노력을 했는지, 그리고 새로운 지식이나 기술을 습득하는 데 있어 얼마나 적극적인지 평가합니다.
    - 지속적인 성장 의지: 특정 경험이나 결과에 안주하지 않고, 끊임없이 배우고 발전하려는 의지가 있는지 확인합니다.
    - 실제 적용 능력: 습득한 지식이나 기술을 실제 문제 해결이나 프로젝트에 어떻게 적용했는지 구체적인 사례를 통해 전문성의 깊이를 파악합니다. 단순히 무엇을 배웠는지가 아니라, 그것을 어떻게 활용했는지가 중요합니다.
    - 문제 해결 능력 및 성과: 전문성을 통해 어떤 문제를 해결했고, 어떤 성과를 달성했는지 확인하여 해당 분야에 대한 실질적인 기여 가능성을 봅니다.

3. 공동의 목표를 위해 협업을 한 경험:
    - 팀워크 및 협업 능력: 공동의 목표 달성을 위해 다른 사람들과 얼마나 효과적으로 소통하고 협력하는지 평가합니다. 갈등 상황에서의 대처 능력도 포함될 수 있습니다.
    - 책임감 및 기여도: 팀 내에서 자신의 역할을 명확히 인지하고, 책임감을 가지고 목표 달성에 얼마나 기여했는지 확인합니다.
    - 갈등 관리 및 조율 능력: 팀원 간의 의견 차이나 갈등이 발생했을 때, 이를 어떻게 조율하고 해결하여 공동의 목표를 향해 나아갔는지 봅니다.
    - 타인에 대한 이해 및 존중: 다양한 배경과 의견을 가진 팀원들을 이해하고 존중하며 함께 일하는 태도를 평가합니다.

4. 도전적인 목표를 세우고 성취하기 위해 노력한 경험:
    - 목표 설정 능력: 현실적이면서도 도전적인 목표를 스스로 설정할 수 있는지, 그리고 그 목표가 얼마나 구체적이고 측정 가능한지 평가합니다.
    - 실행력 및 추진력: 목표 달성을 위해 어떤 전략을 세우고, 이를 실제로 어떻게 실행에 옮겼는지 파악합니다. 난관에 부딪혔을 때 포기하지 않고 끈기 있게 노력하는 모습도 중요합니다.
    - 문제 해결 능력: 예상치 못한 어려움이나 문제가 발생했을 때, 이를 어떻게 분석하고 해결했는지 과정을 통해 지원자의 문제 해결 역량을 봅니다.
    - 회복 탄력성 및 학습 능력: 실패나 좌절을 겪었을 때, 이를 통해 무엇을 배우고 어떻게 극복했는지 파악하여 성장 가능성을 평가합니다.

5. 자신의 성장과정:
    - 가치관 및 인성: 지원자가 어떤 경험을 통해 현재의 가치관과 인성을 형성하게 되었는지 파악합니다. 조직의 문화에 잘 융화될 수 있는 인재인지 봅니다.
    - 핵심 역량 형성 과정: 학창 시절, 대외 활동, 인턴십 등 다양한 경험 속에서 현재의 직무 역량이나 강점이 어떻게 형성되고 발전되었는지 확인합니다.
    - 자기 성찰 및 발전 의지: 과거의 경험을 통해 스스로 무엇을 배우고 성장했으며, 앞으로 어떻게 발전해나가고 싶은지 보여주는지를 평가합니다.
    - 인생의 전환점 및 중요한 경험: 지원자의 삶에 큰 영향을 미쳤거나 중요한 깨달음을 준 경험을 통해 지원자의 깊이 있는 면모를 파악합니다.

- 구체적인 예시와 함께 개선 방안을 제안해주세요.
- 문맥에 맞지 않거나 모호한 부분이 있다면 구체적으로 제시해주세요.
- 전체적인 일관성과 논리적 흐름에 대한 피드백을 추가해주세요.
- 답변의 내용이 질문의 의도와 얼마나 부합하는지 평가해주세요.
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