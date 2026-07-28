package io.nexus.api.schema;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.junit.jupiter.api.Test;
import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.Driver;
import org.neo4j.driver.GraphDatabase;
import org.neo4j.driver.Record;
import org.neo4j.driver.Session;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.neo4j.Neo4jContainer;
import org.testcontainers.utility.DockerImageName;

import io.nexus.api.query.dto.EntityDetailDto;
import io.nexus.api.query.input_validation.exceptions.ApiInputException;
import io.nexus.api.query.dto.GraphEdgeDto;
import io.nexus.api.query.dto.GraphSliceDto;
import io.nexus.api.query.input_validation.GraphQueryService;

@Testcontainers
class GraphContractIntegrationTest {
    private static final String NEO4J_IMAGE = "neo4j:5.26.28-community@" +
            "sha256:20779498e70e05772836fb980449bf691f519b42d87372e3f499312cb32c5430";

    private static final String NEO4J_PASSWORD = "test-only-password";

    private static final List<String> INVARIANT_RESOURCES = List.of(
            "/invariants/01_typed_entities_have_entity.cypher",
            "/invariants/02_source_record_has_one_dataset.cypher",
            "/invariants/03_active_record_has_one_entity.cypher",
            "/invariants/04_successful_run_metadata.cypher",
            "/invariants/05_source_entities_are_preserved.cypher",
            "/invariants/06_identity_links_are_canonical.cypher",
            "/invariants/07_investigation_include_only_entities.cypher",
            "/invariants/08_public_facts_have_evidence.cypher");

    @Container
    private static final Neo4jContainer NEO4J = new Neo4jContainer(
            DockerImageName.parse(NEO4J_IMAGE)
                    .asCompatibleSubstituteFor("neo4j"))
            .withAdminPassword(NEO4J_PASSWORD);

    @Test
    void schemaAndFixtureAreRepeatable() throws IOException {
        try (
                Driver driver = GraphDatabase.driver(
                        NEO4J.getBoltUrl(),
                        AuthTokens.basic("neo4j", NEO4J_PASSWORD));
                Session session = driver.session()) {
            driver.verifyConnectivity();

            runScript(session, "/schema.cypher");
            runScript(session, "/schema.cypher");

            session.run("CALL db.awaitIndexes(60)").consume();

            assertConstraintNames(session);
            assertIndexDefinitions(session);

            runScript(session, "/fixtures/demo/fixture.cypher");
            runScript(session, "/fixtures/demo/fixture.cypher");

            assertGraphCounts(session);
            assertInvariants(session);
            assertAveryFullTextSearch(session);
            assertAveryToAuroraPath(session);
            assertAveryNeighborhood(driver, session);
            assertPhaseThreeQueries(driver, session);
        }
    }

    private static void assertConstraintNames(Session session) {
        List<String> names = session.run("""
                SHOW CONSTRAINTS
                YIELD name
                RETURN name
                ORDER BY name
                """)
                .list(record -> record.get("name").asString());

        assertThat(names).containsExactlyInAnyOrder(
                "entity_id",
                "dataset_id",
                "import_run_id",
                "source_record_id",
                "investigation_id");
    }

    private static void assertIndexDefinitions(Session session) {
        List<String> expectedNames = List.of(
                "entity_name_search",
                "source_record_external_id",
                "vessel_imo");

        List<Record> indexes = session.run(
                """
                        SHOW INDEXES
                        YIELD name, type, state
                        WHERE name IN $names
                        RETURN name, type, state
                        """,
                Map.of("names", expectedNames)).list();

        assertThat(indexes).hasSize(3);
        assertThat(indexes).allSatisfy(index -> assertThat(index.get("state").asString())
                .as("state of index %s", index.get("name").asString())
                .isEqualTo("ONLINE"));

        Map<String, String> typesByName = indexes.stream()
                .collect(Collectors.toMap(
                        index -> index.get("name").asString(),
                        index -> index.get("type").asString()));

        assertThat(typesByName)
                .hasSize(3)
                .containsEntry("entity_name_search", "FULLTEXT")
                .containsEntry("source_record_external_id", "RANGE")
                .containsEntry("vessel_imo", "RANGE");
    }

