package io.nexus.api.investigation;

import java.util.List;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

import io.nexus.api.node.relationships.IncludesRelationship;

/** Investigation node (PLAN.md §3, T8.2). Mapping depends on design decision D2. */
@Node("Investigation")
public class Investigation {
    @Id private String id;
    private String title;
    private String owner;

    @Property("created_at")
    private String createdAt;

    @Property("updated_at")
    private String updatedAt;

    @Relationship(
        type = "INCLUDES",
        direction = Relationship.Direction.OUTGOING
    )

    private List<IncludesRelationship> includes;
}
