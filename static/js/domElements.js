// static/js/domElements.js

// DOM 요소들을 캐싱하여 전역적으로 접근할 수 있도록 내보냅니다.
export const editModal = document.getElementById("edit-modal");
export const modalTitle = document.getElementById("modal-title");
export const formFields = document.getElementById("form-fields");

// ⭐️ 변경: aiFeedbackContent는 이제 overall feedback 전용으로 사용
export const aiOverallFeedbackContent = document.getElementById(
  "ai-overall-feedback-content"
);
// ⭐️ 추가: 개별 피드백 컨테이너
export const aiIndividualFeedbacksContainer = document.getElementById(
  "ai-individual-feedbacks-container"
);

export const aiFeedbackArea = document.getElementById("ai-feedback-area");
export const documentForm = document.getElementById("document-form");
export const loadingOverlay = document.getElementById("loading-overlay");
export const diagramContainer = document.getElementById("document-diagram"); // 다이어그램 컨테이너 추가

// ⭐️ 추가: 로딩 메시지 p 태그의 ID가 "loading-message"로 명시되어 있다면 추가
export const loadingMessage = document.getElementById("loading-message");
