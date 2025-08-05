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
import {
  companyModal,
  companyNameInput,
  analyzeCompanyButton,
  companyAnalysisText,
  companyLoadingOverlay,
  companyLoadingMessage,
} from "./domElements.js";

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
      documentData.resume = [];
      documentData.cover_letter = [];
      documentData.portfolio = [];

      // Helper to process loaded documents for a given document type
      const processLoadedDocs = (docType, loadedDocs) => {
        const koreanName =
          docType === "resume"
            ? "이력서"
            : docType === "cover_letter"
            ? "자기소개서"
            : "포트폴리오";
        if (loadedDocs && loadedDocs.length > 0) {
          if (loadedDocs[0].version > 0) {
            documentData[docType].push({
              version: 0,
              content: {},
              displayContent: `${koreanName} (v0)`,
              koreanName: koreanName,
              feedback: "",
            });
          }
          loadedDocs.forEach((doc) => {
            documentData[docType].push({
              ...doc,
              koreanName: koreanName,
              displayContent: `${koreanName} (v${doc.version})`,
            });
          });
        } else {
          documentData[docType].push({
            version: 0,
            content: {},
            displayContent: `${koreanName} (v0)`,
            koreanName: koreanName,
            feedback: "",
          });
        }
      };

      processLoadedDocs("resume", loadedData.resume);
      processLoadedDocs("cover_letter", loadedData.cover_letter);
      processLoadedDocs("portfolio", loadedData.portfolio);
    } else {
      console.error("Failed to load documents from DB:", await response.text());
      initializeDefaultDocumentData();
    }
  } catch (error) {
    console.error("Error fetching documents on load:", error);
    initializeDefaultDocumentData();
  } finally {
    showLoading(false);
  }

  drawDiagram();

  // 팝업창 닫기 버튼 클릭 이벤트
  document.querySelector(".close-button").onclick = () => {
    closeEditModal();
  };

  // 모달 외부 클릭 시 닫기 이벤트
  window.onclick = (event) => {
    const editModal = document.getElementById("edit-modal");
    const companyModal = document.getElementById("company-modal");
    if (event.target == editModal) {
      closeEditModal();
    }
    if (event.target == companyModal) {
      companyModal.style.display = "none";
    }
  };

  // 💖 [새로 추가된 부분]: 페이지 로드 시 마지막으로 분석한 기업 정보 로드
  try {
    const lastAnalysisResponse = await fetch("/api/load_last_company_analysis");
    if (lastAnalysisResponse.ok) {
      const lastAnalysis = await lastAnalysisResponse.json();
      // 데이터가 존재하고, 기업명이 있으면 화면에 표시
      if (lastAnalysis && lastAnalysis.company_name) {
        companyNameInput.value = lastAnalysis.company_name;
        renderCompanyAnalysis(lastAnalysis);
        document.getElementById("company-analysis-area").style.display =
          "block";
      }
    } else {
      console.warn("이전에 분석한 기업 데이터가 없습니다.");
    }
  } catch (error) {
    console.error("마지막 기업 분석 데이터를 불러오는 중 오류 발생:", error);
  }

  // 기업 분석 버튼 클릭 이벤트 리스너 추가
  analyzeCompanyButton.addEventListener("click", async () => {
    const companyName = companyNameInput.value.trim();
    if (!companyName) {
      alert("기업명을 입력해주세요.");
      return;
    }

    showLoading(
      true,
      "AI가 기업을 분석 중...",
      companyLoadingOverlay,
      companyLoadingMessage
    );

    try {
      const response = await fetch("/api/analyze_company", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_name: companyName,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "기업 분석에 실패했습니다.");
      }

      const result = await response.json();
      const companyAnalysis = result.company_analysis;

      // JSON 문자열 대신, 동적으로 HTML을 생성하여 표시
      renderCompanyAnalysis(companyAnalysis);

      // `companyAnalysisResult` 대신 `companyAnalysisArea`를 표시
      document.getElementById("company-analysis-area").style.display = "block";
    } catch (error) {
      alert(`기업 분석 중 오류가 발생했습니다: ${error.message}`);
      // `companyAnalysisResult` 대신 `companyAnalysisArea`를 숨김
      document.getElementById("company-analysis-area").style.display = "none";
    } finally {
      showLoading(false, null, companyLoadingOverlay, companyLoadingMessage);
    }
  });

  /**
   * AI 기업 분석 결과를 동적으로 생성하여 표시합니다.
   * @param {Object} analysisData - AI 분석 결과 JSON 객체.
   */
  function renderCompanyAnalysis(analysisData) {
    // JSON 키를 한국어 제목으로 매핑하는 객체
    const koreanTitles = {
      company_summary: "기업 개요",
      key_values: "핵심 가치",
      competencies_to_highlight: "강조할 역량",
      interview_tips: "면접 팁",
    };

    // 기존 내용을 지우고 새로운 내용을 추가할 준비
    companyAnalysisText.innerHTML = "";

    if (!analysisData || Object.keys(analysisData).length === 0) {
      companyAnalysisText.textContent = "분석 결과가 없습니다.";
      return;
    }

    // 각 항목을 순회하며 HTML을 생성
    for (const key in analysisData) {
      if (Object.prototype.hasOwnProperty.call(analysisData, key)) {
        const value = analysisData[key];
        const displayTitle = koreanTitles[key] || key; // 매핑된 한국어 제목 사용

        const analysisSection = document.createElement("div");
        analysisSection.className = "analysis-section";

        const titleElement = document.createElement("h4");
        titleElement.textContent = displayTitle;
        analysisSection.appendChild(titleElement);

        // 'competencies_to_highlight'는 배열이므로 별도로 처리
        if (key === "competencies_to_highlight" && Array.isArray(value)) {
          const listElement = document.createElement("ul");
          value.forEach((item) => {
            const listItem = document.createElement("li");
            listItem.textContent = item;
            listElement.appendChild(listItem);
          });
          analysisSection.appendChild(listElement);
        } else {
          const contentElement = document.createElement("p");
          contentElement.textContent = value;
          analysisSection.appendChild(contentElement);
        }

        companyAnalysisText.appendChild(analysisSection);
      }
    }
  }
});
