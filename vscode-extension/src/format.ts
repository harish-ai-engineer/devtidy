const UNITS = ["B", "KB", "MB", "GB", "TB"];

export function humanSize(bytes: number): string {
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const rendered = value >= 100 || unit === 0 ? Math.round(value).toString() : value.toFixed(1);
  return `${rendered} ${UNITS[unit]}`;
}

export function humanAge(lastActivityEpochSeconds: number): string {
  const days = Math.floor((Date.now() / 1000 - lastActivityEpochSeconds) / 86400);
  if (days < 1) {
    return "active today";
  }
  if (days < 30) {
    return `${days}d idle`;
  }
  if (days < 365) {
    return `${Math.floor(days / 30)}mo idle`;
  }
  return `${Math.floor(days / 365)}y idle`;
}
