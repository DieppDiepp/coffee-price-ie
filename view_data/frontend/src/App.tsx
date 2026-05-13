import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CoffeeChartPage from './pages/CoffeeChartPage'; // Import file mới
import CoffeeSearchPage from './pages/CoffeeSearchPage';
import PaperChartPage from './pages/PaperChartPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        {/* Thêm route cho trang biểu đồ */}
        <Route path="/charts" element={<CoffeeChartPage />} /> 
        <Route path="/search" element={<CoffeeSearchPage />} /> 
        <Route path="/paperChart" element={<PaperChartPage />} /> 
      </Routes>
    </BrowserRouter>
  );
}

export default App;