package io.nexus.api.query.input_validation;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Result;
import org.neo4j.driver.Values;
import org.neo4j.driver.types.Node;
import org.neo4j.driver.types.Relationship;
import org.springframework.stereotype.Service;

import io.nexus.api.query.dto.EntityDetailDto;
import io.nexus.api.query.dto.EntityKind;
import io.nexus.api.query.dto.GraphEdgeDto;
import io.nexus.api.query.dto.GraphNodeDto;
import io.nexus.api.query.dto.GraphSliceDto;
import io.nexus.api.query.dto.MatchExplanationDto;
import io.nexus.api.query.dto.SearchHitDto;
import io.nexus.api.query.dto.SourceRecordSummaryDto;

@Service
public class GraphQueryService {
    private final Driver driver;

    private static final int DEFAULT_NODE_LIMIT = 100;
    private static final int MAX_NODE_LIMIT = 200;
    private static final int DEFAULT_EDGE_LIMIT = 200;
    private static final int MAX_EDGE_LIMIT = 500;

    private static final String SEARCH_QUERY = """
        CALL db.index.fulltext.queryNodes(
            "entity_name_search",
            $term
        )
        YIELD node, score
        
        OPTIONAL MATCH
            (record:SourceRecord)-[:DESCRIBES]->(node)
        
        WITH node,
            score,
            collect(DISTINCT record.dataset_id) AS datasetIds,
            count(
                CASE
                    WHEN coalesce(record.active, false)
                    THEN 1
                END
            ) > 0 AS sanctioned
        
        RETURN node.id AS id,
            node.kind AS kind,
            node.display_name AS displayName,
            coalesce(node.aliases, []) AS aliases,
            datasetIds,
            sanctioned,
            score
        
        ORDER BY score DESC, id ASC
        LIMIT $limit
    """;

    private static final String ENTITY_SOURCE_RECORDS_QUERY = """
        MATCH
            (record:SourceRecord)-[:DESCRIBES]->
            (:Entity {id: $id})
        MATCH
            (record)-[:FROM_DATASET]->(dataset:Dataset)
        OPTIONAL MATCH
            (record)-[:OBSERVED_IN]->(run:ImportRun)

        WITH record,
            dataset,
            max(run.started_at) AS retrievedAt

        RETURN record.id AS id,
            dataset.id AS datasetId,
            dataset.name AS datasetName,
            record.external_id AS externalId,
            retrievedAt,
            record.record_hash AS recordHash,
            coalesce(record.active, false) AS active

        ORDER BY datasetId, externalId
    """;

    private static final String ENTITY_MATCHES_QUERY = """
        MATCH
            (entity:Entity {id: $id})
            -[relationship:SAME_AS|POSSIBLE_MATCH]-
            (other:Entity)

        RETURN other.id AS otherEntityId,
            type(relationship) AS type,
            relationship.score AS score,
            coalesce(relationship.reasons, []) AS reasons,
            relationship.algorithm_version AS algorithmVersion,
            relationship.decided_at AS decidedAt,
            relationship.decision_source AS decisionSource,
            relationship.review_status AS reviewStatus,
            startNode(relationship).id AS sourceId,
            endNode(relationship).id AS targetId

        ORDER BY type, otherEntityId
    """;

    private static final String ENTITY_QUERY = """
        MATCH (entity:Entity {id: $id})
        OPTIONAL MATCH
            (record:SourceRecord)-[:DESCRIBES]->(entity)
        OPTIONAL MATCH
            (record)-[:FROM_DATASET]->(dataset:Dataset)

        WITH entity,
            collect(DISTINCT dataset.id) AS datasetIds,
            count(
                CASE
                    WHEN coalesce(record.active, false)
                    THEN 1
                END
            ) > 0 AS sanctioned,
            collect(coalesce(record.programs, [])) AS programLists

        RETURN entity, datasetIds, sanctioned, programLists
    """;

    static final List<String> ANALYST_RELATIONSHIP_TYPES = List.of(
        "OWNS",
        "CONTROLS",
        "OFFICER_OF",
        "LOCATED_AT",
        "SAME_AS",
        "POSSIBLE_MATCH"
    );

    private static final String ANALYST_RELATIONSHIP_PATTERN = 
        String.join("|", ANALYST_RELATIONSHIP_TYPES);

    public GraphQueryService(Driver driver) {
        this.driver = driver;
    }

