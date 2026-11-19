export function saveBlob(blob: Blob, filename: string): void {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(anchor.href), 2000);
}

export function baseName(filename: string): string {
  return filename.replace(/\.[^.]+$/, "") || "image";
}

export function scrollToElement(id: string): void {
  setTimeout(() => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 50);
}
