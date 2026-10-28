import {
  emptyEmployee, phoneSegment, accountDigits, changeBank, changeBankName, payNotice,
} from "./fields.mjs";
import {
  emptyState, isUntouched, addCurrent, prepareSubmission, markUnknown, completeSubmission,
} from "./state.mjs";

const root = document.querySelector("#app");
const draftKey = "staff-registration-draft";
let state = emptyState();
try {
  const restored = JSON.parse(localStorage.getItem(draftKey) || "null");
  if (restored?.current && Array.isArray(restored.rows)) state = restored;
} catch { /* A malformed local draft starts a fresh form. */ }
if (state.phase === "saving") state = markUnknown(state, "등록 결과를 확인해 주세요.");
let opened = false;
let saved = [];
let listError = "";
let accountOpen = false;
const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));
const selected = (a, b) => a === b ? "selected" : "";

function persist() {
  if (state.phase === "complete") localStorage.removeItem(draftKey);
  else localStorage.setItem(draftKey, JSON.stringify(state));
}

async function refresh() {
  try {
    const response = await fetch("/api/entries", { cache: "no-store" });
    if (!response.ok) throw new Error();
    saved = (await response.json()).entries;
    listError = "";
  } catch {
    listError = "직원 목록을 불러오지 못했어요.";
  }
  render();
}

function render() {
  const active = document.activeElement;
  const focusId = active?.id;
  const selection = typeof active?.selectionStart === "number" ? [active.selectionStart, active.selectionEnd] : null;
  if (!opened) {
    root.innerHTML = `<h1>직원 관리</h1>
      <button class="primary wide" id="open">직원 추가</button>
      ${listError ? `<p role="alert" class="error">${escape(listError)}</p><button id="refresh">다시 불러오기</button>` : ""}
      <h2>등록된 직원 ${saved.length}명</h2>
      ${saved.length ? saved.map((entry) => `<div class="saved"><strong>${escape(entry.name)}</strong>
      <span>${escape(entry.phonePrefix)}-${escape(entry.phoneMiddle)}-${escape(entry.phoneLast)}</span>
      <div class="quiet">${entry.payType === "monthly" ? "월급" : "시급"} ${escape(entry.payAmount)}원</div></div>`).join("") : '<p class="empty">등록된 직원이 없어요.</p>'}`;
    document.querySelector("#open").onclick = () => {
      if (state.phase === "complete") state = emptyState();
      opened = true;
      accountOpen = Boolean(state.current.bank || state.current.account || state.current.bankName);
      render();
    };
    document.querySelector("#refresh")?.addEventListener("click", refresh);
    return;
  }
  const top = `<div class="top"><span class="quiet">직원 추가</span><button class="plain" id="close">닫기</button></div>`;
  if (state.phase === "complete") {
    root.innerHTML = `${top}<h1>${state.result.count}명 등록 완료</h1>
      <p>직원 관리에서 등록한 정보를 확인할 수 있어요.</p>
      <div class="footer"><button class="primary" id="done">완료</button></div>`;
    document.querySelector("#done").onclick = close;
  } else if (state.phase === "unknown" || state.phase === "saving") {
    root.innerHTML = `${top}<h1>${state.phase === "saving" ? "등록 중" : "등록 결과 확인"}</h1>
      <p>${state.pending.entries.length}명의 등록 결과를 확인하고 있어요.</p>
      ${state.error ? `<p role="alert" class="error">${escape(state.error)}</p>` : ""}
      <div class="footer"><button id="retry" ${state.phase === "saving" ? "disabled" : ""}>다시 시도</button>
      <button class="primary" id="lookup" ${state.phase === "saving" ? "disabled" : ""}>등록 결과 확인</button></div>`;
    document.querySelector("#retry").onclick = submit;
    document.querySelector("#lookup").onclick = lookup;
  } else {
    const current = state.current;
    const notice = payNotice(current);
    root.innerHTML = `${top}<h1>새 직원</h1>
      ${state.rows.length ? `<p class="quiet">작성한 직원 ${state.rows.length}명</p>` : ""}
      <div class="field"><label for="name">이름</label><input id="name" autocomplete="off" value="${escape(current.name)}"></div>
      <div class="field"><label for="phonePrefix">전화번호</label><div class="phone">
      <select id="phonePrefix" aria-label="휴대전화 국번">${["010", "011", "016", "017", "018", "019"].map((value) => `<option ${selected(current.phonePrefix, value)}>${value}</option>`).join("")}</select>
      <input id="phoneMiddle" aria-label="전화번호 가운데 네 자리" inputmode="numeric" value="${escape(current.phoneMiddle)}">
      <input id="phoneLast" aria-label="전화번호 마지막 네 자리" inputmode="numeric" value="${escape(current.phoneLast)}"></div></div>
      <h2>급여</h2><div class="field"><label for="payType">급여 방식</label>
      <select id="payType"><option value="hourly" ${selected(current.payType, "hourly")}>시급</option><option value="monthly" ${selected(current.payType, "monthly")}>월급</option></select></div>
      <div class="field"><label for="payAmount">${current.payType === "monthly" ? "월급" : "시급"}</label><input id="payAmount" inputmode="numeric" value="${escape(current.payAmount)}"></div>
      ${notice ? `<p class="notice">${escape(notice)}</p>` : ""}
      <details id="payment" ${accountOpen ? "open" : ""}><summary>지급 계좌 (선택)</summary>
      <div class="field"><label for="bank">은행</label><select id="bank"><option value="">선택 안 함</option>
      <option value="sample-a" ${selected(current.bank, "sample-a")}>예시 은행 A</option>
      <option value="sample-b" ${selected(current.bank, "sample-b")}>예시 은행 B</option>
      <option value="other" ${selected(current.bank, "other")}>직접 입력</option></select></div>
      ${current.bank === "other" ? `<div class="field"><label for="bankName">은행명</label><input id="bankName" value="${escape(current.bankName)}"></div>` : ""}
      <div class="field"><label for="account">계좌번호</label><input id="account" inputmode="numeric" value="${escape(current.account)}"></div></details>
      ${state.error ? `<p role="alert" class="error">${escape(state.error)}</p>` : ""}
      ${state.rows.length && !isUntouched(current) ? '<button class="plain" id="clear">이번 입력 지우기</button>' : ""}
      <div class="footer"><button id="next">다음 직원 입력</button><button class="primary" id="submit">등록하기</button></div>`;
    document.querySelector("#payment").ontoggle = (event) => { accountOpen = event.target.open; };
    root.querySelectorAll("input, select").forEach((input) => {
      const apply = (event) => {
        if (event.isComposing) return;
        const key = input.id;
        if (key === "phoneMiddle" || key === "phoneLast") {
          const result = phoneSegment(input.value);
          state = { ...state, current: { ...state.current, [key]: result.value }, error: result.error };
        } else if (key === "bank") state = { ...state, current: changeBank(state.current, input.value), error: "" };
        else if (key === "bankName") state = { ...state, current: changeBankName(state.current, input.value), error: "" };
        else state = { ...state, current: { ...state.current, [key]: key === "account" ? accountDigits(input.value) : input.value }, error: "" };
        persist();
        render();
      };
      input.addEventListener(input.tagName === "SELECT" ? "change" : "input", apply);
      input.addEventListener("compositionend", apply);
    });
    document.querySelector("#next").onclick = () => {
      try { state = addCurrent(state); } catch (error) { state = { ...state, error: error.message }; }
      persist(); render();
      document.querySelector("#name")?.focus();
    };
    document.querySelector("#submit").onclick = submit;
    document.querySelector("#clear")?.addEventListener("click", () => {
      state = { ...state, current: emptyEmployee(), error: "" };
      persist(); render();
    });
  }
  document.querySelector("#close").onclick = close;
  const restoredFocus = focusId && document.getElementById(focusId);
  if (restoredFocus) {
    restoredFocus.focus({ preventScroll: true });
    if (selection && typeof restoredFocus.setSelectionRange === "function") {
      try { restoredFocus.setSelectionRange(...selection); } catch { /* Select controls have no selection range. */ }
    }
  }
}

