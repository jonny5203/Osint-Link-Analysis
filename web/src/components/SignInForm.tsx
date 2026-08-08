import { useState, type FormEvent } from "react";

import type { Credentials } from "../auth/credentials";

type SignInFormProps = {
  errorMessage: string | null;
  pending: boolean;
  onSubmit: (credentials: Credentials) => Promise<void>;
};

export function SignInForm({
  errorMessage,
  pending,
  onSubmit,
}: SignInFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSubmit({ username, password });
    setPassword("");
  }

  return (
    <main className="sign-in-page">
      <form className="sign-in-card" onSubmit={handleSubmit}>
        <p className="eyebrow">Nexus local demo</p>
        <h1>Sign in to the graph explorer</h1>
        <p>
          Credentials stay in this browser tab&apos;s memory. Refreshing the page
          signs you out.
        </p>

        <label htmlFor="username">Username</label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          disabled={pending}
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          disabled={pending}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {errorMessage ? <p role="alert">{errorMessage}</p> : null}

        <button type="submit" disabled={pending}>
          {pending ? "Signing in…" : "Sign in"}
        </button>

        <p className="demo-warning">
          Local demo only. Do not expose HTTP Basic credentials over an
          untrusted network.
        </p>
      </form>
    </main>
  );
}
