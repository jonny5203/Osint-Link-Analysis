package io.nexus.api.query.dto;

import java.util.List;

public record MatchExplanationDto(
    String edgeId,
    String otherEntityId,
    String type,
    Double score,
    List<String> reasons,
    String algorithmVersion,
    String decidedAt,
    String decisionSource,
    String reviewStatus
) {
    public MatchExplanationDto {
        reasons = List.copyOf(reasons);
    }
}
