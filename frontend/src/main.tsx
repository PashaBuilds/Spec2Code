import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { maybeSeedDemo } from "./lib/demoSeed";

maybeSeedDemo();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
