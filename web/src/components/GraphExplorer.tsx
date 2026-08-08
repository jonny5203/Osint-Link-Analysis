import { useApolloClient } from "@apollo/client";
import cytoscape, { type Core } from "cytoscape";
import { useEffect, useRef, useState } from "react";

import type { GraphElements } from "../graph/graphAdapter";
import {
  NEIGHBORHOOD,
  type GraphSlice,
} from "../graphql/queries";

type GraphExplorerProps = {
  elements: GraphElements;
  selectedNodeId: string | null;
  onExpand: (slice: GraphSlice, anchorId: string) => void;
  onSelectNode: (id: string) => void;
};

const GRAPH_STYLES: cytoscape.StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(displayName)",
      "font-size": 11,
      "text-wrap": "wrap",
      "text-max-width": "120px",
      "text-valign": "bottom",
      "text-margin-y": 7,
      width: 54,
      height: 54,
      "border-width": 2,
      "border-color": "#334155",
    },
  },
  {
    selector: 'node[kind = "PERSON"]',
    style: { shape: "ellipse", "background-color": "#3b82f6" },
  },
  {
    selector: 'node[kind = "ORGANIZATION"]',
    style: { shape: "round-rectangle", "background-color": "#22c55e" },
  },
  {
    selector: 'node[kind = "VESSEL"]',
    style: { shape: "diamond", "background-color": "#f59e0b" },
  },
  {
    selector: 'node[kind = "ADDRESS"]',
    style: { shape: "hexagon", "background-color": "#a855f7" },
  },
  {
    selector: "node[sanctioned = true]",
    style: {
      "border-width": 7,
      "border-color": "#b91c1c",
      "border-style": "double",
    },
  },
  {
    selector: "node:selected",
    style: { "overlay-color": "#0f172a", "overlay-opacity": 0.14 },
  },
  {
    selector: "edge",
    style: {
      label: "data(type)",
      "curve-style": "bezier",
      "font-size": 9,
      "line-color": "#64748b",
      "target-arrow-color": "#64748b",
      "target-arrow-shape": "triangle",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.85,
      "text-background-padding": "2px",
      width: 2,
    },
  },
  {
    selector: 'edge[type = "POSSIBLE_MATCH"]',
    style: {
      "line-style": "dashed",
      "line-color": "#c2410c",
      "target-arrow-color": "#c2410c",
    },
  },
];

export function GraphExplorer({
  elements,
  selectedNodeId,
  onExpand,
  onSelectNode,
}: GraphExplorerProps) {
  const isHeadless = import.meta.env.MODE === "test";
  const client = useApolloClient();
  const containerRef = useRef<HTMLDivElement>(null);
  const cytoscapeRef = useRef<Core | null>(null);
  const selectHandlerRef = useRef(onSelectNode);
  const [expanding, setExpanding] = useState(false);
  const [expansionError, setExpansionError] = useState(false);
  const [truncated, setTruncated] = useState(false);

  useEffect(() => {
    selectHandlerRef.current = onSelectNode;
  }, [onSelectNode]);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const instance = cytoscape({
      container: isHeadless ? undefined : containerRef.current,
      elements: [],
      headless: isHeadless,
      layout: { name: "preset" },
      style: GRAPH_STYLES,
    });
    const selectNode = (event: cytoscape.EventObject) => {
      selectHandlerRef.current(event.target.id());
    };

    instance.on("tap", "node", selectNode);
    cytoscapeRef.current = instance;

    return () => {
      instance.off("tap", "node", selectNode);
      instance.destroy();
      cytoscapeRef.current = null;
    };
  }, [isHeadless]);

  useEffect(() => {
    const instance = cytoscapeRef.current;
    if (!instance) {
      return;
    }

    instance.batch(() => {
      for (const node of elements.nodes) {
        const existing = instance.getElementById(node.data.id);
        if (existing.nonempty()) {
          existing.data(node.data);
        } else {
          instance.add({ group: "nodes", ...node });
        }
      }

      for (const edge of elements.edges) {
        const existing = instance.getElementById(edge.data.id);
        if (existing.nonempty()) {
          existing.data(edge.data);
        } else {
          instance.add({ group: "edges", ...edge });
        }
      }
    });

    if (!isHeadless) {
      instance.fit(undefined, 45);
    }
  }, [elements, isHeadless]);

  useEffect(() => {
    const instance = cytoscapeRef.current;
    if (!instance) {
      return;
    }

    instance.$(":selected").unselect();
    if (selectedNodeId) {
      instance.getElementById(selectedNodeId).select();
    }
  }, [selectedNodeId]);

  async function expandSelectedNode() {
    if (!selectedNodeId || expanding) {
      return;
    }

    setExpanding(true);
    setExpansionError(false);
    try {
      const { data } = await client.query({
        query: NEIGHBORHOOD,
        variables: {
          id: selectedNodeId,
          depth: 1,
          nodeLimit: 100,
          edgeLimit: 200,
        },
        fetchPolicy: "no-cache",
      });
      onExpand(data.neighborhood, selectedNodeId);
      setTruncated(data.neighborhood.truncated);
    } catch {
      setExpansionError(true);
    } finally {
      setExpanding(false);
    }
  }

  function reLayout() {
    const instance = cytoscapeRef.current;
    if (!instance || instance.nodes().length === 0) {
      return;
    }

    instance.layout({ name: "cose", animate: false, fit: true, padding: 45 }).run();
  }

  return (
    <section className="graph-explorer" aria-labelledby="graph-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Directed relationship view</p>
          <h2 id="graph-heading">Graph</h2>
        </div>
        <div className="graph-actions">
          <button
            type="button"
            disabled={!selectedNodeId || expanding}
            onClick={() => void expandSelectedNode()}
          >
            {expanding ? "Expanding…" : "Expand selected"}
          </button>
          <button type="button" className="secondary" onClick={reLayout}>
            Re-layout
          </button>
        </div>
      </div>
      {elements.nodes.length === 0 && (
        <p className="empty-state">Search for an entity and add it to begin.</p>
      )}
      {expansionError && (
        <p className="error-state" role="alert">
          The neighborhood could not be loaded. Try again.
        </p>
      )}
      {truncated && (
        <p className="warning-state" role="status">
          The API limit was reached; this neighborhood is incomplete.
        </p>
      )}
      <div
        ref={containerRef}
        className="cytoscape-canvas"
        data-testid="graph-canvas"
        aria-label="Interactive relationship graph"
      />
      <div className="graph-readable-summary">
        <section aria-labelledby="nodes-heading">
          <h3 id="nodes-heading">Nodes ({elements.nodes.length})</h3>
          <ul>
            {elements.nodes.map(({ data }) => (
              <li key={data.id}>
                <button
                  type="button"
                  aria-pressed={selectedNodeId === data.id}
                  onClick={() => onSelectNode(data.id)}
                >
                  {data.displayName} <small>{data.kind.toLowerCase()}</small>
                  {data.sanctioned && <span className="sanction-badge">sanctioned</span>}
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="relationships-heading">
          <h3 id="relationships-heading">Relationships ({elements.edges.length})</h3>
          {elements.edges.length === 0 ? (
            <p>Expand a node to load directed relationships.</p>
          ) : (
            <ul>
              {elements.edges.map(({ data }) => (
                <li key={data.id}>
                  <code>{data.sourceId}</code>
                  <span aria-hidden="true"> → </span>
                  <strong>{data.type}</strong>
                  <span aria-hidden="true"> → </span>
                  <code>{data.targetId}</code>
                  {data.type === "POSSIBLE_MATCH" && (
                    <span className="lead-badge">uncertain lead</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </section>
  );
}
