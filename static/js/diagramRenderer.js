// static/js/diagramRenderer.js
import { diagramContainer, editModal } from "./domElements.js";
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
} from "./uiHandler.js";
import { renderFormFields } from "./formRenderer.js";

/**
 * 다이어그램 노드 클릭 이벤트를 설정합니다.
 */
export function setupNodeClickEvents() {
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
      const docType = clickedNode.dataset.docType;
      const version = parseInt(clickedNode.dataset.version, 10);
      setCurrentDocInfo(docType, version);

      const currentDocKoreanName = clickedNode.dataset.koreanName;

      // 팝업을 열 때 해당 버전의 데이터를 불러옴
      const versionData = getDocumentVersionData(docType, version);
      const docContent = versionData.content;
      const savedFeedback = versionData.feedback; // 이전 버전의 피드백

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
            editModal.style.display = "none"; // Hide modal if schema fetch fails
            return null; // Return null to prevent further execution with invalid schema
          });

        if (!formSchema) {
          showLoading(false); // 로딩 숨김
          return; // Stop if schema fetch failed
        }

        console.log("Fetched Form Schema:", formSchema);

        renderFormFields(formSchema, docContent); // 불러온 데이터로 폼 필드 렌더링

        openEditModal(
          `${currentDocKoreanName} 편집 (v${currentDocVersion})`,
          savedFeedback
        );
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
 * 다이어그램 그리기 함수 (수정됨)
 */
export function drawDiagram() {
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
        setAiFeedback(versionData.feedback || "");
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
