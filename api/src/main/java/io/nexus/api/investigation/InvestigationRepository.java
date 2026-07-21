package io.nexus.api.investigation;

import org.springframework.data.neo4j.repository.Neo4jRepository;

/** Investigation repository (PLAN.md T8.2). */
public interface InvestigationRepository extends Neo4jRepository<Investigation, String> {
}
