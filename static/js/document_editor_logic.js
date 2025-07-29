// static/js/document_editor_logic.js

// 1. 전역 변수 및 DOM 요소 캐싱
let jobTitle;
let currentDocType;
let currentDocVersion;
let documentData = {}; // 문서 버전 데이터를 저장할 객체

const editModal = document.getElementById("edit-modal");
const modalTitle = document.getElementById("modal-title");
const formFields = document.getElementById("form-fields");
const aiFeedbackContent = document.getElementById("ai-feedback-content");
const aiFeedbackArea = document.getElementById("ai-feedback-area");
const documentForm = document.getElementById("document-form");
const loadingOverlay = document.getElementById("loading-overlay");

// Helper function for default documentData initialization
function initializeDefaultDocumentData() {
  documentData = {
    resume: [
      {
        version: 0,
        content: {},
        displayContent: "이력서 (v0)",
        koreanName: "이력서",
        feedback: "",
      },
    ],
    cover_letter: [
      {
        version: 0,
        content: {},
        displayContent: "자기소개서 (v0)",
        koreanName: "자기소개서",
        feedback: "",
      },
    ],
    portfolio: [
      {
        version: 0,
        content: {},
        displayContent: "포트폴리오 (v0)",
        koreanName: "포트폴리오",
        feedback: "",
      },
    ],
  };
}

// 2. 모든 함수 정의

/**
 * 다이어그램 노드 클릭 이벤트를 설정합니다.
 */
