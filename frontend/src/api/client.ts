export type UploadInfo = {
  method: string;
  url: string;
  headers: Record<string, string>;
  storage_path: string;
  expires_in_sec: number;
};

export type CreateVideoResponse = {
  video_id: string;
  share_token: string;
  upload: UploadInfo;
  limits: { max_duration_sec: number; max_size_bytes: number };
};

export type StageInfo = {
  name: string;
  status: string;
  started_at?: string | null;
  ended_at?: string | null;
};

export type ArtifactInfo = {
  kind: string;
  version: string;
  url: string | null;
  expires_in_sec: number | null;
};

export type ArtifactsMap = {
  original: ArtifactInfo | null;
  normalized: ArtifactInfo | null;
  keypoints: ArtifactInfo | null;
  features: ArtifactInfo | null;
  feedback: ArtifactInfo | null;
};

export type VideoStatusResponse = {
  video_id: string;
  status: string;
  pipeline_version: string | null;
  progress: {
    pct: number;
    stage: string;
    stage_pct: number;
    eta_sec: number | null;
    updated_at: string | null;
  } | null;
  stages: StageInfo[];
  artifacts: ArtifactsMap;
  errors: string[];
};

const apiBase = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

const withBase = (path: string) => (apiBase ? `${apiBase}${path}` : path);

export async function createVideo(file: File): Promise<CreateVideoResponse> {
  const response = await fetch(withBase("/v1/videos"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type || "video/mp4",
      size_bytes: file.size
    })
  });

  if (!response.ok) {
    throw new Error(`Create video failed: ${response.status}`);
  }

  return response.json();
}

export async function uploadVideoFile(upload: UploadInfo, file: File): Promise<void> {
  const headers = new Headers(upload.headers || {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", file.type || "video/mp4");
  }

  const response = await fetch(upload.url, {
    method: upload.method || "PUT",
    headers,
    body: file
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }
}

export async function completeUpload(videoId: string, shareToken: string): Promise<void> {
  const response = await fetch(withBase(`/v1/videos/${videoId}/complete-upload`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      share_token: shareToken,
      client: {
        user_agent: navigator.userAgent,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
      }
    })
  });

  if (!response.ok) {
    throw new Error(`Complete upload failed: ${response.status}`);
  }
}

export async function fetchStatus(
  videoId: string,
  shareToken: string
): Promise<VideoStatusResponse> {
  const url = withBase(`/v1/videos/${videoId}?share_token=${encodeURIComponent(shareToken)}`);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Status fetch failed: ${response.status}`);
  }

  return response.json();
}
