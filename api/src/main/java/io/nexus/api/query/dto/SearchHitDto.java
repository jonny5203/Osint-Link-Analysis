package io.nexus.api.query.dto;

public record SearchHitDto(
    GraphNodeDto node,
    double score
) {}
