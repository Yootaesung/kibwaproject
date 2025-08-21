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
 * 로딩 오버레이 표시/숨김
 */
export function showLoading(
  show,
  message = "처리 중...",
  overlayElement,
  messageElement
) {
  const overlay = overlayElement || loadingOverlay;
  const msgEl = messageElement || loadingMessage;
  if (!overlay) return;

  if (show) {
    overlay.style.display = "flex";
    if (msgEl) {
      msgEl.textContent = message;
    } else {
      const p = overlay.querySelector("p");
      if (p) p.textContent = message;
    }
  } else {
    overlay.style.display = "none";
  }
}

/**
 * 모달 열기/닫기
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
  editModal.scrollTop = 0;
}

export function closeEditModal() {
  saveCurrentFormContent();
  editModal.style.display = "none";
  editModal.scrollTop = 0;

  if (aiOverallFeedbackContent) aiOverallFeedbackContent.textContent = "";
  if (aiIndividualFeedbacksContainer)
    aiIndividualFeedbacksContainer.innerHTML = "";
  if (aiFeedbackArea) aiFeedbackArea.style.display = "none";
}

/**
 * AI 피드백 세팅
 * - 이력서: education / activities / awards / certificates
 * - 자소서: reason_for_application / expertise_experience / collaboration_experience / challenging_goal_experience / growth_process
 * - 포트폴리오: portfolio_link / file_name 등(있으면 표시)
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

  aiOverallFeedbackContent.textContent = overallFeedback || "";
  aiOverallFeedbackContent.style.whiteSpace = "pre-line";

  aiIndividualFeedbacksContainer.innerHTML = "";

  const labelMap = {
    // 이력서 (신규 스키마)
    education: "학력",
    activities: "대외활동",
    awards: "수상경력",
    certificates: "자격증",

    // 자기소개서
    reason_for_application: "지원 동기",
    expertise_experience: "전문성 경험",
    collaboration_experience: "협업 경험",
    challenging_goal_experience: "도전적 경험",
    growth_process: "성장 과정",

    // 포트폴리오
    portfolio_link: "포트폴리오 링크",
    file_name: "파일명",
  };

  const validDocTypes = ["cover_letter", "resume", "portfolio"];
  const hasIndividual =
    individualFeedbacks && Object.keys(individualFeedbacks).length > 0;

  if (hasIndividual && validDocTypes.includes(docType)) {
    const fragment = document.createDocumentFragment();

    // key 순서 가독성(이력서 우선 정렬)
    const preferredOrder =
      docType === "resume"
        ? ["education", "activities", "awards", "certificates"]
        : Object.keys(individualFeedbacks);

    const printed = new Set();
    preferredOrder.forEach((k) => {
      if (k in individualFeedbacks) {
        const feedbackText = individualFeedbacks[k] || "";
        const label = labelMap[k] || k;

        const itemDiv = document.createElement("div");
        itemDiv.className = "individual-feedback-item";
        itemDiv.style.marginBottom = "12px";

        const title = document.createElement("h5");
        title.textContent = `${label} 피드백:`;
        title.style.fontWeight = "bold";
        title.style.marginBottom = "5px";

        const content = document.createElement("p");
        content.textContent = feedbackText;
        content.style.fontSize = "0.9em";
        content.style.lineHeight = "1.4";
        content.style.whiteSpace = "pre-line";

        itemDiv.appendChild(title);
        itemDiv.appendChild(content);
        fragment.appendChild(itemDiv);
        printed.add(k);
      }
    });

    // 나머지 키(있다면)
    Object.keys(individualFeedbacks).forEach((k) => {
      if (printed.has(k)) return;
      const itemDiv = document.createElement("div");
      itemDiv.className = "individual-feedback-item";
      itemDiv.style.marginBottom = "12px";

      const title = document.createElement("h5");
      title.textContent = `${labelMap[k] || k} 피드백:`;
      title.style.fontWeight = "bold";
      title.style.marginBottom = "5px";

      const content = document.createElement("p");
      content.textContent = individualFeedbacks[k] || "";
      content.style.fontSize = "0.9em";
      content.style.lineHeight = "1.4";
      content.style.whiteSpace = "pre-line";

      itemDiv.appendChild(title);
      itemDiv.appendChild(content);
      fragment.appendChild(itemDiv);
    });

    aiIndividualFeedbacksContainer.appendChild(fragment);
    aiIndividualFeedbacksContainer.style.display = "block";
  } else {
    aiIndividualFeedbacksContainer.style.display = "none";
  }

  aiFeedbackArea.style.display =
    overallFeedback || hasIndividual ? "block" : "none";
}

// 기업 분석 모달
export function openCompanyModal() {
  if (companyModal) companyModal.style.display = "block";
}
export function closeCompanyModal() {
  if (companyModal) companyModal.style.display = "none";
}

export function setModalTitle(title) {
  modalTitle.textContent = title;
}
