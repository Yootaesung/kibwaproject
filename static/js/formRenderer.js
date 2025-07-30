// static/js/formRenderer.js
import { formFields, documentForm } from "./domElements.js";
import {
  handleDocumentFormSubmit,
  handlePortfolioFormSubmit,
} from "./formSubmitHandler.js"; // 폼 제출 핸들러 임포트

/**
 * 주어진 스키마와 내용에 따라 폼 필드를 렌더링합니다.
 * @param {Object} schema - 문서 스키마 (sections 또는 fields 포함).
 * @param {Object} currentContent - 현재 문서 내용.
 */
export function renderFormFields(schema, currentContent) {
  formFields.innerHTML = ""; // 기존 폼 필드 초기화
  console.log("Rendering form fields for schema:", schema);

  // schema.korean_name이 없을 경우를 대비하여 방어 코드 추가
  const docKoreanName =
    schema.korean_name || schema.title || currentContent.koreanName;

  if (docKoreanName === "포트폴리오") {
    formFields.innerHTML = `
            <div class="input-group">
                <label>포트폴리오 PDF 업로드:</label>
                <input type="file" name="portfolio_pdf" accept=".pdf">
            </div>
            <div class="input-group">
                <label>포트폴리오 링크 입력:</label>
                <input type="text" name="portfolio_link" placeholder="포트폴리오가 업로드된 웹사이트, 블로그, Github 등 링크를 입력하세요." value="${
                  currentContent.portfolio_link || ""
                }">
            </div>
        `;
    const submitBtn = document.querySelector(
      '#document-form button[type="submit"]'
    );
    submitBtn.textContent = "요약 및 다운";
    documentForm.onsubmit = handlePortfolioFormSubmit;
    return;
  } else if (docKoreanName === "자기소개서") {
    const qaContainer = document.createElement("div");
    qaContainer.id = "qa-container";

    // 5가지 새로운 질문에 대한 필드 렌더링
    qaContainer.innerHTML = `
            <div class="input-group">
                <label>1. 해당 직무에 지원한 이유를 서술하시오.<span class="required">*</span></label>
                <textarea name="reason_for_application" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;" required>${
                  currentContent.reason_for_application || ""
                }</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${
                      (currentContent.reason_for_application || "").length
                    }</span>
                </div>
                <div class="error-message" style="color: red; font-size: 0.8em; display: none;">필수 입력 항목입니다.</div>
            </div>
            <div class="input-group" style="margin-top: 20px;">
                <label>2. 해당 분야에 대한 전문성을 기르기 위해 노력한 경험을 서술하시오.<span class="required">*</span></label>
                <textarea name="expertise_experience" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;" required>${
                  currentContent.expertise_experience || ""
                }</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${
                      (currentContent.expertise_experience || "").length
                    }</span>
                </div>
                <div class="error-message" style="color: red; font-size: 0.8em; display: none;">필수 입력 항목입니다.</div>
            </div>
            <div class="input-group" style="margin-top: 20px;">
                <label>3. 공동의 목표를 위해 협업을 한 경험을 서술하시오.<span class="required">*</span></label>
                <textarea name="collaboration_experience" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;" required>${
                  currentContent.collaboration_experience || ""
                }</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${
                      (currentContent.collaboration_experience || "").length
                    }</span>
                </div>
                <div class="error-message" style="color: red; font-size: 0.8em; display: none;">필수 입력 항목입니다.</div>
            </div>
            <div class="input-group" style="margin-top: 20px;">
                <label>4. 도전적인 목표를 세우고 성취하기 위해 노력한 경험을 서술하시오.<span class="required">*</span></label>
                <textarea name="challenging_goal_experience" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;" required>${
                  currentContent.challenging_goal_experience || ""
                }</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${
                      (currentContent.challenging_goal_experience || "").length
                    }</span>
                </div>
                <div class="error-message" style="color: red; font-size: 0.8em; display: none;">필수 입력 항목입니다.</div>
            </div>
            <div class="input-group" style="margin-top: 20px;">
                <label>5. 자신의 성장과정을 서술하시오.<span class="required">*</span></label>
                <textarea name="growth_process" placeholder="내용을 입력하세요." style="width: 100%; min-height: 120px;" required>${
                  currentContent.growth_process || ""
                }</textarea>
                <div class="char-counter" style="text-align: right; font-size: 0.9em; color: #666; margin-top: 3px;">
                    글자수: <span class="char-count">${
                      (currentContent.growth_process || "").length
                    }</span>
                </div>
                <div class="error-message" style="color: red; font-size: 0.8em; display: none;">필수 입력 항목입니다.</div>
            </div>
        `;
    formFields.appendChild(qaContainer);

    qaContainer.querySelectorAll("textarea").forEach((textarea) => {
      const charCountSpan =
        textarea.nextElementSibling.querySelector(".char-count");
      textarea.addEventListener("input", () => {
        charCountSpan.textContent = textarea.value.length;
        // 입력 시 에러 메시지 숨김
        const errorMessageDiv =
          textarea.parentElement.querySelector(".error-message");
        if (errorMessageDiv) {
          errorMessageDiv.style.display = "none";
        }
      });
    });
    const submitBtn = document.querySelector(
      '#document-form button[type="submit"]'
    );
    submitBtn.textContent = "저장 및 분석";
    documentForm.onsubmit = handleDocumentFormSubmit;
    return;
  }

  if (schema.sections) {
    console.log("Rendering sections for Resume.");
    schema.sections.forEach((section) => {
      const sectionDiv = document.createElement("div");
      sectionDiv.className = "form-section";

      const sectionTitle = document.createElement("h3");
      sectionTitle.textContent = section.title;
      sectionDiv.appendChild(sectionTitle);

      section.fields.forEach((field) => {
        const div = document.createElement("div");
        div.className = "input-group";

        const label = document.createElement("label");
        label.textContent = field.label;
        // field.required가 true면 * 추가
        if (field.required) {
          const requiredSpan = document.createElement("span");
          requiredSpan.className = "required";
          requiredSpan.textContent = "*";
          label.appendChild(requiredSpan);
        }
        div.appendChild(label);

        let inputElement;
        if (field.type === "textarea") {
          inputElement = document.createElement("textarea");
          inputElement.placeholder = field.placeholder;
          inputElement.rows = 5;
          inputElement.value = currentContent[field.name] || "";
        } else if (field.type === "file") {
          inputElement = document.createElement("input");
          inputElement.type = "file";
          inputElement.accept = field.accept;
        } else if (field.type === "date") {
          inputElement = document.createElement("input");
          inputElement.type = "date";
          inputElement.value = currentContent[field.name] || "";
        } else {
          inputElement = document.createElement("input");
          inputElement.type = field.type;
          inputElement.placeholder = field.placeholder;
          inputElement.value = currentContent[field.name] || "";
        }
        inputElement.name = field.name;
        inputElement.id = field.name;
        // field.required가 true면 required 속성 추가
        if (field.required) {
          inputElement.setAttribute("required", "true");
        }
        inputElement.addEventListener("input", () => {
          // 입력 시 에러 메시지 숨김
          const errorMessageDiv =
            inputElement.parentElement.querySelector(".error-message");
          if (errorMessageDiv) {
            errorMessageDiv.style.display = "none";
          }
        });

        div.appendChild(inputElement);
        // 에러 메시지 div 추가
        const errorMessageDiv = document.createElement("div");
        errorMessageDiv.className = "error-message";
        errorMessageDiv.style.color = "red";
        errorMessageDiv.style.fontSize = "0.8em";
        errorMessageDiv.style.display = "none"; // 기본적으로 숨김
        errorMessageDiv.textContent = "필수 입력 항목입니다.";
        div.appendChild(errorMessageDiv);

        sectionDiv.appendChild(div);
      });
      formFields.appendChild(sectionDiv);
    });
  } else if (schema.fields) {
    // schema에 'fields'만 있는 경우
    console.log("Rendering fields for general document type.");
    schema.fields.forEach((field) => {
      const div = document.createElement("div");
      div.className = "input-group";
      let inputHtml = "";
      if (field.type === "textarea") {
        inputHtml = `
                    <label>${field.label}: ${
          field.required ? '<span class="required">*</span>' : ""
        }</label>
                    <textarea name="${field.name}" placeholder="${
          field.placeholder || ""
        }" ${field.required ? "required" : ""}>${
          currentContent[field.name] || ""
        }</textarea>
                `;
      } else if (field.type === "text") {
        inputHtml = `
                    <label>${field.label}: ${
          field.required ? '<span class="required">*</span>' : ""
        }</label>
                    <input type="text" name="${field.name}" value="${
          currentContent[field.name] || ""
        }" placeholder="${field.placeholder || ""}" ${
          field.required ? "required" : ""
        }>
                `;
      }
      div.innerHTML = inputHtml;

      // 에러 메시지 div 추가 (innerHTML 이후에 접근)
      const errorMessageDiv = document.createElement("div");
      errorMessageDiv.className = "error-message";
      errorMessageDiv.style.color = "red";
      errorMessageDiv.style.fontSize = "0.8em";
      errorMessageDiv.style.display = "none";
      errorMessageDiv.textContent = "필수 입력 항목입니다.";
      div.appendChild(errorMessageDiv);

      formFields.appendChild(div);

      // 동적으로 생성된 input/textarea에 input 이벤트 리스너 추가
      const createdInput = div.querySelector(
        `[name="${field.name}"][required]`
      );
      if (createdInput) {
        createdInput.addEventListener("input", () => {
          const errorMsgDiv =
            createdInput.parentElement.querySelector(".error-message");
          if (errorMsgDiv) {
            errorMsgDiv.style.display = "none";
          }
        });
      }
    });
  }

  const submitBtn = document.querySelector(
    '#document-form button[type="submit"]'
  );
  submitBtn.textContent = "저장 및 분석";
  documentForm.onsubmit = handleDocumentFormSubmit;
}
