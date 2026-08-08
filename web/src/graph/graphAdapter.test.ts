import { describe, expect, it } from "vitest";

import type { GraphEdge, GraphNode, GraphSlice } from "../graphql/queries";
import { EMPTY_GRAPH, mergeGraphSlice } from "./graphAdapter";

function node(id: string, displayName = id): GraphNode {
  return {
    id,
    displayName,
    kind: "PERSON",
    aliases: [],
    sanctioned: false,
    datasetIds: [],
  };
}

function edge(id: string, sourceId: string, targetId: string): GraphEdge {
  return {
    id,
    sourceId,
    targetId,
    type: "OWNS",
    label: "owns",
    confidence: null,
    reviewStatus: null,
  };
}

function slice(nodes: GraphNode[], edges: GraphEdge[] = []): GraphSlice {
  return { nodes, edges, truncated: false };
}

describe("mergeGraphSlice", () => {
  it("deduplicates stable node and edge IDs", () => {
    const graphSlice = slice(
      [node("avery"), node("northstar")],
      [edge("owns-1", "avery", "northstar")],
    );

    const first = mergeGraphSlice(EMPTY_GRAPH, graphSlice);
    const second = mergeGraphSlice(first.elements, graphSlice);

    expect(second.elements.nodes).toHaveLength(2);
    expect(second.elements.edges).toHaveLength(1);
    expect(second.elements.edges[0].data).toMatchObject({
      source: "avery",
      target: "northstar",
    });
    expect(second.rejectedEdgeIds).toEqual([]);
  });

  it("rejects an edge when either endpoint is absent", () => {
    const result = mergeGraphSlice(
      EMPTY_GRAPH,
      slice([node("avery")], [edge("broken", "avery", "missing")]),
    );

    expect(result.elements.nodes).toHaveLength(1);
    expect(result.elements.edges).toEqual([]);
    expect(result.rejectedEdgeIds).toEqual(["broken"]);
  });

  it("preserves existing positions and places new nodes around the expansion anchor", () => {
    const initial = mergeGraphSlice(EMPTY_GRAPH, slice([node("avery")])).elements;
    const originalPosition = initial.nodes[0].position;

    const expanded = mergeGraphSlice(
      initial,
      slice(
        [node("avery", "Avery Stone"), node("northstar")],
        [edge("owns-1", "avery", "northstar")],
      ),
      "avery",
    ).elements;

    expect(expanded.nodes.find(({ data }) => data.id === "avery")?.position).toEqual(
      originalPosition,
    );
    expect(
      expanded.nodes.find(({ data }) => data.id === "northstar")?.position,
    ).not.toEqual(originalPosition);
  });
});
