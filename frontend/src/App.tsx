import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import JDPage from './pages/JDPage';
import EvaluationPage from './pages/EvaluationPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/jd/:jdId" element={<JDPage />} />
        <Route path="/evaluation/:evalId" element={<EvaluationPage />} />
      </Route>
    </Routes>
  );
}
