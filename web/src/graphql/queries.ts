import { gql, type TypedDocumentNode } from "@apollo/client";

// Templates must match the SDL in api/src/main/resources/graphql/schema.graphqls.

export type EntityKind = "PERSON" | "ORGANIZATION" | "VESSEL" | "ADDRESS";

export type GraphNode = {
  id: string;
  kind: EntityKind;
  displayName: string;
  aliases: string[];
  sanctioned: boolean;
  datasetIds: string[];
};

export type GraphEdge = {
  id: string;
  sourceId: string;
  targetId: string;
  type: string;
  label: string;
  confidence: number | null;
  reviewStatus: string | null;
};

export type GraphSlice = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
};

export type SourceRecordSummary = {
  id: string;
  datasetId: string;
  datasetName: string;
  externalId: string;
  retrievedAt: string | null;
  recordHash: string;
  active: boolean;
};

export type MatchExplanation = {
  edgeId: string;
  otherEntityId: string;
  type: string;
  score: number | null;
  reasons: string[];
  algorithmVersion: string | null;
  decidedAt: string | null;
  decisionSource: string | null;
  reviewStatus: string | null;
};

export type EntityDetail = {
  node: GraphNode;
  normalizedName: string | null;
  datesOfBirth: string[];
  nationalities: string[];
  jurisdiction: string | null;
  registrationNumber: string | null;
  imo: string | null;
  flag: string | null;
  programs: string[];
  sourceRecords: SourceRecordSummary[];
  matches: MatchExplanation[];
};

export type SearchResult = {
  searchEntities: Array<{ score: number; node: GraphNode }>;
};

export type SearchVariables = {
  term: string;
  limit?: number | null;
};

export type EntityResult = { entity: EntityDetail | null };
export type EntityVariables = { id: string };

export type NeighborhoodResult = { neighborhood: GraphSlice };
export type NeighborhoodVariables = {
  id: string;
  depth?: number | null;
  nodeLimit?: number | null;
  edgeLimit?: number | null;
};

export type ShortestPathResult = { shortestPath: GraphSlice | null };
export type ShortestPathVariables = {
  fromId: string;
  toId: string;
  maxHops?: number | null;
};

export const SEARCH: TypedDocumentNode<SearchResult, SearchVariables> = gql`
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

export const ENTITY: TypedDocumentNode<EntityResult, EntityVariables> = gql`
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

export const NEIGHBORHOOD: TypedDocumentNode<
  NeighborhoodResult,
  NeighborhoodVariables
> = gql`
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

export const SHORTEST_PATH: TypedDocumentNode<
  ShortestPathResult,
  ShortestPathVariables
> = gql`
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