    public List<SearchHitDto> search(String rawTerm, Integer rawLimit) {
        String term = QueryInputs.searchTerm(rawTerm);
        int limit = QueryInputs.searchLimit(rawLimit);

        try (var session = driver.session()) {
            return session.executeRead(transaction ->
                transaction.run(
                    SEARCH_QUERY,
                    Map.of(
                        "term", QueryInputs.luceneLiteral(term),
                        "limit", limit
                    )
                ).list(record ->
                    new SearchHitDto(
                        new GraphNodeDto(
                            record.get("id").asString(),
                            EntityKind.valueOf(record.get("kind").asString()),
                            record.get("displayName").asString(),
                            record.get("aliases").asList(value -> value.asString()),
                            record.get("sanctioned").asBoolean(),
                            record.get("datasetIds").asList(value -> value.asString())
                        ),
                        record.get("score").asDouble()
                    )
                )
            );
        }
    }

    public Optional<EntityDetailDto> entity(String rawId) {
        String id = QueryInputs.id("id", rawId);

        try (var session = driver.session()) {
            return session.executeRead(transaction -> {
                Result result = transaction.run(
                    ENTITY_QUERY,
                    Values.parameters("id", id)
                );

                if (!result.hasNext()) {
                    return Optional.empty();
                }

                var entityRecord = result.single();
                Node node = entityRecord.get("entity").asNode();

                List<String> programs = entityRecord.get("programLists")
                    .asList(value ->
                        value.asList(item -> item.asString())
                    )
                    .stream()
                    .flatMap(List::stream)
                    .distinct()
                    .sorted()
                    .toList();

                List<String> aliases = node.get("aliases").isNull()
                    ? List.of()
                    : node.get("aliases").asList(value -> value.asString());

                String normalizedName = node.get("normalized_name").isNull()
                    ? node.get("normalized_address").asString(null)
                    : node.get("normalized_name").asString();

                List<SourceRecordSummaryDto> sourceRecords = transaction.run(
                    ENTITY_SOURCE_RECORDS_QUERY,
                    Values.parameters("id", id)
                ).list(record ->
                    new SourceRecordSummaryDto(
                        record.get("id").asString(),
                        record.get("datasetId").asString(),
                        record.get("datasetName").asString(),
                        record.get("externalId").asString(),
                        record.get("retrievedAt").asString(null),
                        record.get("recordHash").asString(),
                        record.get("active").asBoolean()
                    )
                );

                List<MatchExplanationDto> matches = transaction.run(
                    ENTITY_MATCHES_QUERY,
                    Values.parameters("id", id)
                ).list(record ->
                    new MatchExplanationDto(
                        StableEdgeIds.from(
                            record.get("sourceId").asString(),
                            record.get("type").asString(),
                            record.get("targetId").asString()
                        ),
                        record.get("otherEntityId").asString(),
                        record.get("type").asString(),
                        record.get("score").isNull()
                            ? null
                            : record.get("score").asDouble(),
                        record.get("reasons")
                            .asList(value -> value.asString()),
                        record.get("algorithmVersion").asString(null),
                        record.get("decidedAt").asString(null),
                        record.get("decisionSource").asString(null),
                        record.get("reviewStatus").asString(null)
                    )
                );

                EntityDetailDto detail = new EntityDetailDto(
                    new GraphNodeDto(
                        node.get("id").asString(),
                        EntityKind.valueOf(node.get("kind").asString()),
                        node.get("display_name").asString(),
                        aliases,
                        entityRecord.get("sanctioned").asBoolean(),
                        entityRecord.get("datasetIds")
                            .asList(value -> value.asString())
                    ),
                    normalizedName,
                    node.get("dates_of_birth").isNull()
                        ? List.of()
                        : node.get("dates_of_birth")
                            .asList(value -> value.asString()),
                    node.get("nationalities").isNull()
                        ? List.of()
                        : node.get("nationalities")
                            .asList(value -> value.asString()),
                    node.get("jurisdiction").asString(null),
                    node.get("registration_number").asString(null),
                    node.get("imo").asString(null),
                    node.get("flag").asString(null),
                    programs,
                    sourceRecords,
                    matches
                );

                return Optional.of(detail);
            });
        }
    }

