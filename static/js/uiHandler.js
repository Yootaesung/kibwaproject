// static/js/uiHandler.js
import {
  editModal,
  modalTitle,
  aiOverallFeedbackContent,
  aiIndividualFeedbacksContainer,
  aiFeedbackArea,
  loadingOverlay,
  loadingMessage,
  companyModal,
  companyLoadingOverlay,
  companyLoadingMessage,
} from "./domElements.js";
import { saveCurrentFormContent } from "./documentData.js";

/**
 * 로딩 오버레이를 표시하거나 숨깁니다.
 * @param {boolean} show - true면 표시, false면 숨김
 * @param {string} message - 로딩 메시지
 * @param {HTMLElement} overlayElement - 로딩 오버레이 요소
 * @param {HTMLElement} messageElement - 로딩 메시지 요소
 */
export function showLoading(
  show,
  message = "처리 중...",
  overlayElement,
  messageElement
) {
  const overlay = overlayElement || loadingOverlay;
  const msgEl = messageElement || loadingMessage;
  if (show) {
    overlay.style.display = "flex";
    if (msgEl) {
      msgEl.textContent = message;
    } else {
      overlay.querySelector("p").textContent = message;
    }
  } else {
    overlay.style.display = "none";
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
  setAiFeedback(overallFeedback, individualFeedbacks, docType);
  editModal.style.display = "block";
}

/**
 * 모달을 닫습니다.
 */
export function closeEditModal() {
  saveCurrentFormContent();
  editModal.style.display = "none";
  if (aiOverallFeedbackContent) aiOverallFeedbackContent.textContent = "";
  if (aiIndividualFeedbacksContainer)
    aiIndividualFeedbacksContainer.innerHTML = "";
  if (aiFeedbackArea) aiFeedbackArea.style.display = "none";
}

/**
 * AI 피드백 내용을 모달에 설정합니다.
 * @param {string} overallFeedback - 전체 피드백
 * @param {object} individualFeedbacks - 개별 항목 피드백 객체
 * @param {string} docType - 문서 타입 ('resume', 'cover_letter', 'portfolio')
 */
export function setAiFeedback(overallFeedback, individualFeedbacks, docType) {
  if (
    !aiOverallFeedbackContent ||
    !aiIndividualFeedbacksContainer ||
    !aiFeedbackArea
  ) {
    console.error("AI feedback elements not found.");
    return;
  }

  aiOverallFeedbackContent.textContent = overallFeedback;

  aiIndividualFeedbacksContainer.innerHTML = "";
  if (
    Object.keys(individualFeedbacks).length > 0 &&
    (docType === "cover_letter" || docType === "resume")
  ) {
    const qaLabels = {
      // 이력서 항목
      education_history: "학력",
      career_history: "경력",
      certifications: "자격증",
      awards_activities: "수상/대외활동",
      skills_tech: "기술 스택",
      // 자기소개서 항목
      reason_for_application: "지원 동기",
      expertise_experience: "전문성 경험",
      collaboration_experience: "협업 경험",
      challenging_goal_experience: "도전적 경험",
      growth_process: "성장 과정",
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
    aiFeedbackArea.style.display = overallFeedback ? "block" : "none";
  }
}

// 기업 분석 모달 관련 함수
export function openCompanyModal() {
  companyModal.style.display = "block";
}

export function closeCompanyModal() {
  companyModal.style.display = "none";
}

export function setModalTitle(title) {
  modalTitle.textContent = title;
}
