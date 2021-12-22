// https://stackoverflow.com/a/55987414
export function abbrNum(n) {
  if (n < 1e3) return n;
  if (n >= 1e3 && n < 1e6) return +(n / 1e3).toFixed(1) + "K";
  if (n >= 1e6 && n < 1e9) return +(n / 1e6).toFixed(1) + "M";
  if (n >= 1e9 && n < 1e12) return +(n / 1e9).toFixed(1) + "B";
  if (n >= 1e12) return +(n / 1e12).toFixed(1) + "T";
}
export function linkToPost(post) {
  return window.location.pathname;
}
export function delay(timeout) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(), timeout);
  });
}