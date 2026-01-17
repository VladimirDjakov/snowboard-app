import type { ArtifactsMap } from "../api/client";

export type ArtifactListProps = {
  artifacts: ArtifactsMap | null;
};

const entries = (artifacts: ArtifactsMap | null) => {
  if (!artifacts) return [];
  return Object.values(artifacts).filter(Boolean) as NonNullable<ArtifactsMap[keyof ArtifactsMap]>[];
};

export default function ArtifactList({ artifacts }: ArtifactListProps) {
  const items = entries(artifacts);

  return (
    <div className="card">
      <div className="label">Step 3 · Outputs</div>
      <h2>Artifacts</h2>
      <p>Download or open generated artifacts as they become available.</p>
      <div className="artifact-list">
        {items.length === 0 && <div style={{ color: "var(--muted)" }}>No artifacts yet.</div>}
        {items.map((artifact) => (
          <a
            key={`${artifact.kind}-${artifact.version}`}
            className="artifact-link"
            href={artifact.url || "#"}
            target="_blank"
            rel="noreferrer"
          >
            <span>{artifact.kind}</span>
            <span>{artifact.url ? "Open" : "Pending"}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
