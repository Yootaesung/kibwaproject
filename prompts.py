# prompts.py
import json
from typing import Dict, Any, Optional, List, Tuple

# ------------------------------------------------------------
# 기업 분석 프롬프트 (원본 유지)
# ------------------------------------------------------------
def get_company_analysis_prompt(company_name: str) -> Tuple[str, str]:
    system_instruction = f"""
당신은 기업 분석 전문가 AI입니다. 사용자가 제시한 기업의 특징, 주요 사업, 핵심 가치, 인재상 등을 종합적으로 분석하고 요약합니다.
- 모든 응답은 반드시 한국어로 작성합니다.
- 반환은 아래 JSON 스키마를 정확히 따릅니다. 그 외 텍스트/마크다운/설명은 금지합니다.

반환 JSON 스키마:
{{
  "company_summary": "string",                // 기업의 주요 사업, 제품/서비스, 시장 포지션, 최근 동향(추정 기반) 요약
  "key_values": "string",                     // 가치관/문화/인재상 개요
  "competencies_to_highlight": ["string"],    // 지원서에서 강조하면 좋은 역량 키워드
  "interview_tips": "string"                  // 실전 준비 팁(핵심 포인트 중심)
}}
"""
    user_prompt = f"아래 기업을 분석해 위 JSON만 반환하세요.\n기업명: {company_name}"
    return system_instruction, user_prompt


