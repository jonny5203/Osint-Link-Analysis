import { gql } from "@apollo/client";

// Templates must match the SDL in api/src/main/resources/graphql/schema.graphqls.

export const SEARCH = gql`
  query Search($term: String!, $limit: Int) {
    search(term: $term, limit: $limit) {
      node {
        id
        name
        labels
      }
      score
    }
  }
`;

export const NEIGHBORS = gql`
  query Neighbors($id: ID!, $limit: Int) {
    neighbors(id: $id, limit: $limit) {
      id
      name
      labels
    }
  }
`;

export const SHORTEST_PATH = gql`
  query ShortestPath($fromId: ID!, $toId: ID!, $maxHops: Int) {
    shortestPath(fromId: $fromId, toId: $toId, maxHops: $maxHops) {
      nodes {
        id
        name
        labels
      }
      length
    }
  }
`;
