// static/js/domElements.js

// DOM 요소들을 캐싱하여 전역적으로 접근할 수 있도록 내보냅니다.
export const editModal = document.getElementById("edit-modal");
export const modalTitle = document.getElementById("modal-title");
export const formFields = document.getElementById("form-fields");

export const aiOverallFeedbackContent = document.getElementById(
  "ai-overall-feedback-content"
);
export const aiIndividualFeedbacksContainer = document.getElementById(
  "ai-individual-feedbacks-container"
);

export const aiFeedbackArea = document.getElementById("ai-feedback-area");
export const documentForm = document.getElementById("document-form");
export const loadingOverlay = document.getElementById("loading-overlay");
export const loadingMessage = document.getElementById("loading-message");
export const diagramContainer = document.getElementById("document-diagram");

// 기업 분석 모달 관련 DOM 요소 추가
export const companyModal = document.getElementById("company-modal");
export const companyNameInput = document.getElementById("company-name-input");
export const analyzeCompanyButton = document.getElementById(
  "analyze-company-button"
);
export const companyAnalysisArea = document.getElementById(
  "company-analysis-area"
);
export const companyAnalysisText = document.getElementById(
  "company-analysis-text"
);
export const companyLoadingOverlay = document.getElementById(
  "company-loading-overlay"
);
export const companyLoadingMessage = document.getElementById(
  "company-loading-message"
);
export const closeCompanyModalButton = document.getElementById(
  "close-company-modal"
);
