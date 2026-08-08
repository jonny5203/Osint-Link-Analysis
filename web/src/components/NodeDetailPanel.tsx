import { useApolloClient } from "@apollo/client";
import { useEffect, useRef, useState } from "react";

import {
  ENTITY,
  type EntityDetail,
  type EntityResult,
} from "../graphql/queries";

type DetailLoader = (id: string) => Promise<EntityResult>;

type NodeDetailPanelProps = {
  selectedNodeId: string | null;
  detailLoader?: DetailLoader;
};

function Values({ values, empty = "None" }: { values: string[]; empty?: string }) {
  return <span>{values.length > 0 ? values.join(", ") : empty}</span>;
}

export function NodeDetailPanel({
  selectedNodeId,
  detailLoader,
}: NodeDetailPanelProps) {
  const client = useApolloClient();
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const requestGeneration = useRef(0);

  useEffect(() => {
    const generation = ++requestGeneration.current;

    if (!selectedNodeId) {
      return;
    }

    async function load() {
      await Promise.resolve();
      if (requestGeneration.current !== generation) {
        return;
      }

      setDetail(null);
      setError(false);
      setLoading(true);

      try {
        const data = detailLoader
          ? await detailLoader(selectedNodeId!)
          : (
              await client.query({
                query: ENTITY,
                variables: { id: selectedNodeId! },
                fetchPolicy: "no-cache",
              })
            ).data;

        if (requestGeneration.current === generation) {
          setDetail(data.entity);
        }
      } catch {
        if (requestGeneration.current === generation) {
          setError(true);
        }
      } finally {
        if (requestGeneration.current === generation) {
          setLoading(false);
        }
      }
    }

    void load();
  }, [client, detailLoader, selectedNodeId]);

  return (
    <aside className="node-detail" aria-labelledby="detail-heading">
      <p className="eyebrow">Selection</p>
      <h2 id="detail-heading">Entity details</h2>
      {!selectedNodeId && <p className="empty-state">Select a graph node to inspect it.</p>}
      {loading && <p role="status">Loading details…</p>}
      {error && (
        <p className="error-state" role="alert">
          Entity details could not be loaded. Try selecting the node again.
        </p>
      )}
      {selectedNodeId && !loading && !error && !detail && (
        <p className="empty-state">This entity no longer exists.</p>
      )}
      {detail && (
        <div className="detail-content">
          <div>
            <h3>{detail.node.displayName}</h3>
            <p>{detail.node.kind.toLowerCase()}</p>
          </div>
          <dl>
            <dt>ID</dt>
            <dd><code>{detail.node.id}</code></dd>
            <dt>Aliases</dt>
            <dd><Values values={detail.node.aliases} /></dd>
            <dt>Datasets</dt>
            <dd><Values values={detail.node.datasetIds} /></dd>
            <dt>Programs</dt>
            <dd><Values values={detail.programs} /></dd>
          </dl>

          <section aria-labelledby="provenance-heading">
            <h3 id="provenance-heading">Provenance</h3>
            {detail.sourceRecords.length === 0 ? (
              <p>No source records.</p>
            ) : (
              <ul className="provenance-list">
                {detail.sourceRecords.map((record) => (
                  <li key={record.id}>
                    <strong>{record.datasetName}</strong>
                    <dl>
                      <dt>Source record ID</dt>
                      <dd><code>{record.id}</code></dd>
                      <dt>External ID</dt>
                      <dd><code>{record.externalId}</code></dd>
                      <dt>Retrieved</dt>
                      <dd>{record.retrievedAt ?? "Unknown"}</dd>
                      <dt>Status</dt>
                      <dd>{record.active ? "Active" : "Inactive"}</dd>
                    </dl>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="matches-heading">
            <h3 id="matches-heading">Identity links</h3>
            {detail.matches.length === 0 ? (
              <p>No identity links.</p>
            ) : (
              <ul className="match-list">
                {detail.matches.map((match) => (
                  <li key={match.edgeId}>
                    <strong>{match.type}</strong> with <code>{match.otherEntityId}</code>
                    {match.type === "POSSIBLE_MATCH" && (
                      <p className="lead-notice">
                        This is a lead, not a verified identity fact.
                      </p>
                    )}
                    <p><Values values={match.reasons} empty="No explanation supplied" /></p>
                    <small>
                      Score: {match.score ?? "unknown"}; review: {match.reviewStatus ?? "not reviewed"}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}
