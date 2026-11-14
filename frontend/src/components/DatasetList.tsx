import type { Dataset } from "../types/api";
import { DatasetCard } from "./DatasetCard";

interface DatasetListProps {
  datasets: Dataset[];
  onRemove: (id: string) => void;
}

export function DatasetList({ datasets, onRemove }: DatasetListProps) {
  if (datasets.length === 0) return <p className="empty-note">No datasets yet.</p>;
  return (
    <ul className="card-list">
      {datasets.map((dataset) => (
        <DatasetCard
          key={dataset.id}
          dataset={dataset}
          onRemove={onRemove}
        />
      ))}
    </ul>
  );
}
