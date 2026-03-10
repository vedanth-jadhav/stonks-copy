function formatCurrency(value) {
  if (value === null || value === void 0 || Number.isNaN(value)) return "--";
  return `Rs.${Math.round(value).toLocaleString("en-IN")}`;
}
function formatSignedPercent(value) {
  if (value === null || value === void 0 || Number.isNaN(value)) return "--";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}
function formatPercent(value) {
  if (value === null || value === void 0 || Number.isNaN(value)) return "--";
  return `${value.toFixed(2)}%`;
}
function formatDateTime(value) {
  if (!value) return "--";
  return new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });
}
function formatDate(value) {
  if (!value) return "--";
  return new Date(value).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}
export {
  formatCurrency as a,
  formatSignedPercent as b,
  formatPercent as c,
  formatDate as d,
  formatDateTime as f
};
