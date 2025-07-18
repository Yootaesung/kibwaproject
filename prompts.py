from typing import Dict, Any 

def get_document_analysis_prompt(job_title: str, doc_type: str, document_content: Dict[str, Any]) -> str:
    """
    Gemini AI 모델에 전달할 문서 분석 프롬프트를 생성합니다.
    """
    base_prompt = f"당신은 {job_title} 직무 채용 전문가 AI입니다. 다음 내용을 분석하여 지원자의 서류 합격 가능성을 높일 수 있는 구체적인 피드백을 제공해주세요. 불필요한 서론 없이 바로 피드백 본론부터 시작하세요.\n\n"

    if doc_type == "resume":
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        prompt = f"{base_prompt}--- 이력서 분석 ---\n\n현재 이력서 내용:\n{content_str}\n\n[피드백 요청]\n{job_title} 직무 관점에서 이력서의 각 항목(학력, 전공, 학점, 수상내역, 대외활동, 경력사항)이 어떻게 더 효과적으로 어필될 수 있는지 구체적인 개선 방안과 부족한 점을 지적해주세요. 특히, 경력 사항은 직무 연관성과 성과를 중심으로 상세히 분석해주세요."
    elif doc_type == "cover_letter":
        qa_pairs = ""
        for qa in document_content.get('qa', []):
            qa_pairs += f"질문: {qa['question']}\n답변: {qa['answer']}\n\n"
        prompt = f"{base_prompt}--- 자기소개서 분석 ---\n\n현재 자기소개서 내용 (질문과 답변):\n{qa_pairs}\n\n[피드백 요청]\n{job_title} 직무 관점에서 각 질문에 대한 답변이 직무 역량, 경험, 회사 기여도를 얼마나 잘 드러내는지 평가하고, 더 매력적인 답변을 위한 구체적인 수정 제안과 보완할 점을 알려주세요. 특히, 경험과 성과를 구체적인 사례와 수치로 표현하는 방법을 제시해주세요."
    elif doc_type == "portfolio":
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        prompt = f"{base_prompt}--- 포트폴리오 분석 ---\n\n현재 포트폴리오 설명:\n{content_str}\n\n[피드백 요청]\n{job_title} 직무 관점에서 포트폴리오의 각 프로젝트 설명이 직무 역량과 연결되어 얼마나 잘 어필되는지 분석하고, 프로젝트의 기여도, 기술 스택, 결과물을 더 효과적으로 제시하기 위한 구체적인 개선 방안을 제시해주세요. 링크 첨부의 중요성도 언급해주세요."
    elif doc_type == "career_statement":
        content_str = "\n".join([f"{key}: {value}" for key, value in document_content.items()])
        prompt = f"{base_prompt}--- 경력기술서 분석 ---\n\n현재 경력기술서 내용:\n{content_str}\n\n[피드백 요청]\n{job_title} 직무 관점에서 경력기술서의 각 회사 및 역할별 상세 업무와 성과가 얼마나 명확하고 매력적인지 분석하고, 경험을 수치화하고 직무 연관성을 강조하는 구체적인 수정 제안을 해주세요."
    else:
        prompt = f"{base_prompt}--- 일반 문서 분석 ---\n\n현재 문서 내용:\n{document_content}\n\n[피드백 요청]\n해당 문서가 {job_title} 직무에 얼마나 적합한지 전반적인 피드백을 제공해주세요."

    return prompt