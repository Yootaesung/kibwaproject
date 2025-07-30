// static/js/formSubmitHandler.js
import { formFields, documentForm } from "./domElements.js";
import {
  jobTitle,
  currentDocType,
  currentDocVersion, // currentDocVersion은 여기서 읽기 전용으로 사용
  documentData,
  addNewDocumentVersion,
  truncateDocumentVersions,
  getDocumentVersionData,
  setCurrentDocInfo, // <-- setCurrentDocInfo 함수 임포트
} from "./documentData.js";
import { showLoading, setAiFeedback, setModalTitle } from "./uiHandler.js";
import { drawDiagram } from "./diagramRenderer.js";

/**
 * 일반 문서 (이력서, 자기소개서) 폼 제출을 처리합니다.
 * @param {Event} e - 제출 이벤트.
 */
export async function handleDocumentFormSubmit(e) {
  e.preventDefault();

  const formData = new FormData(documentForm);
  const docContent = {}; // 사용자가 현재 폼에서 입력한 내용
  let isValid = true; // 유효성 검사 플래그

  // 기존 오류 메시지 모두 숨기기
  document.querySelectorAll(".error-message").forEach((el) => {
    el.style.display = "none";
  });

  // 모든 required 필드에 대한 유효성 검사 및 docContent 구성
  const requiredFields = formFields.querySelectorAll("[required]");
  requiredFields.forEach((field) => {
    if (
      field.tagName === "TEXTAREA" ||
      field.type === "text" ||
      field.type === "date"
    ) {
      docContent[field.name] = field.value.trim();
      if (field.value.trim() === "") {
        isValid = false;
        const errorMessageDiv =
          field.parentElement.querySelector(".error-message");
        if (errorMessageDiv) {
          errorMessageDiv.style.display = "block";
        }
      }
    } else {
      docContent[field.name] = field.value;
      if (field.value === "") {
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
    ).previousElementSibling;
    if (firstInvalidField) {
      firstInvalidField.focus();
      firstInvalidField.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
    alert("필수 입력 항목을 모두 채워주세요.");
    return;
  }

  try {
    const currentDocInArray = getDocumentVersionData(
      currentDocType,
      currentDocVersion
    );

    const requestBody = {
      job_title: jobTitle,
      document_content: docContent,
      version: currentDocVersion,
    };

    showLoading(true, "AI 분석 중...");

    const response = await fetch(`/api/analyze_document/${currentDocType}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });
    const result = await response.json();

    showLoading(false);

    if (response.ok) {
      if (currentDocInArray) {
        currentDocInArray.content = docContent;
        currentDocInArray.feedback = result.feedback;
      }

      if (currentDocVersion < documentData[currentDocType].length - 1) {
        truncateDocumentVersions(currentDocType, currentDocVersion);
      }

      const newVersionNumberForPush = documentData[currentDocType].length;

      const newDocForNextVersion = {
        version: newVersionNumberForPush,
        content: { ...currentDocInArray.content },
        displayContent: `${currentDocInArray.koreanName} (v${newVersionNumberForPush})`,
        koreanName: currentDocInArray.koreanName,
        feedback: currentDocInArray.feedback,
      };

      addNewDocumentVersion(currentDocType, newDocForNextVersion);

      // ⭐️ 수정된 부분: currentDocVersion에 직접 재할당하는 대신 setCurrentDocInfo 사용 ⭐️
      setCurrentDocInfo(currentDocType, newVersionNumberForPush); // <-- 여기를 수정했습니다.

      setModalTitle(
        `${currentDocInArray.koreanName} 편집 (v${newVersionNumberForPush})` // 새로운 버전 번호 사용
      );
      setAiFeedback(result.feedback);

      drawDiagram();
      alert("문서가 저장되고 분석되었습니다. AI 피드백을 확인하세요.");
    } else {
      const errorMessage = result.detail
        ? result.detail.map((d) => d.msg).join(", ")
        : result.error || "알 수 없는 오류";
      alert(`분석 실패: ${errorMessage}`);
      setAiFeedback(`오류: ${errorMessage}`);
    }
  } catch (error) {
    console.error("API 통신 오류:", error);
    alert("서버와 통신 중 오류가 발생했습니다.");
    showLoading(false);
    setAiFeedback(`오류: ${error.message}`);
  }
}

/**
 * 포트폴리오 폼 제출을 처리합니다.
 * @param {Event} e - 제출 이벤트.
 */
export async function handlePortfolioFormSubmit(e) {
  e.preventDefault();
  const pdfInput = document.querySelector('input[name="portfolio_pdf"]');
  const linkInput = document.querySelector('input[name="portfolio_link"]');
  const formData = new FormData();
  formData.append("job_title", jobTitle);

  let hasPortfolioContent = false; // 포트폴리오 내용 존재 여부 플래그

  if (pdfInput.files.length > 0) {
    formData.append("portfolio_pdf", pdfInput.files[0]);
    hasPortfolioContent = true;
  }
  if (linkInput.value.trim()) {
    formData.append("portfolio_link", linkInput.value.trim());
    hasPortfolioContent = true;
  }

  // 필수 입력 검사
  if (!hasPortfolioContent) {
    alert("포트폴리오 PDF 파일을 업로드하거나 링크를 입력하세요.");
    return; // 내용이 없으면 제출 방지
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
}
