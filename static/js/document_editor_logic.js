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

// 2. 모든 함수 정의

/**
 * 다이어그램 노드 클릭 이벤트를 설정합니다.
 */
function setupNodeClickEvents() {
  // 롤백 버튼 이벤트 리스너 (기존 로직 유지)
  document.querySelectorAll(".rollback-button").forEach((button) => {
    button.onclick = (e) => {
      const docType = button.dataset.docType;
      const versionToRollback = parseInt(button.dataset.version, 10);
      rollbackDocument(docType, versionToRollack);
    };
  });

  document.querySelectorAll(".diagram-node.document-node").forEach((node) => {
    node.onclick = async (e) => {
      const clickedNode = e.target.closest(".document-node");
      currentDocType = clickedNode.dataset.docType;
      currentDocVersion = parseInt(clickedNode.dataset.version, 10);
      const currentDocTitle = clickedNode.dataset.koreanName;

      modalTitle.textContent = `${currentDocTitle} 편집 (v${currentDocVersion})`;

      // 팝업을 열 때 해당 버전의 데이터를 불러옴
      const versionData = documentData[currentDocType].find(
        (d) => d.version === currentDocVersion
      );
      const docContent = versionData.content;
      const savedFeedback = versionData.feedback; // 이전 버전의 피드백

      try {
        const formSchema = await fetch(
          `/api/job_schema/${currentDocType}?job_slug=${jobTitle
            .replace(/ /g, "-")
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

  if (schema.korean_name === "포트폴리오") {
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
  } else if (schema.korean_name === "자기소개서") {
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
                    <input type="text" name="${field.name}" value="${
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
  const docContent = {};

  for (let [key, value] of formData.entries()) {
    // portfolio_pdf는 다른 핸들러에서 처리되므로 여기서는 제외
    if (key !== "portfolio_pdf") {
      docContent[key] = value;
    }
  }

  // **** 이 부분에 유효성 검사 로직 추가 또는 강화 ****
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
    return; // 내용이 없으면 여기서 함수 종료
  }
  // *************************************************

  try {
    const analysisData = {
      job_title: jobTitle,
      document_content: docContent,
      current_version: currentDocVersion,
    };

    loadingOverlay.style.display = "flex";
    formFields.style.display = "none";

    const response = await fetch(`/api/analyze_document/${currentDocType}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(analysisData),
    });
    const result = await response.json();

    loadingOverlay.style.display = "none";
    formFields.style.display = "block";

    if (response.ok) {
      aiFeedbackContent.textContent = result.feedback;
      aiFeedbackArea.style.display = "block";

      const versionToUpdate = documentData[currentDocType].find(
        (d) => d.version === currentDocVersion
      );
      if (versionToUpdate) {
        versionToUpdate.content = docContent; // 기존 버전 업데이트
        versionToUpdate.feedback = result.feedback; // 피드백도 함께 저장
      }

      drawDiagram();
      alert("문서가 저장되고 분석되었습니다. AI 피드백을 확인하세요.");
    } else {
      // 서버에서 422 오류 메시지를 더 상세하게 보내줄 경우 처리
      const errorMessage = result.detail
        ? result.detail.map((d) => d.msg).join(", ")
        : result.error || "알 수 없는 오류";
      alert(`분석 실패: ${errorMessage}`);
    }
  } catch (error) {
    console.error("API 통신 오류:", error);
    alert("서버와 통신 중 오류가 발생했습니다.");
    loadingOverlay.style.display = "none";
    formFields.style.display = "block";
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
  // 현재 입력된 링크 값도 documentData에 저장
  if (currentDocType && currentDocVersion !== undefined) {
    const versionToUpdate = documentData[currentDocType].find(
      (d) => d.version === currentDocVersion
    );
    if (versionToUpdate) {
      versionToUpdate.content = { portfolio_link: linkInput.value.trim() };
    }
  }

  if (formData.has("portfolio_pdf") || formData.get("portfolio_link")) {
    loadingOverlay.style.display = "flex";
    try {
      const response = await fetch("/api/portfolio_summary", {
        method: "POST",
        body: formData,
      });
      loadingOverlay.style.display = "none";
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
      loadingOverlay.style.display = "none";
      alert("서버 오류: " + err);
    }
  } else {
    alert("PDF 파일을 업로드하거나 링크를 입력하세요.");
  }
}

// 다이어그램 그리기 함수
function drawDiagram() {
  const diagramContainer = document.getElementById("document-diagram");
  diagramContainer.innerHTML = `
        <div class="diagram-node job-node" data-doc-type="job">${jobTitle}</div>
        <div class="initial-documents">
            <div class="diagram-node document-node" data-doc-type="resume" data-version="0" data-korean-name="이력서">이력서</div>
            <div class="diagram-node document-node" data-doc-type="cover_letter" data-version="0" data-korean-name="자기소개서">자기소개서</div>
            <div class="diagram-node document-node" data-doc-type="portfolio" data-version="0" data-korean-name="포트폴리오">포트폴리오</div>
        </div>
    `;

  for (const docType in documentData) {
    for (let i = 1; i < documentData[docType].length; i++) {
      const doc = documentData[docType][i];
      const parentElement = diagramContainer.querySelector(
        `.diagram-node[data-doc-type="${docType}"][data-version="${
          doc.version - 1
        }"]`
      );

      if (parentElement) {
        const nodeContainer = document.createElement("div");
        nodeContainer.className = "document-node-container";

        const node = document.createElement("div");
        node.className = "diagram-node document-node";
        node.dataset.docType = docType;
        node.dataset.version = doc.version;
        node.dataset.koreanName = doc.koreanName;
        node.textContent = doc.displayContent;

        const rollbackButton = document.createElement("button");
        rollbackButton.className = "rollback-button";
        rollbackButton.textContent = "되돌리기";
        rollbackButton.dataset.docType = docType;
        rollbackButton.dataset.version = doc.version;

        nodeContainer.appendChild(node);
        nodeContainer.appendChild(rollbackButton);

        diagramContainer.appendChild(nodeContainer);
      }
    }
  }
  setupNodeClickEvents();
}

// 문서 되돌리기 함수
function rollbackDocument(docType, versionToRollback) {
  if (
    confirm(
      `${documentData[docType][0].koreanName}를 v${versionToRollback}으로 되돌리시겠습니까?`
    )
  ) {
    documentData[docType] = documentData[docType].slice(
      0,
      versionToRollback + 1
    );

    currentDocVersion = versionToRollback;

    drawDiagram();

    if (editModal.style.display === "block" && currentDocType === docType) {
      const versionData = documentData[docType].find(
        (d) => d.version === currentDocVersion
      );
      fetch(
        `/api/job_schema/${currentDocType}?job_slug=${jobTitle
          .replace(/ /g, "-")
          .toLowerCase()}`
      )
        .then((res) => res.json())
        .then((schema) => renderFormFields(schema, versionData.content));
      aiFeedbackContent.textContent = versionData.feedback || "";
      aiFeedbackArea.style.display = versionData.feedback ? "block" : "none";
      modalTitle.textContent = `${versionData.koreanName} 편집 (v${versionData.version})`;
    }
    alert(
      `${documentData[docType][0].koreanName}가 v${versionToRollback}으로 되돌려졌습니다.`
    );
  }
}

/**
 * 현재 폼 필드의 내용을 documentData에 임시 저장합니다.
 */
function saveCurrentFormContent() {
  if (!currentDocType || currentDocVersion === undefined) return; // 현재 편집 중인 문서가 없으면 저장하지 않음

  const versionToUpdate = documentData[currentDocType].find(
    (d) => d.version === currentDocVersion
  );

  if (versionToUpdate) {
    const docContent = {};
    if (currentDocType === "portfolio") {
      const linkInput = document.querySelector('input[name="portfolio_link"]');
      if (linkInput) {
        docContent.portfolio_link = linkInput.value.trim();
      }
      // PDF 파일은 Blob으로 저장하기 어려우므로, 링크만 유지
    } else if (currentDocType === "cover_letter") {
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
      // 이력서 등 일반 문서
      const formData = new FormData(documentForm);
      for (let [key, value] of formData.entries()) {
        if (key !== "portfolio_pdf") {
          // PDF 제외
          docContent[key] = value;
        }
      }
    }
    versionToUpdate.content = docContent;
  }
}

// 3. 초기 로딩 시 데이터 설정 및 이벤트 리스너 설정
document.addEventListener("DOMContentLoaded", () => {
  jobTitle = document.body.dataset.jobTitle;

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

  drawDiagram();

  // 팝업창 닫기 버튼 클릭 이벤트 수정
  document.querySelector(".close-button").onclick = () => {
    saveCurrentFormContent(); // 닫기 전에 현재 내용 저장
    editModal.style.display = "none";
    aiFeedbackContent.textContent = "";
    aiFeedbackArea.style.display = "none";
  };

  // 모달 외부 클릭 시 닫기 이벤트 수정
  window.onclick = (event) => {
    if (event.target == editModal) {
      saveCurrentFormContent(); // 닫기 전에 현재 내용 저장
      editModal.style.display = "none";
      aiFeedbackContent.textContent = "";
      aiFeedbackArea.style.display = "none";
    }
  };
});
