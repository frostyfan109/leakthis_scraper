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
// Multiple mainTypes can have the same subtype, e.g., "video/mp4" and "audio/mp4".
// This shouldn't matter though, since it can be differentiated by checking the main type.
export const FileSubType = Object.freeze({
  // Audio
  AAC: "AAC",
  WAV: "WAV",
  
  // Video
  MP4: "MP4",

  // Ambiguous
  MPEG: "MPEG",
  M4A: "M4A",
  OGG: "OGG",
  WEBM: "WEBM"
})
export const FileType = Object.freeze({
  ZIP: "ZIP",
  AUDIO: "AUDIO",
  VIDEO: "VIDEO",
  UNKNOWN: "UNKNOWN"
});
function getSubType(mimeSubType) {
  // Map mime subtype to FileSubType.
  switch (mimeSubType) {
    case "aac":
      return FileSubType.AAC;
    case "wav":
      return FileSubType.WAV;
    case "mp4":
      return FileSubType.MP4;
    case "mpeg":
      return FileSubType.MPEG;
    case "m4a":
    case "x-m4a":
      return FileSubType.M4A;
    case "ogg":
      return FileSubType.OGG;
    case "webm":
      return FileSubType.WEBM;
    default:
      return null;
  }
}
export function getFileType(mimeType) {
  if (!mimeType) return FileType.UNKNOWN;
  // Only split first segment before possible semi-colon.
  const split = mimeType.split(";")[0].split("/");
  const [mainType, mimeSubType] = mimeType.split("/");
  let type;
  let subType = getSubType(mimeSubType);
  if (
    mimeType === "application/zip" ||
    mimeType === "application/zip-compressed" ||
    mimeType === "multipart/x-zip" ||
    mimeType == "application/x-zip-compressed") {
      type = FileType.ZIP;
  }
  else if (mainType === "audio") {
    type = FileType.AUDIO;
  }
  else if (mainType === "video") {
    type = FileType.VIDEO;
  }
  else type = FileType.UNKNOWN;
  return [type, subType];
}

export const palette1 = [
  "#488f31",
  "#a7c162",
  "#fff59f",
  "#f49e5c",
  "#de425b"
].reverse();
export const pastel = [
  "#ffadad",
  "#ffd6a5",
  "#fdffb6",
  "#caffbf",
  "#9bf6ff",
  "#a0c4ff",
  "#bdb2ff",
  "#ffc6ff"
];
export const palette3 = [
  "#ef476f",
  "#ffd166",
  "#06d6a0",
  "#118ab2",
  "#073b4c"
];
const defaultPalette = palette3;
export const getColor = (i, colors=defaultPalette) => colors[i % colors.length]; 
/* Currently doesn't scale `hueShift` down based on cycles past 360deg, since this isn't necessary right now. */
export function getColorHueShift(i, hueShift=60, colors=defaultPalette) {
  const shifts = Math.floor(i / colors.length);
  const index = i % colors.length;
  const rawColor = colors[index];
  const hslColor = hexToHsl(rawColor);
  hslColor.h += ((hueShift * shifts) / 360) % 360;
  const adjustedColor = hslToHex(hslColor.h, hslColor.s, hslColor.l);
  return adjustedColor;
}
/** https://gist.github.com/xenozauros/f6e185c8de2a04cdfecf */
function hexToHsl(hex) {
  var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    let r = parseInt(result[1], 16);
    let g = parseInt(result[2], 16);
    let b = parseInt(result[3], 16);
    r /= 255; g /= 255; b /= 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b);
    var h, s, l = (max + min) / 2;
    if(max == min){
      h = s = 0; // achromatic
    }else{
      var d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch(max){
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h /= 6;
    }
  var HSL = new Object();
  HSL['h']=h;
  HSL['s']=s;
  HSL['l']=l;
  return HSL;
}
/** Slightly modified from: https://stackoverflow.com/a/44134328
 * 
 * @param {h} - [0, 1]
 * @param {s} - [0, 1]
 * @param {l} - [0, 1]
 */
function hslToHex(h, s, l) {
  h = 360 * h;
  s *= 100;
  const a = s * Math.min(l, 1 - l) / 100;
  const f = n => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');   // convert to Hex and prefix "0" if needed
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}