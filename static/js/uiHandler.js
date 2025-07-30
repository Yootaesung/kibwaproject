// static/js/uiHandler.js
import {
  editModal,
  modalTitle,
  aiFeedbackContent,
  aiFeedbackArea,
  loadingOverlay,
} from "./domElements.js";
import { saveCurrentFormContent } from "./documentData.js"; // saveCurrentFormContent는 documentData에 의존합니다.

/**
 * 로딩 오버레이를 표시하거나 숨깁니다.
 * @param {boolean} show - true면 표시, false면 숨김
 * @param {string} message - 로딩 메시지
 */
export function showLoading(show, message = "처리 중...") {
  if (show) {
    loadingOverlay.style.display = "flex";
    loadingOverlay.querySelector("p").textContent = message;
  } else {
    loadingOverlay.style.display = "none";
  }
}

export function openEditModal(title, feedback = "") {
  modalTitle.textContent = title;
  aiFeedbackContent.textContent = feedback;
  aiFeedbackArea.style.display = feedback ? "block" : "none";
  editModal.style.display = "block";
}

export function closeEditModal() {
  saveCurrentFormContent(); // 닫기 전에 현재 내용 저장
  editModal.style.display = "none";
  aiFeedbackContent.textContent = "";
  aiFeedbackArea.style.display = "none";
}

export function setModalTitle(title) {
  modalTitle.textContent = title;
}

export function setAiFeedback(feedback) {
  aiFeedbackContent.textContent = feedback;
  aiFeedbackArea.style.display = feedback ? "block" : "none";
}
