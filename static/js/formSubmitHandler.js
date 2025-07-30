// static/js/formSubmitHandler.js
import { formFields, documentForm } from "./domElements.js";
import {
  jobTitle,
  currentDocType,
  currentDocVersion,
  documentData, // documentData 직접 접근 (업데이트를 위해)
  updateDocumentData,
  addNewDocumentVersion,
  truncateDocumentVersions,
  getDocumentVersionData,
} from "./documentData.js";
import { showLoading, setAiFeedback, setModalTitle } from "./uiHandler.js";
import { drawDiagram, setupNodeClickEvents } from "./diagramRenderer.js"; // diagramRenderer에서 함수 임포트

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

  // 모든 required 필드에 대한 유효성 검사
  const requiredFields = formFields.querySelectorAll("[required]");
  requiredFields.forEach((field) => {
    if (field.value.trim() === "") {
      isValid = false;
      const errorMessageDiv =
        field.parentElement.querySelector(".error-message");
      if (errorMessageDiv) {
        errorMessageDiv.style.display = "block";
      }
      // 첫 번째 빈 필드로 스크롤 이동 및 포커스
      if (!document.querySelector(".error-message[style*='block']")) {
        field.focus();
        field.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    }
    docContent[field.name] = field.value.trim(); // 일단 내용 저장 (유효성 검사 후 사용)
  });

  // 파일 입력 필드는 required 검사에서 제외하고 별도 처리
  const fileInputs = formFields.querySelectorAll('input[type="file"]');
  fileInputs.forEach((fileInput) => {
    // 파일 입력은 FormData에 직접 추가되므로 docContent에는 포함시키지 않음
    // 이 부분은 기존 로직과 동일하게 유지. 파일 유효성은 별도 로직 필요 시 추가
  });

  if (!isValid) {
    alert("필수 입력 항목을 모두 채워주세요.");
    return; // 유효성 검사 실패 시 함수 종료
  }

  // 이하는 기존의 AI 분석 및 저장 로직
  try {
    // 1. 현재 편집 중인 문서 버전을 documentData에서 찾습니다.
    const currentDocInArray = getDocumentVersionData(
      currentDocType,
      currentDocVersion
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
        truncateDocumentVersions(currentDocType, currentDocVersion);
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
      addNewDocumentVersion(currentDocType, newDocForNextVersion);

      // 7. 현재 활성 버전을 새로 생성된 vN+1로 업데이트합니다.
      currentDocVersion = newVersionNumberForPush;

      // UI 업데이트
      setModalTitle(
        `${currentDocInArray.koreanName} 편집 (v${currentDocVersion})`
      );
      setAiFeedback(result.feedback);

      drawDiagram(); // 다이어그램 다시 그리기
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
    showLoading(false); // 로딩 오버레이 숨김
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
