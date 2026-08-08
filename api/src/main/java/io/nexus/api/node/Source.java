package io.nexus.api.node;

import java.util.List;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

import io.nexus.api.node.relationships.DatabaseRelationship;
import io.nexus.api.node.relationships.DescribesRelationship;
import io.nexus.api.node.relationships.ObservedRelationship;

@Node("Source")
public class Source {
    @Id private String id;
    private String list;
    private String url;
    @Property("retrieved_at")
    private String retrievedAt;

    @Relationship(
        type = "FROM_DATASET",
        direction = Relationship.Direction.OUTGOING
    )
    private List<DatabaseRelationship> dataset;

    @Relationship(
        type = "OBSERVED_IN",
        direction = Relationship.Direction.OUTGOING
    )
    private List<ObservedRelationship> observedIn;

    @Relationship(
        type = "DESCRIBES",
        direction = Relationship.Direction.OUTGOING
    )
    private List<DescribesRelationship> describes;
}
