import { describe, expectTypeOf, it } from "vitest";

import {
  ENTITY,
  NEIGHBORHOOD,
  SEARCH,
  SHORTEST_PATH,
  type EntityDetail,
  type EntityResult,
  type EntityVariables,
  type GraphEdge,
  type GraphSlice,
  type NeighborhoodResult,
  type NeighborhoodVariables,
  type SearchResult,
  type SearchVariables,
  type ShortestPathResult,
  type ShortestPathVariables,
} from "./queries";
import type { TypedDocumentNode } from "@apollo/client";

describe("typed GraphQL documents", () => {
  it("carries result and variable types for every Phase 4 query", () => {
    expectTypeOf(SEARCH).toMatchTypeOf<
      TypedDocumentNode<SearchResult, SearchVariables>
    >();
    expectTypeOf(ENTITY).toMatchTypeOf<
      TypedDocumentNode<EntityResult, EntityVariables>
    >();
    expectTypeOf(NEIGHBORHOOD).toMatchTypeOf<
      TypedDocumentNode<NeighborhoodResult, NeighborhoodVariables>
    >();
    expectTypeOf(SHORTEST_PATH).toMatchTypeOf<
      TypedDocumentNode<ShortestPathResult, ShortestPathVariables>
    >();
  });

  it("preserves the nullable fields required by the server schema", () => {
    expectTypeOf<EntityResult["entity"]>().toEqualTypeOf<
      EntityDetail | null
    >();
    expectTypeOf<ShortestPathResult["shortestPath"]>().toEqualTypeOf<
      GraphSlice | null
    >();
    expectTypeOf<GraphEdge["confidence"]>().toEqualTypeOf<number | null>();
    expectTypeOf<GraphEdge["reviewStatus"]>().toEqualTypeOf<string | null>();
  });
});
