package io.nexus.api.node;

import java.util.List;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Vessel")
public class Vessel {
    @Id
    private String id;

    protected Vessel(){

    }

    public Vessel(String id){
        this.id = id;
    }

    public String getId(){
        return id;
    }
}
