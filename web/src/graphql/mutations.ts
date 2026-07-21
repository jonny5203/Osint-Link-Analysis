import { gql } from "@apollo/client";

// Templates must match the SDL in api/src/main/resources/graphql/schema.graphqls.

export const CREATE_INVESTIGATION = gql`
  mutation CreateInvestigation($title: String!) {
    createInvestigation(title: $title) {
      id
      title
      createdAt
    }
  }
`;

export const ADD_ENTITY = gql`
  mutation AddEntity($investigationId: ID!, $entityId: ID!, $x: Float, $y: Float) {
    addEntity(investigationId: $investigationId, entityId: $entityId, x: $x, y: $y) {
      id
    }
  }
`;

export const ANNOTATE = gql`
  mutation Annotate($investigationId: ID!, $entityId: ID!, $annotation: String!) {
    annotate(investigationId: $investigationId, entityId: $entityId, annotation: $annotation) {
      id
    }
  }
`;

export const SAVE_LAYOUT = gql`
  mutation SaveLayout($investigationId: ID!, $layout: [LayoutItem!]!) {
    saveLayout(investigationId: $investigationId, layout: $layout) {
      id
    }
  }
`;
