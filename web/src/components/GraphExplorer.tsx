// PLAN.md T9.4: stateful Cytoscape component.
// TODO: init empty graph; on search-result click, fetch + render the node;
//       on node tap, fetch neighbors and merge; use fcose; style by label
//       (Person=blue circle, Org=green rect, Vessel=orange diamond, sanctioned=red border).
export function GraphExplorer() {
  return (
    <div className="graph-explorer">Graph canvas (T9)</div>
  );
}
