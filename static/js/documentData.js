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
        individual_feedbacks: {},
        embedding: [], // AI 분석 시 생성될 임베딩 필드
        content_hash: "", // AI 분석 시 생성될 콘텐츠 해시 필드
      },
    ],
    cover_letter: [
      {
        version: 0,
        content: {},
        displayContent: "자기소개서 (v0)",
        koreanName: "자기소개서",
        feedback: "",
        individual_feedbacks: {},
        embedding: [],
        content_hash: "",
      },
    ],
    portfolio: [
      {
        version: 0,
        content: {},
        displayContent: "포트폴리오 (v0)",
        koreanName: "포트폴리오",
        feedback: "",
        individual_feedbacks: {},
        embedding: [],
        content_hash: "",
      },
    ],
  };
}

// 헬퍼 함수: 문서 타입에 대한 한글 이름을 가져옵니다.
function getKoreanName(docType) {
  switch (docType) {
    case "resume":
      return "이력서";
    case "cover_letter":
      return "자기소개서";
    case "portfolio":
      return "포트폴리오"; // 필요한 경우 추가적인 문서 타입 처리
    default:
      return docType;
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
 * 기존 문서 버전을 업데이트합니다.
 * @param {string} docType - 문서 타입 ('resume', 'cover_letter', 'portfolio').
 * @param {number} version - 업데이트할 버전 번호.
 * @param {object} content - 업데이트할 문서 내용.
 * @param {string} feedback - AI 피드백 (전체).
 * @param {object} individualFeedbacks - 개별 피드백 객체.
 * @param {Array<number>} embedding - 문서의 임베딩.
 * @param {string} contentHash - 문서 내용의 해시.
 */
export function updateExistingDocumentVersion(
  docType,
  version,
  content,
  feedback = "",
  individualFeedbacks = {},
  embedding = [],
  contentHash = ""
) {
  if (documentData[docType]) {
    const index = documentData[docType].findIndex(
      (doc) => doc.version === version
    );
    if (index !== -1) {
      const docToUpdate = documentData[docType][index];
      docToUpdate.content = content;
      docToUpdate.feedback = feedback;
      docToUpdate.individual_feedbacks = individualFeedbacks;
      docToUpdate.embedding = embedding;
      docToUpdate.content_hash = contentHash; // ⭐️ 수정된 부분: 모든 문서의 다이어그램 제목에서 피드백 제거
      docToUpdate.displayContent = `${docToUpdate.koreanName} (v${version})`;
      console.log(`Updated document ${docType} v${version}`);
    } else {
      console.warn(`Document ${docType} v${version} not found for update.`);
    }
  }
}

/**
 * 새 문서 버전을 추가합니다. 이 함수는 주로 기존 버전의 내용을 복사하여 새 버전을 만들 때 사용됩니다.
 * @param {string} docType - 문서 타입 ('resume', 'cover_letter', 'portfolio').
 * @param {number} version - 새 버전 번호.
 * @param {object} content - 새 버전의 문서 내용.
 * @param {string} feedback - 새 버전의 AI 피드백 (전체).
 * @param {object} individualFeedbacks - 새 버전의 개별 피드백 객체.
 * @param {Array<number>} embedding - 새 버전의 문서 임베딩.
 * @param {string} contentHash - 새 버전의 문서 내용 해시.
 */
export function addNewDocumentVersion(
  docType,
  version,
  content,
  feedback = "",
  individualFeedbacks = {},
  embedding = [],
  contentHash = ""
) {
  if (!documentData[docType]) {
    documentData[docType] = [];
  }

  const koreanName = getKoreanName(docType);
  const newVersionData = {
    version: version,
    content: content,
    feedback: feedback,
    individual_feedbacks: individualFeedbacks,
    embedding: embedding,
    content_hash: contentHash,
    koreanName: koreanName, // ⭐️ 수정된 부분: 모든 문서의 다이아그램 제목에서 피드백 제거
    displayContent: `${koreanName} (v${version})`,
  };

  documentData[docType].push(newVersionData); // 버전을 기준으로 정렬하여 항상 오름차순 유지
  documentData[docType].sort((a, b) => a.version - b.version);
  console.log(`Added new document version ${docType} v${version}`);
}

export function truncateDocumentVersions(docType, version) {
  // 지정된 버전(포함) 이후의 모든 버전을 잘라냅니다.
  // 예를 들어, v2에서 새로운 분석을 하면 v2 이후의 v3, v4 등을 잘라냅니다.
  documentData[docType] = documentData[docType].slice(0, version + 1);
}

export function getDocumentVersionData(docType, version) {
  if (!documentData[docType]) {
    return null;
  }
  return documentData[docType].find((d) => d.version === version);
}

// saveCurrentFormContent 함수는 현재 이 시나리오에서 직접 사용되지 않지만,
// 향후 자동 저장 등의 기능을 위해 유지될 수 있습니다.
// 이 함수는 DOM을 직접 조작하므로, 다른 모듈에서 폼 데이터를 가져오는 방식과 중복되거나 충돌할 수 있습니다.
// 현재 `formSubmitHandler.js`에서 폼 데이터를 직접 수집하므로 이 함수의 직접적인 호출은 필요 없습니다.
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
    const formFieldsContainer = document.getElementById("form-fields"); // domElements에서 가져오는 것이 더 좋음 // 폼 필드에서 데이터를 가져오는 일반화된 로직 (formSubmitHandler와 유사하게)

    formFieldsContainer
      .querySelectorAll("textarea, input:not([type='file'])")
      .forEach((field) => {
        if (field.classList.contains("array-input-field")) {
          // 배열 필드는 특별 처리 (예: education, experience)
          const parentDiv = field.closest(".array-field-container");
          const arrayFieldName = parentDiv.dataset.arrayFieldName || field.name; // data-array-field-name 사용 또는 name 속성 사용
          if (!docContent[arrayFieldName]) {
            docContent[arrayFieldName] = [];
          }
          const itemInputs = parentDiv.querySelectorAll(
            ".array-item input, .array-item textarea"
          ); // array-item 내부의 input/textarea 모두
          const itemValues = Array.from(itemInputs)
            .map((input) => input.value.trim())
            .filter((v) => v);
          docContent[arrayFieldName] = itemValues;
        } else {
          docContent[field.name] = field.value;
        }
      });

    versionToUpdate.content = docContent;
    console.log(
      `Saved current form content to ${currentDocType} v${currentDocVersion}`
    );
  }
}
