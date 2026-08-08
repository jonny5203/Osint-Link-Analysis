package io.nexus.api.investigation;

import org.springframework.data.neo4j.repository.Neo4jRepository;

public interface InvestigationRepository extends Neo4jRepository<Investigation, String> {
}