    private static void assertGraphCounts(Session session) {
        long nodes = session.run("""
                MATCH (node)
                RETURN count(node) AS count
                """)
                .single()
                .get("count")
                .asLong();

        long relationships = session.run("""
                MATCH ()-[relationship]->()
                RETURN count(relationship) AS count
                """)
                .single()
                .get("count")
                .asLong();

        assertThat(nodes).isEqualTo(17L);
        assertThat(relationships).isEqualTo(21L);
    }

    private static void assertInvariants(Session session) throws IOException {
        for (String resource : INVARIANT_RESOURCES) {
            List<String> statements = readStatements(resource);

            assertThat(statements)
                    .as("%s must contain exactly one Cypher statement", resource)
                    .hasSize(1);

            long violations = session.run(statements.get(0))
                    .single()
                    .get("violations")
                    .asLong();

            assertThat(violations)
                    .as("violations returned by %s", resource)
                    .isZero();
        }
    }

    private static void assertAveryFullTextSearch(Session session) {
        List<String> entityIds = session.run("""
                CALL db.index.fulltext.queryNodes(
                    "entity_name_search",
                    "Avery"
                )
                YIELD node
                RETURN node.id AS id
                ORDER BY id
                """)
                .list(record -> record.get("id").asString());

        assertThat(entityIds).containsExactly(
                "fixture:entity:avery",
                "fixture:entity:avery-variant");
    }

    private static void assertAveryToAuroraPath(Session session) {
        List<List<String>> paths = session.run("""
                MATCH path =
                    (:Person {id: "fixture:entity:avery"})
                    -[:OWNS|CONTROLS*1..4]->
                    (:Vessel {id: "fixture:entity:aurora-tide"})
                RETURN [
                    relationship IN relationships(path) |
                    type(relationship)
                ] AS relationship_types
                """)
                .list(record -> record.get("relationship_types")
                        .asList(value -> value.asString()));

        assertThat(paths).containsExactly(
                List.of("OWNS", "CONTROLS", "OWNS"));
    }

    private static void assertAveryNeighborhood(
            Driver driver,
            Session session) {
        session.run("""
                MATCH (avery:Entity {id: "fixture:entity:avery"})
                MATCH (variant:Entity {id: "fixture:entity:avery-variant"})
                MERGE (avery)-[:INTERNAL_TEST]->(variant)
                """).consume();

        try {
            GraphQueryService service = new GraphQueryService(driver);

            GraphSliceDto complete = service.neighborhood(
                    "fixture:entity:avery",
                    1,
                    100,
                    200);

            assertThat(complete.nodes())
                    .extracting(node -> node.id())
                    .containsExactly(
                            "fixture:entity:avery",
                            "fixture:address:avery:0",
                            "fixture:entity:northstar");
            assertThat(complete.edges())
                    .extracting(GraphEdgeDto::type)
                    .containsExactly("LOCATED_AT", "OWNS");
            assertThat(complete.truncated()).isFalse();
            assertAllEdgeEndpointsArePresent(complete);

            GraphSliceDto nodeLimited = service.neighborhood(
                    "fixture:entity:avery",
                    1,
                    2,
                    200);

            assertThat(nodeLimited.nodes())
                    .extracting(node -> node.id())
                    .containsExactly(
                            "fixture:entity:avery",
                            "fixture:address:avery:0");
            assertThat(nodeLimited.edges())
                    .extracting(GraphEdgeDto::type)
                    .containsExactly("LOCATED_AT");
            assertThat(nodeLimited.truncated()).isTrue();
            assertAllEdgeEndpointsArePresent(nodeLimited);

            GraphSliceDto edgeLimited = service.neighborhood(
                    "fixture:entity:avery",
                    1,
                    100,
                    1);

            assertThat(edgeLimited.edges()).hasSize(1);
            assertThat(edgeLimited.truncated()).isTrue();
            assertAllEdgeEndpointsArePresent(edgeLimited);
        } finally {
            session.run("""
                    MATCH
                        (:Entity {id: "fixture:entity:avery"})
                        -[relationship:INTERNAL_TEST]-
                        (:Entity {id: "fixture:entity:avery-variant"})
                    DELETE relationship
                    """).consume();
        }
    }

