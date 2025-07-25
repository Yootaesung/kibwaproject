# prompts.py
from typing import Dict, Any 
from job_data import JOB_DETAILS # JOB_DETAILS 임포트

def get_document_analysis_prompt(job_title: str, doc_type: str, document_content: Dict[str, Any]) -> str:
    """
    OpenAI AI 모델에 전달할 문서 분석 프롬프트를 생성합니다.
    """
    # 기본 피드백 프롬프트 (분석에 사용)
    base_feedback_prompt = f"당신은 {job_title} 직무 채용 전문가 AI입니다. 다음 내용을 분석하여 지원자의 서류 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요. 불필요한 서론 없이 바로 피드백 본론부터 시작하세요.\n\n"

    # 포트폴리오 요약에 사용될 별도의 프롬프트
    base_summary_prompt = f"당신은 {job_title} 직무 채용 전문가입니다. 다음 내용을 바탕으로 한 장짜리 요약본(핵심 경력, 프로젝트, 성과 중심)을 작성해 주세요. 요약은 간결하고 핵심적이어야 합니다.\n\n"

    if doc_type == "resume":
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        
        # 기술 스택 피드백 추가
        tech_stack_feedback_request = ""
        if job_competencies:
            tech_stack_feedback_request = (
                f"- 직무 핵심 역량({', '.join(job_competencies)})과 지원자의 '보유 기술 스택'을 비교하여, "
                f"유사한 기술 스택을 얼마나 잘 갖추고 있는지 평가하고, 부족한 점이나 추가로 어필할 수 있는 기술 스택에 대한 구체적인 피드백을 제공해주세요."
            )

        prompt = f"{base_feedback_prompt}--- 이력서 분석 ---\\n\\n현재 이력서 내용:\\n{content_str}\\n\\n[피드백 요청]\\n" \
                 f"{job_title} 직무 관점에서 이력서의 각 항목(학력, 전공, 학점, 수상내역, 대외활동, 경력, 기술 스택 등)이 직무와 얼마나 관련성이 높고 매력적인지 분석하고, 다음 사항들을 중점적으로 피드백해주세요:\n" \
                 f"- 각 항목을 직무와 연결하여 더 효과적으로 어필하는 방법\n" \
                 f"- 불필요하거나 부족한 내용에 대한 구체적인 개선 방안\n" \
                 f"{tech_stack_feedback_request}\n" \
                 f"- 전체적인 가독성 및 형식 개선 제안"
        
    elif doc_type == "cover_letter":
        # 자기소개서 필드명 변경에 맞춰 document_content에서 직접 값 가져오기
        motivation_expertise = document_content.get('motivation_expertise', '')
        collaboration_experience = document_content.get('collaboration_experience', '')

        feedback_sections = []
        
        # 1번 문항: 직무 이해도와 역량 평가
        section1 = f"""
        --- 1번 문항 분석 ---
        [문항 유형] 직무 이해도와 직무 역량
        
        [질문]
        해당 직무의 지원동기와 전문성을 기르기 위해 노력한 경험을 서술하시오.
        
        [답변]
        {motivation_expertise}
        
        [평가 기준]
        1. 지원 직무에 대한 명확한 이해도
        2. 본인의 전문성과 역량을 직무와 연결한 설명
        3. 구체적인 경험과 성과를 통한 역량 입증
        4. 직무 수행을 위한 준비 과정과 노력
        
        [피드백]
        """
        feedback_sections.append(section1)

        # 2번 문항: 협업능력과 의사소통능력 평가
        section2 = f"""
        --- 2번 문항 분석 ---
        [문항 유형] 협업능력과 의사소통능력
        
        [질문]
        공동의 목표를 위해 협업을 한 경험을 서술하시오.
        
        [답변]
        {collaboration_experience}
        
        [평가 기준]
        1. 팀워크와 협업 경험의 구체성
        2. 갈등 상황에서의 대처 방식과 문제 해결 능력
        3. 효과적인 의사소통 사례
        4. 팀 내에서의 기여도와 역할
        
        [피드백]
        """
        feedback_sections.append(section2)
        
        prompt = f"{base_feedback_prompt}--- 자기소개서 분석 ---\n\n"
        prompt += "\n\n".join(feedback_sections)
        prompt += "\n\n[공통 가이드라인]\n- 각 문항별로 2~3개의 주요 강점과 개선이 필요한 부분을 구체적으로 제시해주세요.\n- 답변의 내용이 질문의 의도와 얼마나 부합하는지 평가해주세요.\n- 구체적인 예시와 함께 개선 방안을 제안해주세요.\n- 전체적인 일관성과 논리적 흐름에 대한 피드백을 추가해주세요."
    elif doc_type == "portfolio":
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        prompt = f"{base_feedback_prompt}--- 포트폴리오 분석 ---\n\n현재 포트폴리오 설명:\n{content_str}\n\n[피드백 요청]\n{job_title} 직무 관점에서 포트폴리오의 각 프로젝트 설명이 직무 역량과 연결되어 얼마나 잘 어필되는지 분석하고, 프로젝트의 기여도, 기술 스택, 결과물을 더 효과적으로 제시하기 위한 구체적인 개선 방안을 제시해주세요. 링크 첨부의 중요성도 언급해주세요."
    elif doc_type == "portfolio_summary_url":
        portfolio_url = document_content.get("portfolio_url", "")
        if not portfolio_url:
            return "오류: 포트폴리오 URL이 제공되지 않았습니다."
        prompt = f"{base_summary_prompt}다음 URL의 포트폴리오를 분석해주세요.\nURL: {portfolio_url}\n\n[분석 요청]\n- 핵심 경력, 프로젝트, 성과를 중심으로 요약해주세요.\n- 기술 스택과 기여한 바를 명확히 해주세요.\n- 해당 직무와의 연관성을 고려해주세요."
    elif doc_type == "portfolio_summary_text":
        extracted_text = document_content.get("extracted_text", "")
        if not extracted_text.strip():
            return "오류: 추출된 포트폴리오 텍스트가 없습니다."
        prompt = f"{base_summary_prompt}다음은 포트폴리오에서 추출한 텍스트입니다. 이 내용을 바탕으로 분석해주세요.\n\n[포함된 내용]\n{extracted_text[:3000]}\n\n[분석 요청]\n1. 핵심 경력, 프로젝트, 성과를 요약해주세요.\n2. 기술 스택과 구체적인 기여 내용을 정리해주세요.\n3. 해당 직무와의 연관성을 고려한 평가를 해주세요."
    else:
        prompt = f"{base_feedback_prompt}--- 일반 문서 분석 ---\n\n현재 문서 내용:\n{document_content}\n\n[피드백 요청]\n해당 문서가 {job_title} 직무에 얼마나 적합한지 전반적인 피드백을 제공해주세요."

    return prompt