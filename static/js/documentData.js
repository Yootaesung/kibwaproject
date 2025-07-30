// static/js/documentData.js

// 문서 데이터를 관리하는 전역 변수
export let documentData = {};
export let jobTitle;
export let currentDocType;
export let currentDocVersion;

// 데이터 초기화 함수
export function initializeDefaultDocumentData() {
  documentData = {
    resume: [
      {
        version: 0,
        content: {},
        displayContent: "이력서 (v0)",
        koreanName: "이력서",
        feedback: "",
        individual_feedbacks: {}, // ⭐️ 추가: 이력서에도 개별 피드백 필드 추가
      },
    ],
    cover_letter: [
      {
        version: 0,
        content: {},
        displayContent: "자기소개서 (v0)",
        koreanName: "자기소개서",
        feedback: "",
        individual_feedbacks: {}, // ⭐️ 추가: 자기소개서에도 개별 피드백 필드 추가
      },
    ],
    portfolio: [
      {
        version: 0,
        content: {},
        displayContent: "포트폴리오 (v0)",
        koreanName: "포트폴리오",
        feedback: "",
        individual_feedbacks: {}, // ⭐️ 추가: 포트폴리오에도 개별 피드백 필드 추가
      },
    ],
  };
}

// 데이터 업데이트 함수 (필요에 따라 추가)
export function updateDocumentData(type, version, data) {
  const docIndex = documentData[type].findIndex((d) => d.version === version);
  if (docIndex !== -1) {
    documentData[type][docIndex] = { ...documentData[type][docIndex], ...data };
  }
}

export function setCurrentDocInfo(type, version) {
  currentDocType = type;
  currentDocVersion = version;
}

export function setJobTitle(title) {
  jobTitle = title;
}

/**
 * 새 문서 버전을 추가하고 currentDocVersion을 업데이트합니다.
 * @param {string} docType - 문서 타입 ('resume', 'cover_letter', 'portfolio').
 * @param {number} version - 새 버전 번호.
 * @param {object} content - 문서 내용.
 * @param {string} feedback - AI 피드백 (전체).
 * @param {object} individualFeedbacks - 개별 피드백 객체. ⭐️ 추가 파라미터
 */
export function addNewDocumentVersion(
  docType,
  version,
  content,
  feedback,
  individualFeedbacks = {}
) {
  if (!documentData[docType]) {
    documentData[docType] = [];
  }

  const newVersionData = {
    version: version,
    content: content,
    displayContent: `${
      getDocumentVersionData(docType, 0).koreanName
    } (v${version})`,
    koreanName: getDocumentVersionData(docType, 0).koreanName,
    feedback: feedback,
    individual_feedbacks: individualFeedbacks, // ⭐️ 저장: 개별 피드백 저장
  };

  documentData[docType].push(newVersionData);
  // setCurrentDocInfo는 외부에서 호출될 것이므로 여기서 currentDocVersion을 직접 업데이트하지 않습니다.
}

export function truncateDocumentVersions(docType, version) {
  documentData[docType] = documentData[docType].slice(0, version + 1);
}

export function getDocumentVersionData(docType, version) {
  return documentData[docType].find((d) => d.version === version);
}

// 현재 폼 내용 임시 저장 함수
// 이 함수는 documentData를 직접 조작하므로 여기에 배치
export function saveCurrentFormContent() {
  if (
    !currentDocType ||
    currentDocVersion === undefined ||
    currentDocType === "portfolio"
  )
    return;

  const versionToUpdate = getDocumentVersionData(
    currentDocType,
    currentDocVersion
  );

  if (versionToUpdate) {
    const docContent = {};
    if (currentDocType === "cover_letter") {
      // 5가지 새로운 질문 필드에서 값 가져오기
      const reasonForApplication = document.querySelector(
        'textarea[name="reason_for_application"]'
      );
      const expertiseExperience = document.querySelector(
        'textarea[name="expertise_experience"]'
      );
      const collaborationExperience = document.querySelector(
        'textarea[name="collaboration_experience"]'
      );
      const challengingGoalExperience = document.querySelector(
        'textarea[name="challenging_goal_experience"]'
      );
      const growthProcess = document.querySelector(
        'textarea[name="growth_process"]'
      );

      if (reasonForApplication)
        docContent.reason_for_application = reasonForApplication.value;
      if (expertiseExperience)
        docContent.expertise_experience = expertiseExperience.value;
      if (collaborationExperience)
        docContent.collaboration_experience = collaborationExperience.value;
      if (challengingGoalExperience)
        docContent.challenging_goal_experience =
          challengingGoalExperience.value;
      if (growthProcess) docContent.growth_process = growthProcess.value;
    } else {
      // 이력서 등의 다른 문서 타입 처리
      const textareas = document
        .getElementById("form-fields")
        .querySelectorAll("textarea");
      const inputs = document
        .getElementById("form-fields")
        .querySelectorAll('input:not([type="file"])');

      textareas.forEach((textarea) => {
        docContent[textarea.name] = textarea.value;
      });
      inputs.forEach((input) => {
        docContent[input.name] = input.value;
      });
    }
    versionToUpdate.content = docContent;
  }
}
