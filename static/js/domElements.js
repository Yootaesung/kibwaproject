// static/js/domElements.js

// DOM 요소들을 캐싱하여 전역적으로 접근할 수 있도록 내보냅니다.
export const editModal = document.getElementById("edit-modal");
export const modalTitle = document.getElementById("modal-title");
export const formFields = document.getElementById("form-fields");

// ⭐️ 중요: HTML ID와 정확히 일치하는지 확인
export const aiOverallFeedbackContent = document.getElementById(
  "ai-overall-feedback-content"
);
// ⭐️ 중요: HTML ID와 정확히 일치하는지 확인
export const aiIndividualFeedbacksContainer = document.getElementById(
  "ai-individual-feedbacks-container"
);

export const aiFeedbackArea = document.getElementById("ai-feedback-area");
export const documentForm = document.getElementById("document-form");
export const loadingOverlay = document.getElementById("loading-overlay");
export const loadingMessage = document.getElementById("loading-message");
export const diagramContainer = document.getElementById("document-diagram");
