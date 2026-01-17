import type { VideoStatusResponse } from "../api/client";

export type VideoResultProps = {
  status: VideoStatusResponse;
};

export default function VideoResult({ status }: VideoResultProps) {
  return (
    <section className="card">
      <div className="label">Result</div>
      <h2>Pipeline summary</h2>
      <p>Status: {status.status}</p>
      <p>Pipeline version: {status.pipeline_version || "—"}</p>
    </section>
  );
}
