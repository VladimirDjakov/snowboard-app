import UploadForm from "../components/UploadForm";
import StatusPanel from "../components/StatusPanel";
import ArtifactList from "../components/ArtifactList";
import type { ArtifactsMap, VideoStatusResponse } from "../api/client";

export type UploadPageProps = {
  file: File | null;
  busy: boolean;
  phase: string;
  status: VideoStatusResponse | null;
  artifacts: ArtifactsMap | null;
  shareToken: string | null;
  videoId: string | null;
  limits: { max_duration_sec: number; max_size_bytes: number } | null;
  onFileChange: (file: File | null) => void;
  onSubmit: () => void;
  logs: string[];
};

export default function UploadPage({
  file,
  busy,
  phase,
  status,
  artifacts,
  shareToken,
  videoId,
  limits,
  onFileChange,
  onSubmit,
  logs
}: UploadPageProps) {
  return (
    <main>
      <section className="hero">
        <div className="label">Snowboard Coach</div>
        <h1>Upload a ride and watch the pipeline work.</h1>
        <p>
          A simple control panel for uploading a video, kicking off the analysis pipeline, and
          tracking artifacts.
        </p>
      </section>

      <section className="panel-grid">
        <UploadForm
          file={file}
          busy={busy}
          onFileChange={onFileChange}
          onSubmit={onSubmit}
          limits={limits}
        />
        <StatusPanel status={status} shareToken={shareToken} videoId={videoId} phase={phase} />
      </section>

      <section className="panel-grid">
        <ArtifactList artifacts={artifacts} />
        <div className="card">
          <div className="label">Live logs</div>
          <h2>Activity</h2>
          <p>Local client events to help you debug the upload flow.</p>
          <div className="log-box">
            {logs.length === 0 ? "Waiting for activity..." : logs.join("\n")}
          </div>
        </div>
      </section>
    </main>
  );
}
