package io.nexus.api.query.dto;

public record SourceRecordSummaryDto(
    String id,
    String datasetId,
    String datasetName,
    String externalId,
    String retrievedAt,
    String recordHash,
    boolean active
) {}
