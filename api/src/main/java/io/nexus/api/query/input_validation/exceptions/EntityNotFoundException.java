package io.nexus.api.query.input_validation.exceptions;

public final class EntityNotFoundException extends RuntimeException{
    public EntityNotFoundException(String id) {
        super("Entity not found: " + id);
    }    
}