# ------------------------------------------------------------
# 문서 분석 프롬프트 (자기소개서 강화, 스키마/시그니처 불변)
# ------------------------------------------------------------
def get_document_analysis_prompt(
    job_title: str,
    doc_type: str,
    document_content: Dict[str, Any],
    job_competencies: Optional[List[str]] = None,
    previous_document_data: Optional[Dict[str, Any]] = None,
    older_document_data: Optional[Dict[str, Any]] = None,
    additional_user_context: Optional[str] = None,
    company_name: Optional[str] = None,
    company_analysis: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:

    # ---------------- System: 규칙 강화 (스키마는 불변) ----------------
    system_instruction = f"""
당신은 {job_title} 채용 전문가 AI입니다. 목표는 **합격 가능성을 높이는 구체적·실행 가능한 피드백**을 주는 것입니다.
- **반드시 한국어**로 작성합니다.
- **반드시 JSON만** 반환하며, 마크다운/불릿/설명 텍스트는 출력하지 않습니다.
- 출력은 아래 스키마만 허용합니다. **추가 키 금지**. 값은 모두 문자열이며, 빈 문자열 허용.
- 사실이 없는 내용은 임의로 꾸미지 말고, 필요한 데이터(수치/로그)를 요구하세요.

공통 반환 JSON 스키마:
{{
  "summary": "string",          // 문서 핵심 요약 (6~10줄 권장, **첫 2줄은 '이전 대비 변화' 요약**)
  "overall_feedback": "string", // 전체 개선 제안 (6~12줄 권장)
  "individual_feedbacks": {{    // 섹션별 피드백(문자열)
    // doc_type === "resume" 인 경우: 아래 4개 키만!
    "education": "string",
    "activities": "string",
    "awards": "string",
    "certificates": "string",

    // doc_type === "cover_letter" 인 경우: 아래 5개 키만!
    "reason_for_application": "string",
    "expertise_experience": "string",
    "collaboration_experience": "string",
    "challenging_goal_experience": "string",
    "growth_process": "string"
  }}
}}

품질 규칙(공통):
- “이전 버전 대비 무엇이 좋아/나빠졌는지”를 명확히 짚습니다. 내용이 늘었어도 **구체성·직무적합성·논리성**이 떨어지면 **질 하락**으로 지적합니다.
- 수치/성과/역할(STAR)을 선호합니다. 모호한 표현은 구체화 지시를 줍니다.
- 개인식별정보는 대상에서 제외합니다.
- 회사 맞춤성(있다면)을 확인해 **일반론 지양**.

형식 강제(cover_letter 전용, 각 항목 문자열 내부 형식):
- 아래의 줄머리/순서를 지키세요. 줄머리 이모지는 그대로 사용합니다.
  1) 📌 핵심 문제: 1~2줄
  2) ✅ 수정 지시: 번호 리스트(최소 3개) — 각 항목은 [행동 지시] + [이유(근거)] + [성과 지표]를 포함
  3) ✍ 예시 문장: 3~5문장, STAR 흐름(S→T→A→R)으로 자연스러운 한국어
  4) 🔎 필요 근거: 필요한 데이터/로그/지표/기간/역할 범위 등 나열
  5) 🎯 회사 연결: company_analysis가 있을 때만 1~2줄 (없으면 이 줄은 생략해도 됨)
- 각 항목(✅/✍)에는 **최소 1개 이상의 정량 지표**(%, 건수, ms, p95, RPS, 사용자 수, MTTR 등)를 포함하려 시도하세요.
- 사용자가 수치를 제공하지 않았다면, ✍ 예시에 허구 수치를 만들지 말고 “수치 제시 필요”라고 명시하세요.
"""

    # ---------------- User: 컨텍스트 구성 (원본 로직 유지) ----------------
    parts: List[str] = []

    # (선택) 기업 분석 문맥
    if company_name and company_analysis:
        parts.append(
            f"지원 기업: {company_name} / 지원 직무: {job_title}\n"
            "--- 기업 분석 요약 ---\n"
            f"- 기업 요약: {company_analysis.get('company_summary','')}\n"
            f"- 핵심가치/문화: {company_analysis.get('key_values','')}\n"
            f"- 강조 역량: {', '.join(company_analysis.get('competencies_to_highlight', []))}\n"
            "- 위 내용을 고려해 기업 맞춤 적합성도 함께 평가하세요.\n"
        )

    # 직무 핵심역량
    if job_competencies:
        parts.append(f"직무 핵심역량: {', '.join(job_competencies)}")

    # 현재 문서 내용
    parts.append("\n--- 현재 문서 내용 ---")
    if doc_type == "resume":
        edu = document_content.get("education", [])
        acts = document_content.get("activities", [])
        awds = document_content.get("awards", [])
        certs = document_content.get("certificates", [])

        lines = ["■ 학력"]
        for e in edu:
            lines.append(f"- 학력:{e.get('level','')}, 상태:{e.get('status','')}, 학교:{e.get('school','')}, 전공:{e.get('major','')}")
        lines.append("\n■ 대외활동")
        for a in acts:
            lines.append(f"- 제목:{a.get('title','')}, 내용:{a.get('content','')}")
        lines.append("\n■ 수상경력")
        for w in awds:
            lines.append(f"- 제목:{w.get('title','')}, 내용:{w.get('content','')}")
        lines.append("\n■ 자격증")
        for c in certs:
            lines.append(f"- {c}")
        parts.append("\n".join(lines) if any([edu, acts, awds, certs]) else "이력서 항목이 거의 비어 있습니다.")

    elif doc_type == "cover_letter":
        qmap = [
            ("reason_for_application", "지원 동기"),
            ("expertise_experience", "전문성 경험"),
            ("collaboration_experience", "협업 경험"),
            ("challenging_goal_experience", "도전적 목표 경험"),
            ("growth_process", "성장 과정"),
        ]
        for k, label in qmap:
            parts.append(f"- {label}: {document_content.get(k,'').strip() or '작성되지 않음'}")

        # 회사명 일치성 체크 가이드
        if company_name:
            parts.append(
                "\n[검증] 지원 동기에 특정 기업명/제품/가치 연결이 있는지 확인하고, "
                f"'{company_name}'와의 정합성을 평가하세요. 일반론이면 어떤 키워드로 보완해야 하는지 지시."
            )

    elif doc_type == "portfolio_summary_text":
        extracted = document_content.get("extracted_text", "")
        if not extracted:
            return system_instruction, "오류: 추출된 텍스트가 제공되지 않았습니다."
        parts.append(f"[포트폴리오 텍스트 일부]\n{extracted[:2000]}...")

    elif doc_type == "portfolio_summary_url":
        url = document_content.get("portfolio_url", "")
        if not url:
            return system_instruction, "오류: 포트폴리오 URL이 제공되지 않았습니다."
        parts.append(f"[포트폴리오 URL] {url}\n(실제 접속 불가: 일반적 성공요건 기반으로 평가)")

    elif doc_type == "portfolio":
        parts.append(json.dumps(document_content, ensure_ascii=False, indent=2))

    else:
        return system_instruction, f"오류: 알 수 없는 문서 타입 '{doc_type}'입니다."

    # 이전 버전 비교 컨텍스트
    def _fmt_prev(d: Dict[str, Any]) -> str:
        c = d.get("content", {}) or {}
        if doc_type == "resume":
            keep = {
                "education": c.get("education", []),
                "activities": c.get("activities", []),
                "awards": c.get("awards", []),
                "certificates": c.get("certificates", []),
            }
            return json.dumps(keep, ensure_ascii=False, indent=2)
        elif doc_type == "cover_letter":
            keep = {k: c.get(k, "") for k in [
                "reason_for_application", "expertise_experience", "collaboration_experience",
                "challenging_goal_experience", "growth_process"
            ]}
            return json.dumps(keep, ensure_ascii=False, indent=2)
        else:
            return json.dumps(c, ensure_ascii=False, indent=2)

    added_change_guide = False
    if previous_document_data:
        parts.append(
            f"\n--- 관련 이전 버전 (v{previous_document_data.get('version','?')}) ---\n"
            f"{_fmt_prev(previous_document_data)}\n"
            f"그 당시 피드백: {previous_document_data.get('feedback','(없음)')}\n"
        )
        added_change_guide = True

    if older_document_data:
        parts.append(
            f"\n--- 그 다음 이전 버전 (v{older_document_data.get('version','?')}) ---\n"
            f"{_fmt_prev(older_document_data)}\n"
            f"그 당시 피드백: {older_document_data.get('feedback','(없음)')}\n"
        )
        added_change_guide = True

    if added_change_guide:
        parts.append(
            "\n[비교 지침]\n"
            "- 반드시 '이전 대비 변화(추가/수정/삭제)'를 명확히 지적.\n"
            "- 내용이 늘어도 구체성/직무적합성/논리성 저하 시 '질 하락'으로 판단하고 보완안을 제시.\n"
        )

    if additional_user_context:
        parts.append(
            f"\n[사용자 반영 설명]\n\"{additional_user_context}\"\n"
            "- 실제 반영 여부를 확인하고 칭찬 또는 구체 보완안을 함께 제시.\n"
        )

    # ----------- 타입별 피드백 요청(cover_letter만 형식 엄격화) -----------
    if doc_type == "resume":
        parts.append(
            "\n[피드백 요청 - 이력서]\n"
            "- individual_feedbacks에는 반드시 'education','activities','awards','certificates' 4개 키만 사용해 각 1~2문장으로 핵심 피드백.\n"
            "- overall_feedback에는 직무적합성, STAR형 성과화, 수치화, 공백/누락 보완 가이드를 포함.\n"
        )
    elif doc_type == "cover_letter":
        parts.append(
            "\n[피드백 요청 - 자기소개서]\n"
            "- individual_feedbacks의 각 키 값(문자열)은 반드시 아래 형식을 포함:\n"
            "  📌 핵심 문제: 1~2줄\n"
            "  ✅ 수정 지시: 번호 리스트(최소 3개) — [행동 지시] + [이유] + [성과 지표]\n"
            "  ✍ 예시 문장: 3~5문장, STAR 흐름, 허구 수치 금지(없으면 '수치 제시 필요' 명시)\n"
            "  🔎 필요 근거: 필요한 데이터/로그/지표/기간/역할 범위 등\n"
            "  🎯 회사 연결: company_analysis가 있을 때만 1~2줄(없으면 생략 가능)\n"
            "- overall_feedback에는 논리 흐름/일관성/기업 맞춤성/중복 제거/문장 간결화 가이드를 포함하고, 최소 2개의 정량적 보완 제안을 제시.\n"
        )
    else:
        parts.append(
            "\n[피드백 요청 - 포트폴리오]\n"
            "- summary는 프로젝트 핵심(역할/기술/문제해결/성과) 중심.\n"
            "- overall_feedback은 가독성/접근성/프로젝트별 역할·성과 명확화, 수치화 가이드 포함.\n"
            "- individual_feedbacks는 비워도 무방.\n"
        )

    return system_instruction, "\n".join(parts)
