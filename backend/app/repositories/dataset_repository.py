"""Persistence for datasets and relationships."""

from collections.abc import Iterable, Sequence

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetRelationship


class DatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, dataset: Dataset) -> Dataset:
        self._session.add(dataset)
        self._session.commit()
        return dataset

    def get(self, dataset_id: str) -> Dataset | None:
        return self._session.get(Dataset, dataset_id)

    def list(self) -> Sequence[Dataset]:
        return self._session.scalars(select(Dataset).order_by(Dataset.created_at)).all()

    def get_many(self, dataset_ids: Iterable[str]) -> Sequence[Dataset]:
        return self._session.scalars(select(Dataset).where(Dataset.id.in_(list(dataset_ids)))).all()

    def table_names(self) -> set[str]:
        return set(self._session.scalars(select(Dataset.table_name)).all())

    def delete(self, dataset: Dataset) -> None:
        self._session.execute(
            delete(DatasetRelationship).where(
                or_(
                    DatasetRelationship.left_dataset_id == dataset.id,
                    DatasetRelationship.right_dataset_id == dataset.id,
                )
            )
        )
        self._session.delete(dataset)
        self._session.commit()

    def add_relationships(self, relationships: Iterable[DatasetRelationship]) -> None:
        self._session.add_all(list(relationships))
        self._session.commit()

    def list_relationships(self, dataset_ids: Iterable[str] | None = None) -> Sequence[DatasetRelationship]:
        query = select(DatasetRelationship)
        if dataset_ids is not None:
            ids = list(dataset_ids)
            query = query.where(
                DatasetRelationship.left_dataset_id.in_(ids),
                DatasetRelationship.right_dataset_id.in_(ids),
            )
        return self._session.scalars(query).all()
