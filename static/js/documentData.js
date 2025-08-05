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
        embedding: [],
        content_hash: "",
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
      return "포트폴리오";
    case "company":
      return "기업"; // 'company' 타입 추가
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
      docToUpdate.content_hash = contentHash;
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
    koreanName: koreanName,
    displayContent: `${koreanName} (v${version})`,
  };

  documentData[docType].push(newVersionData);
  documentData[docType].sort((a, b) => a.version - b.version);
  console.log(`Added new document version ${docType} v${version}`);
}

export function truncateDocumentVersions(docType, version) {
  documentData[docType] = documentData[docType].slice(0, version + 1);
}

export function getDocumentVersionData(docType, version) {
  if (!documentData[docType]) {
    return null;
  }
  return documentData[docType].find((d) => d.version === version);
}

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
    const formFieldsContainer = document.getElementById("form-fields");

    formFieldsContainer
      .querySelectorAll("textarea, input:not([type='file'])")
      .forEach((field) => {
        if (field.classList.contains("array-input-field")) {
          const parentDiv = field.closest(".array-field-container");
          const arrayFieldName = parentDiv.dataset.arrayFieldName || field.name;
          if (!docContent[arrayFieldName]) {
            docContent[arrayFieldName] = [];
          }
          const itemInputs = parentDiv.querySelectorAll(
            ".array-item input, .array-item textarea"
          );
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
