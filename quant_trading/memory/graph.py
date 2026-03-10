from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from quant_trading.db.models import MemoryEdge, MemoryNode
from quant_trading.memory.semantic import dense_similarity, sparse_similarity


@dataclass(frozen=True, slots=True)
class GraphHit:
    ref_id: str
    content: str
    node_type: str
    score: float


class GraphMemory:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_episode(self, ref_id: str, content: str, metadata: dict | None = None) -> None:
        node = self.session.query(MemoryNode).filter(MemoryNode.ref_id == ref_id).one_or_none()
        if node is None:
            node = MemoryNode(node_type="episode", ref_id=ref_id, content=content, details=metadata or {})
            self.session.add(node)
        else:
            node.content = content
            node.details = metadata or {}
        self.session.commit()

    def relate(self, source_ref: str, target_ref: str, relation: str, metadata: dict | None = None) -> None:
        edge = (
            self.session.query(MemoryEdge)
            .filter(
                MemoryEdge.source_ref == source_ref,
                MemoryEdge.target_ref == target_ref,
                MemoryEdge.relation == relation,
            )
            .one_or_none()
        )
        if edge is None:
            edge = MemoryEdge(
                source_ref=source_ref,
                target_ref=target_ref,
                relation=relation,
                details=metadata or {},
            )
            self.session.add(edge)
        else:
            edge.details = metadata or {}
        self.session.commit()

    def search(self, query: str, limit: int = 5) -> list[str]:
        return [hit.content for hit in self.search_hits(query=query, limit=limit)]

    def search_hits(self, query: str, limit: int = 5) -> list[GraphHit]:
        terms = [term.strip().lower() for term in query.split() if term.strip()]
        stmt = self.session.query(MemoryNode)
        if terms:
            clauses = [
                or_(
                    MemoryNode.content.ilike(f"%{term}%"),
                    MemoryNode.ref_id.ilike(f"%{term}%"),
                    MemoryNode.node_type.ilike(f"%{term}%"),
                )
                for term in terms
            ]
            stmt = stmt.filter(or_(*clauses))

        hits: list[GraphHit] = []
        for node in stmt.limit(max(limit * 3, limit)).all():
            haystack = f"{node.ref_id} {node.node_type} {node.content}".lower()
            score = float(sum(3 for term in terms if term in node.ref_id.lower()))
            score += float(sum(2 for term in terms if term in node.node_type.lower()))
            score += float(sum(1 for term in terms if term in haystack))
            score += sparse_similarity(query, haystack) * 5.0
            dense_score = dense_similarity(query, haystack)
            if dense_score is not None:
                score += dense_score * 4.0
            hits.append(GraphHit(ref_id=node.ref_id, content=node.content, node_type=node.node_type, score=score))

        hits.sort(key=lambda item: (-item.score, item.ref_id))
        return hits[:limit]
