import { useMemo } from "react";

export type UploadFormProps = {
  file: File | null;
  busy: boolean;
  onFileChange: (file: File | null) => void;
  onSubmit: () => void;
  limits?: { max_duration_sec: number; max_size_bytes: number } | null;
};

export default function UploadForm({
  file,
  busy,
  onFileChange,
  onSubmit,
  limits
}: UploadFormProps) {
  const fileSize = useMemo(() => {
    if (!file) return "";
    const mb = file.size / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  }, [file]);

  return (
    <div className="card">
      <div className="label">Step 1 · Upload</div>
      <h2>Select a video file</h2>
      <p>We will create an upload slot, push your file, then kick off the pipeline.</p>
      <label className={`file-button ${busy ? "disabled" : ""}`}>
        <input
          className="file-input"
          type="file"
          accept="video/*"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          disabled={busy}
        />
        Choose file
      </label>
      <div style={{ marginTop: 12, color: "var(--muted)" }}>
        {file ? `Selected: ${file.name} (${fileSize})` : "No file selected"}
      </div>
      {limits && (
        <div style={{ marginTop: 8, color: "var(--muted)" }}>
          Max size: {(limits.max_size_bytes / (1024 * 1024)).toFixed(0)} MB · Max duration:
          {" "}{limits.max_duration_sec}s
        </div>
      )}
      <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="button" onClick={onSubmit} disabled={!file || busy}>
          {busy ? "Uploading..." : "Start upload"}
        </button>
        <button className="button ghost" type="button" onClick={() => onFileChange(null)}>
          Clear
        </button>
      </div>
    </div>
  );
}
