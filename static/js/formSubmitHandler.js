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
  setCurrentDocInfo,
} from "./documentData.js";
import { showLoading, setAiFeedback, setModalTitle } from "./uiHandler.js"; // setModalTitle은 uiHandler에서 가져옵니다.
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

    // 새 버전 번호 결정 (현재 버전 + 1)
    const newVersionNumber = documentData[currentDocType].length;

    const requestBody = {
      job_title: jobTitle,
      document_content: docContent,
      // 새로운 AI 분석 요청 시에는 항상 최신 버전을 기준으로 함
      version: newVersionNumber,
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
      // 새 버전이 생성될 경우 기존 데이터는 유지하고 새 버전에 결과 반영
      // 현재 버전 이후의 가지치기
      truncateDocumentVersions(currentDocType, currentDocVersion);

      // 새로운 버전 추가
      addNewDocumentVersion(
        currentDocType,
        newVersionNumber, // 새 버전 번호 전달
        docContent, // 사용자가 입력한 폼 데이터
        result.ai_feedback, // 백엔드로부터 받은 전체 피드백
        result.individual_feedbacks // ⭐️ 핵심: 백엔드로부터 받은 개별 피드백
      );

      // 현재 문서 정보 업데이트 (새로운 버전으로)
      setCurrentDocInfo(currentDocType, newVersionNumber);

      // 모달 제목 업데이트 (새로운 버전 번호 반영)
      const currentDocKoreanName = currentDocInArray
        ? currentDocInArray.koreanName
        : currentDocType;
      setModalTitle(`${currentDocKoreanName} 편집 (v${newVersionNumber})`);

      // AI 피드백 UI 업데이트
      setAiFeedback(
        result.ai_feedback, // overall_feedback
        result.individual_feedbacks, // individual_feedbacks
        currentDocType // 문서 타입 전달 (uiHandler에서 개별 피드백 렌더링에 사용)
      );

      drawDiagram(); // 다이어그램 다시 그리기 (새 버전 반영)
      alert("문서가 저장되고 분석되었습니다. AI 피드백을 확인하세요.");
    } else {
      const errorMessage = result.detail
        ? result.detail.map((d) => d.msg).join(", ")
        : result.error || "알 수 없는 오류";
      alert(`분석 실패: ${errorMessage}`);
      // 오류 발생 시에도 피드백 영역에 오류 메시지 표시
      setAiFeedback(errorMessage, {}, currentDocType);
    }
  } catch (error) {
    console.error("API 통신 오류:", error);
    alert("서버와 통신 중 오류가 발생했습니다.");
    showLoading(false);
    // 네트워크 오류 시에도 피드백 영역에 오류 메시지 표시
    setAiFeedback(`네트워크 오류: ${error.message}`, {}, currentDocType);
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
  // ⭐️ 포트폴리오는 파일 업로드/링크 입력 즉시 AI 분석을 요청하므로,
  // 폼 제출 시 항상 새로운 버전을 생성하거나, 기존 최신 버전을 업데이트하는 방식.
  // 여기서는 새로운 버전으로 처리하는 것을 고려.
  const newVersionNumber = documentData["portfolio"].length;
  // 이전 버전 자르기 (항상 최신 버전에서만 작업한다고 가정)
  truncateDocumentVersions("portfolio", currentDocVersion); // currentDocVersion이 현재 포트폴리오 버전을 가리키도록

  showLoading(true, "포트폴리오 요약 및 PDF 생성 중..."); // 로딩 표시
  try {
    const response = await fetch("/api/portfolio_summary", {
      method: "POST",
      body: formData,
    });
    showLoading(false); // 로딩 숨김

    const result = await response.json();

    if (response.ok) {
      // PDF 다운로드 처리 (기존 로직)
      if (result.download_url) {
        // 다운로드 URL이 blob이 아니라 실제 URL인 경우
        window.open(result.download_url, "_blank");
        alert("포트폴리오 요약이 완료되었습니다. PDF를 다운로드합니다.");
      } else if (result.pdf_content_base64) {
        // Base64 인코딩된 PDF 내용이 오는 경우 (Blob 변환)
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
        a.download = `portfolio_summary_v${newVersionNumber}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert("포트폴리오 요약 PDF가 다운로드되었습니다.");
      } else {
        alert("PDF 다운로드 정보가 없습니다.");
      }

      // 새 버전 데이터 추가 (포트폴리오 분석 결과 저장)
      addNewDocumentVersion(
        "portfolio",
        newVersionNumber,
        {
          portfolio_link: linkInput.value.trim(),
          file_name: pdfInput.files[0] ? pdfInput.files[0].name : "",
        }, // 포트폴리오 내용 (링크, 파일명)
        result.ai_summary || "요약 피드백 없음", // AI 요약 결과
        result.individual_feedbacks || {} // ⭐️ 핵심: 포트폴리오의 경우에도 개별 피드백 저장 (없을 경우 빈 객체)
      );

      // 현재 문서 정보 업데이트
      setCurrentDocInfo("portfolio", newVersionNumber);

      // 모달 제목 업데이트
      setModalTitle(`포트폴리오 편집 (v${newVersionNumber})`);

      // AI 피드백 UI 업데이트
      setAiFeedback(
        result.ai_summary || "요약 피드백 없음",
        result.individual_feedbacks || {},
        "portfolio"
      );
      drawDiagram();
    } else {
      const resultError = result.error || "알 수 없는 오류";
      alert(`요약 실패: ${resultError}`);
      setAiFeedback(`오류: ${resultError}`, {}, "portfolio"); // 오류 피드백도 표시
    }
  } catch (err) {
    showLoading(false); // 로딩 숨김
    console.error("서버 오류:", err);
    alert("포트폴리오 분석 중 서버 오류가 발생했습니다. " + err.message);
    setAiFeedback(`네트워크 오류: ${err.message}`, {}, "portfolio"); // 오류 피드백 표시
  }
}
