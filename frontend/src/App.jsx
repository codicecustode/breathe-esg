import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Review from "./pages/Review";
import styles from "./App.module.css";

export default function App() {
  return (
    <div className={styles.shell}>
      <nav className={styles.nav}>
        <span className={styles.logo}>Breathe ESG</span>
        <NavLink to="/" end className={({ isActive }) => isActive ? styles.active : ""}>Dashboard</NavLink>
        <NavLink to="/upload" className={({ isActive }) => isActive ? styles.active : ""}>Upload</NavLink>
        <NavLink to="/review" className={({ isActive }) => isActive ? styles.active : ""}>Review</NavLink>
      </nav>
      <main className={styles.main}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/review" element={<Review />} />
        </Routes>
      </main>
    </div>
  );
}
