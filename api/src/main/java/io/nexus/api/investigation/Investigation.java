package io.nexus.api.investigation;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

/** Investigation node (PLAN.md §3, T8.2). Mapping depends on design decision D2. */
@Node("Investigation")
public class Investigation {
    @Id private String id;
    // TODO(T8.2): id, title, owner, created_at, updated_at
    //             D2-a (in-graph): @Relationship("INCLUDES") -> entities with {annotation, x, y}
    //             D2-b (Postgres): switch to a JPA @Entity + spring-boot-starter-data-jpa
}
