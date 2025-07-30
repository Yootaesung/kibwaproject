// static/js/main.js - 애플리케이션의 진입점
import {
  jobTitle,
  setJobTitle,
  initializeDefaultDocumentData,
  documentData,
  setCurrentDocInfo,
} from "./documentData.js";
import { showLoading, closeEditModal } from "./uiHandler.js";
import { drawDiagram } from "./diagramRenderer.js";

// DOM이 완전히 로드되면 실행됩니다.
document.addEventListener("DOMContentLoaded", async () => {
  setJobTitle(document.body.dataset.jobTitle);
  const jobSlug = jobTitle.replace(/ /g, "-").replace(/\//g, "-").toLowerCase();

  try {
    showLoading(true, "문서 데이터 로딩 중...");
    const response = await fetch(`/api/load_documents/${jobSlug}`);
    if (response.ok) {
      const loadedData = await response.json();

      // Initialize documentData structure
      documentData.resume = []; // 기존 documentData 객체를 재할당하지 않고 속성만 초기화
      documentData.cover_letter = [];
      documentData.portfolio = [];

      // Helper to process loaded documents for a given document type
      const processLoadedDocs = (docType, loadedDocs) => {
        const koreanName =
          docType === "resume"
            ? "이력서"
            : docType === "cover_letter"
            ? "자기소개서"
            : "포트폴리오"; // Added portfolio to koreanName logic
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
      processLoadedDocs("portfolio", loadedData.portfolio);
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
    closeEditModal();
  };

  // 모달 외부 클릭 시 닫기 이벤트
  window.onclick = (event) => {
    const editModal = document.getElementById("edit-modal"); // domElements에서 가져와도 됨
    if (event.target == editModal) {
      closeEditModal();
    }
  };
});