    public GraphSliceDto neighborhood(
        String rawId,
        Integer rawDepth,
        Integer rawNodeLimit,
        Integer rawEdgeLimit
    ) {
        String id = QueryInputs.id("id", rawId);
        QueryInputs.depth(rawDepth);
        int nodeLimit = QueryInputs.boundedLimit(
            "nodeLimit",
            rawNodeLimit,
            DEFAULT_NODE_LIMIT,
            MAX_NODE_LIMIT
        );
        int edgeLimit = QueryInputs.boundedLimit(
            "edgeLimit",
            rawEdgeLimit,
            DEFAULT_EDGE_LIMIT,
            MAX_EDGE_LIMIT
        );

        String querySelectNeighboringNodes = """
            MATCH
                (start:Entity {id: $id})
                -[:%s]-
                (neighbor:Entity)
            WITH DISTINCT neighbor
            ORDER BY neighbor.id
            LIMIT $neighborFetchLimit

            OPTIONAL MATCH (record:SourceRecord)-[:DESCRIBES]->(neighbor)

            RETURN neighbor,
                collect(DISTINCT record.dataset_id) AS datasetIds,
                count(
                    CASE
                        WHEN coalesce(record.active, false)
                        THEN 1
                    END
                ) > 0 AS sanctioned
            ORDER BY neighbor.id
        """.formatted(ANALYST_RELATIONSHIP_PATTERN);

        String querySelectEdges = """
            MATCH
                (start:Entity {id: $id})
                -[relationship:%s]-
                (neighbor:Entity)
            WHERE neighbor.id IN $neighborIds
            RETURN relationship,
                startNode(relationship).id AS sourceId,
                endNode(relationship).id AS targetId
            ORDER BY sourceId, type(relationship), targetId
            LIMIT $edgeFetchLimit
        """.formatted(ANALYST_RELATIONSHIP_PATTERN);

        try (var session = driver.session()) {
            return session.executeRead(transaction -> {
                Result startResult = transaction.run(
                    ENTITY_QUERY,
                    Values.parameters("id", id)
                );

                if (!startResult.hasNext()) {
                    return new GraphSliceDto(List.of(), List.of(), false);
                }

                var startRecord = startResult.single();
                Node start = startRecord.get("entity").asNode();
                GraphNodeDto startNode = new GraphNodeDto(
                    start.get("id").asString(),
                    EntityKind.valueOf(start.get("kind").asString()),
                    start.get("display_name").asString(),
                    start.get("aliases").isNull()
                        ? List.of()
                        : start.get("aliases")
                            .asList(value -> value.asString()),
                    startRecord.get("sanctioned").asBoolean(),
                    startRecord.get("datasetIds")
                        .asList(value -> value.asString())
                );

                int neighborLimit = nodeLimit - 1;
                List<GraphNodeDto> neighborCandidates = transaction.run(
                    querySelectNeighboringNodes,
                    Values.parameters(
                        "id", id,
                        "neighborFetchLimit", neighborLimit + 1
                    )
                ).list(record -> {
                    Node neighbor = record.get("neighbor").asNode();

                    List<String> dataset = record.get("datasetIds").isNull()
                        ? List.of()
                        : record.get("datasetIds").asList(value -> value.asString());
                    boolean sanctioned = record.get("sanctioned").asBoolean();

                    return new GraphNodeDto(
                        neighbor.get("id").asString(),
                        EntityKind.valueOf(neighbor.get("kind").asString()),
                        neighbor.get("display_name").asString(),
                        neighbor.get("aliases").isNull()
                            ? List.of()
                            : neighbor.get("aliases").asList(value -> value.asString()),
                        sanctioned,
                        dataset
                    );
                });

                boolean nodesTruncated =
                    neighborCandidates.size() > neighborLimit;
                List<GraphNodeDto> neighbors = neighborCandidates.subList(
                    0,
                    Math.min(neighborLimit, neighborCandidates.size())
                );

                List<GraphNodeDto> nodes = new ArrayList<>(nodeLimit);
                nodes.add(startNode);
                nodes.addAll(neighbors);

                List<String> neighborIds = neighbors.stream()
                    .map(GraphNodeDto::id)
                    .toList();

                List<GraphEdgeDto> edgeCandidates = transaction.run(
                    querySelectEdges,
                    Values.parameters(
                        "id", id,
                        "neighborIds", neighborIds,
                        "edgeFetchLimit", edgeLimit + 1
                    )
                ).list(record -> {
                    Relationship relationship = record.get("relationship")
                        .asRelationship();

                    String sourceId = record.get("sourceId").asString();
                    String targetId = record.get("targetId").asString();
                    String type = relationship.type();

                    Double confidence = null;
                    if (relationship.containsKey("confidence")) {
                        confidence = relationship.get("confidence").asDouble();
                    } else if (relationship.containsKey("score")) {
                        confidence = relationship.get("score").asDouble();
                    }

                    String reviewStatus = relationship.containsKey("review_status")
                        ? relationship.get("review_status").asString()
                        : null;

                    return new GraphEdgeDto(
                        StableEdgeIds.from(sourceId, type, targetId),
                        sourceId,
                        targetId,
                        type,
                        type,
                        confidence,
                        reviewStatus
                    );
                });

                boolean edgesTruncated = edgeCandidates.size() > edgeLimit;
                List<GraphEdgeDto> edges = edgeCandidates.subList(
                    0,
                    Math.min(edgeLimit, edgeCandidates.size())
                );

                return new GraphSliceDto(
                    nodes,
                    edges,
                    nodesTruncated || edgesTruncated
                );
            });
        }
    }

