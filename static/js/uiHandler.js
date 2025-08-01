// static/js/uiHandler.js
import {
  editModal,
  modalTitle,
  aiOverallFeedbackContent,
  aiIndividualFeedbacksContainer,
  aiFeedbackArea,
  loadingOverlay,
  loadingMessage,
} from "./domElements.js";
import { saveCurrentFormContent } from "./documentData.js";

/**
 * 로딩 오버레이를 표시하거나 숨깁니다.
 * @param {boolean} show - true면 표시, false면 숨김
 * @param {string} message - 로딩 메시지
 */
export function showLoading(show, message = "처리 중...") {
  if (show) {
    loadingOverlay.style.display = "flex";
    if (loadingMessage) {
      loadingMessage.textContent = message;
    } else {
      loadingOverlay.querySelector("p").textContent = message;
    }
  } else {
    loadingOverlay.style.display = "none";
  }
}

/**
 * 모달을 엽니다.
 * @param {string} title - 모달 제목
 * @param {string} [overallFeedback=""] - AI의 전체 피드백 (선택 사항)
 * @param {object} [individualFeedbacks={}] - AI의 개별 항목 피드백 객체 (선택 사항)
 * @param {string} [docType=""] - 현재 문서 타입 (예: 'cover_letter', 'resume', 'portfolio')
 */
export function openEditModal(
  title,
  overallFeedback = "",
  individualFeedbacks = {},
  docType = ""
) {
  modalTitle.textContent = title;

  // 모달을 열 때 피드백 영역 초기화
  if (aiOverallFeedbackContent) aiOverallFeedbackContent.textContent = "";
  if (aiIndividualFeedbacksContainer)
    aiIndividualFeedbacksContainer.innerHTML = "";
  if (aiFeedbackArea) aiFeedbackArea.style.display = "none";

  // 모달을 열 때 기존 피드백이 있다면 바로 표시
  if (overallFeedback || Object.keys(individualFeedbacks).length > 0) {
    setAiFeedback(overallFeedback, individualFeedbacks, docType);
  }

  editModal.style.display = "block";
}

export function closeEditModal() {
  saveCurrentFormContent();
  editModal.style.display = "none";

  // 닫을 때 피드백 내용도 초기화
  if (aiOverallFeedbackContent) aiOverallFeedbackContent.textContent = "";
  if (aiIndividualFeedbacksContainer)
    aiIndividualFeedbacksContainer.innerHTML = "";
  if (aiFeedbackArea) aiFeedbackArea.style.display = "none";
}

export function setModalTitle(title) {
  modalTitle.textContent = title;
}

/**
 * AI 피드백을 UI에 설정합니다.
 * @param {string} overallFeedback - AI의 전체적인 피드백 문자열입니다.
 * @param {object} individualFeedbacks - 각 항목별 개별 피드백을 담은 객체입니다. (예: {field_name: "feedback"})
 * @param {string} docType - 현재 문서 타입 (예: 'cover_letter', 'resume', 'portfolio')
 */
export function setAiFeedback(
  overallFeedback,
  individualFeedbacks = {},
  docType
) {
  // ⭐️ 수정: DOM 요소가 유효한지 체크
  if (aiOverallFeedbackContent) {
    aiOverallFeedbackContent.textContent =
      overallFeedback || "종합 피드백이 제공되지 않았습니다.";
  }

  if (aiIndividualFeedbacksContainer) {
    aiIndividualFeedbacksContainer.innerHTML = "";
  }

  if (
    Object.keys(individualFeedbacks).length > 0 &&
    (docType === "cover_letter" || docType === "resume")
  ) {
    const qaLabels = {
      reason_for_application: "지원 이유",
      expertise_experience: "전문성과 경험",
      collaboration_experience: "협업 경험",
      challenging_goal_experience: "도전적 목표 달성 경험",
      growth_process: "성장 과정",
      education_history: "학력",
      career_history: "경력",
      certifications: "보유 자격증",
      awards_activities: "수상 내역 및 대외활동",
      skills_tech: "보유 기술 스택",
      name: "이름",
      email: "이메일",
      phone: "연락처",
      career_summary: "경력 요약",
      experience: "경력",
      skills: "보유 기술",
      projects: "프로젝트",
      languages: "어학 능력",
    };

    const fragment = document.createDocumentFragment();

    for (const fieldName in individualFeedbacks) {
      if (Object.hasOwnProperty.call(individualFeedbacks, fieldName)) {
        const feedbackText = individualFeedbacks[fieldName];
        const label = qaLabels[fieldName] || fieldName;

        const feedbackItemDiv = document.createElement("div");
        feedbackItemDiv.className = "individual-feedback-item";
        feedbackItemDiv.style.marginBottom = "10px";

        const itemTitle = document.createElement("h5");
        itemTitle.textContent = `${label} 피드백:`;
        itemTitle.style.fontWeight = "bold";
        itemTitle.style.marginBottom = "5px";
        feedbackItemDiv.appendChild(itemTitle);

        const itemContent = document.createElement("p");
        itemContent.textContent = feedbackText;
        itemContent.style.fontSize = "0.9em";
        itemContent.style.lineHeight = "1.4";
        feedbackItemDiv.appendChild(itemContent);

        fragment.appendChild(feedbackItemDiv);
      }
    }
    aiIndividualFeedbacksContainer.appendChild(fragment);
    aiIndividualFeedbacksContainer.style.display = "block";
  } else if (aiIndividualFeedbacksContainer) {
    aiIndividualFeedbacksContainer.style.display = "none";
  }

  if (aiFeedbackArea) {
    aiFeedbackArea.style.display =
      overallFeedback || Object.keys(individualFeedbacks).length > 0
        ? "block"
        : "none";
  }
}
