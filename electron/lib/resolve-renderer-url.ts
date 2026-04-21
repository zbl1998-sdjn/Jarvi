export function resolveRendererUrl(devServerUrl: string | undefined): string {
  return devServerUrl ?? 'about:blank';
}
