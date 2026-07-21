package io.nexus.api.node;

import java.util.List;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Person")
public class Person {
    @Id
    private String id;

    protected Person() {
    }

    public Person(String id) {
        this.id = id;
    }

    public String getId() {
        return id;
    }
}
