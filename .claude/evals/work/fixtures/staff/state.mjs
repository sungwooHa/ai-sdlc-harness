import { emptyEmployee, employeeErrors } from "./fields.mjs";

export function emptyState() {
  return { rows: [], current: emptyEmployee(), pending: null, phase: "editing", result: null, error: "" };
}

export function isUntouched(employee) {
  const blank = emptyEmployee();
  return Object.keys(blank).every((key) => employee[key] === blank[key]);
}

export function addCurrent(state) {
  const errors = employeeErrors(state.current, state.rows);
  if (errors.length) throw new Error(errors[0]);
  return { ...state, rows: [...state.rows, { ...state.current }], current: emptyEmployee(), error: "" };
}

export function prepareSubmission(state, makeId) {
  if (isUntouched(state.current)) throw new Error("직원 정보를 입력해 주세요.");
  const entries = [...state.rows, state.current];
  if (!entries.length) throw new Error("등록할 직원을 입력해 주세요.");
  if (entries.length > 10) throw new Error("한 번에 10명까지 등록할 수 있어요.");
  for (let index = 0; index < entries.length; index += 1) {
    const errors = employeeErrors(entries[index], entries.slice(0, index));
    if (errors.length) throw new Error(errors[0]);
  }
  return {
    ...state, phase: "saving", error: "",
    pending: { request_id: makeId(), entries: entries.map((entry) => ({ ...entry })) },
  };
}

export function markUnknown(state, message) {
  return { ...state, phase: "unknown", error: message };
}

export function completeSubmission(state, result) {
  if (!state.pending || result.request_id !== state.pending.request_id) {
    throw new Error("등록 결과를 확인해 주세요.");
  }
  return { ...emptyState(), phase: "complete", result: { ...result } };
}
