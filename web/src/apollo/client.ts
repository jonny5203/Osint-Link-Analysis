import {
  ApolloClient,
  HttpLink,
  InMemoryCache,
  gql,
  type NormalizedCacheObject,
  type TypedDocumentNode,
} from "@apollo/client";

type AuthProbeResult = {
  __typename: "Query";
};

export const AUTH_PROBE: TypedDocumentNode<
  AuthProbeResult,
  Record<string, never>
> = gql`
  query AuthProbe {
    __typename
  }
`;

export function createApolloClient(
  authorization: string,
  fetchImpl: typeof fetch = globalThis.fetch,
): ApolloClient<NormalizedCacheObject> {
  return new ApolloClient({
    link: new HttpLink({
      uri: "/graphql",
      headers: { authorization },
      fetch: fetchImpl,
    }),
    cache: new InMemoryCache(),
  });
}

export async function validateCredentials(
  client: ApolloClient<NormalizedCacheObject>,
): Promise<void> {
  await client.query({
    query: AUTH_PROBE,
    fetchPolicy: "no-cache",
  });
}
