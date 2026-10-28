export function normalizeCreate(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return { error: "object_required" };
  }
  const result = {};
  result.id = value.id === undefined ? null : value.id;
  result.name = value.name == null ? "" : String(value.name).trim();
  result.phone = value.phone == null ? "" : String(value.phone).replace(/[^0-9]/g, "");
  result.account = value.account == null ? "" : String(value.account).replace(/[^0-9]/g, "");
  result.active = value.active === undefined ? true : Boolean(value.active);
  return result;
}

export function normalizeUpdate(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return { error: "object_required" };
  }
  const result = {};
  if (Object.hasOwn(value, "id")) result.id = value.id === undefined ? null : value.id;
  if (Object.hasOwn(value, "name")) result.name = value.name == null ? "" : String(value.name).trim();
  if (Object.hasOwn(value, "phone")) result.phone = value.phone == null ? "" : String(value.phone).replace(/[^0-9]/g, "");
  if (Object.hasOwn(value, "account")) result.account = value.account == null ? "" : String(value.account).replace(/[^0-9]/g, "");
  if (Object.hasOwn(value, "active")) result.active = value.active === undefined ? true : Boolean(value.active);
  return result;
}
