import { gql } from "@apollo/client";

// Templates must match the SDL in api/src/main/resources/graphql/schema.graphqls.

export const SEARCH = gql`
  query Search($term: String!, $limit: Int) {
    searchEntities(term: $term, limit: $limit) {
      score
      node {
        id
        kind
        displayName
        aliases
        sanctioned
        datasetIds
      }
    }
  }
`;

export const ENTITY = gql`
  query Entity($id: ID!) {
    entity(id: $id) {
      node {
        id
        kind
        displayName
        aliases
        sanctioned
        datasetIds
      }
      normalizedName
      datesOfBirth
      nationalities
      jurisdiction
      registrationNumber
      imo
      flag
      programs
      sourceRecords {
        id
        datasetId
        datasetName
        externalId
        retrievedAt
        recordHash
        active
      }
      matches {
        edgeId
        otherEntityId
        type
        score
        reasons
        algorithmVersion
        decidedAt
        decisionSource
        reviewStatus
      }
    }
  }
`;

export const NEIGHBORHOOD = gql`
  query Neighborhood(
    $id: ID!
    $depth: Int
    $nodeLimit: Int
    $edgeLimit: Int
  ) {
    neighborhood(
      id: $id
      depth: $depth
      nodeLimit: $nodeLimit
      edgeLimit: $edgeLimit
    ) {
      nodes {
        id
        kind
        displayName
        aliases
        sanctioned
        datasetIds
      }
      edges {
        id
        sourceId
        targetId
        type
        label
        confidence
        reviewStatus
      }
      truncated
    }
  }
`;

export const SHORTEST_PATH = gql`
  query ShortestPath(
    $fromId: ID!, 
    $toId: ID!, 
    $maxHops: Int
  ) {
    shortestPath(
      fromId: $fromId, 
      toId: $toId, 
      maxHops: $maxHops
    ) {
      nodes {
        id
        kind
        displayName
        aliases
        sanctioned
        datasetIds
      }
      edges {
        id
        sourceId
        targetId
        type
        label
        confidence
        reviewStatus
      }
      truncated
    }
  }
`;

