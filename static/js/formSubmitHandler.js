// static/js/formSubmitHandler.js
import { formFields, documentForm, companyNameInput } from "./domElements.js";
import {
  jobTitle,
  currentDocType,
  currentDocVersion,
  documentData,
  addNewDocumentVersion,
  truncateDocumentVersions,
  getDocumentVersionData,
  setCurrentDocInfo,
  updateExistingDocumentVersion,
} from "./documentData.js";
import { showLoading, setAiFeedback, setModalTitle } from "./uiHandler.js";
import { drawDiagram } from "./diagramRenderer.js";
import { renderFormFields } from "./formRenderer.js";

// 헬퍼 함수: 문서 타입에 대한 한글 이름을 가져옵니다.
function getKoreanNameForDisplay(docType) {
  switch (docType) {
    case "resume":
      return "이력서";
    case "cover_letter":
      return "자기소개서";
    case "portfolio":
      return "포트폴리오";
    default:
      return docType;
  }
}

/**
 * 일반 문서 (이력서, 자기소개서) 폼 제출을 처리합니다.
 * @param {Event} e - 제출 이벤트.
 */
export async function handleDocumentFormSubmit(e) {
  e.preventDefault();

  const docContent = {};
  let isValid = true;

  document.querySelectorAll(".error-message").forEach((el) => {
    el.style.display = "none";
  });

  const requiredFields = formFields.querySelectorAll("[required]");
  requiredFields.forEach((field) => {
    const fieldName = field.name || field.dataset.fieldName;
    if (!fieldName) {
      console.warn("Field missing name or data-field-name:", field);
      return;
    }

    if (field.closest(".array-field-container")) {
      const arrayContainer = field.closest(".array-field-container");
      const arrayFieldName = arrayContainer.dataset.arrayFieldName;
      if (!docContent[arrayFieldName]) {
        docContent[arrayFieldName] = [];
      }
      const itemValue = field.value.trim();
      if (itemValue) {
        docContent[arrayFieldName].push(itemValue);
      }

      if (itemValue === "" && field.hasAttribute("required")) {
        isValid = false;
        const errorMessageDiv = arrayContainer.querySelector(".error-message");
        if (errorMessageDiv) {
          errorMessageDiv.style.display = "block";
        }
      }
    } else {
      docContent[fieldName] = field.value.trim();
      if (field.value.trim() === "") {
        isValid = false;
        const errorMessageDiv =
          field.parentElement.querySelector(".error-message");
        if (errorMessageDiv) {
          errorMessageDiv.style.display = "block";
        }
      }
    }
  });

  if (!isValid) {
    const firstInvalidField = document.querySelector(
      ".error-message[style*='block']"
    );
    if (firstInvalidField) {
      firstInvalidField.previousElementSibling.focus();
      firstInvalidField.previousElementSibling.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
    alert("필수 입력 항목을 모두 채워주세요.");
    return;
  }

  showLoading(true, "AI 분석 중...");

  try {
    const feedbackReflection =
      document.getElementById("feedback-reflection-input")?.value || "";

    // 기업명 입력 필드에서 값을 가져옵니다.
    const companyName = companyNameInput.value.trim();

    const response = await fetch(`/api/analyze_document/${currentDocType}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_title: jobTitle,
        document_content: docContent,
        version: currentDocVersion,
        feedback_reflection: feedbackReflection,
        // 이 부분을 추가하여 기업명을 API 요청에 포함시킵니다.
        company_name: companyName,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      alert(`AI 분석 오류: ${result.error || response.statusText}`);
      setAiFeedback(result.error || "AI 분석 중 오류 발생", {}, currentDocType);
      showLoading(false);
      return;
    }

    const overallAiFeedback = result.ai_feedback || "";
    const individualAiFeedbacks = result.individual_feedbacks || {};
    const newEmbedding = result.new_version_data
      ? result.new_version_data.embedding
      : [];
    const newContentHash = result.new_version_data
      ? result.new_version_data.content_hash
      : "";

    updateExistingDocumentVersion(
      currentDocType,
      currentDocVersion,
      docContent,
      overallAiFeedback,
      individualAiFeedbacks,
      newEmbedding,
      newContentHash
    );

    truncateDocumentVersions(currentDocType, currentDocVersion);

    const nextVersionNumber = currentDocVersion + 1;

    addNewDocumentVersion(
      currentDocType,
      nextVersionNumber,
      docContent,
      overallAiFeedback,
      individualAiFeedbacks,
      newEmbedding,
      newContentHash
    );

    setCurrentDocInfo(currentDocType, nextVersionNumber);

    drawDiagram();

    const schemaResponse = await fetch(
      "/api/document_schema/" +
        currentDocType +
        "?job_slug=" +
        jobTitle.replace(/ /g, "-").replace(/\//g, "-").toLowerCase()
    );
    const schema = await schemaResponse.json();

    renderFormFields(schema, docContent);

    setModalTitle(
      `${getKoreanNameForDisplay(currentDocType)} (v${nextVersionNumber})`
    );
    setAiFeedback(overallAiFeedback, individualAiFeedbacks, currentDocType);

    document.getElementById("edit-modal").style.display = "block";

    alert("문서가 성공적으로 분석되고 다음 버전이 생성되었습니다!");
  } catch (error) {
    console.error("문서 제출 중 오류 발생:", error);
    alert("문서 분석 및 저장 중 오류가 발생했습니다.");
    setAiFeedback(`오류: ${error.message}`, {}, currentDocType);
  } finally {
    showLoading(false);
  }
}

/**
 * 포트폴리오 폼 제출을 처리합니다.
 */
export async function handlePortfolioFormSubmit(e) {
  e.preventDefault();
  const pdfInput = document.querySelector('input[name="portfolio_pdf"]');
  const linkInput = document.querySelector('input[name="portfolio_link"]');
  const formData = new FormData();
  formData.append("job_title", jobTitle);

  // 포트폴리오 분석에도 기업명 정보를 추가합니다.
  const companyName = companyNameInput.value.trim();
  if (companyName) {
    formData.append("company_name", companyName);
  }

  let hasPortfolioContent = false;

  if (pdfInput.files.length > 0) {
    formData.append("portfolio_pdf", pdfInput.files[0]);
    hasPortfolioContent = true;
  }
  if (linkInput.value.trim()) {
    formData.append("portfolio_link", linkInput.value.trim());
    hasPortfolioContent = true;
  }

  if (!hasPortfolioContent) {
    alert("포트폴리오 PDF 파일을 업로드하거나 링크를 입력하세요.");
    return;
  }

  showLoading(true, "포트폴리오 요약 및 PDF 생성 중...");
  try {
    const response = await fetch("/api/portfolio_summary", {
      method: "POST",
      body: formData,
    });
    showLoading(false);

    const result = await response.json();

    if (response.ok) {
      if (result.download_url) {
        window.open(result.download_url, "_blank");
        alert("포트폴리오 요약이 완료되었습니다. PDF를 다운로드합니다.");
      } else if (result.pdf_content_base64) {
        const binaryString = atob(result.pdf_content_base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: "application/pdf" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const portfolioFileName = pdfInput.files[0]
          ? pdfInput.files[0].name.replace(/\.pdf$/, "")
          : "portfolio_summary";
        a.download = `${portfolioFileName}_summary_v${
          currentDocVersion + 1
        }.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert("포트폴리오 요약 PDF가 다운로드되었습니다.");
      } else {
        alert("PDF 다운로드 정보가 없습니다.");
      }

      const aiSummary = result.ai_summary || "";
      const individualFeedbacks = result.individual_feedbacks || {};
      const embedding = result.new_version_data
        ? result.new_version_data.embedding
        : [];
      const contentHash = result.new_version_data
        ? result.new_version_data.content_hash
        : "";

      updateExistingDocumentVersion(
        "portfolio",
        currentDocVersion,
        {
          portfolio_link: linkInput.value.trim(),
          file_name: pdfInput.files[0] ? pdfInput.files[0].name : "",
        },
        aiSummary,
        individualFeedbacks,
        embedding,
        contentHash
      );

      const nextPortfolioVersionNumber = currentDocVersion + 1;
      truncateDocumentVersions("portfolio", currentDocVersion);

      addNewDocumentVersion(
        "portfolio",
        nextPortfolioVersionNumber,
        {
          portfolio_link: linkInput.value.trim(),
          file_name: pdfInput.files[0] ? pdfInput.files[0].name : "",
        },
        aiSummary,
        individualFeedbacks,
        embedding,
        contentHash
      );

      setCurrentDocInfo("portfolio", nextPortfolioVersionNumber);

      setModalTitle(`포트폴리오 편집 (v${nextPortfolioVersionNumber})`);

      setAiFeedback(aiSummary, individualFeedbacks, "portfolio");
      drawDiagram();

      const nextPortDocVersionData = getDocumentVersionData(
        "portfolio",
        nextPortfolioVersionNumber
      );
      const schemaResponse = await fetch(
        "/api/document_schema/portfolio?job_slug=" +
          jobTitle.replace(/ /g, "-").replace(/\//g, "-").toLowerCase()
      );
      const schema = await schemaResponse.json();
      renderFormFields(schema, nextPortDocVersionData.content);
      document.getElementById("edit-modal").style.display = "block";

      alert("포트폴리오가 성공적으로 요약되고 다음 버전이 생성되었습니다.");
    } else {
      const resultError = result.error || "알 수 없는 오류";
      alert(`요약 실패: ${resultError}`);
      setAiFeedback(`오류: ${resultError}`, {}, "portfolio");
    }
  } catch (err) {
    showLoading(false);
    console.error("서버 오류:", err);
    alert("포트폴리오 분석 중 서버 오류가 발생했습니다. " + err.message);
    setAiFeedback(`네트워크 오류: ${err.message}`, {}, "portfolio");
  } finally {
    showLoading(false);
  }
}
