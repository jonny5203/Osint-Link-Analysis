package io.nexus.api.query.input_validation;

import java.util.Set;

import io.nexus.api.query.input_validation.exceptions.ApiInputException;

final class QueryInputs {
    private static final Set<Character> LUCENE_SPECIAL = Set.of(
        '+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^',
        '"', '~', '*', '?', ':', '\\', '/'
    );

    private QueryInputs() {}

    static String searchTerm(String value) {
        String term = value == null ? "" : value.trim();
        if (term.length() < 2 || term.length() > 100) {
            throw new ApiInputException(
                "term must contain between 2 and 100 characters after trimming"
            );
        }
        return term;
    }

    static String luceneLiteral(String term) {
        StringBuilder escaped = new StringBuilder(term.length());
        for (char character : term.toCharArray()) {
            if (LUCENE_SPECIAL.contains(character)){
                escaped.append('\\');
            }
            
            escaped.append(character);
        }
        
        return escaped.toString();
    }

    static int searchLimit(Integer value) {
        int limit = value == null ? 20 : value;
        return Math.clamp(limit, 1, 50);
    }

    static void depth(Integer value){
        int depth = value == null ? 1 : value;
        if (depth != 1) {
            throw new ApiInputException("depth must be 1 in Nexus v1");
        }
    }

    static int boundedLimit(
        String name,
        Integer value,
        int defaultValue,
        int maximum
    ) {
        int limit = value == null ? defaultValue : value;
        if(limit < 1 || limit > maximum) {
            throw new ApiInputException(
                name + " must be between 1 and " + maximum
            );
        }
        return limit;
    }

    static int maxHops(Integer value) {
        int hops = value == null ? 6 : value;
        if (hops < 1 || hops > 6) {
            throw new ApiInputException("maxHops must be between 1 and 6");
        }
        return hops;
    }

    static String id(String name, String value) {
        String id = value == null ? "" : value.trim();
        if (id.isEmpty() || id.length() > 512) {
            throw new ApiInputException(
                name + " must be a non-blank ID of at most 512 characters long"
            );
        }
        return id;
    }
}
