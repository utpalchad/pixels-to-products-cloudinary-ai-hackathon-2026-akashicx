export type CloudinaryPrepOptions = {
  removeBackground: boolean;
  restore: boolean;
  upscale: boolean;
  improve: boolean;
  width?: number;
  height?: number;
};

const UPLOAD_MARKER = "/image/upload/";
const UPSCALE_PIXEL_LIMIT = 4_200_000;

export function canCloudinaryUpscale(width?: number, height?: number) {
  if (!width || !height) return false;
  return width * height < UPSCALE_PIXEL_LIMIT;
}

export function buildCloudinaryPrepUrl(
  url: string,
  options: CloudinaryPrepOptions,
) {
  if (!url || !url.includes(UPLOAD_MARKER)) return url;

  const steps: string[] = [];

  // Restore must run before background removal because gen_restore
  // does not support transparent input images.
  if (options.restore) steps.push("e_gen_restore");
  if (options.improve) steps.push("e_improve");

  if (
    options.upscale &&
    canCloudinaryUpscale(options.width, options.height)
  ) {
    steps.push("e_upscale");
  }

  if (options.removeBackground) {
    steps.push("e_background_removal");
  }

  if (!steps.length) return url;

  return url.replace(
    UPLOAD_MARKER,
    `${UPLOAD_MARKER}${steps.join("/")}/`,
  );
}

export function buildCloudinaryPreviewUrl(
  url: string,
  options: CloudinaryPrepOptions,
) {
  const prepared = buildCloudinaryPrepUrl(url, options);
  if (!prepared || !prepared.includes(UPLOAD_MARKER)) return prepared;

  // Browser delivery optimization is separate from the high-detail AI input.
  // Keep transparency-safe delivery when background removal is enabled.
  const delivery = options.removeBackground ? "q_auto" : "q_auto/f_auto";

  return prepared.replace(
    UPLOAD_MARKER,
    `${UPLOAD_MARKER}${delivery}/`,
  );
}
