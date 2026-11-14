import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { Dataset, Relationship, UploadFailure } from "../types/api";

export interface UseDatasets {
  datasets: Dataset[];
  relationships: Relationship[];
  uploading: boolean;
  error: string | null;
  failures: UploadFailure[];
  upload: (files: File[]) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export function useDatasets(): UseDatasets {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failures, setFailures] = useState<UploadFailure[]>([]);

  useEffect(() => {
    api
      .listDatasets()
      .then(setDatasets)
      .catch((e: Error) => setError(e.message));
    // Join suggestions are a nicety; a failure here must not surface as an error.
    api.listRelationships().then(setRelationships).catch(() => undefined);
  }, []);

  const upload = useCallback(async (files: File[]) => {
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadDatasets(files);
      setDatasets((prev) => [...prev, ...result.datasets]);
      setRelationships((prev) => [...prev, ...result.relationships]);
      setFailures(result.failures);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    try {
      await api.deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
      setRelationships((prev) =>
        prev.filter((r) => r.left_dataset_id !== id && r.right_dataset_id !== id),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  return { datasets, relationships, uploading, error, failures, upload, remove };
}
