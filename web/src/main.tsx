import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// T9 wraps <App /> in <ApolloProvider>. For now, just mount the placeholder.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
