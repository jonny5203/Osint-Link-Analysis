package io.nexus.api.query.dto;

public record GraphEdgeDto(
    String id,
    String sourceId,
    String targetId,
    String type,
    String label,
    Double confidence,
    String reviewStatus
) {}
