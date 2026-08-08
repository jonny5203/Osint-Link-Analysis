import { ApolloError } from "@apollo/client";

export type Credentials = Readonly<{
  username: string;
  password: string;
}>;

export type SignInFailure =
  | "invalid-input"
  | "invalid-credentials"
  | "service-unavailable";

export const SIGN_IN_FAILURE_MESSAGES: Record<SignInFailure, string> = {
  "invalid-input": "Enter a valid username and password.",
  "invalid-credentials": "The username or password is incorrect.",
  "service-unavailable": "The local API is unavailable. Try again when it is running.",
};

export class CredentialInputError extends Error {
  constructor() {
    super("Invalid credential input");
    this.name = "CredentialInputError";
  }
}

export function createBasicAuthorization(credentials: Credentials): string {
  if (
    credentials.username.trim() === "" ||
    credentials.username.includes(":")
  ) {
    throw new CredentialInputError();
  }

  if (credentials.password.trim() === "") {
    throw new CredentialInputError();
  }

  const bytes = new TextEncoder().encode(
    `${credentials.username}:${credentials.password}`,
  );
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join("");
  return `Basic ${btoa(binary)}`;
}

export function classifySignInFailure(error: unknown): SignInFailure {
  if (error instanceof CredentialInputError) {
    return "invalid-input";
  }

  if (error instanceof ApolloError) {
    const networkError = error.networkError;

    if (
      networkError !== null &&
      "statusCode" in networkError &&
      networkError.statusCode === 401
    ) {
      return "invalid-credentials";
    }
  }

  return "service-unavailable";
}
