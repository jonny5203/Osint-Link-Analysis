package io.nexus.api.query.dto;

import java.util.List;

public record EntityDetailDto(
    GraphNodeDto node,
    String normalizedName,
    List<String> datesOfBirth,
    List<String> nationalities,
    String jurisdiction,
    String registrationNumber,
    String imo,
    String flag,
    List<String> programs,
    List<SourceRecordSummaryDto> sourceRecords,
    List<MatchExplanationDto> matches
) {
    public EntityDetailDto {
        datesOfBirth = List.copyOf(datesOfBirth);
        nationalities = List.copyOf(nationalities);
        programs = List.copyOf(programs);
        sourceRecords = List.copyOf(sourceRecords);
        matches = List.copyOf(matches);
    }
}
