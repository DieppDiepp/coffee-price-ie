import { BrowserRouter, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import CoffeeChartPage from "./pages/CoffeeChartPage";
import CoffeeSearchPage from "./pages/CoffeeSearchPage";
import PaperChartPage from "./pages/PaperChartPage";
import ModelPage from "./pages/ModelPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/charts" element={<CoffeeChartPage />} />
        <Route path="/search" element={<CoffeeSearchPage />} />
        <Route path="/paperChart" element={<PaperChartPage />} />
        <Route path="/model" element={<ModelPage />} />
      </Routes>
    </BrowserRouter>
  );
}
