package io.nexus.api.query.dto;

import java.util.List;

public record GraphSliceDto(
    List<GraphNodeDto> nodes,
    List<GraphEdgeDto> edges,
    boolean truncated
) {
    public GraphSliceDto {
        nodes = List.copyOf(nodes);
        edges = List.copyOf(edges);
    }
}
