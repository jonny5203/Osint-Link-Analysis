import type {
  GraphEdge,
  GraphNode,
  GraphSlice,
} from "../graphql/queries";

export type GraphNodeElement = {
  data: GraphNode;
  position: { x: number; y: number };
};

export type GraphEdgeElement = {
  data: GraphEdge & { source: string; target: string };
};

export type GraphElements = {
  nodes: GraphNodeElement[];
  edges: GraphEdgeElement[];
};

export type GraphMergeResult = {
  elements: GraphElements;
  rejectedEdgeIds: string[];
};

export const EMPTY_GRAPH: GraphElements = { nodes: [], edges: [] };

const NEW_NODE_RADIUS = 170;

function nextUnanchoredPosition(index: number) {
  const column = index % 4;
  const row = Math.floor(index / 4);
  return { x: 130 + column * 190, y: 120 + row * 150 };
}

function nextAnchoredPosition(
  anchor: { x: number; y: number },
  index: number,
  total: number,
) {
  const angle = (2 * Math.PI * index) / Math.max(total, 1);
  return {
    x: anchor.x + Math.cos(angle) * NEW_NODE_RADIUS,
    y: anchor.y + Math.sin(angle) * NEW_NODE_RADIUS,
  };
}

export function mergeGraphSlice(
  current: GraphElements,
  slice: GraphSlice,
  anchorId?: string,
): GraphMergeResult {
  const existingNodes = new Map(current.nodes.map((node) => [node.data.id, node]));
  const incomingNodes = new Map(slice.nodes.map((node) => [node.id, node]));
  const newNodes = [...incomingNodes.values()].filter(
    (node) => !existingNodes.has(node.id),
  );
  const anchor = anchorId ? existingNodes.get(anchorId)?.position : undefined;

  const nodes = current.nodes.map((element) => {
    const updated = incomingNodes.get(element.data.id);
    return updated ? { ...element, data: updated } : element;
  });

  newNodes.forEach((node, index) => {
    nodes.push({
      data: node,
      position: anchor
        ? nextAnchoredPosition(anchor, index, newNodes.length)
        : nextUnanchoredPosition(nodes.length),
    });
  });

  const knownNodeIds = new Set(nodes.map((node) => node.data.id));
  const existingEdges = new Map(current.edges.map((edge) => [edge.data.id, edge]));
  const rejectedEdgeIds: string[] = [];

  for (const edge of slice.edges) {
    if (!knownNodeIds.has(edge.sourceId) || !knownNodeIds.has(edge.targetId)) {
      rejectedEdgeIds.push(edge.id);
      continue;
    }

    existingEdges.set(edge.id, {
      data: { ...edge, source: edge.sourceId, target: edge.targetId },
    });
  }

  return {
    elements: { nodes, edges: [...existingEdges.values()] },
    rejectedEdgeIds,
  };
}
