// static/js/uiHandler.js
import {
  editModal,
  modalTitle,
  aiOverallFeedbackContent, // ⭐️ 변경: aiFeedbackContent 대신 aiOverallFeedbackContent 임포트
  aiIndividualFeedbacksContainer, // ⭐️ 추가: 개별 피드백 컨테이너 임포트
  aiFeedbackArea,
  loadingOverlay,
  loadingMessage, // ⭐️ 추가: loadingMessage 임포트
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
    if (loadingMessage) {
      // loadingMessage DOM 요소가 존재하는지 확인
      loadingMessage.textContent = message;
    } else {
      // Fallback for cases where loadingMessage ID isn't set in HTML or not found
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
  // ⭐️ 변경: 피드백 인자 추가
  modalTitle.textContent = title;

  // 모달을 열 때 피드백 영역 초기화
  aiOverallFeedbackContent.textContent = "";
  aiIndividualFeedbacksContainer.innerHTML = "";
  aiFeedbackArea.style.display = "none";

  // ⭐️ 모달을 열 때 기존 피드백이 있다면 바로 표시
  if (overallFeedback || Object.keys(individualFeedbacks).length > 0) {
    setAiFeedback(overallFeedback, individualFeedbacks, docType);
  }

  editModal.style.display = "block";
}

export function closeEditModal() {
  saveCurrentFormContent(); // 닫기 전에 현재 내용 저장
  editModal.style.display = "none";

  // ⭐️ 닫을 때 피드백 내용도 초기화
  aiOverallFeedbackContent.textContent = "";
  aiIndividualFeedbacksContainer.innerHTML = "";
  aiFeedbackArea.style.display = "none";
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
  // ⭐️ 변경: 인자 추가
  // 1. 종합 피드백 설정
  aiOverallFeedbackContent.textContent = overallFeedback;

  // 2. 개별 피드백 컨테이너 초기화
  aiIndividualFeedbacksContainer.innerHTML = ""; // 이전 내용 지우기

  // 3. 개별 피드백이 있고, 자기소개서 타입일 경우에만 상세 피드백 표시
  // 'resume'도 개별 피드백을 가질 수 있도록 조건 변경 또는 제거 가능
  if (
    Object.keys(individualFeedbacks).length > 0 &&
    (docType === "cover_letter" || docType === "resume")
  ) {
    // ⭐️ 조건 변경: 이력서도 개별 피드백 고려
    // 백엔드에서 사용하는 자기소개서/이력서 항목 이름을 한글 라벨로 매핑 (job_data.py 참고)
    const qaLabels = {
      // 자기소개서 항목
      reason_for_application: "지원 이유",
      expertise_experience: "전문성과 경험",
      collaboration_experience: "협업 경험",
      challenging_goal_experience: "도전적 목표 달성 경험",
      growth_process: "성장 과정",
      // 이력서 항목 (예시 - 실제 스키마에 따라 추가)
      education_history: "학력", // '경력*' 대신 '학력'이 더 적절해 보입니다.
      career_history: "경력", // '경력*'에서 * 제거
      certifications: "보유 자격증", // '보유 자격증'에 해당하는 필드명 (가정)
      awards_activities: "수상 내역 및 대외활동", // '수상 내역 및 대외활동'에 해당하는 필드명 (가정)
      skills_tech: "보유 기술 스택", // '보유 기술 스택*'에서 * 제거
      // ... (기존에 정의된 다른 이력서 필드명들이 있다면 여기에 추가)
      name: "이름",
      email: "이메일",
      phone: "연락처",
      career_summary: "경력 요약",
      experience: "경력", // career_history와 역할이 겹칠 수 있으니 실제 스키마 확인 필요
      skills: "보유 기술", // skills_tech와 역할이 겹칠 수 있으니 실제 스키마 확인 필요
      projects: "프로젝트",
      languages: "어학 능력",
      // ... job_data.py의 스키마에 정의된 모든 필드명 추가
    };

    const fragment = document.createDocumentFragment(); // 성능을 위해 DocumentFragment 사용

    for (const fieldName in individualFeedbacks) {
      if (Object.hasOwnProperty.call(individualFeedbacks, fieldName)) {
        const feedbackText = individualFeedbacks[fieldName];
        const label = qaLabels[fieldName] || fieldName; // 매핑된 한글 라벨 사용

        const feedbackItemDiv = document.createElement("div");
        feedbackItemDiv.className = "individual-feedback-item"; // CSS 스타일링을 위한 클래스 추가
        feedbackItemDiv.style.marginBottom = "10px"; // 각 항목별 간격

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
    aiIndividualFeedbacksContainer.style.display = "block"; // 컨테이너 보이게
  } else {
    aiIndividualFeedbacksContainer.style.display = "none"; // 개별 피드백이 없거나 자기소개서가 아니면 숨김
  }

  // AI 피드백 영역 전체 표시/숨김
  // 종합 피드백이 있거나, 개별 피드백이 하나라도 있다면 전체 영역 표시
  aiFeedbackArea.style.display =
    overallFeedback || Object.keys(individualFeedbacks).length > 0
      ? "block"
      : "none";
}
