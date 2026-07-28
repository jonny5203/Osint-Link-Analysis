package io.nexus.api.query.dto;

import java.util.List;

public record GraphNodeDto(
    String id,
    EntityKind kind,
    String displayName,
    List<String> aliases,
    boolean sanctioned,
    List<String> datasetIds
) {
    public GraphNodeDto {
        aliases = List.copyOf(aliases);
        datasetIds = List.copyOf(datasetIds);
    }
}
