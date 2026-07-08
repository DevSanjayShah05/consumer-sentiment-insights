import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./styles/components.css";
import { Layout } from "./components/Layout";
import { Explorer } from "./pages/Explorer";
import { RestaurantDetail } from "./pages/RestaurantDetail";
import { Compare } from "./pages/Compare";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Explorer />} />
          <Route path="/restaurant/:id" element={<RestaurantDetail />} />
          <Route path="/compare" element={<Compare />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