function close() {
  persist();
  opened = false;
  refresh();
}

async function submit() {
  try {
    state = prepareSubmission(state, () => crypto.randomUUID());
  } catch (error) {
    state = { ...state, error: error.message };
    render();
    return;
  }
  persist(); render();
  try {
    const response = await fetch("/api/batches", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state.pending),
    });
    if (response.status === 400) {
      state = { ...state, pending: null, phase: "editing", error: "입력한 정보를 확인해 주세요." };
    } else {
      if (!response.ok) throw new Error();
      state = completeSubmission(state, await response.json());
    }
  } catch {
    state = markUnknown(state, "등록 결과를 받지 못했어요. 결과를 확인하거나 다시 시도해 주세요.");
  }
  persist(); render();
}

async function lookup() {
  try {
    const response = await fetch("/api/results/" + encodeURIComponent(state.pending.request_id), { cache: "no-store" });
    if (response.status === 404) {
      state = { ...state, error: "아직 등록되지 않았어요. 같은 내용으로 다시 시도할 수 있어요." };
    } else {
      if (!response.ok) throw new Error();
      state = completeSubmission(state, await response.json());
    }
  } catch {
    state = { ...state, error: "지금은 결과를 확인할 수 없어요. 작성한 내용은 보관돼 있어요." };
  }
  persist(); render();
}

refresh();
