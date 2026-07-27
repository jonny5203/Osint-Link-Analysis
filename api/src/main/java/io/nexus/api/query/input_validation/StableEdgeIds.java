package io.nexus.api.query.input_validation;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;

public class StableEdgeIds {
    private StableEdgeIds() {}

    static String from(
        String sourceId,
        String type,
        String targetId
    ){
        return from(sourceId, type, targetId, "");
    }

    static String from(
        String sourceId,
        String type,
        String targetId,
        String semanticQualifier
    ){
        String canonicalTuple = 
            "[" +
            jsonString(Objects.requireNonNull(type)) + "," +
            jsonString(Objects.requireNonNull(sourceId)) + "," +
            jsonString(Objects.requireNonNull(targetId)) + "," +
            jsonString(Objects.requireNonNull(semanticQualifier)) + 
            "]";
        
        try{
            byte[] hash = MessageDigest.getInstance("SHA-256")
                .digest(
                    canonicalTuple.getBytes(StandardCharsets.UTF_8)
                );
            return "edge:v1" + HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(
                "SHA-256 is unavailable",
                exception
            );
        }
    }

    private static String jsonString(String value){
        StringBuilder escaped = new StringBuilder(value.length() + 2);
        escaped.append('"');

        for (char character : value.toCharArray()){
            switch (character) {
                case '"' -> escaped.append("\\\"");
                case '\\' -> escaped.append("\\\\");
                case '\b' -> escaped.append("\\b");
                case '\f' -> escaped.append("\\f");
                case '\n' -> escaped.append("\\n");
                case '\r' -> escaped.append("\\r");
                case '\t' -> escaped.append("\\t");
                default -> {
                    if (character < 0x20) {
                        escaped.append(
                            String.format("\\u%04x", (int) character)
                        );
                    } else {
                        escaped.append(character);
                    }
                }
            }
        }

        escaped.append('"');
        return escaped.toString();
    }
}
