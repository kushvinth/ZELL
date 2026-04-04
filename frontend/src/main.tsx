import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

const resolveInitialTheme = (): "light" | "dark" => {
  const stored = window.localStorage.getItem("zell-theme");
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

const initialTheme = resolveInitialTheme();
document.documentElement.classList.remove("light", "dark");
document.documentElement.classList.add(initialTheme);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
