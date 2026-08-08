import {
  ApolloProvider,
  type ApolloClient,
  type NormalizedCacheObject,
} from "@apollo/client";
import { useState } from "react";

import {
  classifySignInFailure,
  createBasicAuthorization,
  SIGN_IN_FAILURE_MESSAGES,
  type Credentials,
  type SignInFailure,
} from "./auth/credentials";
import {
  createApolloClient,
  validateCredentials,
} from "./apollo/client";
import { ExplorerWorkspace } from "./components/ExplorerWorkspace";
import { SignInForm } from "./components/SignInForm";

type Session = {
  client: ApolloClient<NormalizedCacheObject>;
  username: string;
};

type AppProps = {
  authorizationFactory?: typeof createBasicAuthorization;
  clientFactory?: typeof createApolloClient;
  credentialValidator?: typeof validateCredentials;
};

export default function App({
  authorizationFactory = createBasicAuthorization,
  clientFactory = createApolloClient,
  credentialValidator = validateCredentials,
}: AppProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<SignInFailure | null>(null);

  async function handleSignIn(credentials: Credentials) {
    setPending(true);
    setFailure(null);

    let candidate: ApolloClient<NormalizedCacheObject> | null = null;

    try {
      const authorization = authorizationFactory(credentials);
      candidate = clientFactory(authorization);
      await credentialValidator(candidate);
      setSession({ client: candidate, username: credentials.username });
    } catch (error) {
      candidate?.stop();
      setFailure(classifySignInFailure(error));
    } finally {
      setPending(false);
    }
  }

  function handleSignOut() {
    if (!session) {
      return;
    }

    const { client } = session;
    setSession(null);
    setFailure(null);
    void client
      .clearStore()
      .catch(() => undefined)
      .finally(() => client.stop());
  }

  if (!session) {
    return (
      <SignInForm
        errorMessage={failure ? SIGN_IN_FAILURE_MESSAGES[failure] : null}
        pending={pending}
        onSubmit={handleSignIn}
      />
    );
  }

  return (
    <ApolloProvider client={session.client}>
      <main className="explorer-shell">
        <header className="explorer-header">
          <div>
            <p className="eyebrow">Signed in as {session.username}</p>
            <h1>Nexus graph explorer</h1>
          </div>
          <button type="button" onClick={handleSignOut}>
            Sign out
          </button>
        </header>
        <ExplorerWorkspace />
      </main>
    </ApolloProvider>
  );
}
