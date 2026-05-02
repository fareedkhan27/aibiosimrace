import RacePanel from "./components/Race/RacePanel.jsx";

const ACCESS_KEY = import.meta.env.VITE_ACCESS_KEY || "";

export default function App() {
  return (
    <div style={{ maxWidth: 1024, margin: "0 auto", padding: "0 1.5rem" }}>
      <RacePanel accessKey={ACCESS_KEY} />
    </div>
  );
}
