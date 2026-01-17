import type { StageInfo, VideoStatusResponse } from "../api/client";

export type StatusPanelProps = {
  status: VideoStatusResponse | null;
  shareToken: string | null;
  videoId: string | null;
  phase: string;
};

const badgeClass = (status: string) => {
  if (status === "done") return "badge done";
  if (status === "failed") return "badge failed";
  return "badge";
};

const toPct = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return 0;
  return Math.min(100, Math.max(0, Math.round(value * 100)));
};

const deriveProgress = (stages: StageInfo[]) => {
  if (!stages.length) return 0;
  const done = stages.filter((stage) => stage.status === "done").length;
  return Math.round((done / stages.length) * 100);
};

export default function StatusPanel({ status, shareToken, videoId, phase }: StatusPanelProps) {
  const pct = status?.progress ? toPct(status.progress.pct) : deriveProgress(status?.stages || []);

  return (
    <div className="card">
      <div className="label">Step 2 · Status</div>
      <h2>Pipeline progress</h2>
      <p>Track normalization, pose, features, and feedback in real-time.</p>
      <div className="progress-bar">
        <span style={{ width: `${pct}%` }} />
      </div>
      <div style={{ marginTop: 10, color: "var(--muted)" }}>
        {phase.toUpperCase()} · {pct}%
      </div>

      <div style={{ marginTop: 14, display: "grid", gap: 6, color: "var(--muted)" }}>
        <div>Video ID: {videoId || "—"}</div>
        <div>Share token: {shareToken ? `${shareToken.slice(0, 8)}...` : "—"}</div>
      </div>

      <ul className="stage-list">
        {(status?.stages || []).map((stage) => (
          <li className="stage-item" key={stage.name}>
            <span>{stage.name}</span>
            <span className={badgeClass(stage.status)}>{stage.status}</span>
          </li>
        ))}
        {!status?.stages?.length && (
          <li className="stage-item">
            <span>Waiting for job</span>
            <span className="badge">idle</span>
          </li>
        )}
      </ul>
    </div>
  );
}
