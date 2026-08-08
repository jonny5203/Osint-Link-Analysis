import { useCallback, useState } from "react";

import {
  EMPTY_GRAPH,
  mergeGraphSlice,
  type GraphElements,
} from "../graph/graphAdapter";
import type { GraphNode, GraphSlice } from "../graphql/queries";
import { GraphExplorer } from "./GraphExplorer";
import { NodeDetailPanel } from "./NodeDetailPanel";
import { SearchBar } from "./SearchBar";

export function ExplorerWorkspace() {
  const [elements, setElements] = useState<GraphElements>(EMPTY_GRAPH);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const mergeSlice = useCallback((slice: GraphSlice, anchorId?: string) => {
    setElements((current) => {
      const result = mergeGraphSlice(current, slice, anchorId);

      if (result.rejectedEdgeIds.length > 0) {
        console.warn(
          "Ignored graph edges with missing endpoints:",
          result.rejectedEdgeIds,
        );
      }

      return result.elements;
    });
  }, []);

  function addSearchResult(node: GraphNode) {
    mergeSlice({ nodes: [node], edges: [], truncated: false });
    setSelectedNodeId(node.id);
  }

  return (
    <>
      <SearchBar onSelect={addSearchResult} />
      <section className="explorer-workspace">
        <GraphExplorer
          elements={elements}
          selectedNodeId={selectedNodeId}
          onExpand={mergeSlice}
          onSelectNode={setSelectedNodeId}
        />
        <NodeDetailPanel selectedNodeId={selectedNodeId} />
      </section>
    </>
  );
}