function setupNodeClickEvents() {
  // 롤백 버튼 이벤트 리스너
  document.querySelectorAll(".rollback-button").forEach((button) => {
    button.onclick = (e) => {
      e.stopPropagation(); // 노드 클릭 이벤트와 중복 방지
      const docType = button.dataset.docType;
      // dataset.version에서 해당 버튼이 되돌릴 버전을 가져옴
      const versionToRollback = parseInt(button.dataset.version, 10);
      rollbackDocument(docType, versionToRollback);
    };
  });

  document.querySelectorAll(".diagram-node.document-node").forEach((node) => {
    node.onclick = async (e) => {
      const clickedNode = e.target.closest(".document-node");
      currentDocType = clickedNode.dataset.docType;
      currentDocVersion = parseInt(clickedNode.dataset.version, 10);
      const currentDocKoreanName = clickedNode.dataset.koreanName; // 데이터셋으로 한글 이름 가져옴

      modalTitle.textContent = `${currentDocKoreanName} 편집 (v${currentDocVersion})`;

      // 팝업을 열 때 해당 버전의 데이터를 불러옴
      const versionData = documentData[currentDocType].find(
        (d) => d.version === currentDocVersion
      );
      const docContent = versionData.content;
      const savedFeedback = versionData.feedback; // 이전 버전의 피드백

      try {
        showLoading(true, "문서 스키마 로딩 중..."); // 로딩 표시
        const formSchema = await fetch(
          `/api/document_schema/${currentDocType}?job_slug=${jobTitle
            .replace(/ /g, "-")
            .replace(/\//g, "-")
            .toLowerCase()}`
        )
          .then((res) => {
            if (!res.ok) {
              throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
          })
          .catch((error) => {
            console.error("Error fetching form schema:", error);
            alert("문서 스키마를 불러오는 데 실패했습니다. 콘솔을 확인하세요.");
            editModal.style.display = "none"; // Hide modal if schema fetch fails
            return null; // Return null to prevent further execution with invalid schema
          });

        if (!formSchema) {
          showLoading(false); // 로딩 숨김
          return; // Stop if schema fetch failed
        }

        console.log("Fetched Form Schema:", formSchema); // Log the schema for debugging

        renderFormFields(formSchema, docContent); // 불러온 데이터로 폼 필드 렌더링

        if (savedFeedback) {
          aiFeedbackContent.textContent = savedFeedback;
          aiFeedbackArea.style.display = "block";
        } else {
          aiFeedbackContent.textContent = ""; // 내용 초기화
          aiFeedbackArea.style.display = "none";
        }

        editModal.style.display = "block";
      } catch (error) {
        console.error("An error occurred during node click event:", error);
        alert("문서 편집기를 여는 중 오류가 발생했습니다. 콘솔을 확인하세요.");
        editModal.style.display = "none";
      } finally {
        showLoading(false); // 로딩 숨김
      }
    };
  });
}

/**
 * 주어진 스키마와 내용에 따라 폼 필드를 렌더링합니다.
 * @param {Object} schema - 문서 스키마 (sections 또는 fields 포함).
 * @param {Object} currentContent - 현재 문서 내용.
 */
function renderFormFields(schema, currentContent) {
  formFields.innerHTML = ""; // 기존 폼 필드 초기화
  console.log("Rendering form fields for schema:", schema); // Log schema when rendering starts

  // schema.korean_name이 없을 경우를 대비하여 방어 코드 추가
  const docKoreanName = schema.korean_name || schema.title || currentDocType;

  if (docKoreanName === "포트폴리오") {
    formFields.innerHTML = `
            <div class="input-group">
                <label>포트폴리오 PDF 업로드:</label>
                <input type="file" name="portfolio_pdf" accept=".pdf">
            </div>
            <div class="input-group">
                <label>포트폴리오 링크 입력:</label>
                <input type="text" name="portfolio_link" placeholder="포트폴리오가 업로드된 웹사이트, 블로그, Github 등 링크를 입력하세요." value="${
                  currentContent.portfolio_link || ""
                }">
            </div>
        `;
    const submitBtn = document.querySelector(
      '#document-form button[type="submit"]'
    );
    submitBtn.textContent = "요약 및 다운";
    documentForm.onsubmit = handlePortfolioFormSubmit;
    return;
  } else if (docKoreanName === "자기소개서") {
    const qaContainer = document.createElement("div");
    qaContainer.id = "qa-container";
    const motivationExpertise = currentContent.motivation_expertise || "";
    const collaborationExperience =
      currentContent.collaboration_experience || "";

    qaContainer.innerHTML = `
            <div class="input-group">
                <label>1. 해당 직무의 지원동기와 전문성을 기르기 위해 노력한 경험을 서술하시오.</label>
                <textarea name="motivation_expertise" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;">${motivationExpertise}</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${motivationExpertise.length}</span>
                </div>
            </div>
            <div class="input-group" style="margin-top: 20px;">
                <label>2. 공동의 목표를 위해 협업을 한 경험을 서술하시오.</label>
                <textarea name="collaboration_experience" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;">${collaborationExperience}</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${collaborationExperience.length}</span>
                </div>
            </div>
        `;
    formFields.appendChild(qaContainer);

    qaContainer.querySelectorAll("textarea").forEach((textarea) => {
      const charCountSpan =
        textarea.nextElementSibling.querySelector(".char-count");
      textarea.addEventListener("input", () => {
        charCountSpan.textContent = textarea.value.length;
      });
    });
    const submitBtn = document.querySelector(
      '#document-form button[type="submit"]'
    );
    submitBtn.textContent = "저장 및 분석";
    documentForm.onsubmit = handleDocumentFormSubmit;
    return;
  }

  if (schema.sections) {
    console.log("Rendering sections for Resume.");
    schema.sections.forEach((section) => {
      const sectionDiv = document.createElement("div");
      sectionDiv.className = "form-section";

      const sectionTitle = document.createElement("h3");
      sectionTitle.textContent = section.title;
      sectionDiv.appendChild(sectionTitle);

      section.fields.forEach((field) => {
        const div = document.createElement("div");
        div.className = "input-group";

        const label = document.createElement("label");
        label.textContent = field.label;
        div.appendChild(label);

        let inputElement;
        if (field.type === "textarea") {
          inputElement = document.createElement("textarea");
          inputElement.placeholder = field.placeholder;
          inputElement.rows = 5;
          inputElement.value = currentContent[field.name] || "";
        } else if (field.type === "file") {
          inputElement = document.createElement("input");
          inputElement.type = "file";
          inputElement.accept = field.accept;
        } else if (field.type === "date") {
          inputElement = document.createElement("input");
          inputElement.type = "date";
          inputElement.value = currentContent[field.name] || "";
        } else {
          inputElement = document.createElement("input");
          inputElement.type = field.type;
          inputElement.placeholder = field.placeholder;
          inputElement.value = currentContent[field.name] || "";
        }
        inputElement.name = field.name;
        inputElement.id = field.name;

        div.appendChild(inputElement);
        sectionDiv.appendChild(div);
      });
      formFields.appendChild(sectionDiv);
    });
  } else if (schema.fields) {
    console.log("Rendering fields for general document type.");
    schema.fields.forEach((field) => {
      const div = document.createElement("div");
      div.className = "input-group";
      if (field.type === "textarea") {
        div.innerHTML = `
                                <label>${field.label}:</label>
                                <textarea name="${field.name}" placeholder="${
          field.placeholder || ""
        }">${currentContent[field.name] || ""}</textarea>
                            `;
      } else if (field.type === "text") {
        div.innerHTML = `
                                <label>${field.label}:</label>
                                <input type="text" name="${
                                  field.name
                                }" value="${
          currentContent[field.name] || ""
        }" placeholder="${field.placeholder || ""}">
                            `;
      }
      formFields.appendChild(div);
    });
  }

  const submitBtn = document.querySelector(
    '#document-form button[type="submit"]'
  );
  submitBtn.textContent = "저장 및 분석";
  documentForm.onsubmit = handleDocumentFormSubmit;
}

/**
 * 일반 문서 (이력서, 자기소개서) 폼 제출을 처리합니다.
 * @param {Event} e - 제출 이벤트.
 */
async function handleDocumentFormSubmit(e) {
  e.preventDefault();
  const formData = new FormData(documentForm);
  const docContent = {}; // 사용자가 현재 폼에서 입력한 내용

  for (let [key, value] of formData.entries()) {
    if (key !== "portfolio_pdf") {
      docContent[key] = value;
    }
  }

  let hasMeaningfulContent = false;
  for (const key in docContent) {
    if (
      docContent.hasOwnProperty(key) &&
      docContent[key] &&
      docContent[key].trim() !== ""
    ) {
      hasMeaningfulContent = true;
      break;
    }
  }

  if (!hasMeaningfulContent) {
    alert("분석할 내용이 없습니다. 내용을 입력해주세요.");
    return;
  }

  try {
    // 1. 현재 편집 중인 문서 버전을 documentData에서 찾습니다.
    const currentDocInArray = documentData[currentDocType].find(
      (doc) => doc.version === currentDocVersion
    );

    // ⭐️ 수정 시작: 백엔드 Pydantic 모델에 맞게 requestBody 구성 ⭐️
    // 'version' 필드를 추가하고, 이전 버전 데이터 필드는 백엔드에서 직접 처리하도록 제거합니다.
    const requestBody = {
      job_title: jobTitle,
      document_content: docContent, // 현재 폼에서 입력된 내용
      version: currentDocVersion, // 이 필드가 '422 Unprocessable Entity' 오류의 주된 원인이었습니다.
    };
    // ⭐️ 수정 끝 ⭐️

    showLoading(true, "AI 분석 중..."); // 로딩 오버레이 표시

    const response = await fetch(`/api/analyze_document/${currentDocType}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });
    const result = await response.json();

    showLoading(false); // 로딩 오버레이 숨김

    if (response.ok) {
      // 2. 현재 버전 (vN)의 content와 feedback을 업데이트합니다.
      if (currentDocInArray) {
        currentDocInArray.content = docContent; // 현재 폼 내용으로 업데이트
        currentDocInArray.feedback = result.feedback; // 새로 받은 AI 피드백으로 업데이트
      }

      // 3. 만약 현재 편집 중인 버전이 가장 최신 버전이 아니라면, 그 이후의 버전을 잘라냅니다.
      // (예: v0을 편집하고 저장하면, v1, v2...가 있었다면 모두 제거하고 v0에서 새로운 브랜치 시작)
      if (currentDocVersion < documentData[currentDocType].length - 1) {
        documentData[currentDocType] = documentData[currentDocType].slice(
          0,
          currentDocVersion + 1
        );
      }

      // 4. 새로운 버전 (vN+1)의 번호를 결정합니다. (배열의 현재 길이)
      const newVersionNumberForPush = documentData[currentDocType].length;

      // 5. 새로 생성될 버전 (vN+1) 객체를 정의합니다.
      // 이 객체는 현재 업데이트된 vN의 내용과 피드백을 복사합니다.
      const newDocForNextVersion = {
        version: newVersionNumberForPush,
        content: { ...currentDocInArray.content }, // 업데이트된 vN의 content 복사
        displayContent: `${currentDocInArray.koreanName} (v${newVersionNumberForPush})`,
        koreanName: currentDocInArray.koreanName,
        feedback: currentDocInArray.feedback, // 업데이트된 vN의 feedback 복사
      };

      // 6. 새로운 버전을 documentData 배열에 추가합니다.
      documentData[currentDocType].push(newDocForNextVersion);

      // 7. 현재 활성 버전을 새로 생성된 vN+1로 업데이트합니다.
      currentDocVersion = newVersionNumberForPush;

      // UI 업데이트
      modalTitle.textContent = `${currentDocInArray.koreanName} 편집 (v${currentDocVersion})`;
      aiFeedbackContent.textContent = result.feedback;
      aiFeedbackArea.style.display = "block";

      drawDiagram(); // 다이어그램 다시 그리기
      alert("문서가 저장되고 분석되었습니다. AI 피드백을 확인하세요.");
    } else {
      const errorMessage = result.detail
        ? result.detail.map((d) => d.msg).join(", ")
        : result.error || "알 수 없는 오류";
      alert(`분석 실패: ${errorMessage}`);
      aiFeedbackContent.textContent = `오류: ${errorMessage}`;
      aiFeedbackArea.style.display = "block";
    }
  } catch (error) {
    console.error("API 통신 오류:", error);
    alert("서버와 통신 중 오류가 발생했습니다.");
    showLoading(false); // 로딩 오버레이 숨김
    aiFeedbackContent.textContent = `오류: ${error.message}`;
    aiFeedbackArea.style.display = "block";
  }
}

/**
 * 포트폴리오 폼 제출을 처리합니다.
 * @param {Event} e - 제출 이벤트.
 */
async function handlePortfolioFormSubmit(e) {
  e.preventDefault();
  const pdfInput = document.querySelector('input[name="portfolio_pdf"]');
  const linkInput = document.querySelector('input[name="portfolio_link"]');
  const formData = new FormData();
  formData.append("job_title", jobTitle);
  if (pdfInput.files.length > 0) {
    formData.append("portfolio_pdf", pdfInput.files[0]);
  }
  if (linkInput.value.trim()) {
    formData.append("portfolio_link", linkInput.value.trim());
  }
  // 현재 입력된 링크 값도 documentData에 저장 (PDF는 직접 저장하지 않음)
  if (currentDocType && currentDocVersion !== undefined) {
    const versionToUpdate = documentData[currentDocType].find(
      (d) => d.version === currentDocVersion
    );
    if (versionToUpdate) {
      versionToUpdate.content = {
        portfolio_link: linkInput.value.trim(),
      };
    }
  }

  if (formData.has("portfolio_pdf") || formData.get("portfolio_link")) {
    showLoading(true, "포트폴리오 요약 및 PDF 생성 중..."); // 로딩 표시
    try {
      const response = await fetch("/api/portfolio_summary", {
        method: "POST",
        body: formData,
      });
      showLoading(false); // 로딩 숨김
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "portfolio_summary.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert("요약 PDF가 다운로드되었습니다.");
      } else {
        const result = await response.json();
        alert(result.error || "요약 실패");
      }
    } catch (err) {
      showLoading(false); // 로딩 숨김
      alert("서버 오류: " + err);
    }
  } else {
    alert("PDF 파일을 업로드하거나 링크를 입력하세요.");
  }
}

/**
 * 다이어그램 그리기 함수 (수정됨)
 */
function drawDiagram() {
  const diagramContainer = document.getElementById("document-diagram");
  diagramContainer.innerHTML = ""; // 다이어그램 전체를 비우고 새로 그립니다.

  // 1. 직무 노드 추가
  const jobNode = document.createElement("div");
  jobNode.className = "diagram-node job-node";
  jobNode.dataset.docType = "job";
  jobNode.textContent = jobTitle;
  diagramContainer.appendChild(jobNode);

  // 2. 각 문서 타입별 '레인'을 담을 컨테이너 생성 (수평 배치용)
  const documentLanesContainer = document.createElement("div");
  documentLanesContainer.className = "document-lanes-container";
  diagramContainer.appendChild(documentLanesContainer);

  // 3. 각 문서 타입(이력서, 자기소개서, 포트폴리오)별 '레인' 생성 및 노드 추가
  for (const docType in documentData) {
    const docLane = document.createElement("div");
    docLane.className = "document-lane";
    docLane.dataset.docType = docType;
    documentLanesContainer.appendChild(docLane); // 레인 컨테이너에 레인 추가

    // 해당 문서 타입의 전체 버전 수
    const totalVersions = documentData[docType].length;

    // 모든 버전을 순회하며 노드 생성
    for (let i = 0; i < totalVersions; i++) {
      const doc = documentData[docType][i];
      const nodeVersion = doc.version; // 0, 1, 2, ...

      const nodeVersionGroup = document.createElement("div");
      nodeVersionGroup.className = "node-version-group";

      const node = document.createElement("div");
      node.className = `diagram-node document-node v${nodeVersion}`; // 동적으로 vX 클래스 추가
      node.dataset.docType = docType;
      node.dataset.version = nodeVersion;
      node.dataset.koreanName = doc.koreanName;
      node.textContent = doc.displayContent;

      // 변경된 로직: 최신 버전이 아닌 모든 노드에 되돌리기 버튼 추가
      if (nodeVersion < totalVersions - 1) {
        // 최신 버전(totalVersions - 1)을 제외한 모든 이전 버전에 버튼 추가
        const rollbackButton = document.createElement("button");
        rollbackButton.className = "rollback-button";
        rollbackButton.textContent = `v${nodeVersion} 되돌리기`; // 버튼 텍스트에 되돌릴 버전 명시
        rollbackButton.dataset.docType = docType;
        rollbackButton.dataset.version = nodeVersion; // 해당 노드의 버전으로 되돌리도록 설정
        node.appendChild(rollbackButton);
      }

      nodeVersionGroup.appendChild(node);
      docLane.appendChild(nodeVersionGroup);
    }
  }
  setupNodeClickEvents(); // 새로 생성된 노드들에 이벤트 리스너 다시 설정
}

// 문서 되돌리기 함수 (선택된 버전으로 되돌림)
async function rollbackDocument(docType, versionToRollback) {
  const docName = documentData[docType][0]
    ? documentData[docType][0].koreanName
    : docType; // v0 노드의 한글 이름 사용

  if (
    confirm(`${docName}를 v${versionToRollback} 버전으로 되돌리시겠습니까?`)
  ) {
    // 1. 클라이언트 측 documentData 업데이트 (버전 잘라내기)
    documentData[docType] = documentData[docType].slice(
      0,
      versionToRollback + 1
    );

    // 2. 서버에 삭제 요청
    showLoading(true, "데이터베이스 롤백 중...");
    try {
      const response = await fetch(
        `/api/rollback_document/${docType}/${jobTitle
          .replace(/ /g, "-")
          .replace(/\//g, "-")
          .toLowerCase()}/${versionToRollback}`,
        {
          method: "DELETE",
        }
      );
      if (!response.ok) {
        const errorResult = await response.json();
        throw new Error(errorResult.detail || "서버 롤백 실패");
      }
      alert(`${docName}가 v${versionToRollback} 버전으로 되돌려졌습니다.`);
    } catch (error) {
      console.error("Rollback API error:", error);
      alert(`롤백 중 오류가 발생했습니다: ${error.message}`);
      // If DB rollback fails, client-side data might be inconsistent with DB.
      // For robustness, could reload from DB here or prompt user.
    } finally {
      showLoading(false);
    }

    currentDocVersion = versionToRollback; // 현재 활성 버전을 되돌린 버전으로 설정

    drawDiagram(); // 다이어그램 다시 그리기

    // 만약 현재 모달이 열려있고, 되돌려진 문서 타입과 같다면 모달 내용 업데이트
    if (editModal.style.display === "block" && currentDocType === docType) {
      const versionData = documentData[docType][versionToRollback]; // 되돌려진 버전의 데이터 다시 로드
      if (versionData) {
        fetch(
          `/api/document_schema/${currentDocType}?job_slug=${jobTitle
            .replace(/ /g, "-")
            .toLowerCase()}`
        )
          .then((res) => res.json())
          .then((schema) => renderFormFields(schema, versionData.content))
          .catch((error) =>
            console.error("Error fetching schema on rollback:", error)
          );
        aiFeedbackContent.textContent = versionData.feedback || "";
        aiFeedbackArea.style.display = versionData.feedback ? "block" : "none";
        modalTitle.textContent = `${versionData.koreanName} 편집 (v${versionData.version})`;
      } else {
        editModal.style.display = "none";
        alert("문서가 초기화되어 현재 편집 중인 내용이 없습니다.");
      }
    }
  }
}

/**
 * 로딩 오버레이를 표시하거나 숨깁니다.
 * @param {boolean} show - true면 표시, false면 숨김
 * @param {string} message - 로딩 메시지
 */
function showLoading(show, message = "처리 중...") {
  if (show) {
    loadingOverlay.style.display = "flex";
    loadingOverlay.querySelector("p").textContent = message;
  } else {
    loadingOverlay.style.display = "none";
  }
}

/**
 * 현재 폼 필드의 내용을 documentData에 임시 저장합니다.
 * 이 함수는 모달이 닫힐 때, 사용자가 "저장 및 분석" 버튼을 누르지 않은 경우에도
 * 현재 편집 중인 버전의 내용을 documentData에 반영하기 위해 사용됩니다.
 */
function saveCurrentFormContent() {
  if (
    !currentDocType ||
    currentDocVersion === undefined ||
    currentDocType === "portfolio"
  )
    return;

  const versionToUpdate = documentData[currentDocType].find(
    (d) => d.version === currentDocVersion
  );

  if (versionToUpdate) {
    const docContent = {};
    if (currentDocType === "cover_letter") {
      const motivationExpertise = document.querySelector(
        'textarea[name="motivation_expertise"]'
      );
      const collaborationExperience = document.querySelector(
        'textarea[name="collaboration_experience"]'
      );
      if (motivationExpertise)
        docContent.motivation_expertise = motivationExpertise.value;
      if (collaborationExperience)
        docContent.collaboration_experience = collaborationExperience.value;
    } else {
      const textareas = formFields.querySelectorAll("textarea");
      const inputs = formFields.querySelectorAll('input:not([type="file"])');

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

// 3. 초기 로딩 시 데이터 설정 및 이벤트 리스너 설정
document.addEventListener("DOMContentLoaded", async () => {
  jobTitle = document.body.dataset.jobTitle;
  const jobSlug = jobTitle.replace(/ /g, "-").replace(/\//g, "-").toLowerCase();

  try {
    showLoading(true, "문서 데이터 로딩 중...");
    const response = await fetch(`/api/load_documents/${jobSlug}`);
    if (response.ok) {
      const loadedData = await response.json();

      // Initialize documentData structure
      documentData = {
        resume: [],
        cover_letter: [],
        portfolio: [],
      };

      // Helper to process loaded documents for a given document type
      const processLoadedDocs = (docType, loadedDocs) => {
        const koreanName =
          docType === "resume"
            ? "이력서"
            : docType === "cover_letter"
            ? "자기소개서"
            : "";
        if (loadedDocs && loadedDocs.length > 0) {
          // If loaded docs do not start with version 0, prepend an empty v0 locally
          if (loadedDocs[0].version > 0) {
            documentData[docType].push({
              version: 0,
              content: {},
              displayContent: `${koreanName} (v0)`,
              koreanName: koreanName,
              feedback: "",
            });
          }
          // Append all loaded versions from DB
          loadedDocs.forEach((doc) => {
            documentData[docType].push({
              ...doc, // spread operator to copy all properties
              koreanName: koreanName, // ensure koreanName is set
              displayContent: `${koreanName} (v${doc.version})`, // ensure displayContent is set
            });
          });
        } else {
          // If no documents loaded from DB, initialize with an empty v0
          documentData[docType].push({
            version: 0,
            content: {},
            displayContent: `${koreanName} (v0)`,
            koreanName: koreanName,
            feedback: "",
          });
        }
      };

      // Process resume and cover_letter data
      processLoadedDocs("resume", loadedData.resume);
      processLoadedDocs("cover_letter", loadedData.cover_letter);

      // Initialize portfolio as it's not managed in DB for this task, always start with v0
      documentData.portfolio.push({
        version: 0,
        content: {},
        displayContent: "포트폴리오 (v0)",
        koreanName: "포트폴리오",
        feedback: "",
      });
    } else {
      console.error("Failed to load documents from DB:", await response.text());
      // Fallback to initial v0 for all if loading fails entirely
      initializeDefaultDocumentData(); // This function already creates empty v0 for all types
    }
  } catch (error) {
    console.error("Error fetching documents on load:", error);
    // Fallback to initial v0 for all if fetching fails entirely
    initializeDefaultDocumentData(); // This function already creates empty v0 for all types
  } finally {
    showLoading(false);
  }

  drawDiagram(); // 초기 다이어그램 그리기

  // 팝업창 닫기 버튼 클릭 이벤트
  document.querySelector(".close-button").onclick = () => {
    saveCurrentFormContent(); // 닫기 전에 현재 내용 저장
    editModal.style.display = "none";
    aiFeedbackContent.textContent = "";
    aiFeedbackArea.style.display = "none";
  };

  // 모달 외부 클릭 시 닫기 이벤트
  window.onclick = (event) => {
    if (event.target == editModal) {
      saveCurrentFormContent(); // 닫기 전에 현재 내용 저장
      editModal.style.display = "none";
      aiFeedbackContent.textContent = "";
      aiFeedbackArea.style.display = "none";
    }
  };
});
