// static/js/formSubmitHandler.js
import { formFields, documentForm, companyNameInput } from "./domElements.js";
import {
  jobTitle,
  currentDocType,
  currentDocVersion,
  addNewDocumentVersion,
  truncateDocumentVersions,
  getDocumentVersionData,
  setCurrentDocInfo,
  updateExistingDocumentVersion,
} from "./documentData.js";
import { showLoading, setAiFeedback, setModalTitle } from "./uiHandler.js";
import { drawDiagram } from "./diagramRenderer.js";
import { renderFormFields } from "./formRenderer.js";

/* ---------------------------------------
   API base & fetch helper
---------------------------------------- */
const ROOT_PREFIX = window.location.pathname.startsWith("/text") ? "/text" : "";
const API_BASE = `${ROOT_PREFIX}/apiText`;

function apiFetch(url, options = {}) {
  const token = localStorage.getItem("token");
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

const isVisible = (el) =>
  !!(el && (el.offsetParent !== null || el.getClientRects().length));

/* ---------------------------------------
   collect (resume, MyPage schema)
---------------------------------------- */
function collectResumeContentFromDOM() {
  const eduContainer = document.getElementById("education-container");
  const eduItems =
    (eduContainer && eduContainer.querySelectorAll(".item-entry")) || [];
  const education = Array.from(eduItems)
    .map((row) => {
      const idx = row.getAttribute("data-index");
      const get = (n) => row.querySelector(`[name="education_${idx}_${n}"]`);
      const level = get("level")?.value?.trim() || "";
      const status = get("status")?.value?.trim() || "";
      const school = get("school")?.value?.trim() || "";
      const major = get("major")?.value?.trim() || "";
      if (!(level || status || school || major)) return null;
      return { level, status, school, major };
    })
    .filter(Boolean);

  const actContainer = document.getElementById("activities-container");
  const actItems =
    (actContainer && actContainer.querySelectorAll(".item-entry")) || [];
  const activities = Array.from(actItems)
    .map((row) => {
      const idx = row.getAttribute("data-index");
      const title =
        row.querySelector(`[name="activities_${idx}_title"]`)?.value?.trim() ||
        "";
      const content =
        row
          .querySelector(`[name="activities_${idx}_content"]`)
          ?.value?.trim() || "";
      if (!(title || content)) return null;
      return { title, content };
    })
    .filter(Boolean);

  const awdContainer = document.getElementById("awards-container");
  const awdItems =
    (awdContainer && awdContainer.querySelectorAll(".item-entry")) || [];
  const awards = Array.from(awdItems)
    .map((row) => {
      const idx = row.getAttribute("data-index");
      const title =
        row.querySelector(`[name="awards_${idx}_title"]`)?.value?.trim() || "";
      const content =
        row.querySelector(`[name="awards_${idx}_content"]`)?.value?.trim() ||
        "";
      if (!(title || content)) return null;
      return { title, content };
    })
    .filter(Boolean);

  const certContainer = document.getElementById("certificates-container");
  const certItems =
    (certContainer && certContainer.querySelectorAll(".item-entry")) || [];
  const certificates = Array.from(certItems)
    .map((row) => {
      const idx = row.getAttribute("data-index");
      const name =
        row.querySelector(`[name="certificates_${idx}_name"]`)?.value?.trim() ||
        "";
      return name || null;
    })
    .filter(Boolean);

  return {
    education: education.length
      ? education
      : [{ level: "", status: "", school: "", major: "" }],
    activities: activities.length ? activities : [{ title: "", content: "" }],
    awards: awards.length ? awards : [{ title: "", content: "" }],
    certificates: certificates.length ? certificates : [""],
  };
}

/* ---------------------------------------
   validate required (visible only)
---------------------------------------- */
function validateRequiredFields() {
  return true;
}

/* ---------------------------------------
   submit (resume/cover_letter) - update current, clone next
---------------------------------------- */
export async function handleDocumentFormSubmit(e) {
  e.preventDefault();

  if (documentForm) {
    documentForm.noValidate = true;
    documentForm.querySelectorAll("[required]").forEach((el) => {
      if (!isVisible(el)) el.required = false;
    });
  }

  let content = {};
  if (currentDocType === "resume") {
    content = collectResumeContentFromDOM();
  } else {
    const formData = new FormData(documentForm);
    for (const [key, value] of formData.entries()) {
      content[key] = value;
    }
  }

  if (!validateRequiredFields(content)) {
    alert("필수 입력 항목을 모두 채워주세요.");
    return;
  }

  showLoading(true, "AI 분석 중...");
  try {
    const feedbackReflection =
      document.getElementById("feedback-reflection-input")?.value || "";
    const companyName = companyNameInput?.value?.trim() || "";

    const response = await apiFetch(
      `${API_BASE}/analyze_document/${currentDocType}`,
      {
        method: "POST",
        body: JSON.stringify({
          job_title: jobTitle,
          document_content: content,
          version: currentDocVersion, // 편집 중인 현재 버전
          feedback_reflection: feedbackReflection,
          company_name: companyName,
        }),
      }
    );

    const result = await response.json();

    if (!response.ok) {
      const errorMsg = result.error || response.statusText || "알 수 없는 오류";
      alert(`AI 분석 오류: ${errorMsg}`);
      setAiFeedback(errorMsg, {}, currentDocType);
      return;
    }

    // 서버가 두 버전을 반환
    const curr = result.current_version_data || {};
    const next = result.next_version_data || {};

    // 1) 현재 버전 갱신
    updateExistingDocumentVersion(
      currentDocType,
      curr.version ?? currentDocVersion,
      curr.content ?? content,
      curr.feedback ?? result.ai_feedback ?? "",
      curr.individual_feedbacks ?? result.individual_feedbacks ?? {},
      curr.embedding ?? [],
      curr.content_hash ?? ""
    );

    // 2) 이후 버전 생성
    truncateDocumentVersions(currentDocType, curr.version ?? currentDocVersion);
    addNewDocumentVersion(
      currentDocType,
      next.version ?? currentDocVersion + 1,
      next.content ?? content,
      next.feedback ?? curr.feedback ?? "",
      next.individual_feedbacks ?? curr.individual_feedbacks ?? {},
      next.embedding ?? [],
      next.content_hash ?? ""
    );

    // 다음 버전을 현재로 전환
    const nextVersionNumber = next.version ?? currentDocVersion + 1;
    setCurrentDocInfo(currentDocType, nextVersionNumber);
    drawDiagram();

    // 폼 재렌더: 다음 버전 내용으로 프리필
    const schemaResponse = await apiFetch(
      `${API_BASE}/document_schema/${currentDocType}?job_slug=${jobTitle
        .replace(/ /g, "-")
        .replace(/\//g, "-")
        .toLowerCase()}`
    );
    const schema = await schemaResponse.json();

    renderFormFields(schema, next.content ?? content);
    const titleKo =
      currentDocType === "resume"
        ? "이력서"
        : currentDocType === "cover_letter"
        ? "자기소개서"
        : "문서";
    setModalTitle(`${titleKo} (v${nextVersionNumber})`);
    setAiFeedback(
      next.feedback ?? curr.feedback ?? "",
      next.individual_feedbacks ?? curr.individual_feedbacks ?? {},
      currentDocType
    );
    document.getElementById("edit-modal").style.display = "block";
    alert("문서가 성공적으로 분석/저장되고 다음 버전이 생성되었습니다!");
  } catch (error) {
    console.error("문서 제출 중 오류 발생:", error);
    alert("문서 분석 및 저장 중 오류가 발생했습니다.\n" + error.message);
    setAiFeedback(`오류: ${error.message}`, {}, currentDocType);
  } finally {
    showLoading(false);
  }
}

/* ---------------------------------------
   portfolio (summary + download) - update current, clone next
---------------------------------------- */
export async function handlePortfolioFormSubmit(e) {
  e.preventDefault();
  documentForm?.setAttribute("novalidate", "");

  const pdfInput = document.querySelector('input[name="portfolio_pdf"]');
  const linkInput = document.querySelector('input[name="portfolio_link"]');
  const formData = new FormData();
  formData.append("job_title", jobTitle);
  formData.append("version", String(currentDocVersion)); // 현재 버전 전달

  const companyName = companyNameInput?.value?.trim();
  if (companyName) formData.append("company_name", companyName);

  let hasPortfolioContent = false;
  if (pdfInput && pdfInput.files.length > 0) {
    formData.append("portfolio_pdf", pdfInput.files[0]);
    hasPortfolioContent = true;
  }
  if (linkInput && linkInput.value.trim()) {
    formData.append("portfolio_link", linkInput.value.trim());
    hasPortfolioContent = true;
  }

  if (!hasPortfolioContent) {
    alert("포트폴리오 PDF 파일을 업로드하거나 링크를 입력하세요.");
    return;
  }

  showLoading(true, "포트폴리오 요약 및 PDF 생성 중...");
  try {
    const response = await apiFetch(`${API_BASE}/portfolio_summary`, {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    if (!response.ok) {
      const resultError = result.error || "알 수 없는 오류";
      alert(`요약 실패: ${resultError}`);
      setAiFeedback(`오류: ${resultError}`, {}, "portfolio");
      return;
    }

    // 인증 포함 다운로드
    if (result.download_url) {
      try {
        // 서버가 /api/... 로 반환해도 안전하게 변환
        let dl = result.download_url;
        if (dl.startsWith("/api/")) {
          dl = dl.replace("/api/", `${API_BASE}/`);
        } else if (dl.startsWith("/apiText/") && ROOT_PREFIX) {
          dl = `${ROOT_PREFIX}${dl}`;
        }

        const token = localStorage.getItem("token");
        const resp = await fetch(dl, {
          method: "GET",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!resp.ok) {
          const msg = await resp.text().catch(() => "");
          throw new Error(
            `파일 다운로드 실패: ${resp.status} ${msg || resp.statusText}`
          );
        }
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const last = dl.split("/").pop() || "portfolio_summary.pdf";
        a.download = decodeURIComponent(last);
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert("포트폴리오 요약 PDF가 다운로드되었습니다.");
      } catch (e) {
        console.error(e);
        alert(String(e.message || e));
      }
    } else {
      alert("PDF 다운로드 정보가 없습니다.");
    }

    // 버전 반영 (현재 갱신 + 다음 복제)
    const curr = result.current_version_data || {};
    const next = result.next_version_data || {};

    updateExistingDocumentVersion(
      "portfolio",
      curr.version ?? currentDocVersion,
      curr.content ?? {
        portfolio_link: linkInput?.value?.trim() || "",
        file_name: pdfInput?.files?.[0] ? pdfInput.files[0].name : "",
      },
      curr.feedback ?? result.ai_summary ?? "",
      curr.individual_feedbacks ?? {},
      curr.embedding ?? [],
      curr.content_hash ?? ""
    );

    truncateDocumentVersions("portfolio", curr.version ?? currentDocVersion);

    addNewDocumentVersion(
      "portfolio",
      next.version ?? currentDocVersion + 1,
      next.content ?? {
        portfolio_link: linkInput?.value?.trim() || "",
        file_name: pdfInput?.files?.[0] ? pdfInput.files[0].name : "",
      },
      next.feedback ?? curr.feedback ?? result.ai_summary ?? "",
      next.individual_feedbacks ?? {},
      next.embedding ?? [],
      next.content_hash ?? ""
    );

    const nextPortfolioVersionNumber = next.version ?? currentDocVersion + 1;
    setCurrentDocInfo("portfolio", nextPortfolioVersionNumber);
    setModalTitle(`포트폴리오 편집 (v${nextPortfolioVersionNumber})`);
    setAiFeedback(
      next.feedback ?? curr.feedback ?? result.ai_summary ?? "",
      next.individual_feedbacks ?? {},
      "portfolio"
    );
    drawDiagram();

    // 폼 리렌더
    const nextPortDocVersionData = getDocumentVersionData(
      "portfolio",
      nextPortfolioVersionNumber
    );
    const schemaResponse = await apiFetch(
      `${API_BASE}/document_schema/portfolio?job_slug=` +
        jobTitle.replace(/ /g, "-").replace(/\//g, "-").toLowerCase()
    );
    const schema = await schemaResponse.json();
    renderFormFields(schema, nextPortDocVersionData.content);
    document.getElementById("edit-modal").style.display = "block";
    alert("포트폴리오가 성공적으로 요약/저장되고 다음 버전이 생성되었습니다.");
  } catch (err) {
    console.error("서버 오류:", err);
    alert("포트폴리오 분석 중 서버 오류가 발생했습니다.\n" + err.message);
    setAiFeedback(`네트워크 오류: ${err.message}`, {}, "portfolio");
  } finally {
    showLoading(false);
  }
}
