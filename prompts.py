# prompts.py

# 채용 서류 분석을 위한 프롬프트 템플릿
# TODO: 실제 AI 모델 학습 및 프롬프트 엔지니어링을 통해 더 정교하게 다듬어야 합니다.
# 현재는 간단한 예시.
def generate_analysis_prompt(job_title: str, resume_content: str, competencies: List[str], certifications: List[str], company_name: Optional[str] = None) -> str:
    company_info = f"회사명: {company_name}\n" if company_name else ""
    
    prompt = f"""
    당신은 채용 서류(이력서, 역량, 자격증)를 분석하여 특정 직무에 대한 지원자의 합격 가능성을 평가하고,
    구체적인 개선 방안을 제시하는 전문 AI 분석가입니다.

    다음 정보를 기반으로 분석을 수행해주세요:
    ---
    **직무:** {job_title}
    {company_info}
    **제출된 이력서 내용:**
    {resume_content if resume_content else "제공된 이력서 텍스트 없음."}

    **지원자가 선택한 역량:**
    {", ".join(competencies) if competencies else "선택된 역량 없음."}

    **지원자가 선택한 자격증:**
    {", ".join(certifications) if certifications else "선택된 자격증 없음."}
    ---

    **분석 목표:**
    1.  위 정보를 바탕으로 지원자가 **'{job_title}' 직무에 합격할 가능성**을 0점에서 100점 사이의 점수로 평가해주세요.
    2.  합격 가능성 점수와 함께, **가장 중요한 강점 2-3가지**와 **개선이 필요한 부분 2-3가지 (구체적인 피드백)**를 제공해주세요.
        * 개선 부분은 '이력서 내용', '선택 역량', '자격증 보완' 등 구체적인 항목을 언급해주세요.
    3.  응답은 반드시 다음 JSON 형식으로 제공해야 합니다:

    ```json
    {{
        "probability": [0-100 사이의 점수],
        "strengths": [
            "강점 1",
            "강점 2",
            "..."
        ],
        "improvements": [
            "개선 사항 1",
            "개선 사항 2",
            "..."
        ]
    }}
    ```
    예시:
    ```json
    {{
        "probability": 75,
        "strengths": [
            "React 숙련도가 높고 프로젝트 경험이 풍부함.",
            "문제 해결 능력이 뛰어나며 커뮤니케이션 스킬도 좋음."
        ],
        "improvements": [
            "이력서에 수치화된 성과를 더 명확히 제시해주세요.",
            "최신 JavaScript 트렌드 학습을 통해 기술 스택을 업데이트하는 것이 좋습니다."
        ]
    }}
    ```
    점수는 엄격하게 평가하며, 피드백은 지원자에게 실질적인 도움이 되도록 구체적으로 작성해주세요.
    """
    return prompt