    private static void assertAllEdgeEndpointsArePresent(
            GraphSliceDto slice) {
        List<String> nodeIds = slice.nodes().stream()
                .map(node -> node.id())
                .toList();

        assertThat(slice.edges()).allSatisfy(edge -> {
            assertThat(nodeIds).contains(edge.sourceId());
            assertThat(nodeIds).contains(edge.targetId());
        });
    }

    private static void runScript(
            Session session,
            String resource) throws IOException {
        for (String statement : readStatements(resource)) {
            session.run(statement).consume();
        }
    }

    private static List<String> readStatements(
            String resource) throws IOException {
        return Arrays.stream(readResource(resource).split(";"))
                .map(String::trim)
                .filter(GraphContractIntegrationTest::hasCypherContent)
                .toList();
    }

    private static boolean hasCypherContent(String statement) {
        return statement.lines()
                .map(String::trim)
                .anyMatch(line -> !line.isBlank() && !line.startsWith("//"));
    }

    private static String readResource(String resource) throws IOException {
        try (
                InputStream input = GraphContractIntegrationTest.class.getResourceAsStream(resource)) {
            if (input == null) {
                throw new IllegalArgumentException(
                        "Classpath resource not found: " + resource);
            }

            return new String(
                    input.readAllBytes(),
                    StandardCharsets.UTF_8);
        }
    }

    private static void assertPhaseThreeQueries(
            Driver driver,
            Session session) {
        GraphQueryService service = new GraphQueryService(driver);

        assertThat(service.search("Avery", 5))
                .extracting(hit -> hit.node().id())
                .containsExactlyInAnyOrder(
                        "fixture:entity:avery",
                        "fixture:entity:avery-variant");

        session.run("""
                MATCH (record:SourceRecord {
                    id: "fixture:record:alpha:avery"
                })
                SET record.programs = ["FIXTURE-PROGRAM"]
                """).consume();

        try {
            EntityDetailDto detail = service
                    .entity("fixture:entity:avery")
                    .orElseThrow();

            assertThat(detail.node().displayName())
                    .isEqualTo("Avery Stone");

            assertThat(detail.programs())
                    .containsExactly("FIXTURE-PROGRAM");

            assertThat(detail.sourceRecords())
                    .singleElement()
                    .satisfies(source -> {
                        assertThat(source.datasetName())
                                .isEqualTo("Fictional Dataset Alpha");
                        assertThat(source.externalId())
                                .isEqualTo("avery-001");
                        assertThat(source.recordHash())
                                .hasSize(64);
                    });
        } finally {
            session.run("""
                    MATCH (record:SourceRecord {
                        id: "fixture:record:alpha:avery"
                    })
                    REMOVE record.programs
                    """).consume();
        }

        GraphSliceDto path = service.shortestPath(
                "fixture:entity:avery",
                "fixture:entity:aurora-tide",
                4).orElseThrow();

        assertThat(path.nodes())
                .extracting(node -> node.id())
                .containsExactly(
                        "fixture:entity:avery",
                        "fixture:entity:northstar",
                        "fixture:entity:blue-harbor",
                        "fixture:entity:aurora-tide");

        assertThat(path.edges())
                .extracting(GraphEdgeDto::type)
                .containsExactly("OWNS", "CONTROLS", "OWNS");

        assertAllEdgeEndpointsArePresent(path);

        assertThat(
                service.shortestPath(
                        "fixture:entity:avery",
                        "fixture:entity:avery-variant",
                        4))
                .isEmpty();

        assertThatThrownBy(() -> service.shortestPath(
                "fixture:entity:avery",
                "fixture:entity:aurora-tide",
                100))
                .isInstanceOf(ApiInputException.class)
                .hasMessage("maxHops must be between 1 and 6");
    }
}
