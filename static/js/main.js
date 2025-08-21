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

// ------------------------------
// 공통: API 베이스 & 토큰/Fetch
// ------------------------------
const ROOT_PREFIX = window.location.pathname.startsWith("/text") ? "/text" : "";
const API_BASE = `${ROOT_PREFIX}/apiText`;

function isJWT(t) {
  return (
    typeof t === "string" &&
    /^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$/.test(t)
  );
}
function getToken() {
  const s = sessionStorage.getItem("token");
  const l = localStorage.getItem("token");
  const t = s || l || "";
  return isJWT(t) ? t : "";
}
async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  // url이 절대경로가 아니라면 API_BASE 붙이기
  const fullUrl = url.startsWith("http")
    ? url
    : url.startsWith("/apiText/")
    ? `${ROOT_PREFIX}${url}`
    : `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
  return fetch(fullUrl, { ...options, headers });
}

// 스토리지의 토큰이 바뀌면 전체 새로고침(SSO 동기화)
window.addEventListener("storage", (e) => {
  if (e.key === "token") location.reload();
});

// ------------------------------
// 앱 시작
// ------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  setJobTitle(document.body.dataset.jobTitle);
  const jobSlug = jobTitle.replace(/ /g, "-").replace(/\//g, "-").toLowerCase();

  try {
    showLoading(true, "문서 데이터 로딩 중...");

    // 사용자별 저장 문서 로드
    const response = await apiFetch(`/load_documents/${jobSlug}`);
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
      const txt = await response.text();
      console.warn("문서 로드 실패(인증 없음/무효 가능):", txt);
      initializeDefaultDocumentData();
    }
  } catch (error) {
    console.error("문서 초기 로딩 오류:", error);
    initializeDefaultDocumentData();
  } finally {
    showLoading(false);
  }

  drawDiagram();

  // 팝업창 닫기 버튼
  document.querySelector(".close-button").onclick = () => {
    closeEditModal();
  };

  // 모달 외부 클릭 시 닫기
  window.onclick = (event) => {
    const editModal = document.getElementById("edit-modal");
    const companyModalEl = document.getElementById("company-modal");
    if (event.target == editModal) closeEditModal();
    if (event.target == companyModalEl) companyModalEl.style.display = "none";
  };

  // 마지막 기업 분석 로드 (있으면 표시)
  try {
    const lastAnalysisResponse = await apiFetch(`/load_last_company_analysis`);
    if (lastAnalysisResponse.ok) {
      const lastAnalysis = await lastAnalysisResponse.json();
      if (lastAnalysis && lastAnalysis.company_name) {
        companyNameInput.value = lastAnalysis.company_name;
        renderCompanyAnalysis(lastAnalysis);
        document.getElementById("company-analysis-area").style.display = "block";
      }
    } else {
      console.warn("이전에 분석한 기업 데이터가 없습니다.");
    }
  } catch (error) {
    console.error("마지막 기업 분석 데이터 로딩 오류:", error);
  }

  // 기업 분석 버튼
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
      const response = await apiFetch(`/analyze_company`, {
        method: "POST",
        body: JSON.stringify({ company_name: companyName }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "기업 분석에 실패했습니다.");
      }

      const result = await response.json();
      const companyAnalysis = result.company_analysis || result;

      renderCompanyAnalysis(companyAnalysis);
      document.getElementById("company-analysis-area").style.display = "block";
    } catch (error) {
      alert(`기업 분석 중 오류가 발생했습니다: ${error.message}`);
      document.getElementById("company-analysis-area").style.display = "none";
    } finally {
      showLoading(false, null, companyLoadingOverlay, companyLoadingMessage);
    }
  });

  // 기업 분석 렌더링
  function renderCompanyAnalysis(analysisData) {
    const koreanTitles = {
      company_summary: "기업 개요",
      key_values: "핵심 가치",
      competencies_to_highlight: "강조할 역량",
      interview_tips: "면접 팁",
    };

    companyAnalysisText.innerHTML = "";

    if (!analysisData || Object.keys(analysisData).length === 0) {
      companyAnalysisText.textContent = "분석 결과가 없습니다.";
      return;
    }

    for (const key in analysisData) {
      if (!Object.prototype.hasOwnProperty.call(analysisData, key)) continue;

      const value = analysisData[key];
      const displayTitle = koreanTitles[key] || key;

      const analysisSection = document.createElement("div");
      analysisSection.className = "analysis-section";

      const titleElement = document.createElement("h4");
      titleElement.textContent = displayTitle;
      analysisSection.appendChild(titleElement);

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
});
