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

/** ================================
 *  공통: API 베이스/토큰/슬러그 유틸
 *  ================================ */
const ROOT_PREFIX = window.location.pathname.startsWith("/text") ? "/text" : "";
const API_BASE = `${ROOT_PREFIX}/apiText`;

function getToken() {
  return localStorage.getItem("token") || sessionStorage.getItem("token") || "";
}

function slugifyAndEncode(title) {
  const slug = title.replace(/ /g, "-").replace(/\//g, "-").toLowerCase();
  return encodeURIComponent(slug);
}

/** 프로필 불러오기 (마이페이지 저장 내용) */
async function fetchUserProfile() {
  const res = await fetch(`${API_BASE}/user_profile`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) {
    throw new Error(`user_profile ${res.status}`);
  }
  return res.json();
}

/** 프로필 → 이력서 폼 데이터 매핑 */
function profileToResumeContent(profile) {
  return {
    education: Array.isArray(profile.education) ? profile.education : [],
    activities: Array.isArray(profile.activities) ? profile.activities : [],
    awards: Array.isArray(profile.awards) ? profile.awards : [],
    certificates: Array.isArray(profile.certificates) ? profile.certificates : [],
  };
}

/** 이력서 내용이 실질적으로 비었는지(placeholder 행만 있는 경우도 비었다고 판단) */
function isEmptyResumeContent(content) {
  if (!content) return true;

  const isEmptyObjRow = (row) => {
    if (!row || typeof row !== "object") return true;
    return Object.values(row).every((v) => {
      if (v == null) return true;
      if (typeof v === "string") return v.trim() === "";
      return false;
    });
  };

  const isEmptyStr = (s) => typeof s !== "string" || s.trim() === "";

  const ed = Array.isArray(content.education) ? content.education : [];
  const ac = Array.isArray(content.activities) ? content.activities : [];
  const aw = Array.isArray(content.awards) ? content.awards : [];
  const ct = Array.isArray(content.certificates) ? content.certificates : [];

  const hasMeaningfulEducation = ed.some((r) => !isEmptyObjRow(r));
  const hasMeaningfulActivities = ac.some((r) => !isEmptyObjRow(r));
  const hasMeaningfulAwards = aw.some((r) => !isEmptyObjRow(r));
  const hasMeaningfulCertificates = ct.some((s) => !isEmptyStr(s));

  return !(
    hasMeaningfulEducation ||
    hasMeaningfulActivities ||
    hasMeaningfulAwards ||
    hasMeaningfulCertificates
  );
}

/**
 * 다이어그램 노드 클릭 이벤트 설정
 */
export function setupNodeClickEvents() {
  // 롤백 버튼
  document.querySelectorAll(".rollback-button").forEach((button) => {
    button.onclick = (e) => {
      e.stopPropagation();
      const docType = button.dataset.docType;
      const versionToRollback = parseInt(button.dataset.version, 10);
      rollbackDocument(docType, versionToRollback);
    };
  });

  // 노드 클릭
  document.querySelectorAll(".diagram-node").forEach((node) => {
    node.onclick = async (e) => {
      const clickedNode = e.target.closest(".diagram-node");
      const docType = clickedNode.dataset.docType;

      if (docType === "company") {
        openCompanyModal();
        return;
      }
      if (!clickedNode.classList.contains("document-node")) return;

      const version = parseInt(clickedNode.dataset.version, 10);
      setCurrentDocInfo(docType, version);

      try {
        showLoading(true, "문서 스키마 로딩 중...");

        // 스키마 요청
        const jobSlug = slugifyAndEncode(jobTitle);
        const schemaUrl = `${API_BASE}/document_schema/${currentDocType}?job_slug=${jobSlug}`;
        const formSchema = await fetch(schemaUrl).then((res) => {
          if (!res.ok) throw new Error(`서버 응답 오류: ${res.status}`);
          return res.json();
        });

        // 현재 버전 데이터
        let versionData = getDocumentVersionData(docType, version);
        let docContent = versionData?.content || {};
        const savedFeedback = versionData?.feedback || "";
        const individualFeedbacks =
          versionData?.individual_feedbacks || {};

        // 이력서면, 내용이 사실상 비어있으면 프로필로 자동 채움
        if (docType === "resume" && isEmptyResumeContent(docContent)) {
          try {
            const profile = await fetchUserProfile();
            const resumeDefaults = profileToResumeContent(profile);
            docContent = {
              education: resumeDefaults.education,
              activities: resumeDefaults.activities,
              awards: resumeDefaults.awards,
              certificates: resumeDefaults.certificates,
            };
          } catch (err) {
            console.warn("프로필 불러오기 실패(이력서 기본값 생략):", err);
          }
        }

        renderFormFields(formSchema, docContent);
        setModalTitle(`${clickedNode.dataset.koreanName} 편집 (v${version})`);
        openEditModal(
          `${clickedNode.dataset.koreanName} 편집 (v${version})`,
          savedFeedback,
          individualFeedbacks,
          docType // 포트폴리오 포함 개별 피드백 표시 가능
        );
      } catch (error) {
        console.error("노드 클릭 처리 중 오류:", error);
        alert(
          "문서 편집기를 여는 중 오류가 발생했습니다. 네트워크나 서버를 확인하세요."
        );
        editModal.style.display = "none";
      } finally {
        showLoading(false);
      }
    };
  });
}

/**
 * 다이어그램 그리기
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

/**
 * 문서 되돌리기
 */
export async function rollbackDocument(docType, versionToRollback) {
  const docName = documentData[docType][0]
    ? documentData[docType][0].koreanName
    : docType;

  if (!confirm(`${docName}를 v${versionToRollback} 버전으로 되돌리시겠습니까?`))
    return;

  truncateDocumentVersions(docType, versionToRollback);

  showLoading(true, "데이터베이스 롤백 중...");
  try {
    const jobSlug = slugifyAndEncode(jobTitle);

    const response = await fetch(
      `${API_BASE}/rollback_document/${docType}/${jobSlug}/${versionToRollback}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${getToken()}` },
      }
    );
    if (!response.ok) {
      let errMsg = `서버 롤백 실패 (${response.status})`;
      try {
        const errorResult = await response.json();
        errMsg = errorResult.detail || errMsg;
      } catch (_) {}
      throw new Error(errMsg);
    }
    alert(`${docName}가 v${versionToRollback} 버전으로 되돌려졌습니다.`);
  } catch (error) {
    console.error("Rollback API error:", error);
    alert(`롤백 중 오류: ${error.message}`);
  } finally {
    showLoading(false);
  }

  setCurrentDocInfo(docType, versionToRollback);

  // 모달 먼저 갱신
  if (editModal.style.display === "block" && currentDocType === docType) {
    const versionData = getDocumentVersionData(docType, versionToRollback);
    if (versionData) {
      try {
        const jobSlug = slugifyAndEncode(jobTitle);
        const schemaUrl = `${API_BASE}/document_schema/${currentDocType}?job_slug=${jobSlug}`;
        const schema = await fetch(schemaUrl).then((res) => {
          if (!res.ok) throw new Error(`서버 응답 오류: ${res.status}`);
          return res.json();
        });

        // 이력서면 비어있을 때 프로필로 채움(롤백 후에도 동일 동작)
        let content = versionData.content || {};
        if (docType === "resume" && isEmptyResumeContent(content)) {
          try {
            const profile = await fetchUserProfile();
            const resumeDefaults = profileToResumeContent(profile);
            content = {
              education: resumeDefaults.education,
              activities: resumeDefaults.activities,
              awards: resumeDefaults.awards,
              certificates: resumeDefaults.certificates,
            };
          } catch (e) {
            console.warn("프로필 불러오기 실패(롤백 후 기본값 생략):", e);
          }
        }

        renderFormFields(schema, content);
        setAiFeedback(
          versionData.feedback || "",
          versionData.individual_feedbacks || {},
          docType // 포트폴리오 포함
        );
        setModalTitle(
          `${versionData.koreanName} 편집 (v${versionData.version})`
        );
      } catch (err) {
        console.error("Error fetching schema on rollback:", err);
      }
    } else {
      editModal.style.display = "none";
      alert("문서가 초기화되어 현재 편집 중인 내용이 없습니다.");
    }
  }

  // 모달 갱신 후 다이어그램 다시 그림
  drawDiagram();
}
