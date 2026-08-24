import { useCallback, useEffect, useRef, useState } from "react";
import UploadPage from "./pages/Upload";
import {
  completeUpload,
  createVideo,
  fetchStatus,
  uploadVideoFile,
  type CreateVideoResponse,
  type VideoStatusResponse
} from "./api/client";

const terminalStates = new Set(["done", "failed", "canceled"]);

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [createData, setCreateData] = useState<CreateVideoResponse | null>(null);
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);
  const pollRef = useRef<number | null>(null);

  const appendLog = useCallback((message: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [`${time} ${message}`, ...prev].slice(0, 40));
  }, []);

  const clearPoll = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (videoId: string, shareToken: string) => {
      clearPoll();
      const poll = async () => {
        try {
          const nextStatus = await fetchStatus(videoId, shareToken);
          setStatus(nextStatus);
          if (terminalStates.has(nextStatus.status)) {
            setPhase(nextStatus.status);
            appendLog(`Pipeline finished with status: ${nextStatus.status}`);
            clearPoll();
          } else {
            setPhase("processing");
          }
        } catch (error) {
          appendLog(`Status error: ${(error as Error).message}`);
        }
      };

      poll();
      pollRef.current = window.setInterval(poll, 3500);
    },
    [appendLog, clearPoll]
  );

  useEffect(() => () => clearPoll(), [clearPoll]);

  const onSubmit = useCallback(async () => {
    if (!file) return;
    setBusy(true);
    setPhase("creating");
    setStatus(null);

    try {
      appendLog("Creating upload slot");
      const created = await createVideo(file);
      setCreateData(created);
      setPhase("uploading");
      appendLog("Uploading file to storage");
      await uploadVideoFile(created.upload, file);
      setPhase("processing");
      appendLog("Confirming upload with API");
      await completeUpload(created.video_id, created.share_token);
      appendLog("Pipeline queued. Polling status...");
      startPolling(created.video_id, created.share_token);
    } catch (error) {
      setPhase("failed");
      appendLog(`Upload failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }, [appendLog, file, startPolling]);

  return (
    <UploadPage
      file={file}
      busy={busy}
      phase={phase}
      status={status}
      artifacts={status?.artifacts ?? null}
      shareToken={createData?.share_token ?? null}
      videoId={createData?.video_id ?? null}
      limits={createData?.limits ?? null}
      onFileChange={setFile}
      onSubmit={onSubmit}
      logs={logs}
    />
  );
}
