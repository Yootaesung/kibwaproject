// static/js/diagramRenderer.js
import {
  diagramContainer,
  editModal,
  companyModal,
  closeCompanyModalButton,
} from "./domElements.js";
import {
  jobTitle,
  documentData,
  currentDocType,
  currentDocVersion,
  setCurrentDocInfo,
  truncateDocumentVersions,
  getDocumentVersionData,
} from "./documentData.js";
import {
  showLoading,
  openEditModal,
  setAiFeedback,
  setModalTitle,
  openCompanyModal,
} from "./uiHandler.js";
import { renderFormFields } from "./formRenderer.js";

/**
 * 다이어그램 노드 클릭 이벤트를 설정합니다.
 */
export function setupNodeClickEvents() {
  // 롤백 버튼 이벤트 리스너
  document.querySelectorAll(".rollback-button").forEach((button) => {
    button.onclick = (e) => {
      e.stopPropagation();
      const docType = button.dataset.docType;
      const versionToRollback = parseInt(button.dataset.version, 10);
      rollbackDocument(docType, versionToRollback);
    };
  });

  document.querySelectorAll(".diagram-node").forEach((node) => {
    node.onclick = async (e) => {
      const clickedNode = e.target.closest(".diagram-node");
      const docType = clickedNode.dataset.docType;

      if (docType === "company") {
        openCompanyModal();
        return;
      }

      if (!clickedNode.classList.contains("document-node")) {
        return;
      }

      const version = parseInt(clickedNode.dataset.version, 10);
      setCurrentDocInfo(docType, version);

      try {
        showLoading(true, "문서 스키마 로딩 중...");
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
            editModal.style.display = "none";
            return null;
          });

        if (!formSchema) {
          showLoading(false);
          return;
        }

        const docContent =
          getDocumentVersionData(docType, version)?.content || {};
        const savedFeedback =
          getDocumentVersionData(docType, version)?.feedback || "";
        const individualFeedbacks =
          getDocumentVersionData(docType, version)?.individual_feedbacks || {};

        renderFormFields(formSchema, docContent);
        setModalTitle(`${clickedNode.dataset.koreanName} 편집 (v${version})`);
        openEditModal(
          `${clickedNode.dataset.koreanName} 편집 (v${version})`,
          savedFeedback,
          individualFeedbacks,
          docType
        );
      } catch (error) {
        console.error("An error occurred during node click event:", error);
        alert("문서 편집기를 여는 중 오류가 발생했습니다. 콘솔을 확인하세요.");
        editModal.style.display = "none";
      } finally {
        showLoading(false);
      }
    };
  });
}

/**
 * 다이어그램 그리기 함수 (수정됨)
 */
export function drawDiagram() {
  diagramContainer.innerHTML = "";

  const jobNode = document.createElement("div");
  jobNode.className = "diagram-node company-node";
  jobNode.dataset.docType = "company";
  jobNode.dataset.koreanName = "기업";
  jobNode.textContent = "기업";
  diagramContainer.appendChild(jobNode);

  const documentLanesContainer = document.createElement("div");
  documentLanesContainer.className = "document-lanes-container";
  diagramContainer.appendChild(documentLanesContainer);

  for (const docType in documentData) {
    const docLane = document.createElement("div");
    docLane.className = "document-lane";
    docLane.dataset.docType = docType;
    documentLanesContainer.appendChild(docLane);

    const totalVersions = documentData[docType].length;

    for (let i = 0; i < totalVersions; i++) {
      const doc = documentData[docType][i];
      const nodeVersion = doc.version;
      const nodeVersionGroup = document.createElement("div");
      nodeVersionGroup.className = "node-version-group";

      const node = document.createElement("div");
      node.className = `diagram-node document-node v${nodeVersion}`;
      node.dataset.docType = docType;
      node.dataset.version = nodeVersion;
      node.dataset.koreanName = doc.koreanName;
      node.textContent = doc.displayContent;

      if (nodeVersion < totalVersions - 1) {
        const rollbackButton = document.createElement("button");
        rollbackButton.className = "rollback-button";
        rollbackButton.textContent = `v${nodeVersion} 되돌리기`;
        rollbackButton.dataset.docType = docType;
        rollbackButton.dataset.version = nodeVersion;
        node.appendChild(rollbackButton);
      }

      node.querySelector(".rollback-button")?.addEventListener("click", (e) => {
        e.stopPropagation();
      });

      nodeVersionGroup.appendChild(node);
      docLane.appendChild(nodeVersionGroup);
    }
  }

  if (closeCompanyModalButton) {
    closeCompanyModalButton.onclick = () => {
      companyModal.style.display = "none";
    };
  }

  setupNodeClickEvents();
}

function getKoreanNameForDisplay(docType) {
  switch (docType) {
    case "resume":
      return "이력서";
    case "cover_letter":
      return "자기소개서";
    case "portfolio":
      return "포트폴리오";
    case "company":
      return "기업";
    default:
      return docType;
  }
}

// rollbackDocument 함수는 변경사항이 없으므로, 원본 그대로 유지됩니다.

// 문서 되돌리기 함수 (선택된 버전으로 되돌림)
export async function rollbackDocument(docType, versionToRollback) {
  const docName = documentData[docType][0]
    ? documentData[docType][0].koreanName
    : docType; // v0 노드의 한글 이름 사용

  if (
    confirm(`${docName}를 v${versionToRollback} 버전으로 되돌리시겠습니까?`)
  ) {
    // 1. 클라이언트 측 documentData 업데이트 (버전 잘라내기)
    truncateDocumentVersions(docType, versionToRollback);

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

    setCurrentDocInfo(docType, versionToRollback);

    drawDiagram(); // 다이어그램 다시 그리기

    // 만약 현재 모달이 열려있고, 되돌려진 문서 타입과 같다면 모달 내용 업데이트
    if (editModal.style.display === "block" && currentDocType === docType) {
      const versionData = getDocumentVersionData(docType, versionToRollback); // 되돌려진 버전의 데이터 다시 로드
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
        // ⭐️ setAiFeedback 호출 시 개별 피드백과 문서 타입도 함께 전달
        setAiFeedback(
          versionData.feedback || "",
          versionData.individual_feedbacks || {}, // ⭐️ 개별 피드백 전달
          docType // ⭐️ 문서 타입 전달
        );
        setModalTitle(
          `${versionData.koreanName} 편집 (v${versionData.version})`
        );
      } else {
        editModal.style.display = "none";
        alert("문서가 초기화되어 현재 편집 중인 내용이 없습니다.");
      }
    }
  }
}
