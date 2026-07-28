package io.nexus.api.query.exceptions;

import org.springframework.graphql.execution.DataFetcherExceptionResolverAdapter;
import org.springframework.graphql.execution.ErrorType;
import org.springframework.stereotype.Component;

import graphql.GraphQLError;
import graphql.GraphqlErrorBuilder;
import graphql.schema.DataFetchingEnvironment;
import io.nexus.api.query.input_validation.exceptions.ApiInputException;

@Component
public class GraphQLExceptionResolver extends DataFetcherExceptionResolverAdapter{
    
    @Override
    protected GraphQLError resolveToSingleError(
        Throwable exception,
        DataFetchingEnvironment environment
    ) {
        if (exception instanceof ApiInputException) {
            return GraphqlErrorBuilder.newError(environment)
                .errorType(ErrorType.BAD_REQUEST)
                .message(exception.getMessage())
                .build();
        }

        return null;
    }
}