    public Optional<GraphSliceDto> shortestPath(
        String rawFromId,
        String rawToId,
        Integer rawMaxHops
    ) {
        String fromId = QueryInputs.id("fromId", rawFromId);
        String toId = QueryInputs.id("toId", rawToId);
        int maxHops = QueryInputs.maxHops(rawMaxHops);

        String queryShortestPath = """
            MATCH path = shortestPath(
                (from:Entity {id: $fromId})
                -[:%s*1..%d]-
                (to:Entity {id: $toId})
            )

            WITH path, nodes(path) AS pathNodes
            UNWIND range(0, size(pathNodes) - 1) AS position

            WITH path, position, pathNodes[position] AS node
            OPTIONAL MATCH (record:SourceRecord)-[:DESCRIBES]->(node)

            WITH path,
                position,
                node,
                collect(DISTINCT record.dataset_id) AS datasetIds,
                count(
                    CASE
                        WHEN coalesce(record.active, false)
                        THEN 1
                    END
                ) > 0 AS sanctioned
            ORDER BY position

            WITH path, collect({
                node: node,
                datasetIds: datasetIds,
                sanctioned: sanctioned
            }) AS nodeResults

            RETURN nodeResults AS nodes,
                [
                    relationship IN relationships(path) |
                    {
                        relationship: relationship,
                        sourceId: startNode(relationship).id,
                        targetId: endNode(relationship).id
                    }
                ] AS relationships
        """.formatted(
            ANALYST_RELATIONSHIP_PATTERN,
            maxHops
        );
        
        try (var session = driver.session()) {
            return session.executeRead(transaction -> {
                if (fromId.equals(toId)) {
                    Result result = transaction.run(
                        ENTITY_QUERY,
                        Values.parameters("id", fromId)
                    );

                    if (!result.hasNext()) {
                        return Optional.empty();
                    }

                    var record = result.single();
                    Node node = record.get("entity").asNode();

                    GraphNodeDto graphNode = new GraphNodeDto(
                        node.get("id").asString(),
                        EntityKind.valueOf(node.get("kind").asString()),
                        node.get("display_name").asString(),
                        node.get("aliases").isNull()
                            ? List.of()
                            : node.get("aliases")
                                .asList(value -> value.asString()),
                        record.get("sanctioned").asBoolean(),
                        record.get("datasetIds")
                            .asList(value -> value.asString())
                    );

                    return Optional.of(
                        new GraphSliceDto(
                            List.of(graphNode),
                            List.of(),
                            false
                        )
                    );
                }

                Result result = transaction.run(
                    queryShortestPath,
                    Values.parameters(
                        "fromId", fromId,
                        "toId", toId
                    )
                );

                if (!result.hasNext()) {
                    return Optional.empty();
                }

                var record = result.single();

                List<GraphNodeDto> nodes = record.get("nodes")
                    .asList(nodeResult -> {
                        Node node = nodeResult.get("node").asNode();
                        List<String> datasetIds =
                            nodeResult.get("datasetIds").isNull()
                            ? List.of()
                            : nodeResult.get("datasetIds")
                                .asList(value -> value.asString());

                        return new GraphNodeDto(
                            node.get("id").asString(),
                            EntityKind.valueOf(node.get("kind").asString()),
                            node.get("display_name").asString(),
                            node.get("aliases").isNull()
                                ? List.of()
                                : node.get("aliases").asList(value -> value.asString()),
                            nodeResult.get("sanctioned").asBoolean(),
                            datasetIds
                        );
                    });

                List<GraphEdgeDto> edges = record.get("relationships")
                    .asList(edgeResult -> {
                        Relationship relationship = edgeResult
                            .get("relationship")
                            .asRelationship();
                        String sourceId = edgeResult.get("sourceId").asString();
                        String targetId = edgeResult.get("targetId").asString();
                        String type = relationship.type();

                        Double confidence = null;

                        if (relationship.containsKey("confidence")) {
                            confidence = relationship.get("confidence").asDouble();
                        } else if (relationship.containsKey("score")) {
                            confidence = relationship.get("score").asDouble();
                        }

                        String reviewStatus =
                            relationship.containsKey("review_status")
                                ? relationship.get("review_status").asString()
                                : null;

                        return new GraphEdgeDto(
                            StableEdgeIds.from(sourceId, type, targetId),
                            sourceId,
                            targetId,
                            type,
                            type,
                            confidence,
                            reviewStatus
                        );
                    });

                return Optional.of(
                    new GraphSliceDto(
                        nodes,
                        edges,
                        false
                    )
                );
            });
        }
    }
}
