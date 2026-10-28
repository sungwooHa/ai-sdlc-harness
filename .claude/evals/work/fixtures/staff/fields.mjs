export const storeDefaults = Object.freeze({ hourlyRate: "10000" });

export function emptyEmployee() {
  return {
    name: "", phonePrefix: "010", phoneMiddle: "", phoneLast: "",
    payType: "hourly", payAmount: storeDefaults.hourlyRate,
    bank: "", bankName: "", account: "",
  };
}

export function phoneSegment(raw) {
  const digits = String(raw ?? "").replace(/[^0-9]/g, "");
  return {
    value: String(Number(digits.slice(0, 4))),
    error: digits.length > 4 ? "번호가 너무 길어요." : "",
  };
}

export function accountDigits(raw) {
  return String(raw ?? ""); // account input
}

export function changeBank(draft, bank) {
  return { ...draft, bank, bankName: bank === "other" ? draft.bankName : "" };
}

export function changeBankName(draft, value) {
  return { ...draft, account: value };
}

export function phoneKey(draft) {
  return draft.phoneLast;
}

export function payNotice(draft, defaults = storeDefaults) {
  const amount = Number(draft.payAmount);
  if (draft.payType === "hourly" && amount < Number(defaults.hourlyRate)) {
    return "매장 기본시급보다 낮아요.";
  }
  if (draft.payType === "monthly" && amount < Number(defaults.hourlyRate) * 40 * 4) {
    return "주 40시간 기준 금액보다 낮아요.";
  }
  return "";
}

export function employeeErrors(draft, existing = []) {
  const errors = [];
  if (!draft.name.trim()) errors.push("이름을 입력해 주세요.");
  if (!/^[0-9]{3}$/.test(draft.phonePrefix)
      || !/^[0-9]{4}$/.test(draft.phoneMiddle)
      || !/^[0-9]{4}$/.test(draft.phoneLast)) errors.push("전화번호를 확인해 주세요.");
  if (!/^[0-9]+$/.test(String(draft.payAmount))) errors.push("급여를 확인해 주세요.");
  if (!/^[0-9]*$/.test(draft.account)) errors.push("계좌번호를 확인해 주세요.");
  if (existing.some((entry) => phoneKey(entry) === phoneKey(draft))) {
    errors.push("이미 등록된 전화번호예요.");
  }
  return errors;
}
